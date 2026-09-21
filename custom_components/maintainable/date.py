"""Date entity: last maintenance, editable from the device page."""

from __future__ import annotations

import datetime as dt

from homeassistant.components.date import DateEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import LAST_SUFFIX
from .coordinator import MaintainableConfigEntry, MaintenanceCoordinator
from .entity import MaintainableEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MaintainableConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    async_add_entities([LastMaintenanceDate(hass, entry.runtime_data)])


class LastMaintenanceDate(MaintainableEntity, DateEntity):
    _attr_icon = "mdi:calendar-check"

    def __init__(self, hass: HomeAssistant, coordinator: MaintenanceCoordinator) -> None:
        super().__init__(
            hass,
            coordinator,
            key="last",
            unique_suffix=LAST_SUFFIX,
            platform="date",
            object_suffix="_last_maintenance",
        )

    @property
    def native_value(self) -> dt.date:
        return dt_util.as_local(self.coordinator.data.last).date()

    async def async_set_value(self, value: dt.date) -> None:
        await self.coordinator.async_set_last_maintenance(value)
