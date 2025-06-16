# Troubleshooting Guide

## Common Issues and Solutions

### 1. Integration not appearing in the list

**Problem:** Cannot find "Maintainable" when adding a new integration.

**Solution:**
1. Ensure the integration is properly installed
2. **Restart Home Assistant completely** (not just reload configuration)
3. Clear browser cache and refresh the page
4. Check that the `custom_components/maintainable` folder exists with all files

### 2. Sensor shows "unavailable" or "unknown"

**Problem:** Maintenance status sensor shows as unavailable.

**Solution:**
1. **Restart Home Assistant** after installation or updates
2. Check Home Assistant logs for error messages
3. Verify the component configuration in Settings → Devices & Services

### 3. Old configuration interface still appears after update

**Problem:** After updating from version 1.0.x to 1.1.x, the old configuration form still shows.

**Solution:**
1. **Fully restart Home Assistant** (required for config flow changes)
2. Do NOT just reload configuration - a complete restart is necessary
3. After restart, try adding the integration again

### 4. Entities not appearing in selected device

**Problem:** Created sensor and button don't appear as part of the selected device.

**Solution:**
1. Ensure you're using version 1.1.2 or later
2. **Restart Home Assistant** after updating
3. Remove and re-add the integration if the issue persists

### 5. New components immediately show "overdue" status

**Problem:** Newly created components show overdue status instead of OK.

**Solution:**
1. When creating a component, set the "Last Maintenance Date" field
2. If you want the component to be considered freshly maintained, set the date to today
3. Leave empty only if the component actually needs maintenance now

### 6. Button doesn't update sensor status

**Problem:** Pressing the maintenance button doesn't update the sensor.

**Solution:**
1. Wait a few seconds for the status to update
2. Refresh the Home Assistant interface
3. Ensure you're using version 1.1.1 or later (fixed synchronization issues)

## Support

If you continue to experience issues:

1. Check the Home Assistant logs for error messages
2. Ensure you're using the latest version of the integration
3. Report issues on the [GitHub repository](https://github.com/your-username/maintainable-plugin) with:
   - Home Assistant version
   - Integration version
   - Error messages from logs
   - Steps to reproduce the issue

## Log Analysis

To view relevant logs:
1. Go to Settings → System → Logs
2. Filter by "maintainable" to see integration-specific messages
3. Look for error or warning messages

Common log entries and their meanings:
- `Config flow not found` - Restart required after update
- `Entity not available` - Integration needs restart
- `Device not found` - Selected device may have been removed 