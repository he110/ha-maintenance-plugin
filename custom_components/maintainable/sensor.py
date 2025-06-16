"""Сенсоры для интеграции Maintainable."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    STATE_DUE,
    STATE_OK,
    STATE_OVERDUE,
)
from .entity import MaintainableEntity
from .global_sensors import async_setup_global_sensors


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Настройка сенсоров из конфигурационной записи."""
    config = config_entry.data
    options = config_entry.options
    
    # Создаем основной сенсор статуса
    entities = [
        MaintainableStatusSensor(config, config_entry.entry_id, options)
    ]
    
    async_add_entities(entities)
    
    # Создаем глобальные сенсоры подсчета (только один раз для всей интеграции)
    await async_setup_global_sensors(hass, async_add_entities)


class MaintainableStatusSensor(MaintainableEntity, SensorEntity):
    """Сенсор статуса обслуживания."""

    def __init__(self, config: dict, entry_id: str, options: dict | None = None) -> None:
        """Инициализация сенсора статуса обслуживания."""
        super().__init__(config, entry_id, options)
        self._attr_name = f"{config['name']} Status"
        self._attr_unique_id = f"{self._attr_unique_id}_status"

    @property
    def state(self) -> str:
        """Возвращает текущее состояние сенсора."""
        return self._get_status()

    @property
    def icon(self) -> str:
        """Иконка сенсора в зависимости от статуса."""
        status = self._get_status()
        if status == STATE_OVERDUE:
            return "mdi:alert-circle"
        elif status == STATE_DUE:
            return "mdi:clock-alert"
        else:
            return "mdi:check-circle"

    @property
    def translation_key(self) -> str:
        """Ключ перевода для сенсора."""
        return "maintenance_status"


 