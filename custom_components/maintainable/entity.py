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
    CONF_DEVICE_CLASS,
    CONF_MAINTENANCE_INTERVAL,
    CONF_NAME,
    DEVICE_CLASS_ICONS,
    DOMAIN,
    STATE_DUE,
    STATE_OK,
    STATE_OVERDUE,
)


class MaintainableEntity(RestoreEntity):
    """Базовая сущность для обслуживаемых компонентов."""

    def __init__(self, config: dict[str, Any]) -> None:
        """Инициализация сущности обслуживаемого компонента."""
        self._attr_name = config[CONF_NAME]
        self._maintenance_interval = config[CONF_MAINTENANCE_INTERVAL]
        self._device_class = config[CONF_DEVICE_CLASS]
        self._last_maintenance: datetime | None = None
        self._attr_unique_id = f"{DOMAIN}_{self._attr_name.lower().replace(' ', '_')}"

    @property
    def device_info(self) -> dict[str, Any]:
        """Информация об устройстве."""
        return {
            "identifiers": {(DOMAIN, self._attr_unique_id)},
            "name": self._attr_name,
            "manufacturer": "Maintainable",
            "model": self._device_class.title(),
        }

    @property
    def icon(self) -> str:
        """Иконка сущности."""
        return DEVICE_CLASS_ICONS.get(self._device_class, "mdi:wrench")

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