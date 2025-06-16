"""Интеграция для учёта компонентов, требующих периодического обслуживания."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback, ServiceCall
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry
from homeassistant.helpers.event import async_track_time_interval
import voluptuous as vol
from homeassistant.helpers import config_validation as cv

from .const import (
    DATA_COORDINATOR,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import MaintenanceCoordinator

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(minutes=30)  # Проверка каждые 30 минут


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Настройка интеграции."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Настройка записи конфигурации."""
    hass.data.setdefault(DOMAIN, {})
    
    # Создаем координатор для управления данными
    coordinator = MaintenanceCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    
    hass.data[DOMAIN][entry.entry_id] = {
        DATA_COORDINATOR: coordinator,
    }
    
    # Настраиваем платформы
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    # Настраиваем автоматическое обновление
    async def update_maintenance_status(now):
        """Обновляет статус обслуживания."""
        await coordinator.async_request_refresh()
    
    # Запускаем обновление каждые 30 минут
    entry.async_on_unload(
        async_track_time_interval(hass, update_maintenance_status, SCAN_INTERVAL)
    )
    
    # Регистрируем сервисы
    await _async_register_services(hass)
    
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Выгрузка записи конфигурации."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
    
    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Перезагрузка записи конфигурации."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)


async def _async_register_services(hass: HomeAssistant) -> None:
    """Регистрация сервисов интеграции."""
    
    # Схема для сервиса выполнения обслуживания
    perform_maintenance_schema = vol.Schema({
        vol.Required("entity_id"): cv.entity_id,
    })
    
    # Схема для сервиса установки даты обслуживания
    set_last_maintenance_schema = vol.Schema({
        vol.Required("entity_id"): cv.entity_id,
        vol.Required("maintenance_date"): cv.date,
    })
    
    async def handle_perform_maintenance(call: ServiceCall) -> None:
        """Обработка сервиса выполнения обслуживания."""
        entity_id = call.data["entity_id"]
        
        # Находим координатор по entity_id
        coordinator = _find_coordinator_by_entity_id(hass, entity_id)
        if coordinator:
            await coordinator.async_perform_maintenance()
        else:
            _LOGGER.error("Не найден координатор для сущности %s", entity_id)
    
    async def handle_set_last_maintenance(call: ServiceCall) -> None:
        """Обработка сервиса установки даты обслуживания."""
        entity_id = call.data["entity_id"]
        maintenance_date = call.data["maintenance_date"]
        
        # Находим координатор по entity_id
        coordinator = _find_coordinator_by_entity_id(hass, entity_id)
        if coordinator:
            # Конвертируем date в datetime
            from datetime import datetime, time
            maintenance_datetime = datetime.combine(maintenance_date, time())
            await coordinator.async_set_maintenance_date(maintenance_datetime)
        else:
            _LOGGER.error("Не найден координатор для сущности %s", entity_id)
    
    # Регистрируем сервисы только если они ещё не зарегистрированы
    if not hass.services.has_service(DOMAIN, "perform_maintenance"):
        hass.services.async_register(
            DOMAIN,
            "perform_maintenance",
            handle_perform_maintenance,
            schema=perform_maintenance_schema,
        )
    
    if not hass.services.has_service(DOMAIN, "set_last_maintenance"):
        hass.services.async_register(
            DOMAIN,
            "set_last_maintenance",
            handle_set_last_maintenance,
            schema=set_last_maintenance_schema,
        )


def _find_coordinator_by_entity_id(hass: HomeAssistant, entity_id: str) -> MaintenanceCoordinator | None:
    """Найти координатор по ID сущности."""
    # Проходим по всем записям интеграции
    for entry_id, entry_data in hass.data.get(DOMAIN, {}).items():
        if DATA_COORDINATOR in entry_data:
            coordinator = entry_data[DATA_COORDINATOR]
            
            # Проверяем, относится ли entity_id к этому координатору
            entry = coordinator.entry
            component_name = entry.data.get("name", "")
            component_name_safe = component_name.lower().replace(" ", "_")
            
            # Проверяем оба типа сенсоров
            expected_status_id = f"sensor.{component_name_safe}_m_status"
            expected_days_id = f"sensor.{component_name_safe}_m_days"
            
            if entity_id == expected_status_id or entity_id == expected_days_id:
                return coordinator
    
    return None 