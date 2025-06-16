"""Глобальные сенсоры подсчета для интеграции Maintainable."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event

from .const import DOMAIN, STATE_OVERDUE, STATE_DUE

_LOGGER = logging.getLogger(__name__)


async def async_setup_global_sensors(
    hass: HomeAssistant,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Настройка глобальных сенсоров подсчета."""
    # Создаем глобальные сенсоры только один раз
    if hass.data[DOMAIN].get('_global_sensors_created'):
        return
    
    entities = [
        MaintenanceOverdueCountSensor(hass),
        MaintenanceDueCountSensor(hass),
    ]
    
    async_add_entities(entities)
    hass.data[DOMAIN]['_global_sensors_created'] = True
    _LOGGER.info("Created global maintenance count sensors")


class MaintenanceCountSensorBase(SensorEntity):
    """Базовый класс для сенсоров подсчета обслуживания."""

    def __init__(self, hass: HomeAssistant, status_filter: str) -> None:
        """Инициализация базового сенсора подсчета."""
        self.hass = hass
        self._status_filter = status_filter
        self._state = 0
        self._items = []
        self._entity_ids = []
        self._details = []
        self._unsub_state_changed = None

    @property
    def should_poll(self) -> bool:
        """Не нужно опрашивать - обновляется по событиям."""
        return False

    @property
    def state(self) -> int:
        """Возвращает количество компонентов."""
        return self._state

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Дополнительные атрибуты сенсора."""
        return {
            "items": self._items,
            "entity_ids": self._entity_ids,
            "details": self._details,
        }

    async def async_added_to_hass(self) -> None:
        """Вызывается при добавлении сенсора в Home Assistant."""
        await super().async_added_to_hass()
        
        # Подписываемся на изменения состояний всех сенсоров maintainable
        self._unsub_state_changed = async_track_state_change_event(
            self.hass,
            None,  # Отслеживаем все сущности
            self._async_state_changed_listener
        )
        
        # Выполняем первоначальное обновление
        await self._async_update_count()

    async def async_will_remove_from_hass(self) -> None:
        """Вызывается при удалении сенсора из Home Assistant."""
        if self._unsub_state_changed:
            self._unsub_state_changed()
            self._unsub_state_changed = None
        await super().async_will_remove_from_hass()

    @callback
    def _async_state_changed_listener(self, event) -> None:
        """Обработчик изменения состояний сущностей."""
        entity_id = event.data.get("entity_id")
        
        # Проверяем, что это сенсор статуса maintainable
        if (entity_id and 
            entity_id.startswith("sensor.") and 
            entity_id.endswith("_status")):
            
            # Планируем обновление счетчика
            self.hass.async_create_task(self._async_update_count())

    async def _async_update_count(self) -> None:
        """Обновление счетчика компонентов."""
        try:
            items = []
            entity_ids = []
            details = []
            
            # Ищем все сенсоры статуса maintainable
            for entity_id, state in self.hass.states.async_all():
                if (entity_id.startswith("sensor.") and 
                    entity_id.endswith("_status") and
                    state.attributes.get("status") == self._status_filter):
                    
                    name = state.attributes.get("friendly_name", entity_id)
                    items.append(name)
                    entity_ids.append(entity_id)
                    
                    # Добавляем подробную информацию
                    detail = {
                        "entity_id": entity_id,
                        "name": name,
                        "status": state.attributes.get("status"),
                        "days_remaining": state.attributes.get("days_remaining"),
                        "last_maintenance": state.attributes.get("last_maintenance"),
                        "next_maintenance": state.attributes.get("next_maintenance"),
                        "maintenance_interval_days": state.attributes.get("maintenance_interval_days"),
                    }
                    details.append(detail)
            
            # Обновляем состояние
            self._state = len(items)
            self._items = items
            self._entity_ids = entity_ids
            self._details = details
            
            self.async_write_ha_state()
            
        except Exception as e:
            _LOGGER.error(f"Error updating {self.entity_id}: {e}")


class MaintenanceOverdueCountSensor(MaintenanceCountSensorBase):
    """Сенсор количества просроченных компонентов."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Инициализация сенсора просроченных компонентов."""
        super().__init__(hass, STATE_OVERDUE)
        self._attr_name = "Maintenance Overdue Count"
        self._attr_unique_id = "maintenance_overdue_count"
        self._attr_icon = "mdi:alert-circle"

    @property
    def icon(self) -> str:
        """Иконка сенсора в зависимости от количества."""
        if self._state > 0:
            return "mdi:alert-circle"
        return "mdi:check-circle"


class MaintenanceDueCountSensor(MaintenanceCountSensorBase):
    """Сенсор количества компонентов требующих обслуживания."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Инициализация сенсора компонентов требующих обслуживания."""
        super().__init__(hass, STATE_DUE)
        self._attr_name = "Maintenance Due Count"
        self._attr_unique_id = "maintenance_due_count"
        self._attr_icon = "mdi:clock-alert"

    @property
    def icon(self) -> str:
        """Иконка сенсора в зависимости от количества."""
        if self._state > 0:
            return "mdi:clock-alert"
        return "mdi:clock-check" 