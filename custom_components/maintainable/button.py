"""Платформа кнопок для интеграции Maintainable."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers import device_registry as dr
from homeassistant.util import dt as dt_util

from .const import (
    CONF_DEVICE_ID,
    CONF_LAST_MAINTENANCE,
    CONF_NAME,
    DOMAIN,
    ICON_BUTTON,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Настройка кнопок из конфигурационной записи."""
    config = config_entry.data
    entry_id = config_entry.entry_id
    
    # Создаем кнопку для выполнения обслуживания
    entities = [MaintainableButton(config, entry_id, config_entry)]
    async_add_entities(entities)
    _LOGGER.info("Created button for %s", config.get(CONF_NAME, "Unknown"))


class MaintainableButton(ButtonEntity):
    """Кнопка для выполнения обслуживания."""

    def __init__(self, config: dict[str, Any], entry_id: str, config_entry: ConfigEntry) -> None:
        """Инициализация кнопки обслуживания."""
        self._config = config
        self._entry_id = entry_id
        self._config_entry = config_entry
        self._name = config[CONF_NAME]
        self._device_id = config.get(CONF_DEVICE_ID)
        
        self._attr_name = f"{self._name} Perform Maintenance"
        self._attr_unique_id = f"{DOMAIN}_{entry_id}_button"

    @property
    def device_info(self) -> DeviceInfo | None:
        """Информация об устройстве для привязки кнопки."""
        if not self._device_id:
            return None
            
        device_registry = dr.async_get(self.hass)
        device = device_registry.async_get(self._device_id)
        
        if not device:
            return None
            
        return DeviceInfo(
            identifiers=device.identifiers,
            name=device.name,
        )

    @property
    def icon(self) -> str:
        """Иконка кнопки."""
        return ICON_BUTTON

    async def async_press(self) -> None:
        """Обработка нажатия кнопки."""
        try:
            _LOGGER.info("Выполнение обслуживания для %s", self._name)
            
            # Обновляем дату последнего обслуживания в конфигурации
            new_data = dict(self._config_entry.data)
            new_data[CONF_LAST_MAINTENANCE] = dt_util.now().date().isoformat()
            
            self.hass.config_entries.async_update_entry(
                self._config_entry, data=new_data
            )
            
            # Обновляем состояние связанных сенсоров
            await self._update_sensors()
            
            _LOGGER.info("Обслуживание выполнено успешно для %s", self._name)
            
        except Exception as e:
            _LOGGER.error("Ошибка при выполнении обслуживания для %s: %s", self._name, e)

    async def _update_sensors(self) -> None:
        """Обновить состояние связанных сенсоров."""
        try:
            # Получаем ссылки на сенсоры из хранилища
            if (DOMAIN in self.hass.data and 
                self._entry_id in self.hass.data[DOMAIN]):
                
                entry_data = self.hass.data[DOMAIN][self._entry_id]
                current_date = dt_util.now()
                
                # Обновляем сенсор статуса
                if "sensor_status" in entry_data:
                    status_sensor = entry_data["sensor_status"]
                    status_sensor.update_last_maintenance(current_date)
                
                # Обновляем сенсор дней
                if "sensor_days" in entry_data:
                    days_sensor = entry_data["sensor_days"]
                    days_sensor.update_last_maintenance(current_date)
                    
        except Exception as e:
            _LOGGER.error("Ошибка при обновлении сенсоров: %s", e) 