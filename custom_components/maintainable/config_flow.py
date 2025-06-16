"""Конфигурационный поток для интеграции Maintainable."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr

from .const import (
    CONF_DEVICE_ID,
    CONF_MAINTENANCE_INTERVAL,
    CONF_NAME,
    CONF_ENABLE_NOTIFICATIONS,
    DEFAULT_MAINTENANCE_INTERVAL,
    DEFAULT_NAME,
    DOMAIN,
    MIN_MAINTENANCE_INTERVAL,
    MAX_MAINTENANCE_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)


def _get_device_options(hass: HomeAssistant) -> dict[str, str]:
    """Получить список доступных устройств."""
    try:
        device_registry = dr.async_get(hass)
        devices = {}
        
        # Добавляем опцию "Без устройства"
        devices[""] = "Без устройства"
        
        # Добавляем все доступные устройства
        for device in device_registry.devices.values():
            if device.name and not device.disabled:
                devices[device.id] = device.name
        
        return devices
    except Exception as e:
        _LOGGER.error("Ошибка получения устройств: %s", e)
        return {"": "Без устройства"}


def _get_step_user_schema(hass: HomeAssistant) -> vol.Schema:
    """Получить схему для пользовательского ввода."""
    device_options = _get_device_options(hass)
    
    return vol.Schema(
        {
            vol.Required(CONF_NAME, default=DEFAULT_NAME): str,
            vol.Required(
                CONF_MAINTENANCE_INTERVAL, 
                default=DEFAULT_MAINTENANCE_INTERVAL
            ): vol.All(int, vol.Range(min=MIN_MAINTENANCE_INTERVAL, max=MAX_MAINTENANCE_INTERVAL)),
            vol.Optional(CONF_DEVICE_ID, default=""): vol.In(device_options),
        }
    )


def _get_step_options_schema() -> vol.Schema:
    """Получить схему для дополнительных опций."""
    return vol.Schema(
        {
            vol.Optional(CONF_ENABLE_NOTIFICATIONS, default=True): bool,
        }
    )


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Обработка конфигурационного потока для Maintainable."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Обработка шага пользовательского ввода."""
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=_get_step_user_schema(self.hass)
            )

        errors = {}

        try:
            info = await validate_input(self.hass, user_input)
        except ValueError as e:
            _LOGGER.warning("Ошибка валидации: %s", e)
            errors["base"] = "invalid_input"
        except Exception as e:  # pylint: disable=broad-except
            _LOGGER.exception("Неожиданная ошибка валидации: %s", e)
            errors["base"] = "unknown"
        else:
            # Добавляем значения по умолчанию для дополнительных опций
            user_input.setdefault(CONF_ENABLE_NOTIFICATIONS, True)
            
            return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=_get_step_user_schema(self.hass), errors=errors
        )

    @staticmethod
    def async_get_options_flow(config_entry):
        """Получить поток опций."""
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Обработка потока опций."""

    def __init__(self, config_entry):
        """Инициализация обработчика опций."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Управление опциями."""
        if user_input is not None:
            # Валидируем опции
            errors = {}
            try:
                await validate_options(user_input)
            except ValueError as e:
                _LOGGER.warning("Ошибка валидации опций: %s", e)
                errors["base"] = "invalid_options"
            except Exception as e:
                _LOGGER.exception("Неожиданная ошибка валидации опций: %s", e)
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(title="", data=user_input)

            return self.async_show_form(
                step_id="init",
                data_schema=_get_step_options_schema(),
                errors=errors
            )

        # Получаем текущие значения из конфигурации или опций
        current_notifications = (
            self.config_entry.options.get(CONF_ENABLE_NOTIFICATIONS) or
            self.config_entry.data.get(CONF_ENABLE_NOTIFICATIONS, True)
        )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_ENABLE_NOTIFICATIONS, 
                        default=current_notifications
                    ): bool,
                }
            ),
        )


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Валидация пользовательского ввода."""
    # Валидация названия
    name = data.get(CONF_NAME, "").strip()
    if not name:
        raise ValueError("Название не может быть пустым")
    
    if len(name) > 100:
        raise ValueError("Название слишком длинное (максимум 100 символов)")
    
    # Валидация интервала обслуживания
    interval = data.get(CONF_MAINTENANCE_INTERVAL, 0)
    if not isinstance(interval, int) or interval < MIN_MAINTENANCE_INTERVAL or interval > MAX_MAINTENANCE_INTERVAL:
        raise ValueError(
            f"Интервал обслуживания должен быть от {MIN_MAINTENANCE_INTERVAL} до {MAX_MAINTENANCE_INTERVAL} дней"
        )

    # Валидация устройства (если указано)
    device_id = data.get(CONF_DEVICE_ID)
    if device_id:
        device_registry = dr.async_get(hass)
        device = device_registry.async_get(device_id)
        if not device:
            raise ValueError("Указанное устройство не найдено")

    return {"title": name}


async def validate_options(data: dict[str, Any]) -> None:
    """Валидация опций."""
    # Валидация уведомлений
    notifications = data.get(CONF_ENABLE_NOTIFICATIONS)
    if notifications is not None and not isinstance(notifications, bool):
        raise ValueError("Настройка уведомлений должна быть булевым значением") 