"""Fix flow for "maintenance due/overdue" issues: record when it was done."""

from __future__ import annotations

import datetime as dt
from typing import Any

import voluptuous as vol
from homeassistant.components.repairs import RepairsFlow

try:
    from homeassistant.components.repairs import RepairsFlowResult
except ImportError:  # HA < 2026.x: without this fallback the platform fails to import and
    # HA silently falls back to a plain "confirm" flow that records nothing.
    from homeassistant.data_entry_flow import FlowResult as RepairsFlowResult
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers.selector import DateSelector
from homeassistant.util import dt as dt_util

from .const import ATTR_MAINTENANCE_DATE, CONF_NAME


async def async_create_fix_flow(
    hass: HomeAssistant, issue_id: str, data: dict[str, Any] | None
) -> RepairsFlow:
    return MaintenanceDoneFlow((data or {}).get("entry_id", issue_id))


class MaintenanceDoneFlow(RepairsFlow):
    def __init__(self, entry_id: str) -> None:
        self._entry_id = entry_id

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> RepairsFlowResult:
        # Newer HA passes the flow's init data here; the form lives in its own step.
        return await self.async_step_confirm()

    async def async_step_confirm(self, user_input: dict[str, Any] | None = None) -> RepairsFlowResult:
        entry = self.hass.config_entries.async_get_entry(self._entry_id)
        if entry is None or entry.state is not ConfigEntryState.LOADED:
            return self.async_abort(reason="not_loaded")
        if user_input is not None:
            done = dt.date.fromisoformat(user_input[ATTR_MAINTENANCE_DATE])
            await entry.runtime_data.async_set_last_maintenance(done)
            return self.async_create_entry(data={})
        return self.async_show_form(
            step_id="confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        ATTR_MAINTENANCE_DATE, default=dt_util.now().date().isoformat()
                    ): DateSelector()
                }
            ),
            description_placeholders={
                "name": entry.data.get(CONF_NAME, entry.title),
                "days": str(abs(entry.runtime_data.data.days_until)),
                "date": dt_util.as_local(entry.runtime_data.data.next).date().isoformat(),
            },
        )
