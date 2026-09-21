"""Config flow: add a component, reconfigure it, options."""

from __future__ import annotations

import datetime as dt
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.selector import (
    BooleanSelector,
    DateSelector,
    DeviceSelector,
    DeviceSelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    TextSelector,
)
from homeassistant.util import dt as dt_util

from .battery import is_battery
from .const import (
    BATTERY_UNIQUE_ID,
    CONF_DEVICE_ID,
    CONF_DUE_THRESHOLD,
    CONF_ERROR_LEVEL,
    CONF_EXCLUDE_DEVICES,
    CONF_EXCLUDE_INTEGRATIONS,
    CONF_INTERVAL,
    CONF_KIND,
    CONF_LAST_MAINTENANCE,
    CONF_NAME,
    CONF_REPAIRS,
    CONF_WARNING_LEVEL,
    DEFAULT_DUE_THRESHOLD,
    DEFAULT_ERROR_LEVEL,
    DEFAULT_EXCLUDE_INTEGRATIONS,
    DEFAULT_INTERVAL,
    DEFAULT_WARNING_LEVEL,
    DOMAIN,
    KIND_BATTERY,
)


def _days(minimum: int) -> NumberSelector:
    return NumberSelector(
        NumberSelectorConfig(min=minimum, max=3650, mode=NumberSelectorMode.BOX, unit_of_measurement="d")
    )


def _legacy_unique_id(name: str) -> str:
    # Same formula as 1.x, so duplicates of existing components are still detected.
    return f"{DOMAIN}_{name.lower().replace(' ', '_')}"


class MaintainableConfigFlow(ConfigFlow, domain=DOMAIN):
    """One entry per maintained component."""

    VERSION = 1
    MINOR_VERSION = 2

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        return self.async_show_menu(step_id="user", menu_options=["component", "battery"])

    async def async_step_battery(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """One battery monitor per home: it finds every battery by itself."""
        if any(e.unique_id == BATTERY_UNIQUE_ID for e in self._async_current_entries()):
            return self.async_abort(reason="battery_already_configured")
        await self.async_set_unique_id(BATTERY_UNIQUE_ID)
        if user_input is not None:
            russian = self.hass.config.language.startswith("ru")
            return self.async_create_entry(
                title="Контроль батарей" if russian else "Battery monitor",
                data={CONF_KIND: KIND_BATTERY},
                options=_battery_options(user_input),
            )
        return self.async_show_form(
            step_id="battery",
            data_schema=self.add_suggested_values_to_schema(_battery_schema(self.hass), _battery_defaults()),
        )

    async def async_step_component(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            name = user_input[CONF_NAME].strip()
            if not name:
                errors[CONF_NAME] = "invalid_name"
            else:
                await self.async_set_unique_id(_legacy_unique_id(name))
                self._abort_if_unique_id_configured()
                last = user_input.get(CONF_LAST_MAINTENANCE)
                last_iso = (
                    dt_util.start_of_local_day(dt.date.fromisoformat(last)).isoformat()
                    if last
                    else dt_util.now().isoformat()
                )
                return self.async_create_entry(
                    title=name,
                    # 1.x data keys, so that a downgrade can still read the entry.
                    data={
                        CONF_NAME: name,
                        CONF_INTERVAL: int(user_input[CONF_INTERVAL]),
                        CONF_DEVICE_ID: user_input.get(CONF_DEVICE_ID),
                        CONF_LAST_MAINTENANCE: last_iso,
                    },
                    options={
                        CONF_INTERVAL: int(user_input[CONF_INTERVAL]),
                        CONF_DUE_THRESHOLD: int(user_input[CONF_DUE_THRESHOLD]),
                        CONF_REPAIRS: True,
                    },
                )
        schema = vol.Schema(
            {
                vol.Required(CONF_NAME): TextSelector(),
                vol.Required(CONF_INTERVAL, default=DEFAULT_INTERVAL): _days(1),
                vol.Required(CONF_DUE_THRESHOLD, default=DEFAULT_DUE_THRESHOLD): _days(0),
                vol.Optional(CONF_LAST_MAINTENANCE): DateSelector(),
                vol.Optional(CONF_DEVICE_ID): DeviceSelector(),
            }
        )
        return self.async_show_form(
            step_id="component",
            data_schema=self.add_suggested_values_to_schema(schema, user_input),
            errors=errors,
        )

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Rename the component or change the device it belongs to.

        Entity ids stay as they are: they live in the entity registry.
        """
        entry = self._get_reconfigure_entry()
        if entry.data.get(CONF_KIND) == KIND_BATTERY:
            return self.async_abort(reason="use_options")
        errors: dict[str, str] = {}
        if user_input is not None:
            name = user_input[CONF_NAME].strip()
            if not name:
                errors[CONF_NAME] = "invalid_name"
            else:
                return self.async_update_reload_and_abort(
                    entry,
                    title=name,
                    data_updates={CONF_NAME: name, CONF_DEVICE_ID: user_input.get(CONF_DEVICE_ID)},
                )
        schema = vol.Schema(
            {
                vol.Required(CONF_NAME): TextSelector(),
                vol.Optional(CONF_DEVICE_ID): DeviceSelector(),
            }
        )
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.add_suggested_values_to_schema(schema, user_input or dict(entry.data)),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> MaintainableOptionsFlow:
        return MaintainableOptionsFlow()


class MaintainableOptionsFlow(OptionsFlow):
    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if self.config_entry.data.get(CONF_KIND) == KIND_BATTERY:
            return await self.async_step_battery()
        if user_input is not None:
            return self.async_create_entry(
                data={
                    CONF_INTERVAL: int(user_input[CONF_INTERVAL]),
                    CONF_DUE_THRESHOLD: int(user_input[CONF_DUE_THRESHOLD]),
                    CONF_REPAIRS: user_input[CONF_REPAIRS],
                }
            )
        entry = self.config_entry
        current = {
            CONF_INTERVAL: entry.options.get(CONF_INTERVAL, entry.data.get(CONF_INTERVAL, DEFAULT_INTERVAL)),
            CONF_DUE_THRESHOLD: entry.options.get(CONF_DUE_THRESHOLD, DEFAULT_DUE_THRESHOLD),
            CONF_REPAIRS: entry.options.get(CONF_REPAIRS, True),
        }
        schema = vol.Schema(
            {
                vol.Required(CONF_INTERVAL): _days(1),
                vol.Required(CONF_DUE_THRESHOLD): _days(0),
                vol.Required(CONF_REPAIRS): BooleanSelector(),
            }
        )
        return self.async_show_form(
            step_id="init", data_schema=self.add_suggested_values_to_schema(schema, current)
        )

    async def async_step_battery(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=_battery_options(user_input))
        return self.async_show_form(
            step_id="battery",
            data_schema=self.add_suggested_values_to_schema(
                _battery_schema(self.hass), {**_battery_defaults(), **self.config_entry.options}
            ),
        )


def _battery_defaults() -> dict[str, Any]:
    return {
        CONF_WARNING_LEVEL: DEFAULT_WARNING_LEVEL,
        CONF_ERROR_LEVEL: DEFAULT_ERROR_LEVEL,
        CONF_EXCLUDE_INTEGRATIONS: DEFAULT_EXCLUDE_INTEGRATIONS,
        CONF_EXCLUDE_DEVICES: [],
    }


def _battery_options(user_input: dict[str, Any]) -> dict[str, Any]:
    return {
        CONF_WARNING_LEVEL: int(user_input[CONF_WARNING_LEVEL]),
        CONF_ERROR_LEVEL: int(user_input[CONF_ERROR_LEVEL]),
        CONF_EXCLUDE_INTEGRATIONS: list(user_input.get(CONF_EXCLUDE_INTEGRATIONS, [])),
        CONF_EXCLUDE_DEVICES: list(user_input.get(CONF_EXCLUDE_DEVICES, [])),
    }


def _battery_schema(hass) -> vol.Schema:
    """Integrations offered for exclusion: those that actually have batteries here."""
    registry = er.async_get(hass)
    domains = set(DEFAULT_EXCLUDE_INTEGRATIONS)
    for state in hass.states.async_all(("sensor", "binary_sensor")):
        if is_battery(state) and (entry := registry.async_get(state.entity_id)):
            domains.add(entry.platform)
    percent = NumberSelector(
        NumberSelectorConfig(min=0, max=100, mode=NumberSelectorMode.BOX, unit_of_measurement="%")
    )
    return vol.Schema(
        {
            vol.Required(CONF_WARNING_LEVEL): percent,
            vol.Required(CONF_ERROR_LEVEL): percent,
            vol.Optional(CONF_EXCLUDE_INTEGRATIONS): SelectSelector(
                SelectSelectorConfig(options=sorted(domains), multiple=True, custom_value=True)
            ),
            vol.Optional(CONF_EXCLUDE_DEVICES): DeviceSelector(DeviceSelectorConfig(multiple=True)),
        }
    )
