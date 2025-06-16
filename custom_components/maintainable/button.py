"""Платформа кнопок для интеграции Maintainable."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.button import ButtonEntity
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
    """Настройка кнопок из конфигурационной записи."""
    config = config_entry.data
    
    # Создаем кнопку для каждой записи конфигурации
    async_add_entities([MaintenanceButton(config)], True)


class MaintenanceButton(MaintainableEntity, ButtonEntity):
    """Кнопка для выполнения обслуживания."""

    def __init__(self, config: dict[str, Any]) -> None:
        """Инициализация кнопки обслуживания."""
        super().__init__(config)
        self._attr_name = f"{self._attr_name} - Обслужить"
        self._attr_unique_id = f"{self._attr_unique_id}_button"

    @property
    def icon(self) -> str:
        """Иконка кнопки."""
        return "mdi:wrench"

    async def async_press(self) -> None:
        """Обработка нажатия кнопки."""
        _LOGGER.info("Выполнение обслуживания для %s", self._attr_name)
        self.perform_maintenance()
        
        # Найдем соответствующий сенсор и обновим его состояние
        sensor_entity_id = f"sensor.{self._attr_unique_id.replace('_button', '')}"
        if sensor_entity := self.hass.states.get(sensor_entity_id):
            # Попросим сенсор обновиться
            await self.hass.helpers.entity_component.async_update_entity(sensor_entity_id) 