"""State of one maintained component: storage, schedule, events, Repairs issue."""

from __future__ import annotations

import datetime as dt
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import (
    CONF_DUE_THRESHOLD,
    CONF_INTERVAL,
    CONF_LAST_MAINTENANCE,
    CONF_NAME,
    CONF_REPAIRS,
    DEFAULT_DUE_THRESHOLD,
    DEFAULT_INTERVAL,
    DOMAIN,
    EVENT_COMPLETED,
    EVENT_DUE,
    EVENT_OVERDUE,
    STATUS_SUFFIX,
    STORAGE_KEY,
    STORAGE_VERSION,
)
from .schedule import STATUS_DUE, STATUS_OVERDUE, Schedule, compute, parse_stored

_LOGGER = logging.getLogger(__name__)

type MaintainableConfigEntry = ConfigEntry[MaintenanceCoordinator]


def effective_interval(entry: ConfigEntry) -> int:
    return int(entry.options.get(CONF_INTERVAL, entry.data.get(CONF_INTERVAL, DEFAULT_INTERVAL)))


class MaintenanceCoordinator(DataUpdateCoordinator[Schedule]):
    """No polling: recomputed at local midnight and whenever the date changes."""

    def __init__(self, hass: HomeAssistant, entry: MaintainableConfigEntry) -> None:
        super().__init__(hass, _LOGGER, name=f"{DOMAIN} {entry.title}", config_entry=entry)
        self.entry = entry
        self._store: Store[dict[str, Any]] = Store(
            hass, STORAGE_VERSION, STORAGE_KEY.format(entry_id=entry.entry_id)
        )
        self._stored: dict[str, Any] = {}

    @property
    def name_(self) -> str:
        return self.entry.data.get(CONF_NAME, self.entry.title)

    async def async_load(self) -> None:
        stored = await self._store.async_load()
        if stored is None:
            # Same first-run behaviour as 1.x: date from the config flow, else now.
            stored = {
                "last_maintenance_date": self.entry.data.get(CONF_LAST_MAINTENANCE)
                or dt_util.now().isoformat(),
                "name": self.name_,
            }
        self._stored = stored
        await self._save()
        self._recompute()

    async def _save(self) -> None:
        # Keep the 1.x fields in sync so that a downgrade keeps working.
        self._stored["maintenance_interval"] = effective_interval(self.entry)
        self._stored["name"] = self.name_
        await self._store.async_save(self._stored)

    @property
    def last_maintenance(self) -> dt.datetime:
        return parse_stored(self._stored["last_maintenance_date"], dt_util.get_default_time_zone())

    def _recompute(self) -> None:
        options = self.entry.options
        schedule = compute(
            self.last_maintenance,
            effective_interval(self.entry),
            int(options.get(CONF_DUE_THRESHOLD, DEFAULT_DUE_THRESHOLD)),
            dt_util.now().date(),
            dt_util.get_default_time_zone(),
        )
        previous = self._stored.get("last_status")
        if previous is None:
            # First run on 2.x: remember the status silently. 1.x fired due/overdue
            # after every restart; 2.x only fires on real transitions.
            self._stored["last_status"] = schedule.status
            self.hass.async_create_task(self._save(), eager_start=True)
        elif previous != schedule.status:
            self._stored["last_status"] = schedule.status
            self.hass.async_create_task(self._save(), eager_start=True)
            self._fire_transition(schedule)
        self._sync_issue(schedule)
        self.async_set_updated_data(schedule)

    @property
    def status_entity_id(self) -> str | None:
        return er.async_get(self.hass).async_get_entity_id(
            "sensor", DOMAIN, f"{self.entry.entry_id}{STATUS_SUFFIX}"
        )

    def _fire_transition(self, schedule: Schedule) -> None:
        payload: dict[str, Any] = {
            "entity_id": self.status_entity_id,
            "component_name": self.name_,
        }
        if schedule.status == STATUS_DUE:
            self.hass.bus.async_fire(EVENT_DUE, {**payload, "days_until": schedule.days_until})
        elif schedule.status == STATUS_OVERDUE:
            self.hass.bus.async_fire(EVENT_OVERDUE, {**payload, "days_overdue": abs(schedule.days_until)})

    # --- Repairs -------------------------------------------------------------

    @property
    def issue_id(self) -> str:
        return self.entry.entry_id

    def _sync_issue(self, schedule: Schedule) -> None:
        wanted = self.entry.options.get(CONF_REPAIRS, True) and schedule.status in (
            STATUS_DUE,
            STATUS_OVERDUE,
        )
        if not wanted:
            ir.async_delete_issue(self.hass, DOMAIN, self.issue_id)
            return
        overdue = schedule.status == STATUS_OVERDUE
        ir.async_create_issue(
            self.hass,
            DOMAIN,
            self.issue_id,
            is_fixable=True,
            is_persistent=False,
            severity=ir.IssueSeverity.ERROR if overdue else ir.IssueSeverity.WARNING,
            translation_key="maintenance_overdue" if overdue else "maintenance_due",
            translation_placeholders={
                "name": self.name_,
                "days": str(abs(schedule.days_until)),
                "date": dt_util.as_local(schedule.next).date().isoformat(),
            },
            data={"entry_id": self.entry.entry_id},
        )

    def async_remove_issue(self) -> None:
        ir.async_delete_issue(self.hass, DOMAIN, self.issue_id)

    # --- actions ---------------------------------------------------------------

    def async_refresh_schedule(self) -> None:
        """Called at local midnight."""
        self._recompute()

    async def async_set_last_maintenance(self, when: dt.date | dt.datetime | None = None) -> None:
        """Record a maintenance: now, a given date (local midnight) or datetime."""
        if when is None:
            moment = dt_util.now()
        elif isinstance(when, dt.datetime):
            moment = when if when.tzinfo else when.replace(tzinfo=dt_util.get_default_time_zone())
        else:
            moment = dt_util.start_of_local_day(when)
        self._stored["last_maintenance_date"] = moment.isoformat()
        await self._save()
        self.hass.bus.async_fire(
            EVENT_COMPLETED,
            {
                "entity_id": self.status_entity_id,
                "component_name": self.name_,
                "maintenance_date": self._stored["last_maintenance_date"],
            },
        )
        self._recompute()

    async def _async_update_data(self) -> Schedule:  # pragma: no cover - never polled
        return self.data
