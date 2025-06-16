"""Конфигурационный поток для интеграции Maintainable."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv

from .const import (
    CONF_DEVICE_CLASS,
    CONF_MAINTENANCE_INTERVAL,
    CONF_NAME,
    DEFAULT_MAINTENANCE_INTERVAL,
    DEFAULT_NAME,
    DEVICE_CLASSES,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME, default=DEFAULT_NAME): str,
        vol.Required(CONF_MAINTENANCE_INTERVAL, default=DEFAULT_MAINTENANCE_INTERVAL): int,
        vol.Required(CONF_DEVICE_CLASS, default="other"): vol.In(DEVICE_CLASSES),
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
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA
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
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
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