"""Сенсоры для интеграции Maintainable."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import MaintainableEntity


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Настройка сенсоров из конфигурационной записи."""
    config = config_entry.data
    options = config_entry.options
    
    # Создаем два сенсора: статус и дни до обслуживания
    entities = [
        MaintainableStatusSensor(config, config_entry.entry_id, options),
        MaintainableDaysSensor(config, config_entry.entry_id, options),
    ]
    
    async_add_entities(entities)


class MaintainableStatusSensor(MaintainableEntity, SensorEntity):
    """Сенсор статуса обслуживания."""

    def __init__(self, config: dict[str, Any], entry_id: str, options: dict[str, Any] | None = None) -> None:
        """Инициализация сенсора статуса."""
        super().__init__(config, entry_id, options)
        self._attr_name = f"{self._attr_name} Статус"
        self._attr_unique_id = f"{self._attr_unique_id}_status"

    @property
    def state(self) -> str:
        """Возвращает текущее состояние сенсора."""
        return self._get_status()

    @property
    def translation_key(self) -> str:
        """Ключ перевода для сенсора."""
        return "maintenance_status"


class MaintainableDaysSensor(MaintainableEntity, SensorEntity):
    """Сенсор количества дней до обслуживания."""

    def __init__(self, config: dict[str, Any], entry_id: str, options: dict[str, Any] | None = None) -> None:
        """Инициализация сенсора дней."""
        super().__init__(config, entry_id, options)
        self._attr_name = f"{self._attr_name} Дни до обслуживания"
        self._attr_unique_id = f"{self._attr_unique_id}_days"
        self._attr_device_class = SensorDeviceClass.DURATION
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = "дней"

    @property
    def state(self) -> int:
        """Возвращает количество дней до обслуживания."""
        return self._get_days_remaining()

    @property
    def translation_key(self) -> str:
        """Ключ перевода для сенсора."""
        return "maintenance_days"

    @property
    def icon(self) -> str:
        """Иконка сенсора дней."""
        days = self._get_days_remaining()
        if days < 0:
            return "mdi:calendar-alert"
        elif days <= 7:
            return "mdi:calendar-clock"
        else:
            return "mdi:calendar-check"

    async def async_update(self) -> None:
        """Обновление состояния сенсора."""
        # Здесь можно добавить логику обновления, если нужно
        pass 