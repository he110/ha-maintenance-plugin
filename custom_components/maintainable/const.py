"""Константы для интеграции Maintainable."""
from __future__ import annotations

from homeassistant.const import Platform

# Основные константы
DOMAIN = "maintainable"
PLATFORMS = [Platform.SENSOR, Platform.BUTTON]

# Ключи для хранения данных
DATA_COORDINATOR = "coordinator"

# Состояния обслуживания
MAINTENANCE_STATUS_OK = "ok"
MAINTENANCE_STATUS_DUE = "due"
MAINTENANCE_STATUS_OVERDUE = "overdue"

# Пороги для статусов (в днях)
DUE_THRESHOLD = 7  # За 7 дней до срока - статус "due"

# Суффиксы для сущностей
STATUS_SUFFIX = "_m_status"
DAYS_SUFFIX = "_m_days"
BUTTON_SUFFIX = "_maintenance_button"

# События
EVENT_MAINTENANCE_DUE = "maintainable_due"
EVENT_MAINTENANCE_OVERDUE = "maintainable_overdue"
EVENT_MAINTENANCE_COMPLETED = "maintainable_completed"

# Конфигурация по умолчанию
DEFAULT_MAINTENANCE_INTERVAL = 30  # дней 