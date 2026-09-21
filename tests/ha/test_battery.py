"""Battery monitor: finds batteries by itself, reports low ones in Repairs."""

from __future__ import annotations

import pytest
from homeassistant.config_entries import SOURCE_USER, ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import issue_registry as ir
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.maintainable.const import DOMAIN

PERCENT = {"device_class": "battery", "unit_of_measurement": "%"}
FLAG = {"device_class": "battery"}


@pytest.fixture(autouse=True)
def russian(hass: HomeAssistant):
    hass.config.language = "ru"


class Home:
    """Devices of other integrations with battery entities, like a real Zigbee setup."""

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass
        self.entries: dict[str, MockConfigEntry] = {}

    def device(self, platform: str, key: str, name: str) -> dr.DeviceEntry:
        if platform not in self.entries:
            self.entries[platform] = MockConfigEntry(domain=platform)
            self.entries[platform].add_to_hass(self.hass)
        return dr.async_get(self.hass).async_get_or_create(
            config_entry_id=self.entries[platform].entry_id, identifiers={(platform, key)}, name=name
        )

    def battery(self, device: dr.DeviceEntry, platform: str, object_id: str, state: str, attrs=PERCENT):
        domain = "sensor" if attrs is PERCENT else "binary_sensor"
        entity = er.async_get(self.hass).async_get_or_create(
            domain,
            platform,
            object_id,
            device_id=device.id,
            suggested_object_id=object_id,
            config_entry=self.entries[platform],
        )
        self.hass.states.async_set(entity.entity_id, state, attrs)
        return entity.entity_id


@pytest.fixture
def home(hass: HomeAssistant) -> Home:
    return Home(hass)


async def add_monitor(hass: HomeAssistant, **options) -> MockConfigEntry:
    flow = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    flow = await hass.config_entries.flow.async_configure(flow["flow_id"], {"next_step_id": "battery"})
    assert flow["step_id"] == "battery"
    data = {"warning_level": 10, "error_level": 0, "exclude_integrations": ["mobile_app"]} | options
    result = await hass.config_entries.flow.async_configure(flow["flow_id"], data)
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    return result["result"]


def issues(hass: HomeAssistant) -> dict[str, tuple[str, str]]:
    """{device name: (severity, translation key)} of battery issues."""
    return {
        issue.translation_placeholders["name"]: (issue.severity.value, issue.translation_key)
        for (domain, issue_id), issue in ir.async_get(hass).issues.items()
        if domain == DOMAIN and issue_id.startswith("battery_")
    }


async def test_finds_batteries_without_setup(hass: HomeAssistant, home: Home) -> None:
    leak = home.device("mqtt", "leak", "Датчик протечки. Кухня")
    home.battery(leak, "mqtt", "leak_battery", "5")
    home.battery(leak, "mqtt", "leak_battery_low", "off", FLAG)  # vendor flag still off at 5 %
    dead = home.device("mqtt", "dead", "Датчик двери")
    home.battery(dead, "mqtt", "door_battery", "0")
    fine = home.device("mqtt", "fine", "Датчик климата")
    home.battery(fine, "mqtt", "climate_battery", "100")
    flag_only = home.device("xiaomi_ble", "remote", "Пульт")
    home.battery(flag_only, "xiaomi_ble", "remote_battery_low", "on", FLAG)
    phone = home.device("mobile_app", "phone", "iPhone")
    home.battery(phone, "mobile_app", "phone_battery", "3")
    silent = home.device("mqtt", "silent", "Молчун")
    home.battery(silent, "mqtt", "silent_battery", "unknown")

    await add_monitor(hass)

    assert issues(hass) == {
        "Датчик протечки. Кухня": ("warning", "battery_low"),
        "Датчик двери": ("error", "battery_empty"),
        "Пульт": ("warning", "battery_low_flag"),
    }
    state = hass.states.get("sensor.low_battery_devices")
    assert state.state == "3"
    assert [d["name"] for d in state.attributes["devices"]] == [
        "Датчик двери",
        "Датчик протечки. Кухня",
        "Пульт",
    ]
    assert state.attributes["devices"][1]["level"] == 5
    assert state.name == "Контроль батарей Севшие батареи"  # device + entity, HA style


async def test_follows_changes_and_new_devices(hass: HomeAssistant, home: Home) -> None:
    await add_monitor(hass)
    assert issues(hass) == {}

    # A device paired after setup is picked up by itself.
    new = home.device("mqtt", "new", "Новый датчик")
    entity_id = home.battery(new, "mqtt", "new_battery", "8")
    await hass.async_block_till_done()
    assert issues(hass) == {"Новый датчик": ("warning", "battery_low")}
    assert hass.states.get("sensor.low_battery_devices").state == "1"

    hass.states.async_set(entity_id, "0", PERCENT)
    await hass.async_block_till_done()
    assert issues(hass) == {"Новый датчик": ("error", "battery_empty")}

    # Battery replaced → the reminder goes away.
    hass.states.async_set(entity_id, "100", PERCENT)
    await hass.async_block_till_done()
    assert issues(hass) == {}
    assert hass.states.get("sensor.low_battery_devices").state == "0"

    # Unavailable does not count as empty; a removed entity stops being tracked.
    hass.states.async_set(entity_id, "3", PERCENT)
    hass.states.async_set(entity_id, "unavailable", PERCENT)
    await hass.async_block_till_done()
    assert issues(hass) == {}
    hass.states.async_set(entity_id, "3", PERCENT)
    await hass.async_block_till_done()
    hass.states.async_remove(entity_id)
    await hass.async_block_till_done()
    assert issues(hass) == {}


async def test_options_exclusions_and_thresholds(hass: HomeAssistant, home: Home) -> None:
    leak = home.device("mqtt", "leak", "Датчик протечки")
    home.battery(leak, "mqtt", "leak_battery", "15")
    brush = home.device("oralb", "brush", "Щётка")
    home.battery(brush, "oralb", "brush_battery", "5")
    entry = await add_monitor(hass)
    assert issues(hass) == {"Щётка": ("warning", "battery_low")}

    flow = await hass.config_entries.options.async_init(entry.entry_id)
    assert flow["step_id"] == "battery"
    await hass.config_entries.options.async_configure(
        flow["flow_id"],
        {
            "warning_level": 20,
            "error_level": 0,
            "exclude_integrations": ["mobile_app"],
            "exclude_devices": [brush.id],
        },
    )
    await hass.async_block_till_done()
    assert issues(hass) == {"Датчик протечки": ("warning", "battery_low")}


async def test_single_monitor_and_cleanup(hass: HomeAssistant, home: Home) -> None:
    dead = home.device("mqtt", "dead", "Датчик")
    home.battery(dead, "mqtt", "battery", "0")
    entry = await add_monitor(hass)
    assert issues(hass)

    flow = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    flow = await hass.config_entries.flow.async_configure(flow["flow_id"], {"next_step_id": "battery"})
    assert flow["type"] is FlowResultType.ABORT and flow["reason"] == "battery_already_configured"

    # Restart: issues come back from the current states.
    assert await hass.config_entries.async_unload(entry.entry_id)
    assert issues(hass) == {}
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert issues(hass) == {"Датчик": ("error", "battery_empty")}
    assert entry.state is ConfigEntryState.LOADED

    await hass.config_entries.async_remove(entry.entry_id)
    await hass.async_block_till_done()
    assert issues(hass) == {}

    # Reconfigure is not for the monitor.
    entry = await add_monitor(hass)
    flow = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "reconfigure", "entry_id": entry.entry_id}
    )
    assert flow["reason"] == "use_options"
