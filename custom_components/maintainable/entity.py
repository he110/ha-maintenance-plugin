"""Базовая сущность для интеграции Maintainable."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from homeassistant.helpers.entity import Entity
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.util import dt as dt_util

from .const import (
    ATTR_DAYS_REMAINING,
    ATTR_LAST_MAINTENANCE,
    ATTR_MAINTENANCE_INTERVAL,
    ATTR_NEXT_MAINTENANCE,
    ATTR_STATUS,
    CONF_DEVICE_ID,
    CONF_MAINTENANCE_INTERVAL,
    CONF_NAME,
    DEFAULT_ICON,
    DOMAIN,
    STATE_DUE,
    STATE_OK,
    STATE_OVERDUE,
)


class MaintainableEntity(RestoreEntity):
    """Базовая сущность для обслуживаемых компонентов."""

    def __init__(self, config: dict[str, Any], entry_id: str) -> None:
        """Инициализация сущности обслуживаемого компонента."""
        self._attr_name = config[CONF_NAME]
        self._maintenance_interval = config[CONF_MAINTENANCE_INTERVAL]
        self._device_id = config.get(CONF_DEVICE_ID)
        self._last_maintenance: datetime | None = None
        self._entry_id = entry_id
        
        # Создаем уникальный ID на основе entry_id для избежания конфликтов
        clean_name = self._attr_name.lower().replace(' ', '_').replace('-', '_')
        self._attr_unique_id = f"{DOMAIN}_{entry_id}_{clean_name}"
        
        # Если указано устройство, привязываем к нему
        if self._device_id:
            self._attr_device_id = self._device_id

    @property
    def icon(self) -> str:
        """Иконка сущности."""
        return DEFAULT_ICON

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Дополнительные атрибуты состояния."""
        attrs = {
            ATTR_MAINTENANCE_INTERVAL: self._maintenance_interval,
            ATTR_STATUS: self._get_status(),
        }

        if self._last_maintenance:
            attrs[ATTR_LAST_MAINTENANCE] = self._last_maintenance.isoformat()
            attrs[ATTR_NEXT_MAINTENANCE] = self._get_next_maintenance_date().isoformat()
            attrs[ATTR_DAYS_REMAINING] = self._get_days_remaining()

        return attrs

    def _get_status(self) -> str:
        """Получить статус обслуживания."""
        if not self._last_maintenance:
            return STATE_OVERDUE

        days_remaining = self._get_days_remaining()
        
        if days_remaining < 0:
            return STATE_OVERDUE
        elif days_remaining <= 7:  # Предупреждение за неделю
            return STATE_DUE
        else:
            return STATE_OK

    def _get_next_maintenance_date(self) -> datetime:
        """Получить дату следующего обслуживания."""
        if not self._last_maintenance:
            return dt_util.now()
        
        return self._last_maintenance + timedelta(days=self._maintenance_interval)

    def _get_days_remaining(self) -> int:
        """Получить количество дней до следующего обслуживания."""
        if not self._last_maintenance:
            return -999
        
        next_maintenance = self._get_next_maintenance_date()
        return (next_maintenance - dt_util.now()).days

    async def async_added_to_hass(self) -> None:
        """Вызывается при добавлении сущности в Home Assistant."""
        await super().async_added_to_hass()
        
        # Регистрируем сущность в общем хранилище
        if DOMAIN in self.hass.data and self._entry_id in self.hass.data[DOMAIN]:
            self.hass.data[DOMAIN][self._entry_id]["entities"][self.entity_id] = self
        
        # Восстанавливаем состояние из хранилища
        if (state := await self.async_get_last_state()) is not None:
            if last_maintenance_str := state.attributes.get(ATTR_LAST_MAINTENANCE):
                try:
                    self._last_maintenance = datetime.fromisoformat(
                        last_maintenance_str.replace("Z", "+00:00")
                    )
                except ValueError:
                    # Если не можем распарсить дату, оставляем None
                    pass

    def perform_maintenance(self) -> None:
        """Выполнить обслуживание - обновить дату последнего обслуживания."""
        self._last_maintenance = dt_util.now()
        self.async_write_ha_state()
        
        # Уведомляем все связанные сущности об изменении
        if DOMAIN in self.hass.data and self._entry_id in self.hass.data[DOMAIN]:
            entities = self.hass.data[DOMAIN][self._entry_id]["entities"]
            for entity_id, entity in entities.items():
                if entity != self:  # Не уведомляем себя
                    # Обновляем данные связанной сущности
                    entity._last_maintenance = self._last_maintenance
                    entity.async_write_ha_state() 