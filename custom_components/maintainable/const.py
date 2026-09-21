"""Constants for Maintainable."""

from __future__ import annotations

from homeassistant.const import Platform

DOMAIN = "maintainable"
PLATFORMS = [Platform.SENSOR, Platform.BUTTON, Platform.DATE]

# Config entry data — keys and meaning unchanged since 1.x (downgrade-safe).
CONF_NAME = "name"
CONF_INTERVAL = "maintenance_interval"
CONF_DEVICE_ID = "device_id"
CONF_LAST_MAINTENANCE = "last_maintenance_date"

# Options (added in 2.0).
CONF_DUE_THRESHOLD = "due_threshold"
CONF_REPAIRS = "create_repairs"

DEFAULT_INTERVAL = 30
DEFAULT_DUE_THRESHOLD = 7  # the fixed threshold of 1.x

# Storage: one store per component, key and format kept from 1.x.
STORAGE_VERSION = 1
STORAGE_KEY = "maintainable_data_{entry_id}"

# unique_id suffixes — must never change: entity ids and history hang on them.
STATUS_SUFFIX = "_m_status"
DAYS_SUFFIX = "_m_days"
BUTTON_SUFFIX = "_maintenance_button"
NEXT_SUFFIX = "_m_next"  # 2.0
LAST_SUFFIX = "_m_last"  # 2.0

# Bus events — names and payload keys kept from 1.x.
EVENT_DUE = "maintainable_due"
EVENT_OVERDUE = "maintainable_overdue"
EVENT_COMPLETED = "maintainable_completed"

SERVICE_PERFORM = "perform_maintenance"
SERVICE_SET_LAST = "set_last_maintenance"
ATTR_MAINTENANCE_DATE = "maintenance_date"
