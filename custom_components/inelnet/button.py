"""Button platform for INELNET Blinds – one entity per action."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    ACT_DOWN_SHORT,
    ACT_PROGRAM,
    ACT_UP_SHORT,
    CONF_CHANNELS,
    CONF_HOST,
    DOMAIN,
)
from .cover import send_command

# Button kinds: (unique_id_suffix, action_code, entity_name)
BUTTON_UP_SHORT = ("short_up", ACT_UP_SHORT, "Short move up")
BUTTON_DOWN_SHORT = ("short_down", ACT_DOWN_SHORT, "Short move down")
BUTTON_PROGRAM = ("program", ACT_PROGRAM, "Programming mode")


def _device_info(entry: ConfigEntry, channel: int) -> DeviceInfo:
    """Build DeviceInfo for a channel (same as cover so entities share one device)."""
    return DeviceInfo(
        identifiers={(DOMAIN, f"{entry.entry_id}-ch{channel}")},
        name=f"Blind channel {channel}",
        manufacturer="INELNET",
        model="Blinds controller",
    )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up INELNET button entities from a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    host = data[CONF_HOST]
    channels = data[CONF_CHANNELS]

    entities: list[InelnetButtonEntity] = []
    for channel in channels:
        for suffix, act_code, entity_name in (
            BUTTON_UP_SHORT,
            BUTTON_DOWN_SHORT,
            BUTTON_PROGRAM,
        ):
            entities.append(
                InelnetButtonEntity(
                    entry=entry,
                    host=host,
                    channel=channel,
                    unique_id_suffix=suffix,
                    action_code=act_code,
                    entity_name=entity_name,
                )
            )
    async_add_entities(entities)


class InelnetButtonEntity(ButtonEntity):
    """One button entity for a single INELNET action (short up, short down, program)."""

    _attr_has_entity_name = True
    # Disabled by default so the user must enable these entities explicitly
    _attr_entity_registry_enabled_default = False

    def __init__(
        self,
        entry: ConfigEntry,
        host: str,
        channel: int,
        unique_id_suffix: str,
        action_code: int,
        entity_name: str,
    ) -> None:
        """Initialize the button."""
        self._entry = entry
        self._host = host
        self._channel = channel
        self._action_code = action_code
        self._attr_unique_id = f"{entry.entry_id}-ch{channel}-{unique_id_suffix}"
        self._attr_name = entity_name
        self._attr_device_info = _device_info(entry, channel)

    async def async_press(self) -> None:
        """Send the REST command for this action."""
        await send_command(self._host, self._channel, self._action_code)
