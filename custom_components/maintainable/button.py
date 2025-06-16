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
    entities = [MaintainableButton(config, config_entry.entry_id, options)]
    async_add_entities(entities)
    _LOGGER.info(f"Created button entity for {config.get('name', 'Unknown')}")


class MaintainableButton(MaintainableEntity, ButtonEntity):
    """Кнопка для выполнения обслуживания."""

    def __init__(self, config: dict[str, Any], entry_id: str, options: dict[str, Any] | None = None) -> None:
        """Инициализация кнопки обслуживания."""
        super().__init__(config, entry_id, options)
        self._attr_name = f"{config['name']} Perform Maintenance"
        self._attr_unique_id = f"{self._attr_unique_id}_button"
        _LOGGER.info(f"Initialized button with unique_id: {self._attr_unique_id}")

    async def async_added_to_hass(self) -> None:
        """Вызывается при добавлении кнопки в Home Assistant."""
        await super().async_added_to_hass()
        # Немедленно записываем состояние чтобы кнопка стала доступной
        self.async_write_ha_state()
        _LOGGER.info(f"Button {self.entity_id} added to HA and state written")

    @property
    def available(self) -> bool:
        """Кнопка всегда доступна."""
        return True

    @property
    def icon(self) -> str:
        """Иконка кнопки."""
        return "mdi:wrench"

    @property
    def translation_key(self) -> str:
        """Ключ перевода для кнопки."""
        return "perform_maintenance"

    async def async_press(self) -> None:
        """Обработка нажатия кнопки."""
        try:
            _LOGGER.info("Выполнение обслуживания для %s", self.name)
            _LOGGER.debug(f"Button entity_id: {self.entity_id}")
            _LOGGER.debug(f"Button unique_id: {self.unique_id}")
            _LOGGER.debug(f"Button available: {self.available}")
            
            # Проверяем что метод доступен
            if hasattr(self, 'perform_maintenance') and callable(getattr(self, 'perform_maintenance')):
                # Выполняем обслуживание, которое автоматически уведомит все связанные сущности
                self.perform_maintenance()
                _LOGGER.info("Обслуживание выполнено успешно для %s", self.name)
            else:
                _LOGGER.error("Метод perform_maintenance недоступен для %s", self.name)
        except Exception as e:
            _LOGGER.error("Ошибка при выполнении обслуживания для %s: %s", self.name, e) 