"""Кнопки для интеграции Maintainable."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DATA_COORDINATOR,
    DOMAIN,
    BUTTON_SUFFIX,
)
from .coordinator import MaintenanceCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Настройка кнопок."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id][DATA_COORDINATOR]
    
    # Создаём кнопку
    entities = [
        MaintenanceButton(coordinator, config_entry),
    ]
    
    async_add_entities(entities, True)


class MaintenanceButton(CoordinatorEntity, ButtonEntity):
    """Кнопка для выполнения обслуживания."""

    def __init__(
        self,
        coordinator: MaintenanceCoordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Инициализация кнопки."""
        super().__init__(coordinator)
        self.config_entry = config_entry
        self._component_name = config_entry.data.get("name", "Компонент")
        component_name_safe = self._component_name.lower().replace(" ", "_")
        
        self._attr_unique_id = f"{config_entry.entry_id}{BUTTON_SUFFIX}"
        self._attr_name = f"{self._component_name} - Выполнить обслуживание"
        # Отключаем has_entity_name для правильного именования
        self._attr_has_entity_name = False
        self._attr_icon = "mdi:wrench"
        
        # Устанавливаем правильный entity_id
        self.entity_id = f"button.{component_name_safe}_maintenance_button"

    @property
    def device_info(self) -> DeviceInfo | None:
        """Информация об устройстве."""
        device_id = self.config_entry.data.get("device_id")
        _LOGGER.debug("Кнопка %s: device_id из конфигурации = %s", self._component_name, device_id)
        
        if device_id:
            # Получаем устройство из реестра
            from homeassistant.helpers import device_registry as dr
            device_registry = dr.async_get(self.hass)
            device = device_registry.async_get(device_id)
            _LOGGER.debug("Кнопка %s: устройство найдено = %s", self._component_name, device is not None)
            
            if device:
                _LOGGER.info("Кнопка %s: привязываем к устройству %s (identifiers: %s)", 
                           self._component_name, device.name, device.identifiers)
                # Возвращаем DeviceInfo с теми же identifiers что и у оригинального устройства
                return DeviceInfo(
                    identifiers=device.identifiers,
                    connections=device.connections,
                )
            else:
                _LOGGER.warning("Кнопка %s: устройство с ID %s не найдено в реестре", 
                              self._component_name, device_id)
        return None

    @property
    def available(self) -> bool:
        """Доступность кнопки."""
        return self.coordinator.last_update_success

    async def async_press(self) -> None:
        """Обработка нажатия кнопки."""
        try:
            await self.coordinator.async_perform_maintenance()
            _LOGGER.info("Обслуживание выполнено для %s", self._component_name)
        except Exception as err:
            _LOGGER.error("Ошибка при выполнении обслуживания для %s: %s", 
                         self._component_name, err)
            raise

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Дополнительные атрибуты кнопки."""
        if not self.coordinator.data:
            return {}
        
        return {
            "component_name": self._component_name,
            "current_status": self.coordinator.data.get("status"),
            "days_until_maintenance": self.coordinator.data.get("days_until_maintenance"),
            "last_maintenance_date": self.coordinator.data.get("last_maintenance_date"),
        } 