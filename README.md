# Maintainable for Home Assistant

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/)
[![Validate](https://github.com/he110/ha-maintenance-plugin/actions/workflows/validate.yaml/badge.svg)](https://github.com/he110/ha-maintenance-plugin/actions/workflows/validate.yaml)
[![Tests](https://github.com/he110/ha-maintenance-plugin/actions/workflows/tests.yaml/badge.svg)](https://github.com/he110/ha-maintenance-plugin/actions/workflows/tests.yaml)
[![Release](https://img.shields.io/github/v/release/he110/ha-maintenance-plugin)](https://github.com/he110/ha-maintenance-plugin/releases)

[![Open your Home Assistant instance and open this repository in HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=he110&repository=ha-maintenance-plugin&category=integration)
[![Open your Home Assistant instance and add a maintained component.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=maintainable)

Reminders for things that need periodic care but cannot tell you themselves: water filter
cartridges, air purifier filters, vacuum brushes, a descaling, a car service.

It can also watch every battery in your home.

When something is due, it shows up in **Settings → Repairs** — the same place Home Assistant
uses for its own warnings — and you mark it done right there.

[Русская версия](README.ru.md)

## What you get

For each component:

| Entity | |
|---|---|
| `sensor.<name>_m_status` | `ok` / `due` / `overdue` |
| `sensor.<name>_m_days` | Days until maintenance, negative when overdue |
| `sensor.<name>_next_maintenance` | Date of the next maintenance |
| `date.<name>_last_maintenance` | Last maintenance — edit it right on the device page |
| `button.<name>_maintenance_button` | Mark as maintained today |

- **Repairs:** a warning when maintenance is due soon, an error when it is overdue. **Fix** asks
  when it was done and starts the next period from that date. The issue disappears by itself.
- **Link to a device:** show a filter on its purifier's page instead of as a separate device.
- Status is recalculated at local midnight, in your Home Assistant time zone.
- Interval, reminder lead time and device can be changed at any time.

## Battery monitor

Add it once: *Add integration → Maintainable → Batteries of all devices*. No per-device setup:
it finds every battery in your home by itself, including devices added later, and reports
low ones in Repairs — a **warning at 10 % or less**, an **error at 0 %**. The reminder goes away
when the battery is replaced.

- One reminder per device (its lowest battery). The percentage wins over a vendor "battery low"
  flag, which only counts for devices that report no percentage.
- Phones, tablets and watches (`mobile_app`) are ignored by default. *Configure* changes the
  thresholds and excludes integrations or single devices.
- `sensor.low_battery_devices` — how many devices need attention; the list is in its `devices`
  attribute (name, level, severity, entity), handy for dashboards.

## Installation

**HACS (recommended):** click **Open in HACS** above (or HACS → ⋮ → Custom repositories →
`https://github.com/he110/ha-maintenance-plugin`, category *Integration*), install, restart Home Assistant.

**Manual:** copy `custom_components/maintainable` into `config/custom_components/` and restart.

## Adding a component

Click **Add integration** above, or *Settings → Devices & services → Add integration → Maintainable*.
One integration entry is one component.

| Field | |
|---|---|
| Name | e.g. "HEPA filter — bedroom purifier" |
| Maintenance interval | How often, in days |
| Remind in advance | Days before the due date when the status becomes `due` (default 7) |
| Last maintenance | Leave empty for today |
| Device | Optional: show the component on that device's page |

Later: *Configure* changes the interval, the lead time and whether reminders go to Repairs;
*Reconfigure* renames the component or moves it to another device. Entity IDs never change.

## Automations

Services (target any entity of the component):

```yaml
action: maintainable.perform_maintenance      # done now
target:
  entity_id: sensor.hepa_filter_m_status
---
action: maintainable.set_last_maintenance     # done on a given date
target:
  entity_id: sensor.hepa_filter_m_status
data:
  maintenance_date: "2026-09-19"
```

Events, fired when the status changes (not on every restart):

| Event | Data |
|---|---|
| `maintainable_due` | `entity_id`, `component_name`, `days_until` |
| `maintainable_overdue` | `entity_id`, `component_name`, `days_overdue` |
| `maintainable_completed` | `entity_id`, `component_name`, `maintenance_date` |

```yaml
# Example: a phone notification when something becomes overdue.
triggers:
  - trigger: event
    event_type: maintainable_overdue
actions:
  - action: notify.mobile_app_phone
    data:
      message: "{{ trigger.event.data.component_name }} is overdue for maintenance"
```

## Upgrading from 1.x

Nothing to do: entity IDs, states, attributes, services, events and history are kept. See the
[changelog](CHANGELOG.md#200) for what changed and why.

## Development

```bash
pip install -r requirements_test.txt
pytest tests
```

## License

[MIT](LICENSE)
