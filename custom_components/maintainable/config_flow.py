"""Конфигурационный поток для интеграции Maintainable."""
from __future__ import annotations

import logging
from datetime import datetime, date
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv, device_registry as dr
from homeassistant.util import dt as dt_util

from .const import (
    CONF_DEVICE_ID,
    CONF_LAST_MAINTENANCE,
    CONF_MAINTENANCE_INTERVAL,
    CONF_NAME,
    DEFAULT_MAINTENANCE_INTERVAL,
    DEFAULT_NAME,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


def _get_device_options(hass: HomeAssistant) -> dict[str, str]:
    """Получить список доступных устройств."""
    device_registry = dr.async_get(hass)
    devices = {}
    
    # Добавляем опцию "Без устройства"
    devices[""] = "Без устройства"
    
    # Добавляем все доступные устройства
    for device in device_registry.devices.values():
        if device.name and not device.disabled:
            devices[device.id] = device.name
    
    return devices


def _get_step_user_schema(hass: HomeAssistant) -> vol.Schema:
    """Получить схему для пользовательского ввода."""
    device_options = _get_device_options(hass)
    
    return vol.Schema(
        {
            vol.Required(CONF_NAME, default=DEFAULT_NAME): str,
            vol.Required(CONF_MAINTENANCE_INTERVAL, default=DEFAULT_MAINTENANCE_INTERVAL): int,
            vol.Optional(CONF_LAST_MAINTENANCE): cv.date,
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
        except CannotConnect:
            errors["base"] = "cannot_connect"
        except InvalidHost:
            errors["host"] = "cannot_connect"
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Неожиданная ошибка")
            errors["base"] = "unknown"
        else:
            return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=_get_step_user_schema(self.hass), errors=errors
        )


class CannotConnect(HomeAssistantError):
    """Ошибка для обозначения невозможности подключения."""


class InvalidHost(HomeAssistantError):
    """Ошибка для обозначения неверного хоста."""


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Валидация пользовательского ввода позволяет нам дать пользователю полезную обратную связь.

    Словарь данных содержит пользовательский ввод. Нет необходимости валидировать
    схему, это уже сделано.
    """

    # Если ваш хаб PyPI пакет не может подключиться, бросьте CannotConnect.
    # Если хост неверен, бросьте InvalidHost.

    # Возвращаем информацию, которую хотите сохранить в записи конфигурации.
    return {"title": data[CONF_NAME]} 