"""Battery monitor: finds every battery in the home on its own and reports low ones in Repairs."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_DEVICE_CLASS, EVENT_STATE_CHANGED, STATE_ON
from homeassistant.core import Event, EventStateChangedData, HomeAssistant, State, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import issue_registry as ir

from .battery_levels import SEVERITY_ERROR, DeviceBattery, parse_level, severity
from .const import (
    CONF_ERROR_LEVEL,
    CONF_EXCLUDE_DEVICES,
    CONF_EXCLUDE_INTEGRATIONS,
    CONF_WARNING_LEVEL,
    DEFAULT_ERROR_LEVEL,
    DEFAULT_EXCLUDE_INTEGRATIONS,
    DEFAULT_WARNING_LEVEL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

BATTERY_DOMAINS = ("sensor", "binary_sensor")
ISSUE_PREFIX = "battery_"


def is_battery(state: State | None) -> bool:
    return (
        state is not None
        and state.domain in BATTERY_DOMAINS
        and state.attributes.get(ATTR_DEVICE_CLASS) == "battery"
    )


class BatteryMonitor:
    """Tracks battery entities through state changes — new devices are picked up by themselves."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        options = entry.options
        self.warning_level = float(options.get(CONF_WARNING_LEVEL, DEFAULT_WARNING_LEVEL))
        self.error_level = float(options.get(CONF_ERROR_LEVEL, DEFAULT_ERROR_LEVEL))
        self._excluded_integrations = set(
            options.get(CONF_EXCLUDE_INTEGRATIONS, DEFAULT_EXCLUDE_INTEGRATIONS)
        )
        self._excluded_devices = set(options.get(CONF_EXCLUDE_DEVICES, []))
        self.devices: dict[str, DeviceBattery] = {}  # key: device_id or entity_id
        self._entity_key: dict[str, str] = {}
        self._issues: set[str] = set()
        self._listeners: list[Callable[[], None]] = []
        self._unsub: Callable[[], None] | None = None

    # --- lifecycle ---------------------------------------------------------------

    @callback
    def async_start(self) -> None:
        for state in self.hass.states.async_all(BATTERY_DOMAINS):
            if is_battery(state):
                self._track(state.entity_id, state, notify=False)
        for key in list(self.devices):
            self._sync_issue(key)
        self._unsub = self.hass.bus.async_listen(
            EVENT_STATE_CHANGED, self._on_state_changed, event_filter=self._relevant
        )

    @callback
    def async_stop(self) -> None:
        if self._unsub:
            self._unsub()
            self._unsub = None
        for issue_id in self._issues:
            ir.async_delete_issue(self.hass, DOMAIN, issue_id)
        self._issues.clear()

    @callback
    def async_add_listener(self, update: Callable[[], None]) -> Callable[[], None]:
        self._listeners.append(update)
        return lambda: self._listeners.remove(update)

    # --- events -----------------------------------------------------------------

    @callback
    def _relevant(self, event_data: EventStateChangedData) -> bool:
        return is_battery(event_data["new_state"]) or event_data["entity_id"] in self._entity_key

    @callback
    def _on_state_changed(self, event: Event[EventStateChangedData]) -> None:
        self._track(event.data["entity_id"], event.data["new_state"], notify=True)

    # --- bookkeeping --------------------------------------------------------------

    def _key_and_name(self, entity_id: str, state: State) -> tuple[str, str] | None:
        """Group by device; None when the entity is excluded."""
        entry = er.async_get(self.hass).async_get(entity_id)
        if entry is not None and entry.platform in self._excluded_integrations:
            return None
        device_id = entry.device_id if entry else None
        if device_id:
            if device_id in self._excluded_devices:
                return None
            device = dr.async_get(self.hass).async_get(device_id)
            if device is not None:
                return device_id, device.name_by_user or device.name or state.name
        return entity_id, state.name

    @callback
    def _track(self, entity_id: str, state: State | None, *, notify: bool) -> None:
        old_key = self._entity_key.pop(entity_id, None)
        if old_key is not None:
            battery = self.devices[old_key]
            battery.levels.pop(entity_id, None)
            battery.low_flags.pop(entity_id, None)
        key = None
        if is_battery(state) and (grouping := self._key_and_name(entity_id, state)):
            key, name = grouping
            battery = self.devices.setdefault(key, DeviceBattery(name=name))
            battery.name = name
            if state.domain == "sensor":
                if (level := parse_level(state.state)) is not None:
                    battery.levels[entity_id] = level
            else:
                battery.low_flags[entity_id] = state.state == STATE_ON
            self._entity_key[entity_id] = key
        for changed in {old_key, key} - {None}:
            if self.devices[changed].empty and not self._entity_key_used(changed):
                del self.devices[changed]
            if notify:
                self._sync_issue(changed)
        if notify:
            for update in self._listeners:
                update()

    def _entity_key_used(self, key: str) -> bool:
        return key in self._entity_key.values()

    # --- Repairs ----------------------------------------------------------------

    def _sync_issue(self, key: str) -> None:
        issue_id = f"{ISSUE_PREFIX}{key}"
        battery = self.devices.get(key)
        level = severity(battery, self.warning_level, self.error_level) if battery else None
        if level is None:
            if issue_id in self._issues:
                ir.async_delete_issue(self.hass, DOMAIN, issue_id)
                self._issues.discard(issue_id)
            return
        if battery.level is not None:
            translation_key = "battery_empty" if level == SEVERITY_ERROR else "battery_low"
        else:
            translation_key = "battery_low_flag"
        ir.async_create_issue(
            self.hass,
            DOMAIN,
            issue_id,
            is_fixable=False,
            is_persistent=False,
            severity=ir.IssueSeverity.ERROR if level == SEVERITY_ERROR else ir.IssueSeverity.WARNING,
            translation_key=translation_key,
            translation_placeholders={
                "name": battery.name,
                "level": f"{battery.level:g}" if battery.level is not None else "",
            },
        )
        self._issues.add(issue_id)

    # --- for the sensor ---------------------------------------------------------

    def low(self) -> list[dict[str, Any]]:
        """Devices that need attention, emptiest first."""
        result = []
        for battery in self.devices.values():
            level = severity(battery, self.warning_level, self.error_level)
            if level is None:
                continue
            result.append(
                {
                    "name": battery.name,
                    "level": battery.level,
                    "severity": level,
                    "entity_id": min(battery.levels, key=battery.levels.get)
                    if battery.levels
                    else next(e for e, on in battery.low_flags.items() if on),
                }
            )
        return sorted(result, key=lambda d: (d["level"] is None, d["level"] or 0, d["name"]))
