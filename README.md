# Maintainable - Home Assistant Integration

A Home Assistant integration for tracking components that require periodic maintenance.

## Description

The **Maintainable** integration allows you to easily track objects that need periodic maintenance, such as:
- Water filters
- Air purifier and air conditioner filters  
- Robot vacuum consumables
- Any other components requiring replacement or servicing

## Features

- **Maintenance tracking** - Set maintenance intervals in days
- **Automatic status updates** - OK, Due, Overdue
- **One-click maintenance** - Simple button to update maintenance date
- **Persistent state** - Data persists across Home Assistant restarts
- **Device linking** - Attach to existing devices in your system
- **Initial date setup** - Set when components were last serviced
- **Multi-language support** - English and Russian localization

## Installation

### 🚀 HACS (Recommended)

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=he110&repository=ha-maintenance-plugin)


1. Ensure you have [HACS](https://hacs.xyz/) installed
2. Add this repository to HACS as a custom repository:
   - Open HACS
   - Go to **Integrations**
   - Click the three dots in the top right corner
   - Select **Custom repositories**
   - Add this repository URL
   - Select **Integration** category
3. Find "Maintainable" in the HACS integrations list
4. Install the integration
5. **Restart Home Assistant** (especially important when updating!)
6. Add the integration via Settings → Devices & Services → Add Integration → Maintainable

### 📁 Manual Installation

1. Copy the `custom_components/maintainable` folder to your Home Assistant `custom_components` folder
2. **Restart Home Assistant**
3. Add the integration via Settings → Devices & Services → Add Integration → Maintainable

## Usage

1. Add a new maintenance component through the interface
2. Specify the component name and maintenance interval
3. Optionally set the last maintenance date
4. Optionally link to an existing device
5. The following entities will be created:
   - Sensor showing maintenance status
   - Button to perform maintenance

## Component States

- **OK** - Maintenance not needed (more than 7 days remaining)
- **DUE** - Maintenance needed soon (7 days or less)
- **OVERDUE** - Maintenance is overdue

## ⚠️ Important Notes

**When updating the integration, a full Home Assistant restart is required** for configuration flow changes to take effect.

## Planned Features

- Lovelace "Maintenance Feed" widget
- Maintenance notifications
- Statistics and maintenance history

## Support

If you encounter issues, please check the [Troubleshooting Guide](TROUBLESHOOTING.md) or report issues on GitHub.

---

**Developed to simplify home automation maintenance tracking** 🏠 