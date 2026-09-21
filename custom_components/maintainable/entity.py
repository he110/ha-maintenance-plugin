"""Base entity: naming and device linking shared by all platforms."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import slugify

from .const import CONF_DEVICE_ID, DOMAIN
from .coordinator import MaintenanceCoordinator

# Entity names are "<component> - <suffix>", exactly as in 1.x (has_entity_name=False),
# so friendly names do not change on upgrade. A component linked to someone else's
# device ("Breather") would otherwise lose its own name in the UI.
SUFFIXES = {
    "status": ("Статус обслуживания", "Maintenance status"),
    "days": ("Дни до обслуживания", "Days until maintenance"),
    "button": ("Выполнить обслуживание", "Mark as maintained"),
    "next": ("Следующее обслуживание", "Next maintenance"),
    "last": ("Последнее обслуживание", "Last maintenance"),
}


class MaintainableEntity(CoordinatorEntity[MaintenanceCoordinator]):
    _attr_has_entity_name = False

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: MaintenanceCoordinator,
        *,
        key: str,
        unique_suffix: str,
        platform: str,
        object_suffix: str,
    ) -> None:
        super().__init__(coordinator)
        entry = coordinator.entry
        name = coordinator.name_
        russian = hass.config.language.startswith("ru")
        suffix = SUFFIXES[key][0 if russian else 1]
        self._attr_name = f"{name} - {suffix}"
        self._attr_unique_id = f"{entry.entry_id}{unique_suffix}"
        # Only used for brand-new entities; existing ones keep their registry id.
        self.entity_id = f"{platform}.{slugify(name)}{object_suffix}"

        device_id = entry.data.get(CONF_DEVICE_ID)
        if device_id and (device := dr.async_get(hass).async_get(device_id)):
            # Attach to the chosen device of another integration the supported way
            # (DeviceInfo with a foreign device's identifiers is deprecated).
            self.device_entry = device
        elif not device_id:
            self._attr_device_info = DeviceInfo(
                identifiers={(DOMAIN, entry.entry_id)},
                name=name,
                model="Maintainable component",
            )
