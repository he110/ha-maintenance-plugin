"""Платформа сенсоров для интеграции Maintainable."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers import device_registry as dr
from homeassistant.util import dt as dt_util

from .const import (
    ATTR_DAYS_REMAINING,
    ATTR_LAST_MAINTENANCE,
    ATTR_MAINTENANCE_INTERVAL,
    ATTR_NEXT_MAINTENANCE,
    ATTR_STATUS,
    CONF_DEVICE_ID,
    CONF_LAST_MAINTENANCE,
    CONF_MAINTENANCE_INTERVAL,
    CONF_NAME,
    DOMAIN,
    ICON_DAYS,
    ICON_STATUS,
    STATE_DUE,
    STATE_OK,
    STATE_OVERDUE,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Настройка сенсоров из конфигурационной записи."""
    config = config_entry.data
    entry_id = config_entry.entry_id

    # Создаем оба сенсора
    entities = [
        MaintainableStatusSensor(config, entry_id),
        MaintainableDaysSensor(config, entry_id),
    ]
    
    async_add_entities(entities)
    _LOGGER.info("Created sensors for %s", config.get(CONF_NAME, "Unknown"))


class MaintainableSensorBase(SensorEntity):
    """Базовый класс для сенсоров обслуживания."""

    def __init__(self, config: dict[str, Any], entry_id: str) -> None:
        """Инициализация базового сенсора."""
        self._config = config
        self._entry_id = entry_id
        self._name = config[CONF_NAME]
        self._maintenance_interval = config[CONF_MAINTENANCE_INTERVAL]
        self._device_id = config.get(CONF_DEVICE_ID)
        
        # Получаем дату последнего обслуживания
        last_maintenance_str = config.get(CONF_LAST_MAINTENANCE)
        if last_maintenance_str:
            try:
                # Парсим дату из ISO формата
                last_maintenance_date = datetime.fromisoformat(last_maintenance_str).date()
                self._last_maintenance = datetime.combine(
                    last_maintenance_date, datetime.min.time()
                ).replace(tzinfo=dt_util.DEFAULT_TIME_ZONE)
            except (ValueError, TypeError):
                self._last_maintenance = dt_util.now()
        else:
            self._last_maintenance = dt_util.now()

        # Настройка автоматического обновления каждый день в полночь
        self._update_timer = None
        
    async def async_added_to_hass(self) -> None:
        """Вызывается при добавлении сенсора в Home Assistant."""
        await super().async_added_to_hass()
        
        # Настраиваем ежедневное обновление в 00:01
        self._update_timer = async_track_time_change(
            self.hass,
            self._async_daily_update,
            hour=0,
            minute=1,
            second=0
        )
        
        # Сохраняем ссылку на сенсор для кнопки
        if DOMAIN in self.hass.data and self._entry_id in self.hass.data[DOMAIN]:
            self.hass.data[DOMAIN][self._entry_id][f"sensor_{self._sensor_type}"] = self

    async def async_will_remove_from_hass(self) -> None:
        """Вызывается при удалении сенсора из Home Assistant."""
        if self._update_timer:
            self._update_timer()
            self._update_timer = None
        await super().async_will_remove_from_hass()

    async def _async_daily_update(self, now: datetime) -> None:
        """Ежедневное обновление состояния в полночь."""
        try:
            self.async_write_ha_state()
            _LOGGER.debug("Daily update for %s", self.entity_id)
        except Exception as e:
            _LOGGER.error("Error during daily update of %s: %s", self.entity_id, e)

    @property
    def device_info(self) -> DeviceInfo | None:
        """Информация об устройстве для привязки сенсора."""
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

    def _get_status(self) -> str:
        """Получить статус обслуживания."""
        days_remaining = self._get_days_remaining()
        
        if days_remaining < 0:
            return STATE_OVERDUE
        elif days_remaining <= 7:
            return STATE_DUE
        else:
            return STATE_OK

    def _get_next_maintenance_date(self) -> datetime:
        """Получить дату следующего обслуживания."""
        return self._last_maintenance + timedelta(days=self._maintenance_interval)

    def _get_days_remaining(self) -> int:
        """Получить количество дней до следующего обслуживания."""
        next_maintenance = self._get_next_maintenance_date()
        return (next_maintenance.date() - dt_util.now().date()).days

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Дополнительные атрибуты состояния."""
        return {
            ATTR_MAINTENANCE_INTERVAL: self._maintenance_interval,
            ATTR_LAST_MAINTENANCE: self._last_maintenance.date().isoformat(),
            ATTR_NEXT_MAINTENANCE: self._get_next_maintenance_date().date().isoformat(),
            ATTR_DAYS_REMAINING: self._get_days_remaining(),
            ATTR_STATUS: self._get_status(),
        }

    def update_last_maintenance(self, new_date: datetime) -> None:
        """Обновить дату последнего обслуживания."""
        self._last_maintenance = new_date
        self.async_write_ha_state()


class MaintainableStatusSensor(MaintainableSensorBase):
    """Сенсор статуса обслуживания."""
    
    _sensor_type = "status"

    def __init__(self, config: dict[str, Any], entry_id: str) -> None:
        """Инициализация сенсора статуса."""
        super().__init__(config, entry_id)
        self._attr_name = f"{self._name} Status"
        self._attr_unique_id = f"{DOMAIN}_{entry_id}_status"

    @property
    def native_value(self) -> str:
        """Текущее состояние сенсора."""
        return self._get_status()

    @property
    def icon(self) -> str:
        """Иконка сенсора."""
        return ICON_STATUS


class MaintainableDaysSensor(MaintainableSensorBase):
    """Сенсор дней до обслуживания."""
    
    _sensor_type = "days"

    def __init__(self, config: dict[str, Any], entry_id: str) -> None:
        """Инициализация сенсора дней."""
        super().__init__(config, entry_id)
        self._attr_name = f"{self._name} Days"
        self._attr_unique_id = f"{DOMAIN}_{entry_id}_days"
        self._attr_native_unit_of_measurement = "дней"

    @property
    def native_value(self) -> int:
        """Текущее состояние сенсора."""
        return self._get_days_remaining()

    @property
    def icon(self) -> str:
        """Иконка сенсора."""
        return ICON_DAYS 