"""Maintainable 2.0 inside Home Assistant — above all: upgrading from 1.4.0 breaks nothing."""

from __future__ import annotations

import datetime as dt

import pytest
from homeassistant.config_entries import SOURCE_USER, ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import issue_registry as ir
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_capture_events,
    async_fire_time_changed,
)

from custom_components.maintainable.const import DOMAIN

NOW = dt.datetime(2026, 9, 21, 12, 0, tzinfo=dt.timezone(dt.timedelta(hours=3)))
ENTRY_ID = "01HZX0TESTENTRY00000000000"
NAME = "HEPA-фильтр. Бризер: Кухня"
SLUG = "hepa_filtr_brizer_kukhnia"


@pytest.fixture(autouse=True)
async def moscow(hass: HomeAssistant, freezer):
    await hass.config.async_set_time_zone("Europe/Moscow")
    hass.config.language = "ru"
    freezer.move_to(NOW)


@pytest.fixture
def breather(hass: HomeAssistant) -> dr.DeviceEntry:
    """A device of another integration, like "Бризер" from xiaomi_miot."""
    other = MockConfigEntry(domain="xiaomi_miot", title="Xiaomi")
    other.add_to_hass(hass)
    return dr.async_get(hass).async_get_or_create(
        config_entry_id=other.entry_id, identifiers={("xiaomi_miot", "breather-1")}, name="Бризер"
    )


def legacy_entry(hass, hass_storage, device_id: str | None, last: str, interval=180.0) -> MockConfigEntry:
    """Exactly what 1.4.0 left behind: entry 1.1, its store and its registry entries."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        entry_id=ENTRY_ID,
        title=NAME,
        unique_id=f"{DOMAIN}_{NAME.lower().replace(' ', '_')}",
        version=1,
        minor_version=1,
        data={
            "name": NAME,
            "maintenance_interval": interval,  # NumberSelector stored a float
            "device_id": device_id,
            "last_maintenance_date": "2026-03-25T16:19:42.333756",
        },
        options={},
    )
    entry.add_to_hass(hass)
    hass_storage[f"maintainable_data_{ENTRY_ID}"] = {
        "version": 1,
        "minor_version": 1,
        "key": f"maintainable_data_{ENTRY_ID}",
        "data": {"last_maintenance_date": last, "maintenance_interval": int(interval), "name": NAME},
    }
    registry = er.async_get(hass)
    for domain, suffix, object_id in (
        ("sensor", "_m_status", f"{SLUG}_m_status"),
        ("sensor", "_m_days", f"{SLUG}_m_days"),
        ("button", "_maintenance_button", f"{SLUG}_maintenance_button"),
    ):
        registry.async_get_or_create(
            domain,
            DOMAIN,
            f"{ENTRY_ID}{suffix}",
            config_entry=entry,
            suggested_object_id=object_id,
            device_id=device_id,
        )
    return entry


async def test_upgrade_from_1_4_keeps_everything(hass: HomeAssistant, hass_storage, breather) -> None:
    due_events = async_capture_events(hass, "maintainable_due")
    # Serviced 180 days ago at 19:42 local time, stored naive like 1.x did.
    entry = legacy_entry(hass, hass_storage, breather.id, "2026-03-25T19:42:00")
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # Entry migrated in place, downgrade-safe (major version unchanged, data untouched).
    assert entry.state is ConfigEntryState.LOADED
    assert (entry.version, entry.minor_version) == (1, 2)
    assert entry.data["maintenance_interval"] == 180.0
    assert entry.options == {"maintenance_interval": 180, "due_threshold": 7, "create_repairs": True}

    # Same entity ids, states and the attributes dashboards filter on.
    status = hass.states.get(f"sensor.{SLUG}_m_status")
    days = hass.states.get(f"sensor.{SLUG}_m_days")
    assert status.state == "due" and days.state == "0"
    assert days.attributes["status"] == "due"  # auto-entities: sensor.*_m_days + status
    assert days.attributes["unit_of_measurement"] == "d"
    assert status.attributes["maintenance_interval"] == 180
    assert status.attributes["component_name"] == NAME
    # Date attributes byte-for-byte as 1.x rendered them (naive local strings).
    assert status.attributes["last_maintenance_date"] == "2026-03-25T19:42:00"
    assert days.attributes["next_maintenance_date"] == "2026-09-21T19:42:00"
    # Friendly name unchanged. HA 2026.9 prefixes the device name for entities on a device —
    # already the case with 1.4.0 ("Бризер: Кухня HEPA-фильтр… - Статус обслуживания").
    assert status.name.endswith(f"{NAME} - Статус обслуживания")
    assert hass.states.get(f"button.{SLUG}_maintenance_button") is not None

    # New in 2.0.
    assert hass.states.get(f"sensor.{SLUG}_next_maintenance").state == "2026-09-21"
    assert hass.states.get(f"date.{SLUG}_last_maintenance").state == "2026-03-25"

    # Still on the breather's device — now via device_entry, not foreign identifiers.
    registry = er.async_get(hass)
    for entity_id in (f"sensor.{SLUG}_m_status", f"date.{SLUG}_last_maintenance"):
        assert registry.async_get(entity_id).device_id == breather.id

    # No spurious "due" event just because HA started (1.x fired one on every restart).
    assert due_events == []

    # And a reminder in Repairs.
    issue = ir.async_get(hass).async_get_issue(DOMAIN, ENTRY_ID)
    assert issue.severity is ir.IssueSeverity.WARNING
    assert issue.translation_placeholders == {"name": NAME, "days": "0", "date": "2026-09-21"}


async def test_status_changes_at_midnight_with_events_and_repairs(
    hass: HomeAssistant, hass_storage, breather, freezer
) -> None:
    due = async_capture_events(hass, "maintainable_due")
    overdue = async_capture_events(hass, "maintainable_overdue")
    entry = legacy_entry(hass, hass_storage, breather.id, "2026-03-26T10:00:00")  # due tomorrow
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert hass.states.get(f"sensor.{SLUG}_m_status").state == "due"

    for _ in range(2):  # → due today → overdue
        freezer.tick(dt.timedelta(days=1))
        async_fire_time_changed(hass)
        await hass.async_block_till_done()

    assert hass.states.get(f"sensor.{SLUG}_m_status").state == "overdue"
    assert hass.states.get(f"sensor.{SLUG}_m_days").state == "-1"
    assert due == [] and len(overdue) == 1
    assert overdue[0].data == {
        "entity_id": f"sensor.{SLUG}_m_status",
        "component_name": NAME,
        "days_overdue": 1,
    }
    assert ir.async_get(hass).async_get_issue(DOMAIN, ENTRY_ID).severity is ir.IssueSeverity.ERROR


async def test_fix_flow_records_the_date(hass: HomeAssistant, hass_storage, breather) -> None:
    from homeassistant.components.repairs import repairs_flow_manager
    from homeassistant.setup import async_setup_component

    completed = async_capture_events(hass, "maintainable_completed")
    entry = legacy_entry(hass, hass_storage, breather.id, "2026-01-01T10:00:00")  # overdue
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    # HA 2026.2 registers repairs platforms of already-loaded integrations when `repairs`
    # sets up (2026.9 does it lazily); in a real instance both are loaded at startup.
    assert await async_setup_component(hass, "repairs", {})

    manager = repairs_flow_manager(hass)
    flow = await manager.async_init(DOMAIN, data={"issue_id": ENTRY_ID})
    assert flow["type"] is FlowResultType.FORM
    assert flow["step_id"] == "confirm"
    # Everything the step description needs is filled in, on any HA version.
    assert {k: flow["description_placeholders"][k] for k in ("name", "days", "date")} == {
        "name": NAME,
        "days": "83",
        "date": "2026-06-30",
    }
    result = await manager.async_configure(flow["flow_id"], {"maintenance_date": "2026-09-19"})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()

    assert hass.states.get(f"sensor.{SLUG}_m_status").state == "ok"
    assert hass.states.get(f"date.{SLUG}_last_maintenance").state == "2026-09-19"
    assert ir.async_get(hass).async_get_issue(DOMAIN, ENTRY_ID) is None
    assert completed[0].data["entity_id"] == f"sensor.{SLUG}_m_status"
    # Stored so that 1.x could still read it after a downgrade.
    stored = hass_storage[f"maintainable_data_{ENTRY_ID}"]["data"]
    assert stored["last_maintenance_date"].startswith("2026-09-19T00:00:00")
    assert stored["maintenance_interval"] == 180


async def test_services_work_with_transliterated_entity_ids(
    hass: HomeAssistant, hass_storage, breather
) -> None:
    """1.x rebuilt entity ids from the Cyrillic name, so these calls silently did nothing."""
    entry = legacy_entry(hass, hass_storage, breather.id, "2026-01-01T10:00:00")
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    await hass.services.async_call(
        DOMAIN,
        "set_last_maintenance",
        {"entity_id": f"sensor.{SLUG}_m_days", "maintenance_date": "2026-09-01"},
        blocking=True,
    )
    assert hass.states.get(f"date.{SLUG}_last_maintenance").state == "2026-09-01"

    await hass.services.async_call(
        DOMAIN, "perform_maintenance", {"entity_id": f"sensor.{SLUG}_m_status"}, blocking=True
    )
    assert hass.states.get(f"date.{SLUG}_last_maintenance").state == "2026-09-21"

    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            DOMAIN, "perform_maintenance", {"entity_id": "sensor.not_ours"}, blocking=True
        )


async def test_date_entity_and_button(hass: HomeAssistant, hass_storage, breather) -> None:
    entry = legacy_entry(hass, hass_storage, breather.id, "2026-01-01T10:00:00")
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    await hass.services.async_call(
        "date",
        "set_value",
        {"entity_id": f"date.{SLUG}_last_maintenance", "date": "2026-09-10"},
        blocking=True,
    )
    assert hass.states.get(f"sensor.{SLUG}_m_days").state == "169"

    await hass.services.async_call(
        "button", "press", {"entity_id": f"button.{SLUG}_maintenance_button"}, blocking=True
    )
    assert hass.states.get(f"sensor.{SLUG}_m_days").state == "180"


async def test_options_change_interval_and_disable_repairs(
    hass: HomeAssistant, hass_storage, breather
) -> None:
    entry = legacy_entry(hass, hass_storage, breather.id, "2026-03-25T19:42:00")
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert ir.async_get(hass).async_get_issue(DOMAIN, ENTRY_ID) is not None

    flow = await hass.config_entries.options.async_init(entry.entry_id)
    await hass.config_entries.options.async_configure(
        flow["flow_id"], {"maintenance_interval": 200, "due_threshold": 7, "create_repairs": False}
    )
    await hass.async_block_till_done()

    assert hass.states.get(f"sensor.{SLUG}_m_days").state == "20"
    assert hass.states.get(f"sensor.{SLUG}_m_status").state == "ok"
    assert ir.async_get(hass).async_get_issue(DOMAIN, ENTRY_ID) is None
    assert hass_storage[f"maintainable_data_{ENTRY_ID}"]["data"]["maintenance_interval"] == 200


async def test_new_component(hass: HomeAssistant) -> None:
    flow = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert flow["type"] is FlowResultType.MENU
    flow = await hass.config_entries.flow.async_configure(flow["flow_id"], {"next_step_id": "component"})
    result = await hass.config_entries.flow.async_configure(
        flow["flow_id"],
        {
            "name": "Water filter",
            "maintenance_interval": 90,
            "due_threshold": 10,
            "last_maintenance_date": "2026-07-01",
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    entry = result["result"]
    assert (entry.version, entry.minor_version) == (1, 2)

    assert hass.states.get("sensor.water_filter_m_days").state == "8"
    assert hass.states.get("sensor.water_filter_m_status").state == "due"
    # Not linked to a device → gets its own, so it can be put in an area.
    device_id = er.async_get(hass).async_get("sensor.water_filter_m_status").device_id
    assert dr.async_get(hass).async_get(device_id).name == "Water filter"

    again = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    again = await hass.config_entries.flow.async_configure(again["flow_id"], {"next_step_id": "component"})
    again = await hass.config_entries.flow.async_configure(
        again["flow_id"], {"name": "water filter", "maintenance_interval": 30, "due_threshold": 7}
    )
    assert again["type"] is FlowResultType.ABORT and again["reason"] == "already_configured"


async def test_reconfigure_keeps_entity_ids(hass: HomeAssistant, hass_storage, breather) -> None:
    entry = legacy_entry(hass, hass_storage, breather.id, "2026-03-25T19:42:00")
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    flow = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "reconfigure", "entry_id": entry.entry_id}
    )
    result = await hass.config_entries.flow.async_configure(flow["flow_id"], {"name": "HEPA (кухня)"})
    assert result["reason"] == "reconfigure_successful"
    await hass.async_block_till_done()

    state = hass.states.get(f"sensor.{SLUG}_m_status")
    assert state.attributes["component_name"] == "HEPA (кухня)"
    # Device link cleared in the form → the component now has its own device.
    assert er.async_get(hass).async_get(f"sensor.{SLUG}_m_status").device_id != breather.id


async def test_remove_entry_cleans_up(hass: HomeAssistant, hass_storage, breather) -> None:
    entry = legacy_entry(hass, hass_storage, breather.id, "2026-01-01T10:00:00")
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert ir.async_get(hass).async_get_issue(DOMAIN, ENTRY_ID) is not None

    await hass.config_entries.async_remove(entry.entry_id)
    await hass.async_block_till_done()
    assert ir.async_get(hass).async_get_issue(DOMAIN, ENTRY_ID) is None
    assert f"maintainable_data_{ENTRY_ID}" not in hass_storage


async def test_survives_restart(hass: HomeAssistant, hass_storage, breather) -> None:
    """Everything that matters is persisted; a restart changes nothing and fires nothing."""
    events = async_capture_events(hass, "maintainable_due")
    entry = legacy_entry(hass, hass_storage, breather.id, "2026-01-01T10:00:00")
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    await hass.services.async_call(
        "date",
        "set_value",
        {"entity_id": f"date.{SLUG}_last_maintenance", "date": "2026-03-26"},
        blocking=True,
    )
    flow = await hass.config_entries.options.async_init(entry.entry_id)
    await hass.config_entries.options.async_configure(
        flow["flow_id"], {"maintenance_interval": 180, "due_threshold": 3, "create_repairs": True}
    )
    await hass.async_block_till_done()
    before = {e: hass.states.get(e) for e in (f"sensor.{SLUG}_m_status", f"sensor.{SLUG}_m_days")}
    fired = len(events)

    # Restart: unload everything (as on shutdown) and set up again from storage only.
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    for entity_id, old in before.items():
        new = hass.states.get(entity_id)
        assert (new.state, new.attributes) == (old.state, old.attributes), entity_id
    assert hass.states.get(f"date.{SLUG}_last_maintenance").state == "2026-03-26"
    assert entry.options["due_threshold"] == 3
    assert len(events) == fired  # no event just because of the restart
    assert ir.async_get(hass).async_get_issue(DOMAIN, ENTRY_ID) is not None  # reminder is back


async def test_transition_while_ha_was_off_fires_once(
    hass: HomeAssistant, hass_storage, breather, freezer
) -> None:
    """HA off over the day the status changed: the event comes once on the next start."""
    overdue = async_capture_events(hass, "maintainable_overdue")
    entry = legacy_entry(hass, hass_storage, breather.id, "2026-03-25T10:00:00")  # due today
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert await hass.config_entries.async_unload(entry.entry_id)

    freezer.tick(dt.timedelta(days=2))  # ...HA is off; midnight passes unseen
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert hass.states.get(f"sensor.{SLUG}_m_status").state == "overdue"
    assert len(overdue) == 1

    assert await hass.config_entries.async_unload(entry.entry_id)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert len(overdue) == 1  # not again


async def test_split_composite_device_is_repaired(hass: HomeAssistant, hass_storage) -> None:
    """HA 2026.8 split devices that 1.x had joined: entities go back to the real device.

    1.x added its config entry to the linked device; the registry migration split that
    composite device into the owner's device and a Maintainable-owned copy (shown as a
    "related device"), and the stored device_id still holds the composite id.
    """
    import attr

    registry = dr.async_get(hass)
    if not hasattr(dr.DeviceEntry, "__attrs_attrs__") or "composite_device_id" not in {
        a.name for a in attr.fields(dr.DeviceEntry)
    }:
        pytest.skip("Composite device splits exist since Home Assistant 2026.8")

    composite_id = "c0mp0s1te0000000000000000000000a"
    owner = MockConfigEntry(domain="device_tools", title="Device Tools")
    owner.add_to_hass(hass)
    real = registry.async_get_or_create(
        config_entry_id=owner.entry_id, identifiers={("device_tools", "aquaphor")}, name="Фильтр Аквафор"
    )
    entry = legacy_entry(hass, hass_storage, None, "2026-08-06T19:36:18.481098")
    # The entry still stores the pre-split composite id.
    hass.config_entries.async_update_entry(entry, data={**entry.data, "device_id": composite_id})
    copy = registry.async_get_or_create(
        config_entry_id=entry.entry_id, identifiers={("device_tools", "aquaphor-copy")}, name="Фильтр Аквафор"
    )
    # What the registry migration leaves behind (not reachable through public API).
    for device in (real, copy):
        registry._devices[device.id] = attr.evolve(device, composite_device_id=composite_id)
    entities = er.async_get(hass)
    for entity in er.async_entries_for_config_entry(entities, entry.entry_id):
        entities.async_update_entity(entity.entity_id, device_id=copy.id)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # Back on the real device, with history-bearing entity ids unchanged…
    for entity in er.async_entries_for_config_entry(entities, entry.entry_id):
        assert entity.device_id == real.id, entity.entity_id
    assert hass.states.get(f"sensor.{SLUG}_m_status") is not None
    # …the leftover copy is gone, and the entry points at the real device.
    assert registry.async_get(copy.id) is None
    assert entry.data["device_id"] == real.id
    assert entry.state is ConfigEntryState.LOADED
