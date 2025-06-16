# Maintainable - Maintenance Tracking Integration

{% if installed %}
## ✅ Integration Installed

⚠️ **IMPORTANT:** After updating the integration, you must **fully restart Home Assistant** for configuration flow changes to take effect.

You can now add maintenance components via:
**Settings** → **Devices & Services** → **Add Integration** → **Maintainable**

{% endif %}

## Description

The **Maintainable** integration helps you track components that need periodic maintenance:

- 🚰 **Water filters**
- 🌬️ **Air purifier and air conditioner filters**  
- 🤖 **Robot vacuum consumables**
- 🔧 **Any other components**

## Features

### ✨ Core Functions
- **Maintenance interval tracking** - Set periods in days
- **Automatic status updates** - OK, Due, Overdue
- **Simple maintenance** - One button to update dates
- **Persistent state** - Data saved across restarts
- **Device linking** - Attach to existing devices
- **Initial date configuration** - Set when last serviced

### 📱 Interface
- **Status sensor** - Shows current component state
- **Maintenance button** - Quick date updates
- **Detailed attributes** - Days until maintenance, dates, intervals
- **Multi-language support** - English and Russian localization

## Component States

| Status | Description | Icon |
|--------|-------------|------|
| **OK** | Maintenance not needed (>7 days) | 🟢 |
| **DUE** | Maintenance needed soon (≤7 days) | 🟡 |
| **OVERDUE** | Maintenance is overdue | 🔴 |

## 🔄 Updates

**Version 1.1.2:**
- ✅ Added last maintenance date configuration
- ✅ Fixed device linking - entities now appear within selected device
- ✅ Fixed OVERDUE status for new components
- ✅ Added configuration field tooltips

**Version 1.1.1:**
- ✅ Fixed unavailable sensor issues
- ✅ Removed device type selection during setup
- ✅ Added linking to existing devices
- ✅ Improved sensor-button synchronization

⚠️ **Full Home Assistant restart required when updating**

## Planned Features

- 📋 Lovelace "Maintenance Feed" widget
- 🔔 Maintenance notifications
- 📊 Statistics and maintenance history

---

**Developed to simplify home automation** 🏠 