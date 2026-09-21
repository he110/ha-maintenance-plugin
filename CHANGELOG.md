# Changelog

## 2.1.0

- **Battery monitor.** Add it once (*Add integration → Maintainable → Batteries of all devices*):
  it finds every device with a battery by itself and reports low ones in Repairs — a warning at
  10 % or less, an error at 0 % (both adjustable). New devices are picked up automatically, the
  reminder disappears when the battery is replaced.
  - One reminder per device, based on its lowest battery; the percentage wins over a vendor
    "battery low" flag, which is used only by devices without a percentage.
  - Phones, tablets and watches (`mobile_app`) are ignored by default; any integration or device
    can be excluded.
  - `sensor.low_battery_devices`: how many devices need attention, with the list in `devices`.
- Adding Maintainable now starts with a choice: a component to maintain or the battery monitor.

## 2.0.0

A rewrite focused on how it feels to use, fully compatible with existing setups.

### New

- **Reminders in Repairs.** A warning when maintenance is due soon, an error when it is overdue.
  **Fix** asks when it was done; the issue then goes away by itself.
- `date.<name>_last_maintenance` — see and change the last maintenance date on the device page.
- `sensor.<name>_next_maintenance` — the next maintenance date as a real date sensor.
- **Settings after creation:** maintenance interval, reminder lead time (was fixed at 7 days),
  whether to use Repairs; rename a component or move it to another device.
- Components not linked to a device get a device of their own, so they can be put in an area.
- Proper English and Russian translations; integration icon.

### Fixed

- `maintainable.perform_maintenance` and `maintainable.set_last_maintenance` did nothing for
  components with non-Latin names: they rebuilt the entity ID from the name. They now accept
  any entity of a component and report an error for anything else.
- The maintenance interval could not be changed after creation.
- `maintainable_due` / `maintainable_overdue` fired again after every Home Assistant restart;
  they now fire only when the status actually changes.
- Dates are counted in the Home Assistant time zone.

### Under the hood

- Linking to another integration's device uses `entity.device_entry`. The previous way
  (a `DeviceInfo` with that device's identifiers) is deprecated and stops working in
  Home Assistant 2027.8; `device_registry.devices` lookups (deprecated, 2027.9) are gone.
- Status is recalculated at local midnight instead of polling every 30 minutes.
- Test suite running inside Home Assistant 2026.2 and the latest release, including an upgrade
  from 1.4.0 data.

### Upgrading from 1.x

Nothing to do. Kept exactly as they were: entity IDs and unique IDs, states (`ok`/`due`/
`overdue`, days), attributes (including `status` on the days sensor), friendly names,
services and their fields, events and their data, stored maintenance dates.

One visible nuance: the `maintenance_interval` attribute is now a whole number (`180`
instead of `180.0`) — the same value for templates and comparisons.

The config entry is migrated from 1.1 to 1.2 (settings are copied to options; entry data is
left untouched), so going back to 1.4.0 remains possible.
