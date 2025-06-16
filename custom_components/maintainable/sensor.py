"""Платформа сенсоров для интеграции Maintainable."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import MaintainableEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Настройка сенсоров из конфигурационной записи."""
    config = config_entry.data
    
    # Создаем сенсор для каждой записи конфигурации
    async_add_entities([MaintainableSensor(config, config_entry.entry_id)], True)


class MaintainableSensor(MaintainableEntity, SensorEntity):
    """Сенсор для отслеживания статуса обслуживания."""

    def __init__(self, config: dict[str, Any], entry_id: str) -> None:
        """Инициализация сенсора обслуживания."""
        super().__init__(config, entry_id)
        self._attr_device_class = None
        self._attr_native_unit_of_measurement = None

    @property
    def native_value(self) -> str | None:
        """Возвращает значение сенсора - статус обслуживания."""
        return self._get_status()

    @property
    def state_class(self) -> str | None:
        """Класс состояния сенсора."""
        return None

    async def async_update(self) -> None:
        """Обновление состояния сенсора."""
        # Здесь можно добавить логику обновления, если нужно
        pass 