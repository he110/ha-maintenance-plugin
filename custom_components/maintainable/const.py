"""Константы для интеграции Maintainable."""
from __future__ import annotations

from datetime import timedelta

DOMAIN = "maintainable"

# Конфигурационные константы
CONF_NAME = "name"
CONF_LAST_MAINTENANCE = "last_maintenance"
CONF_MAINTENANCE_INTERVAL = "maintenance_interval"
CONF_DEVICE_ID = "device_id"
CONF_UPDATE_INTERVAL = "update_interval"
CONF_ENABLE_NOTIFICATIONS = "enable_notifications"

# Значения по умолчанию
DEFAULT_NAME = "Обслуживаемый компонент"
DEFAULT_MAINTENANCE_INTERVAL = 30  # дни
DEFAULT_SCAN_INTERVAL = timedelta(hours=1)
DEFAULT_UPDATE_INTERVAL = 30  # минуты
MIN_UPDATE_INTERVAL = 5  # минимум 5 минут
MAX_UPDATE_INTERVAL = 1440  # максимум 24 часа

# Ограничения валидации
MIN_MAINTENANCE_INTERVAL = 1  # минимум 1 день
MAX_MAINTENANCE_INTERVAL = 3650  # максимум 10 лет
MAX_PAST_DAYS = 3650  # максимум 10 лет в прошлом

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

# События
EVENT_MAINTENANCE_OVERDUE = "maintainable_overdue"
EVENT_MAINTENANCE_DUE = "maintainable_due"
EVENT_MAINTENANCE_COMPLETED = "maintainable_completed"

# Иконка по умолчанию для обслуживаемых компонентов
DEFAULT_ICON = "mdi:wrench" 