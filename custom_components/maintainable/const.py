"""Константы для интеграции Maintainable."""

# Основные константы
DOMAIN = "maintainable"
DEFAULT_NAME = "Новый компонент"
DEFAULT_MAINTENANCE_INTERVAL = 365

# Константы конфигурации
CONF_NAME = "name"
CONF_MAINTENANCE_INTERVAL = "maintenance_interval"
CONF_DEVICE_ID = "device_id"
CONF_LAST_MAINTENANCE = "last_maintenance"

# Константы состояний
STATE_OK = "ok"
STATE_DUE = "due"
STATE_OVERDUE = "overdue"

# Константы атрибутов
ATTR_MAINTENANCE_INTERVAL = "maintenance_interval"
ATTR_LAST_MAINTENANCE = "last_maintenance"
ATTR_NEXT_MAINTENANCE = "next_maintenance"
ATTR_DAYS_REMAINING = "days_remaining"
ATTR_STATUS = "status"

# Иконки
ICON_STATUS = "mdi:tools"
ICON_DAYS = "mdi:calendar-clock"
ICON_BUTTON = "mdi:wrench"

# Ограничения
MIN_MAINTENANCE_INTERVAL = 1
MAX_MAINTENANCE_INTERVAL = 3650  # 10 лет 