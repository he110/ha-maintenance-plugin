"""Глобальные сенсоры для подсчета компонентов обслуживания."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN, STATE_OVERDUE, STATE_DUE, STATE_OK

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Настройка глобальных сенсоров подсчета."""
    # Проверяем, есть ли уже созданные глобальные сенсоры в реестре сущностей
    entity_registry = er.async_get(hass)
    
    overdue_exists = entity_registry.async_get_entity_id(
        "sensor", DOMAIN, f"{DOMAIN}_overdue_count"
    )
    due_exists = entity_registry.async_get_entity_id(
        "sensor", DOMAIN, f"{DOMAIN}_due_count"
    )
    
    # Создаем только те сенсоры, которых еще нет
    entities = []
    if not overdue_exists:
        entities.append(MaintenanceOverdueCountSensor(hass))
        _LOGGER.debug("Creating maintenance overdue count sensor")
    
    if not due_exists:
        entities.append(MaintenanceDueCountSensor(hass))
        _LOGGER.debug("Creating maintenance due count sensor")
    
    if entities:
        async_add_entities(entities)
    else:
        _LOGGER.debug("Global maintenance sensors already exist, skipping creation")


class MaintenanceCountSensor(SensorEntity):
    """Базовый класс для сенсоров подсчета компонентов обслуживания."""

    def __init__(self, hass: HomeAssistant, status_filter: str) -> None:
        """Инициализация сенсора подсчета."""
        self.hass = hass
        self._status_filter = status_filter
        self._attr_state_class = None
        self._attr_native_unit_of_measurement = None
        self._attr_icon = "mdi:wrench"
        self._attr_should_poll = False
        
        # Подписываемся на изменения всех сенсоров статуса
        async_track_state_change_event(
            hass, None, self._handle_state_change
        )

    @callback
    def _handle_state_change(self, event) -> None:
        """Обработка изменения состояния сенсоров."""
        entity_id = event.data.get("entity_id")
        if entity_id and entity_id.endswith("_status") and entity_id.startswith("sensor."):
            self.async_schedule_update_ha_state()

    def _get_matching_entities(self) -> list[dict[str, Any]]:
        """Получить список сущностей, соответствующих фильтру."""
        matching_entities = []
        
        for entity_id in self.hass.states.async_entity_ids("sensor"):
            if entity_id.endswith("_status"):
                state = self.hass.states.get(entity_id)
                if state and state.attributes.get("status") == self._status_filter:
                    matching_entities.append({
                        "entity_id": entity_id,
                        "name": state.name or entity_id,
                        "status": state.attributes.get("status"),
                        "days_remaining": state.attributes.get("days_remaining"),
                        "last_maintenance": state.attributes.get("last_maintenance"),
                        "next_maintenance": state.attributes.get("next_maintenance"),
                        "maintenance_interval": state.attributes.get("maintenance_interval"),
                    })
        
        return matching_entities

    @property
    def native_value(self) -> int:
        """Возвращает количество компонентов."""
        return len(self._get_matching_entities())

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Дополнительные атрибуты состояния."""
        entities = self._get_matching_entities()
        return {
            "items": [entity["name"] for entity in entities],
            "entity_ids": [entity["entity_id"] for entity in entities],
            "details": entities,
        }


class MaintenanceOverdueCountSensor(MaintenanceCountSensor):
    """Сенсор подсчета просроченных компонентов обслуживания."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Инициализация сенсора просроченных компонентов."""
        super().__init__(hass, STATE_OVERDUE)
        self._attr_name = "Maintenance Overdue Count"
        self._attr_unique_id = f"{DOMAIN}_overdue_count"
        self._attr_icon = "mdi:alert-circle"
        self._attr_translation_key = "maintenance_overdue_count"

    @property
    def icon(self) -> str:
        """Иконка сенсора в зависимости от значения."""
        count = self.native_value
        if count > 0:
            return "mdi:alert-circle"
        return "mdi:check-circle"


class MaintenanceDueCountSensor(MaintenanceCountSensor):
    """Сенсор подсчета компонентов, требующих обслуживания."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Инициализация сенсора компонентов требующих обслуживания."""
        super().__init__(hass, STATE_DUE)
        self._attr_name = "Maintenance Due Count"
        self._attr_unique_id = f"{DOMAIN}_due_count"
        self._attr_icon = "mdi:clock-alert"
        self._attr_translation_key = "maintenance_due_count"

    @property
    def icon(self) -> str:
        """Иконка сенсора в зависимости от значения."""
        count = self.native_value
        if count > 0:
            return "mdi:clock-alert"
        return "mdi:check-circle" 