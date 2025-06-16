"""Константы для интеграции Maintainable."""
from __future__ import annotations

from datetime import timedelta

DOMAIN = "maintainable"

# Конфигурационные константы
CONF_NAME = "name"
CONF_LAST_MAINTENANCE = "last_maintenance"
CONF_MAINTENANCE_INTERVAL = "maintenance_interval"
CONF_DEVICE_CLASS = "device_class"

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

# Типы устройств обслуживания
DEVICE_CLASS_FILTER = "filter"
DEVICE_CLASS_CONSUMABLE = "consumable"
DEVICE_CLASS_PART = "part"
DEVICE_CLASS_OTHER = "other"

DEVICE_CLASSES = [
    DEVICE_CLASS_FILTER,
    DEVICE_CLASS_CONSUMABLE,
    DEVICE_CLASS_PART,
    DEVICE_CLASS_OTHER,
]

# Иконки для различных типов устройств
DEVICE_CLASS_ICONS = {
    DEVICE_CLASS_FILTER: "mdi:air-filter",
    DEVICE_CLASS_CONSUMABLE: "mdi:package-variant",
    DEVICE_CLASS_PART: "mdi:cog",
    DEVICE_CLASS_OTHER: "mdi:wrench",
} 