"""Constants for the INELNET Blinds integration."""

DOMAIN = "inelnet"

CONF_HOST = "host"
CONF_CHANNELS = "channels"

# REST API action codes (send_act parameter)
ACT_STOP = 144
ACT_UP = 160
ACT_UP_SHORT = 176
ACT_DOWN = 192
ACT_DOWN_SHORT = 208
ACT_PROGRAM = 224

# Device action types for device_action.py
ACTION_UP_SHORT = "up_short"
ACTION_DOWN_SHORT = "down_short"
ACTION_PROGRAM = "program"
