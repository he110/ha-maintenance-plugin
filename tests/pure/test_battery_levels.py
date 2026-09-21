import importlib.util
import pathlib
import sys

_path = (
    pathlib.Path(__file__).resolve().parents[2] / "custom_components" / "maintainable" / "battery_levels.py"
)
_spec = importlib.util.spec_from_file_location("battery_levels", _path)
bl = importlib.util.module_from_spec(_spec)
sys.modules["battery_levels"] = bl
_spec.loader.exec_module(bl)


def device(levels=None, flags=None):
    return bl.DeviceBattery(name="x", levels=levels or {}, low_flags=flags or {})


def test_thresholds():
    assert bl.severity(device({"s": 11}), 10, 0) is None
    assert bl.severity(device({"s": 10}), 10, 0) == "warning"
    assert bl.severity(device({"s": 0}), 10, 0) == "error"


def test_lowest_level_of_a_device_counts():
    assert bl.severity(device({"a": 90, "b": 4}), 10, 0) == "warning"


def test_percent_wins_over_vendor_flag():
    # Zigbee leak sensor: 5 % while battery_low is still off → warning;
    # and a flag "on" does not override a healthy percentage.
    assert bl.severity(device({"s": 5}, {"f": False}), 10, 0) == "warning"
    assert bl.severity(device({"s": 80}, {"f": True}), 10, 0) is None


def test_flag_only_devices():
    assert bl.severity(device(flags={"f": True}), 10, 0) == "warning"
    assert bl.severity(device(flags={"f": False}), 10, 0) is None


def test_parse_level():
    assert bl.parse_level("91.5") == 91.5
    for bad in ("unknown", "unavailable", "", None, "-1", "101"):
        assert bl.parse_level(bad) is None
