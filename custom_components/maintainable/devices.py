"""Attach a component to the device it maintains — and clean up after 1.x.

1.x linked entities through a DeviceInfo carrying the other device's identifiers,
which added Maintainable's config entry to that device. Home Assistant 2026.8 split
such composite devices into one device per config entry, so each component ended up
on its own copy of the device (listed as a "related device"), and the stored
device_id now points to the pre-split composite id.
"""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from .const import CONF_DEVICE_ID

_LOGGER = logging.getLogger(__name__)


def _owner(device: dr.DeviceEntry) -> set[str]:
    """Config entries owning a device, across registry versions."""
    if (single := getattr(device, "config_entry_id", None)) is not None:
        return {single}
    return set(getattr(device, "config_entries", ()))


@callback
def resolve_linked_device(hass: HomeAssistant, entry: ConfigEntry) -> dr.DeviceEntry | None:
    """The real device the component is linked to (owned by another integration)."""
    device_id = entry.data.get(CONF_DEVICE_ID)
    if not device_id:
        return None
    registry = dr.async_get(hass)
    try:
        device = registry.async_get(device_id, include_composite_devices=False)
    except TypeError:  # HA before 2026.8 knows no composite devices
        return registry.async_get(device_id)
    if device is not None and entry.entry_id not in _owner(device):
        return device
    # A pre-split composite id, or our own split copy: find the original owner's split.
    composite = device.composite_device_id if device is not None else device_id
    for candidate in registry.devices:
        if getattr(candidate, "composite_device_id", None) == composite and entry.entry_id not in _owner(
            candidate
        ):
            return candidate
    return None


@callback
def async_relink(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Move entities to the real device, remember its id, drop our leftover devices."""
    target = resolve_linked_device(hass, entry)
    if target is None:
        return
    entity_registry = er.async_get(hass)
    # Entities first: removing a device also removes same-entry entities on it.
    for entity in er.async_entries_for_config_entry(entity_registry, entry.entry_id):
        if entity.device_id != target.id:
            entity_registry.async_update_entity(entity.entity_id, device_id=target.id)
    device_registry = dr.async_get(hass)
    for device in dr.async_entries_for_config_entry(device_registry, entry.entry_id):
        if device.id != target.id:
            _LOGGER.info("Removing leftover device %s of %s", device.name, entry.title)
            device_registry.async_remove_device(device.id)
    if entry.data.get(CONF_DEVICE_ID) != target.id:
        hass.config_entries.async_update_entry(entry, data={**entry.data, CONF_DEVICE_ID: target.id})
