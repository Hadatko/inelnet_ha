"""Constants for the INELNET Blinds integration."""

from homeassistant.const import CONF_HOST
from inelnet_api import Action

DOMAIN = "inelnet"

CONF_CHANNELS = "channels"

# Device name template for per-channel devices (identifier only, not user-facing)
DEVICE_NAME_CHANNEL_TEMPLATE = "INELNET Blinds channel {channel}"

# Device action types for device_action.py
ACTION_UP_SHORT = "up_short"
ACTION_DOWN_SHORT = "down_short"
ACTION_PROGRAM = "program"

__all__ = [
    "ACTION_DOWN_SHORT",
    "ACTION_PROGRAM",
    "ACTION_UP_SHORT",
    "Action",
    "CONF_CHANNELS",
    "CONF_HOST",
    "DEVICE_NAME_CHANNEL_TEMPLATE",
    "DOMAIN",
]
