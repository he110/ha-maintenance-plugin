"""Battery assessment rules. No Home Assistant imports — unit-testable."""

from __future__ import annotations

from dataclasses import dataclass, field

SEVERITY_WARNING = "warning"
SEVERITY_ERROR = "error"


@dataclass
class DeviceBattery:
    """Everything known about one device's battery (or a device-less entity)."""

    name: str
    levels: dict[str, float] = field(default_factory=dict)  # entity_id → percent
    low_flags: dict[str, bool] = field(default_factory=dict)  # binary_sensor → on

    @property
    def level(self) -> float | None:
        return min(self.levels.values()) if self.levels else None

    @property
    def empty(self) -> bool:
        return not self.levels and not self.low_flags


def parse_level(state: str) -> float | None:
    """A percentage from a battery sensor state; None for unknown/unavailable/garbage."""
    try:
        value = float(state)
    except (TypeError, ValueError):
        return None
    return value if 0 <= value <= 100 else None


def severity(battery: DeviceBattery, warning_level: float, error_level: float) -> str | None:
    """Percent wins over the vendor's "battery low" flag when both exist.

    Zigbee leak sensors report 5 % while their battery_low flag is still off; the flag
    is only used for devices that report no percentage at all.
    """
    level = battery.level
    if level is not None:
        if level <= error_level:
            return SEVERITY_ERROR
        if level <= warning_level:
            return SEVERITY_WARNING
        return None
    return SEVERITY_WARNING if any(battery.low_flags.values()) else None
