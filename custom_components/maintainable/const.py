"""Константы для интеграции Maintainable."""
from __future__ import annotations

from datetime import timedelta

DOMAIN = "maintainable"

# Конфигурационные константы
CONF_NAME = "name"
CONF_LAST_MAINTENANCE = "last_maintenance"
CONF_MAINTENANCE_INTERVAL = "maintenance_interval"
CONF_DEVICE_ID = "device_id"

# Значения по умолчанию
DEFAULT_NAME = "Обслуживаемый компонент"
DEFAULT_MAINTENANCE_INTERVAL = 30  # дни
DEFAULT_SCAN_INTERVAL = timedelta(hours=1)

# Состояния
STATE_OK = "ok"
STATE_DUE = "due"
STATE_OVERDUE = "overdue"

# Атрибуты
ATTR_LAST_MAINTENANCE = "last_maintenance"
ATTR_NEXT_MAINTENANCE = "next_maintenance"
ATTR_DAYS_REMAINING = "days_remaining"
ATTR_MAINTENANCE_INTERVAL = "maintenance_interval_days"
ATTR_STATUS = "status"

# Иконка по умолчанию для обслуживаемых компонентов
DEFAULT_ICON = "mdi:wrench" 