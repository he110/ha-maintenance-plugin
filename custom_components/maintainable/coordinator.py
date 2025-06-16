"""Координатор данных для интеграции Maintainable."""
from __future__ import annotations

import logging
from datetime import datetime, date, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    DOMAIN,
    MAINTENANCE_STATUS_OK,
    MAINTENANCE_STATUS_DUE,
    MAINTENANCE_STATUS_OVERDUE,
    DUE_THRESHOLD,
    EVENT_MAINTENANCE_DUE,
    EVENT_MAINTENANCE_OVERDUE,
    EVENT_MAINTENANCE_COMPLETED,
)

_LOGGER = logging.getLogger(__name__)

STORAGE_VERSION = 1
STORAGE_KEY = f"{DOMAIN}_data"


class MaintenanceCoordinator(DataUpdateCoordinator):
    """Координатор для управления данными обслуживания."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Инициализация координатора."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(hours=1),  # Обновление каждый час
        )
        self.entry = entry
        self.store = Store(hass, STORAGE_VERSION, f"{STORAGE_KEY}_{entry.entry_id}")
        self._data: dict[str, Any] = {}
        self._previous_status: dict[str, str] = {}

    async def _async_update_data(self) -> dict[str, Any]:
        """Обновление данных."""
        try:
            # Загружаем сохранённые данные
            stored_data = await self.store.async_load()
            if stored_data is None:
                # При первом запуске используем дату из конфигурации или текущую
                last_maintenance_date = self.entry.data.get("last_maintenance_date")
                if not last_maintenance_date:
                    last_maintenance_date = datetime.now().isoformat()
                
                stored_data = {
                    "last_maintenance_date": last_maintenance_date,
                    "maintenance_interval": self.entry.data.get("maintenance_interval", 30),
                    "name": self.entry.data.get("name", "Компонент"),
                }
                
                # Сохраняем начальные данные
                await self.store.async_save(stored_data)
                
                _LOGGER.info("Создан новый компонент: %s, дата последнего обслуживания: %s", 
                           stored_data["name"], last_maintenance_date)

            # Вычисляем текущий статус
            last_maintenance = datetime.fromisoformat(stored_data["last_maintenance_date"])
            interval = stored_data["maintenance_interval"]
            now = datetime.now()
            
            next_maintenance = last_maintenance + timedelta(days=interval)
            days_until_maintenance = (next_maintenance.date() - now.date()).days
            
            _LOGGER.debug("Компонент %s: последнее обслуживание %s, интервал %d дней, дней до обслуживания: %d", 
                         stored_data["name"], last_maintenance.date(), interval, days_until_maintenance)
            
            # Определяем статус
            if days_until_maintenance < 0:
                status = MAINTENANCE_STATUS_OVERDUE
            elif days_until_maintenance <= DUE_THRESHOLD:
                status = MAINTENANCE_STATUS_DUE
            else:
                status = MAINTENANCE_STATUS_OK

            # Проверяем изменение статуса и отправляем события
            entry_id = self.entry.entry_id
            previous_status = self._previous_status.get(entry_id)
            
            if previous_status != status:
                component_name = stored_data.get("name", "Компонент")
                
                if status == MAINTENANCE_STATUS_DUE and previous_status != MAINTENANCE_STATUS_DUE:
                    self.hass.bus.async_fire(EVENT_MAINTENANCE_DUE, {
                        "entity_id": f"sensor.{component_name.lower().replace(' ', '_')}_m_status",
                        "component_name": component_name,
                        "days_until": days_until_maintenance,
                    })
                elif status == MAINTENANCE_STATUS_OVERDUE and previous_status != MAINTENANCE_STATUS_OVERDUE:
                    self.hass.bus.async_fire(EVENT_MAINTENANCE_OVERDUE, {
                        "entity_id": f"sensor.{component_name.lower().replace(' ', '_')}_m_status", 
                        "component_name": component_name,
                        "days_overdue": abs(days_until_maintenance),
                    })
                
                self._previous_status[entry_id] = status

            return {
                "status": status,
                "days_until_maintenance": days_until_maintenance,
                "last_maintenance_date": stored_data["last_maintenance_date"],
                "maintenance_interval": stored_data["maintenance_interval"],
                "name": stored_data["name"],
                "next_maintenance_date": next_maintenance.isoformat(),
            }

        except Exception as err:
            raise UpdateFailed(f"Ошибка обновления данных: {err}") from err

    async def async_perform_maintenance(self) -> None:
        """Выполнить обслуживание - установить текущую дату как дату последнего обслуживания."""
        try:
            # Загружаем текущие данные
            stored_data = await self.store.async_load()
            if stored_data is None:
                stored_data = {}

            # Обновляем дату последнего обслуживания
            stored_data["last_maintenance_date"] = datetime.now().isoformat()
            
            # Сохраняем
            await self.store.async_save(stored_data)
            
            # Отправляем событие о выполненном обслуживании
            component_name = stored_data.get("name", "Компонент")
            self.hass.bus.async_fire(EVENT_MAINTENANCE_COMPLETED, {
                "entity_id": f"sensor.{component_name.lower().replace(' ', '_')}_m_status",
                "component_name": component_name,
                "maintenance_date": stored_data["last_maintenance_date"],
            })
            
            # Обновляем данные
            await self.async_request_refresh()
            
            _LOGGER.info("Обслуживание выполнено для %s", component_name)

        except Exception as err:
            _LOGGER.error("Ошибка при выполнении обслуживания: %s", err)
            raise

    async def async_set_maintenance_date(self, maintenance_date: datetime) -> None:
        """Установить дату последнего обслуживания."""
        try:
            # Загружаем текущие данные
            stored_data = await self.store.async_load()
            if stored_data is None:
                stored_data = {}

            # Обновляем дату последнего обслуживания
            stored_data["last_maintenance_date"] = maintenance_date.isoformat()
            
            # Сохраняем
            await self.store.async_save(stored_data)
            
            # Обновляем данные
            await self.async_request_refresh()
            
            component_name = stored_data.get("name", "Компонент")
            _LOGGER.info("Дата последнего обслуживания установлена для %s: %s", 
                        component_name, maintenance_date.date())

        except Exception as err:
            _LOGGER.error("Ошибка при установке даты обслуживания: %s", err)
            raise 