"""Constants for the GridSense integration."""

from homeassistant.const import Platform

DOMAIN = "gridsense"
DEFAULT_PORT = 3000
DEFAULT_SCAN_INTERVAL = 30

CONF_HOST = "host"

PLATFORMS: list[Platform] = [Platform.SENSOR]
