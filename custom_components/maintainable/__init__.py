"""Интеграция Maintainable для учета обслуживания компонентов."""
from __future__ import annotations

import logging
from datetime import datetime

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.util import dt as dt_util

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor", "button"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Настройка интеграции из конфигурационной записи."""
    _LOGGER.info("Setting up %s entry: %s", DOMAIN, entry.title)

    # Инициализируем хранилище для данных интеграции
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "config": entry.data,
        "options": entry.options,
    }

    # Инициализируем дату последнего обслуживания если её нет
    if "last_maintenance" not in entry.data:
        # Устанавливаем текущую дату как дату последнего обслуживания
        new_data = dict(entry.data)
        new_data["last_maintenance"] = dt_util.now().date().isoformat()
        hass.config_entries.async_update_entry(entry, data=new_data)

    # Настраиваем платформы
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Слушаем обновления опций
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Выгрузка интеграции."""
    _LOGGER.info("Unloading %s entry: %s", DOMAIN, entry.title)

    # Выгружаем платформы
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    # Очищаем данные
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Перезагрузка интеграции при изменении опций."""
    _LOGGER.info("Reloading %s entry: %s", DOMAIN, entry.title)
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry) 