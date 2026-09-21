"""Button: mark the component as maintained today (unchanged since 1.x)."""

from __future__ import annotations

from typing import Any

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import BUTTON_SUFFIX
from .coordinator import MaintainableConfigEntry, MaintenanceCoordinator
from .entity import MaintainableEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MaintainableConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    async_add_entities([MaintenanceButton(hass, entry.runtime_data)])


class MaintenanceButton(MaintainableEntity, ButtonEntity):
    _attr_icon = "mdi:wrench"

    def __init__(self, hass: HomeAssistant, coordinator: MaintenanceCoordinator) -> None:
        super().__init__(
            hass,
            coordinator,
            key="button",
            unique_suffix=BUTTON_SUFFIX,
            platform="button",
            object_suffix="_maintenance_button",
        )

    async def async_press(self) -> None:
        await self.coordinator.async_set_last_maintenance()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        schedule = self.coordinator.data
        return {
            "component_name": self.coordinator.name_,
            "current_status": schedule.status,
            "days_until_maintenance": schedule.days_until,
            "last_maintenance_date": schedule.last.isoformat(),
        }
