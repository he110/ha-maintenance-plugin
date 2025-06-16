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
    options = config_entry.options
    
    # Создаем кнопку для каждой записи конфигурации
    async_add_entities([MaintainableButton(config, config_entry.entry_id, options)], True)


class MaintainableButton(MaintainableEntity, ButtonEntity):
    """Кнопка для выполнения обслуживания."""

    def __init__(self, config: dict[str, Any], entry_id: str, options: dict[str, Any] | None = None) -> None:
        """Инициализация кнопки обслуживания."""
        super().__init__(config, entry_id, options)
        self._attr_name = f"{self._attr_name} Обслужить"
        self._attr_unique_id = f"{self._attr_unique_id}_button"

    @property
    def icon(self) -> str:
        """Иконка кнопки."""
        return "mdi:wrench"

    @property
    def translation_key(self) -> str:
        """Ключ перевода для кнопки."""
        return "maintenance_perform"

    async def async_press(self) -> None:
        """Обработка нажатия кнопки."""
        _LOGGER.info("Выполнение обслуживания для %s", self.name)
        # Выполняем обслуживание, которое автоматически уведомит все связанные сущности
        self.perform_maintenance() 