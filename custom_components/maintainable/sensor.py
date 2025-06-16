"""Сенсоры для интеграции Maintainable."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DATA_COORDINATOR,
    DOMAIN,
    MAINTENANCE_STATUS_OK,
    MAINTENANCE_STATUS_DUE,
    MAINTENANCE_STATUS_OVERDUE,
    STATUS_SUFFIX,
    DAYS_SUFFIX,
)
from .coordinator import MaintenanceCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Настройка сенсоров."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id][DATA_COORDINATOR]
    
    # Создаём сенсоры
    entities = [
        MaintenanceStatusSensor(coordinator, config_entry),
        MaintenanceDaysSensor(coordinator, config_entry),
    ]
    
    async_add_entities(entities, True)


class MaintenanceBaseSensor(CoordinatorEntity):
    """Базовый класс для сенсоров обслуживания."""

    def __init__(
        self,
        coordinator: MaintenanceCoordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Инициализация сенсора."""
        super().__init__(coordinator)
        self.config_entry = config_entry
        self._component_name = config_entry.data.get("name", "Компонент")
        # Отключаем has_entity_name для правильного именования
        self._attr_has_entity_name = False

    @property
    def device_info(self) -> DeviceInfo | None:
        """Информация об устройстве."""
        device_id = self.config_entry.data.get("device_id")
        _LOGGER.debug("Компонент %s: device_id из конфигурации = %s", self._component_name, device_id)
        
        if device_id:
            # Получаем устройство из реестра
            from homeassistant.helpers import device_registry as dr
            device_registry = dr.async_get(self.hass)
            device = device_registry.async_get(device_id)
            _LOGGER.debug("Компонент %s: устройство найдено = %s", self._component_name, device is not None)
            
            if device:
                _LOGGER.info("Компонент %s: привязываем к устройству %s (identifiers: %s)", 
                           self._component_name, device.name, device.identifiers)
                # Возвращаем DeviceInfo с теми же identifiers что и у оригинального устройства
                return DeviceInfo(
                    identifiers=device.identifiers,
                    connections=device.connections,
                )
            else:
                _LOGGER.warning("Компонент %s: устройство с ID %s не найдено в реестре", 
                              self._component_name, device_id)
        return None

    @property
    def available(self) -> bool:
        """Доступность сенсора."""
        return self.coordinator.last_update_success


class MaintenanceStatusSensor(MaintenanceBaseSensor, SensorEntity):
    """Сенсор статуса обслуживания."""

    def __init__(
        self,
        coordinator: MaintenanceCoordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Инициализация сенсора статуса."""
        super().__init__(coordinator, config_entry)
        component_name_safe = self._component_name.lower().replace(" ", "_")
        self._attr_unique_id = f"{config_entry.entry_id}{STATUS_SUFFIX}"
        self._attr_name = f"{self._component_name} - Статус обслуживания"
        # Устанавливаем правильный entity_id
        self.entity_id = f"sensor.{component_name_safe}{STATUS_SUFFIX}"

    @property
    def native_value(self) -> str | None:
        """Текущее значение сенсора."""
        if not self.coordinator.data:
            return None
        return self.coordinator.data.get("status")

    @property
    def icon(self) -> str:
        """Иконка сенсора."""
        if not self.coordinator.data:
            return "mdi:help-circle"
        
        status = self.coordinator.data.get("status")
        if status == MAINTENANCE_STATUS_OK:
            return "mdi:check-circle"
        elif status == MAINTENANCE_STATUS_DUE:
            return "mdi:alert-circle"
        elif status == MAINTENANCE_STATUS_OVERDUE:
            return "mdi:alert-circle-outline"
        return "mdi:help-circle"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Дополнительные атрибуты сенсора."""
        if not self.coordinator.data:
            return {}
        
        return {
            "days_until_maintenance": self.coordinator.data.get("days_until_maintenance"),
            "last_maintenance_date": self.coordinator.data.get("last_maintenance_date"),
            "next_maintenance_date": self.coordinator.data.get("next_maintenance_date"),
            "maintenance_interval": self.coordinator.data.get("maintenance_interval"),
            "component_name": self._component_name,
        }


class MaintenanceDaysSensor(MaintenanceBaseSensor, SensorEntity):
    """Сенсор дней до обслуживания."""

    def __init__(
        self,
        coordinator: MaintenanceCoordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Инициализация сенсора дней."""
        super().__init__(coordinator, config_entry)
        component_name_safe = self._component_name.lower().replace(" ", "_")
        self._attr_unique_id = f"{config_entry.entry_id}{DAYS_SUFFIX}"
        self._attr_name = f"{self._component_name} - Дни до обслуживания"
        self._attr_device_class = SensorDeviceClass.DURATION
        self._attr_native_unit_of_measurement = UnitOfTime.DAYS
        # Устанавливаем правильный entity_id
        self.entity_id = f"sensor.{component_name_safe}{DAYS_SUFFIX}"

    @property
    def native_value(self) -> int | None:
        """Текущее значение сенсора."""
        if not self.coordinator.data:
            return None
        return self.coordinator.data.get("days_until_maintenance")

    @property
    def icon(self) -> str:
        """Иконка сенсора."""
        if not self.coordinator.data:
            return "mdi:calendar-clock"
        
        days = self.coordinator.data.get("days_until_maintenance", 0)
        if days < 0:
            return "mdi:calendar-alert"
        elif days <= 7:
            return "mdi:calendar-warning"
        else:
            return "mdi:calendar-check"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Дополнительные атрибуты сенсора."""
        if not self.coordinator.data:
            return {}
        
        return {
            "status": self.coordinator.data.get("status"),
            "last_maintenance_date": self.coordinator.data.get("last_maintenance_date"),
            "next_maintenance_date": self.coordinator.data.get("next_maintenance_date"),
            "maintenance_interval": self.coordinator.data.get("maintenance_interval"),
            "component_name": self._component_name,
        } 