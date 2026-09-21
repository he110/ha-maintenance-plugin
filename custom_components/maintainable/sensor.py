"""Sensors: status, days until maintenance (both from 1.x), next maintenance date."""

from __future__ import annotations

import datetime as dt
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.const import UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import DAYS_SUFFIX, NEXT_SUFFIX, STATUS_SUFFIX
from .coordinator import MaintainableConfigEntry, MaintenanceCoordinator, effective_interval
from .entity import MaintainableEntity
from .schedule import STATUS_DUE, STATUS_OK, STATUS_OVERDUE


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MaintainableConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        [
            StatusSensor(hass, coordinator),
            DaysSensor(hass, coordinator),
            NextMaintenanceSensor(hass, coordinator),
        ]
    )


def _attributes(coordinator: MaintenanceCoordinator) -> dict[str, Any]:
    """Attributes of 1.x. `status` on the days sensor is used by dashboard filters."""
    schedule = coordinator.data
    return {
        "status": schedule.status,
        "days_until_maintenance": schedule.days_until,
        "last_maintenance_date": schedule.last.isoformat(),
        "next_maintenance_date": schedule.next.isoformat(),
        "maintenance_interval": effective_interval(coordinator.entry),
        "component_name": coordinator.name_,
    }


class StatusSensor(MaintainableEntity, SensorEntity):
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = [STATUS_OK, STATUS_DUE, STATUS_OVERDUE]  # noqa: RUF012 — HA's own convention
    _attr_translation_key = "status"

    def __init__(self, hass: HomeAssistant, coordinator: MaintenanceCoordinator) -> None:
        super().__init__(
            hass,
            coordinator,
            key="status",
            unique_suffix=STATUS_SUFFIX,
            platform="sensor",
            object_suffix=STATUS_SUFFIX,
        )

    @property
    def native_value(self) -> str:
        return self.coordinator.data.status

    @property
    def icon(self) -> str:
        return {
            STATUS_OK: "mdi:check-circle",
            STATUS_DUE: "mdi:alert-circle",
            STATUS_OVERDUE: "mdi:alert-circle-outline",
        }[self.coordinator.data.status]

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        attributes = _attributes(self.coordinator)
        attributes.pop("status")  # 1.x did not expose it here (it is the state)
        return attributes


class DaysSensor(MaintainableEntity, SensorEntity):
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_native_unit_of_measurement = UnitOfTime.DAYS

    def __init__(self, hass: HomeAssistant, coordinator: MaintenanceCoordinator) -> None:
        super().__init__(
            hass,
            coordinator,
            key="days",
            unique_suffix=DAYS_SUFFIX,
            platform="sensor",
            object_suffix=DAYS_SUFFIX,
        )

    @property
    def native_value(self) -> int:
        return self.coordinator.data.days_until

    @property
    def icon(self) -> str:
        days = self.coordinator.data.days_until
        if days < 0:
            return "mdi:calendar-alert"
        if self.coordinator.data.status == STATUS_DUE:
            return "mdi:calendar-clock"
        return "mdi:calendar-check"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        attributes = _attributes(self.coordinator)
        attributes.pop("days_until_maintenance")  # it is the state
        return attributes


class NextMaintenanceSensor(MaintainableEntity, SensorEntity):
    _attr_device_class = SensorDeviceClass.DATE
    _attr_icon = "mdi:calendar-arrow-right"

    def __init__(self, hass: HomeAssistant, coordinator: MaintenanceCoordinator) -> None:
        super().__init__(
            hass,
            coordinator,
            key="next",
            unique_suffix=NEXT_SUFFIX,
            platform="sensor",
            object_suffix="_next_maintenance",
        )

    @property
    def native_value(self) -> dt.date:
        return dt_util.as_local(self.coordinator.data.next).date()
