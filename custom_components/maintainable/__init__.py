"""Maintainable: reminders for things that need periodic maintenance."""

from __future__ import annotations

import logging

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.storage import Store
from homeassistant.helpers.typing import ConfigType

from .battery import BatteryMonitor
from .const import (
    CONF_DUE_THRESHOLD,
    CONF_INTERVAL,
    CONF_KIND,
    CONF_REPAIRS,
    DEFAULT_DUE_THRESHOLD,
    DOMAIN,
    KIND_BATTERY,
    PLATFORMS,
    STORAGE_KEY,
    STORAGE_VERSION,
)
from .coordinator import MaintainableConfigEntry, MaintenanceCoordinator
from .devices import async_relink
from .services import async_register_services

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)
BATTERY_PLATFORMS = [Platform.SENSOR]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    async_register_services(hass)
    return True


async def async_migrate_entry(hass: HomeAssistant, entry: MaintainableConfigEntry) -> bool:
    """1.1 → 1.2: editable settings move to options. Data is left intact.

    Only the minor version changes, so going back to 1.x stays possible.
    """
    if entry.version > 1:
        return False
    if entry.minor_version < 2 and not _is_battery_monitor(entry):
        store = Store(hass, STORAGE_VERSION, STORAGE_KEY.format(entry_id=entry.entry_id))
        stored = await store.async_load() or {}
        # 1.x read the interval from its store (copied there on first run).
        interval = stored.get(CONF_INTERVAL, entry.data.get(CONF_INTERVAL))
        options = {
            CONF_DUE_THRESHOLD: DEFAULT_DUE_THRESHOLD,
            CONF_REPAIRS: True,
            **entry.options,
        }
        if interval:
            options.setdefault(CONF_INTERVAL, int(interval))
        options.pop("enable_notifications", None)  # 1.x option that did nothing
        hass.config_entries.async_update_entry(entry, options=options, minor_version=2)
        _LOGGER.debug("Migrated %s to 1.2", entry.title)
    return True


def _is_battery_monitor(entry: MaintainableConfigEntry) -> bool:
    return entry.data.get(CONF_KIND) == KIND_BATTERY


async def async_setup_entry(hass: HomeAssistant, entry: MaintainableConfigEntry) -> bool:
    if _is_battery_monitor(entry):
        monitor = BatteryMonitor(hass, entry)
        monitor.async_start()
        entry.runtime_data = monitor
        entry.async_on_unload(entry.add_update_listener(_async_update_listener))
        await hass.config_entries.async_forward_entry_setups(entry, BATTERY_PLATFORMS)
        return True

    # Before the update listener exists: fixing the stored device id must not reload.
    async_relink(hass, entry)
    coordinator = MaintenanceCoordinator(hass, entry)
    await coordinator.async_load()
    entry.runtime_data = coordinator

    @callback
    def _midnight(_now) -> None:
        coordinator.async_refresh_schedule()

    entry.async_on_unload(async_track_time_change(hass, _midnight, hour=0, minute=0, second=1))
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: MaintainableConfigEntry) -> bool:
    if _is_battery_monitor(entry):
        unloaded = await hass.config_entries.async_unload_platforms(entry, BATTERY_PLATFORMS)
        if unloaded:
            entry.runtime_data.async_stop()
        return unloaded
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        # A disabled or removed component must not keep nagging in Repairs.
        entry.runtime_data.async_remove_issue()
    return unloaded


async def async_remove_entry(hass: HomeAssistant, entry: MaintainableConfigEntry) -> None:
    if _is_battery_monitor(entry):
        return
    await Store(hass, STORAGE_VERSION, STORAGE_KEY.format(entry_id=entry.entry_id)).async_remove()


async def _async_update_listener(hass: HomeAssistant, entry: MaintainableConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)
