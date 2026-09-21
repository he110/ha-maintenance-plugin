"""Services kept from 1.x, now resolving any entity of a component via the registry."""

from __future__ import annotations

import voluptuous as vol
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import entity_registry as er

from .const import ATTR_MAINTENANCE_DATE, DOMAIN, SERVICE_PERFORM, SERVICE_SET_LAST
from .coordinator import MaintenanceCoordinator

PERFORM_SCHEMA = vol.Schema({vol.Required(ATTR_ENTITY_ID): cv.entity_ids}, extra=vol.ALLOW_EXTRA)
SET_LAST_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_ENTITY_ID): cv.entity_ids,
        vol.Required(ATTR_MAINTENANCE_DATE): cv.date,
    },
    extra=vol.ALLOW_EXTRA,
)


def _coordinators(hass: HomeAssistant, entity_ids: list[str]) -> list[MaintenanceCoordinator]:
    """Any entity of a component (status, days, button, date...) identifies it.

    1.x rebuilt the entity id from the component name, which never matched names with
    non-Latin letters — the services silently did nothing for them.
    """
    registry = er.async_get(hass)
    result: dict[str, MaintenanceCoordinator] = {}
    for entity_id in entity_ids:
        registry_entry = registry.async_get(entity_id)
        entry_id = registry_entry.config_entry_id if registry_entry else None
        entry = hass.config_entries.async_get_entry(entry_id) if entry_id else None
        if entry is None or entry.domain != DOMAIN or entry.state is not ConfigEntryState.LOADED:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="not_maintainable",
                translation_placeholders={"entity_id": entity_id},
            )
        result[entry.entry_id] = entry.runtime_data
    return list(result.values())


@callback
def async_register_services(hass: HomeAssistant) -> None:
    async def perform(call: ServiceCall) -> None:
        for coordinator in _coordinators(hass, call.data[ATTR_ENTITY_ID]):
            await coordinator.async_set_last_maintenance()

    async def set_last(call: ServiceCall) -> None:
        for coordinator in _coordinators(hass, call.data[ATTR_ENTITY_ID]):
            await coordinator.async_set_last_maintenance(call.data[ATTR_MAINTENANCE_DATE])

    hass.services.async_register(DOMAIN, SERVICE_PERFORM, perform, schema=PERFORM_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_SET_LAST, set_last, schema=SET_LAST_SCHEMA)
