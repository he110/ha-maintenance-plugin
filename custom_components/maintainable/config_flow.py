"""Поток конфигурации для интеграции Maintainable."""
from __future__ import annotations

import logging
from typing import Any
from datetime import datetime

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.selector import (
    DeviceSelector,
    DeviceSelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
    DateSelector,
    DateSelectorConfig,
)

from .const import DOMAIN, DEFAULT_MAINTENANCE_INTERVAL

_LOGGER = logging.getLogger(__name__)


class MaintenableConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Обработка потока конфигурации для Maintainable."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Обработка начального шага конфигурации."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                # Проверяем корректность входных данных
                name = user_input["name"].strip()
                maintenance_interval = user_input["maintenance_interval"]
                
                if not name:
                    errors["name"] = "invalid_name"
                elif maintenance_interval <= 0:
                    errors["maintenance_interval"] = "invalid_interval"
                else:
                    # Создаём уникальный ID для этого компонента
                    unique_id = f"{DOMAIN}_{name.lower().replace(' ', '_')}"
                    
                    await self.async_set_unique_id(unique_id)
                    self._abort_if_unique_id_configured()

                    # Обрабатываем дату последнего обслуживания
                    last_maintenance_date = user_input.get("last_maintenance_date")
                    if last_maintenance_date:
                        _LOGGER.info("Получена дата последнего обслуживания: %s (тип: %s)", last_maintenance_date, type(last_maintenance_date))
                        
                        # Обрабатываем разные типы входных данных
                        if hasattr(last_maintenance_date, 'date') and callable(getattr(last_maintenance_date, 'date')):
                            # Это объект datetime
                            last_maintenance_str = last_maintenance_date.isoformat()
                        elif hasattr(last_maintenance_date, 'isoformat'):
                            # Это объект date
                            last_maintenance_datetime = datetime.combine(last_maintenance_date, datetime.min.time())
                            last_maintenance_str = last_maintenance_datetime.isoformat()
                        elif isinstance(last_maintenance_date, str):
                            # Строка - пытаемся парсить
                            try:
                                parsed_datetime = datetime.fromisoformat(last_maintenance_date)
                                last_maintenance_str = parsed_datetime.isoformat()
                            except ValueError:
                                try:
                                    from datetime import date
                                    parsed_date = date.fromisoformat(last_maintenance_date)
                                    parsed_datetime = datetime.combine(parsed_date, datetime.min.time())
                                    last_maintenance_str = parsed_datetime.isoformat()
                                except ValueError:
                                    _LOGGER.error("Не удалось распарсить дату: %s", last_maintenance_date)
                                    last_maintenance_str = datetime.now().isoformat()
                        else:
                            _LOGGER.warning("Неизвестный тип даты: %s", type(last_maintenance_date))
                            last_maintenance_str = datetime.now().isoformat()
                    else:
                        last_maintenance_str = datetime.now().isoformat()
                    
                    _LOGGER.info("Сохраняем дату последнего обслуживания: %s", last_maintenance_str)

                    # Логируем device_id для диагностики
                    device_id = user_input.get("device_id")
                    _LOGGER.info("Device ID выбран: %s (тип: %s)", device_id, type(device_id))

                    return self.async_create_entry(
                        title=name,
                        data={
                            "name": name,
                            "maintenance_interval": maintenance_interval,
                            "device_id": user_input.get("device_id"),
                            "last_maintenance_date": last_maintenance_str,
                        },
                    )
                    
            except Exception as ex:
                _LOGGER.error("Ошибка при настройке: %s", ex)
                errors["base"] = "unknown"

        # Получаем список устройств для селектора
        device_registry = dr.async_get(self.hass)
        devices = list(device_registry.devices.values())
        
        # Создаём схему для формы
        data_schema = vol.Schema({
            vol.Required("name"): TextSelector(
                TextSelectorConfig(type=TextSelectorType.TEXT)
            ),
            vol.Required("maintenance_interval", default=DEFAULT_MAINTENANCE_INTERVAL): 
                NumberSelector(
                    NumberSelectorConfig(
                        mode=NumberSelectorMode.BOX,
                        min=1,
                        unit_of_measurement="дней"
                    )
                ),
            vol.Optional("last_maintenance_date"): DateSelector(
                DateSelectorConfig()
            ),
            vol.Optional("device_id"): DeviceSelector(
                DeviceSelectorConfig()
            ),
        })

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> MaintenableOptionsFlowHandler:
        """Создать поток настройки опций."""
        return MaintenableOptionsFlowHandler(config_entry)


class MaintenableOptionsFlowHandler(config_entries.OptionsFlow):
    """Обработка опций для Maintainable."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Инициализация обработчика опций."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Управление опциями."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Optional(
                    "enable_notifications",
                    default=self.config_entry.options.get("enable_notifications", False),
                ): bool,
            }),
        ) 