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
    DEFAULT_MAINTENANCE_INTERVAL,
    DEFAULT_NAME,
    DOMAIN,
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
            vol.Required(CONF_MAINTENANCE_INTERVAL, default=DEFAULT_MAINTENANCE_INTERVAL): int,
            vol.Optional(CONF_DEVICE_ID, default=""): vol.In(device_options),
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
        except Exception as e:  # pylint: disable=broad-except
            _LOGGER.exception("Ошибка валидации: %s", e)
            errors["base"] = "unknown"
        else:
            return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=_get_step_user_schema(self.hass), errors=errors
        )


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Валидация пользовательского ввода."""
    # Простая валидация
    if not data.get(CONF_NAME):
        raise ValueError("Название не может быть пустым")
    
    interval = data.get(CONF_MAINTENANCE_INTERVAL, 0)
    if interval <= 0:
        raise ValueError("Интервал обслуживания должен быть больше 0")

    return {"title": data[CONF_NAME]} 