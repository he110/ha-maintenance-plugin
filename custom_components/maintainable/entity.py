"""Базовая сущность для интеграции Maintainable."""
from __future__ import annotations

from datetime import datetime, timedelta, date, time
from typing import Any
import asyncio
import logging

from homeassistant.helpers.entity import Entity, DeviceInfo
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers import device_registry as dr
from homeassistant.util import dt as dt_util
from homeassistant.helpers.event import async_track_time_change

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
    CONF_ENABLE_NOTIFICATIONS,
    DEFAULT_ICON,
    DOMAIN,
    EVENT_MAINTENANCE_OVERDUE,
    EVENT_MAINTENANCE_DUE,
    EVENT_MAINTENANCE_COMPLETED,
    STATE_DUE,
    STATE_OK,
    STATE_OVERDUE,
)

_LOGGER = logging.getLogger(__name__)

class MaintainableEntity(RestoreEntity):
    """Базовая сущность для обслуживаемых компонентов."""

    def __init__(self, config: dict[str, Any], entry_id: str, options: dict[str, Any] | None = None) -> None:
        """Инициализация сущности обслуживаемого компонента."""
        self._attr_name = config[CONF_NAME]
        self._maintenance_interval = config[CONF_MAINTENANCE_INTERVAL]
        self._device_id = config.get(CONF_DEVICE_ID)
        self._entry_id = entry_id
        self._update_timer = None
        self._last_status = None  # Для отслеживания изменений статуса
        
        # Получаем настройки из опций или конфигурации
        self._options = options or {}
        self._enable_notifications = (
            self._options.get(CONF_ENABLE_NOTIFICATIONS) or
            config.get(CONF_ENABLE_NOTIFICATIONS, True)
        )
        
        # Инициализируем дату последнего обслуживания
        last_maintenance_date = config.get(CONF_LAST_MAINTENANCE)
        if last_maintenance_date:
            # Конвертируем date в datetime с полуднем для избежания проблем с часовыми поясами
            if isinstance(last_maintenance_date, date):
                self._last_maintenance = datetime.combine(
                    last_maintenance_date, 
                    datetime.min.time().replace(hour=12)  # Используем полдень вместо полуночи
                ).replace(tzinfo=dt_util.DEFAULT_TIME_ZONE)
            else:
                self._last_maintenance = last_maintenance_date
        else:
            # Если дата не указана, устанавливаем текущую дату
            # Это означает что обслуживание только что было выполнено
            self._last_maintenance = dt_util.now()
        
        # Создаем уникальный ID на основе entry_id для избежания конфликтов
        clean_name = self._attr_name.lower().replace(' ', '_').replace('-', '_')
        self._attr_unique_id = f"{DOMAIN}_{entry_id}_{clean_name}"

    def update_options(self, options: dict[str, Any]) -> None:
        """Обновление опций сущности."""
        self._options = options
        self._enable_notifications = options.get(CONF_ENABLE_NOTIFICATIONS, True)

    @property
    def device_info(self) -> DeviceInfo | None:
        """Информация об устройстве для привязки сущности."""
        if not self._device_id:
            return None
            
        # Получаем информацию об устройстве из реестра
        device_registry = dr.async_get(self.hass)
        device = device_registry.async_get(self._device_id)
        
        if not device:
            return None
            
        # Возвращаем информацию для привязки к существующему устройству
        return DeviceInfo(
            identifiers=device.identifiers,
            name=device.name,
            manufacturer=device.manufacturer,
            model=device.model,
            sw_version=device.sw_version,
        )

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

    def _fire_status_event(self, old_status: str | None, new_status: str) -> None:
        """Отправка события при изменении статуса."""
        if not self._enable_notifications or old_status == new_status:
            return

        event_data = {
            "entity_id": self.entity_id,
            "name": self._attr_name,
            "old_status": old_status,
            "new_status": new_status,
            "days_remaining": self._get_days_remaining(),
            "next_maintenance": self._get_next_maintenance_date().isoformat(),
        }

        # Определяем тип события
        if new_status == STATE_OVERDUE and old_status != STATE_OVERDUE:
            self.hass.bus.async_fire(EVENT_MAINTENANCE_OVERDUE, event_data)
            _LOGGER.info(f"Maintenance overdue for {self._attr_name}")
        elif new_status == STATE_DUE and old_status not in [STATE_DUE, STATE_OVERDUE]:
            self.hass.bus.async_fire(EVENT_MAINTENANCE_DUE, event_data)
            _LOGGER.info(f"Maintenance due for {self._attr_name}")

    async def async_added_to_hass(self) -> None:
        """Вызывается при добавлении сущности в Home Assistant."""
        await super().async_added_to_hass()
        
        # Регистрируем сущность в общем хранилище с защитой от race condition
        if DOMAIN in self.hass.data and self._entry_id in self.hass.data[DOMAIN]:
            entities_dict = self.hass.data[DOMAIN][self._entry_id]["entities"]
            # Используем asyncio.Lock для защиты от одновременного доступа
            if not hasattr(entities_dict, '_lock'):
                entities_dict._lock = asyncio.Lock()
            
            async with entities_dict._lock:
                entities_dict[self.entity_id] = self
        
        # Восстанавливаем состояние из хранилища только если не было установлено при создании
        if (state := await self.async_get_last_state()) is not None:
            if last_maintenance_str := state.attributes.get(ATTR_LAST_MAINTENANCE):
                try:
                    restored_date = datetime.fromisoformat(
                        last_maintenance_str.replace("Z", "+00:00")
                    )
                    # Используем восстановленную дату только если она не была задана при создании
                    # и если восстановленная дата более поздняя
                    if self._last_maintenance and restored_date > self._last_maintenance:
                        self._last_maintenance = restored_date
                except ValueError:
                    # Если не можем распарсить дату, оставляем текущую
                    pass

        # Инициализируем последний статус
        self._last_status = self._get_status()

        # Настраиваем автоматическое обновление в полночь
        self._setup_daily_update()

    async def async_will_remove_from_hass(self) -> None:
        """Вызывается при удалении сущности из Home Assistant."""
        # Отменяем таймер обновления
        if self._update_timer:
            self._update_timer()
            self._update_timer = None
        
        # Удаляем сущность из общего хранилища
        if (DOMAIN in self.hass.data and 
            self._entry_id in self.hass.data[DOMAIN] and
            "entities" in self.hass.data[DOMAIN][self._entry_id]):
            
            entities_dict = self.hass.data[DOMAIN][self._entry_id]["entities"]
            if hasattr(entities_dict, '_lock'):
                async with entities_dict._lock:
                    entities_dict.pop(self.entity_id, None)
            else:
                entities_dict.pop(self.entity_id, None)
        
        await super().async_will_remove_from_hass()

    def _setup_daily_update(self) -> None:
        """Настройка автоматического обновления каждый день в полночь."""
        # Обновляем каждый день в 00:01 (чуть после полуночи)
        self._update_timer = async_track_time_change(
            self.hass,
            self._async_daily_update,
            hour=0,
            minute=1,
            second=0
        )

    async def _async_daily_update(self, now: datetime) -> None:
        """Ежедневное обновление состояния в полночь."""
        try:
            old_status = self._last_status
            current_status = self._get_status()
            
            # Проверяем изменение статуса и отправляем события
            self._fire_status_event(old_status, current_status)
            self._last_status = current_status
            
            self.async_write_ha_state()
            _LOGGER.debug(f"Daily update for {self.entity_id}, status: {current_status}")
        except Exception as e:
            _LOGGER.error(f"Error during daily update of {self.entity_id}: {e}")

    def perform_maintenance(self) -> None:
        """Выполнить обслуживание - обновить дату последнего обслуживания."""
        old_status = self._last_status
        self._last_maintenance = dt_util.now()
        new_status = self._get_status()
        
        # Отправляем событие о выполненном обслуживании
        if self._enable_notifications:
            event_data = {
                "entity_id": self.entity_id,
                "name": self._attr_name,
                "maintenance_date": self._last_maintenance.isoformat(),
                "next_maintenance": self._get_next_maintenance_date().isoformat(),
                "days_until_next": self._get_days_remaining(),
            }
            self.hass.bus.async_fire(EVENT_MAINTENANCE_COMPLETED, event_data)
            _LOGGER.info(f"Maintenance completed for {self._attr_name}")
        
        self._last_status = new_status
        self.async_write_ha_state()
        
        # Уведомляем все связанные сущности об изменении с защитой от race condition
        self.hass.async_create_task(self._async_notify_related_entities())

    async def _async_notify_related_entities(self) -> None:
        """Асинхронно уведомляем связанные сущности об изменении."""
        if (DOMAIN in self.hass.data and 
            self._entry_id in self.hass.data[DOMAIN] and
            "entities" in self.hass.data[DOMAIN][self._entry_id]):
            
            entities_dict = self.hass.data[DOMAIN][self._entry_id]["entities"]
            
            # Используем lock если он есть
            if hasattr(entities_dict, '_lock'):
                async with entities_dict._lock:
                    entities_to_update = list(entities_dict.items())
            else:
                entities_to_update = list(entities_dict.items())
            
            # Обновляем сущности вне lock'а
            for entity_id, entity in entities_to_update:
                if entity != self and hasattr(entity, '_last_maintenance'):
                    try:
                        entity._last_maintenance = self._last_maintenance
                        entity._last_status = entity._get_status()  # Обновляем статус
                        entity.async_write_ha_state()
                    except Exception as e:
                        _LOGGER.error(f"Error updating related entity {entity_id}: {e}")

    async def set_last_maintenance(self, maintenance_date: date) -> None:
        """Установить дату последнего обслуживания."""
        # Валидация: дата не должна быть в будущем
        if maintenance_date > dt_util.now().date():
            raise ValueError("Дата обслуживания не может быть в будущем")
        
        # Валидация: дата не должна быть слишком далеко в прошлом
        max_past_date = dt_util.now().date() - timedelta(days=3650)  # 10 лет назад
        if maintenance_date < max_past_date:
            raise ValueError("Дата обслуживания слишком далеко в прошлом")
        
        old_status = self._last_status
        
        # Конвертируем date в datetime с полуднем для избежания проблем с часовыми поясами
        if isinstance(maintenance_date, date):
            self._last_maintenance = datetime.combine(
                maintenance_date, 
                datetime.min.time().replace(hour=12)  # Используем полдень
            ).replace(tzinfo=dt_util.DEFAULT_TIME_ZONE)
        else:
            self._last_maintenance = maintenance_date
        
        new_status = self._get_status()
        
        # Отправляем события при изменении статуса
        self._fire_status_event(old_status, new_status)
        self._last_status = new_status
            
        self.async_write_ha_state()
        
        # Уведомляем все связанные сущности об изменении
        await self._async_notify_related_entities() 