"""
Интеграция Maintainable для Home Assistant.
Позволяет отслеживать объекты, требующие периодического обслуживания.
"""
from __future__ import annotations

import logging
from datetime import timedelta, date
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall, ServiceResponse, SupportsResponse
from homeassistant.helpers import config_validation as cv
from homeassistant.util import dt as dt_util
import voluptuous as vol

from .const import DOMAIN, STATE_OVERDUE, STATE_DUE, STATE_OK, MAX_PAST_DAYS

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BUTTON]

SCAN_INTERVAL = timedelta(minutes=1)

# Схемы для services
SERVICE_GET_OVERDUE_ITEMS = "get_overdue_items"
SERVICE_GET_DUE_ITEMS = "get_due_items"
SERVICE_GET_ALL_ITEMS = "get_all_items"
SERVICE_SET_LAST_MAINTENANCE = "set_last_maintenance"


# Схема для service set_last_maintenance
SERVICE_SET_LAST_MAINTENANCE_SCHEMA = vol.Schema({
    vol.Required("entity_id"): cv.entity_id,
    vol.Required("date"): cv.date,
})


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Настройка интеграции из конфигурационной записи."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN].setdefault(entry.entry_id, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "config": entry.data,
        "entities": {},  # Хранилище для связи между сущностями
    }

    # Устанавливаем флаг для создания глобальных сенсоров
    if '_global_sensors_created' not in hass.data[DOMAIN]:
        hass.data[DOMAIN]['_global_sensors_created'] = False

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Регистрируем services
    await _async_setup_services(hass)

    # Регистрируем обработчик обновления опций
    entry.async_on_unload(entry.add_update_listener(async_update_options))

    return True


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Обновление опций конфигурационной записи."""
    # Обновляем опции для всех сущностей этой записи
    if entry.entry_id in hass.data[DOMAIN]:
        entities_dict = hass.data[DOMAIN][entry.entry_id]["entities"]
        for entity in entities_dict.values():
            if hasattr(entity, 'update_options'):
                entity.update_options(entry.options)
    
    _LOGGER.info(f"Updated options for {entry.title}")


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Выгрузка конфигурационной записи."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
        
        # Если это была последняя запись, удаляем services
        if not hass.data[DOMAIN]:
            hass.services.async_remove(DOMAIN, SERVICE_GET_OVERDUE_ITEMS)
            hass.services.async_remove(DOMAIN, SERVICE_GET_DUE_ITEMS) 
            hass.services.async_remove(DOMAIN, SERVICE_GET_ALL_ITEMS)
            hass.services.async_remove(DOMAIN, SERVICE_SET_LAST_MAINTENANCE)

    return unload_ok


def _is_status_sensor(entity_id: str) -> bool:
    """Проверяет, является ли сущность основным сенсором статуса."""
    return entity_id.endswith("_status")


def _find_entity_by_id(hass: HomeAssistant, entity_id: str) -> Any | None:
    """Быстрый поиск сущности по entity_id с использованием реестра сущностей."""
    # Сначала пробуем найти через реестр сущностей Home Assistant
    entity_registry = hass.helpers.entity_registry.async_get(hass)
    entity_entry = entity_registry.async_get(entity_id)
    
    if entity_entry and entity_entry.platform == DOMAIN:
        # Ищем в нашем хранилище
        for entry_data in hass.data[DOMAIN].values():
            if isinstance(entry_data, dict) and "entities" in entry_data:
                if entity_id in entry_data["entities"]:
                    return entry_data["entities"][entity_id]
    
    return None


def _get_all_status_entities(hass: HomeAssistant) -> list[tuple[str, Any]]:
    """Получить все сущности статуса для оптимизации сервисов."""
    entities = []
    
    for entry_data in hass.data[DOMAIN].values():
        if isinstance(entry_data, dict) and "entities" in entry_data:
            for entity_id, entity in entry_data["entities"].items():
                if (_is_status_sensor(entity_id) and 
                    hasattr(entity, '_get_status')):
                    entities.append((entity_id, entity))
    
    return entities


async def _async_setup_services(hass: HomeAssistant) -> None:
    """Настройка services для интеграции."""
    
    async def async_get_overdue_items(call: ServiceCall) -> ServiceResponse:
        """Service для получения просроченных компонентов."""
        items = []
        
        # Используем оптимизированный поиск
        for entity_id, entity in _get_all_status_entities(hass):
            try:
                if entity._get_status() == STATE_OVERDUE:
                    items.append({
                        "entity_id": entity_id,
                        "name": entity.name,
                        "status": entity._get_status(),
                        "days_remaining": entity._get_days_remaining(),
                        "last_maintenance": entity._last_maintenance.isoformat() if entity._last_maintenance else None,
                        "next_maintenance": entity._get_next_maintenance_date().isoformat(),
                        "maintenance_interval": entity._maintenance_interval,
                    })
            except Exception as e:
                _LOGGER.error(f"Error processing entity {entity_id}: {e}")
        
        return {"items": items}

    async def async_get_due_items(call: ServiceCall) -> ServiceResponse:
        """Service для получения компонентов требующих обслуживания."""
        items = []
        
        # Используем оптимизированный поиск
        for entity_id, entity in _get_all_status_entities(hass):
            try:
                if entity._get_status() == STATE_DUE:
                    items.append({
                        "entity_id": entity_id,
                        "name": entity.name,
                        "status": entity._get_status(),
                        "days_remaining": entity._get_days_remaining(),
                        "last_maintenance": entity._last_maintenance.isoformat() if entity._last_maintenance else None,
                        "next_maintenance": entity._get_next_maintenance_date().isoformat(),
                        "maintenance_interval": entity._maintenance_interval,
                    })
            except Exception as e:
                _LOGGER.error(f"Error processing entity {entity_id}: {e}")
        
        return {"items": items}

    async def async_get_all_items(call: ServiceCall) -> ServiceResponse:
        """Service для получения всех компонентов."""
        items = []
        
        # Используем оптимизированный поиск
        for entity_id, entity in _get_all_status_entities(hass):
            try:
                items.append({
                    "entity_id": entity_id,
                    "name": entity.name,
                    "status": entity._get_status(),
                    "days_remaining": entity._get_days_remaining(),
                    "last_maintenance": entity._last_maintenance.isoformat() if entity._last_maintenance else None,
                    "next_maintenance": entity._get_next_maintenance_date().isoformat(),
                    "maintenance_interval": entity._maintenance_interval,
                })
            except Exception as e:
                _LOGGER.error(f"Error processing entity {entity_id}: {e}")
        
        return {"items": items}

    async def async_set_last_maintenance(call: ServiceCall) -> None:
        """Service для установки даты последнего обслуживания."""
        entity_id = call.data["entity_id"]
        new_date = call.data["date"]
        
        # Дополнительная валидация на уровне сервиса
        if not isinstance(new_date, date):
            _LOGGER.error(f"Invalid date format for {entity_id}: {new_date}")
            return
        
        # Проверяем что дата не в будущем
        if new_date > dt_util.now().date():
            _LOGGER.error(f"Maintenance date cannot be in the future for {entity_id}: {new_date}")
            return
        
        # Проверяем что дата не слишком далеко в прошлом
        max_past_date = dt_util.now().date() - timedelta(days=MAX_PAST_DAYS)
        if new_date < max_past_date:
            _LOGGER.error(f"Maintenance date too far in the past for {entity_id}: {new_date}")
            return
        
        # Используем оптимизированный поиск
        target_entity = _find_entity_by_id(hass, entity_id)
        
        if not target_entity:
            _LOGGER.error(f"Entity {entity_id} not found")
            return
        
        # Устанавливаем новую дату последнего обслуживания
        if hasattr(target_entity, 'set_last_maintenance'):
            try:
                await target_entity.set_last_maintenance(new_date)
                _LOGGER.info(f"Set last maintenance date for {entity_id} to {new_date}")
            except ValueError as e:
                _LOGGER.error(f"Validation error setting maintenance date for {entity_id}: {e}")
            except Exception as e:
                _LOGGER.error(f"Error setting maintenance date for {entity_id}: {e}")
        else:
            _LOGGER.error(f"Entity {entity_id} does not support setting maintenance date")

    # Регистрируем services только если они еще не зарегистрированы
    if not hass.services.has_service(DOMAIN, SERVICE_GET_OVERDUE_ITEMS):
        hass.services.async_register(
            DOMAIN,
            SERVICE_GET_OVERDUE_ITEMS,
            async_get_overdue_items,
            supports_response=SupportsResponse.ONLY,
        )

    if not hass.services.has_service(DOMAIN, SERVICE_GET_DUE_ITEMS):
        hass.services.async_register(
            DOMAIN,
            SERVICE_GET_DUE_ITEMS,
            async_get_due_items,
            supports_response=SupportsResponse.ONLY,
        )

    if not hass.services.has_service(DOMAIN, SERVICE_GET_ALL_ITEMS):
        hass.services.async_register(
            DOMAIN,
            SERVICE_GET_ALL_ITEMS,
            async_get_all_items,
            supports_response=SupportsResponse.ONLY,
        )

    if not hass.services.has_service(DOMAIN, SERVICE_SET_LAST_MAINTENANCE):
        hass.services.async_register(
            DOMAIN,
            SERVICE_SET_LAST_MAINTENANCE,
            async_set_last_maintenance,
            schema=SERVICE_SET_LAST_MAINTENANCE_SCHEMA,
        )


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Перезагрузка конфигурационной записи."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry) 