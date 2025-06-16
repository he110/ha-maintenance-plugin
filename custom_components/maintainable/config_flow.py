"""Конфигурационный поток для интеграции Maintainable."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import device_registry as dr

from .const import (
    CONF_DEVICE_ID,
    CONF_MAINTENANCE_INTERVAL,
    CONF_NAME,
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
        devices = {"": "Без устройства"}
        
        for device in device_registry.devices.values():
            if device.name and not device.disabled:
                devices[device.id] = device.name
        
        return devices
    except Exception as e:
        _LOGGER.error("Ошибка получения устройств: %s", e)
        return {"": "Без устройства"}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Обработка конфигурационного потока для Maintainable."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Обработка шага пользовательского ввода."""
        errors = {}

        if user_input is not None:
            # Валидация названия
            name = user_input[CONF_NAME].strip()
            if not name:
                errors[CONF_NAME] = "empty_name"
            elif len(name) > 100:
                errors[CONF_NAME] = "name_too_long"

            # Валидация интервала
            interval = user_input[CONF_MAINTENANCE_INTERVAL]
            if interval < MIN_MAINTENANCE_INTERVAL or interval > MAX_MAINTENANCE_INTERVAL:
                errors[CONF_MAINTENANCE_INTERVAL] = "invalid_interval"

            # Валидация устройства
            device_id = user_input.get(CONF_DEVICE_ID)
            if device_id:
                device_registry = dr.async_get(self.hass)
                if not device_registry.async_get(device_id):
                    errors[CONF_DEVICE_ID] = "device_not_found"

            if not errors:
                # Проверяем уникальность названия
                for entry in self._async_current_entries():
                    if entry.data.get(CONF_NAME) == name:
                        errors[CONF_NAME] = "name_exists"
                        break

            if not errors:
                return self.async_create_entry(title=name, data=user_input)

        # Получаем список устройств для выбора
        device_options = _get_device_options(self.hass)

        data_schema = vol.Schema(
            {
                vol.Required(CONF_NAME, default=DEFAULT_NAME): str,
                vol.Required(
                    CONF_MAINTENANCE_INTERVAL,
                    default=DEFAULT_MAINTENANCE_INTERVAL
                ): vol.All(int, vol.Range(min=MIN_MAINTENANCE_INTERVAL, max=MAX_MAINTENANCE_INTERVAL)),
                vol.Optional(CONF_DEVICE_ID, default=""): vol.In(device_options),
            }
        )

        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        ) 