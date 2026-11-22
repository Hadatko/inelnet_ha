"""Button platform for INELNET Blinds. One device per channel; each button controls only that channel."""

from __future__ import annotations

from inelnet_api import InelnetChannel

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import InelnetConfigEntry
from .const import (
    Action,
    DEVICE_NAME_CHANNEL_TEMPLATE,
    DOMAIN,
)

# Button kinds: (unique_id_suffix, action) – name from entity translation key
BUTTON_UP_SHORT = ("short_up", Action.UP_SHORT)
BUTTON_DOWN_SHORT = ("short_down", Action.DOWN_SHORT)
BUTTON_PROGRAM = ("program", Action.PROGRAM)


def _device_info(entry: ConfigEntry, channel: int, name: str | None) -> DeviceInfo:
    """Build DeviceInfo for a channel (same as cover so entities share one device)."""
    return DeviceInfo(
        identifiers={(DOMAIN, f"{entry.entry_id}-ch{channel}")},
        name=name or DEVICE_NAME_CHANNEL_TEMPLATE.format(channel=channel),
        manufacturer="INELNET",
        model="Blinds controller",
    )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: InelnetConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up short moves and pairing for each physical channel, not for groups."""
    data = entry.runtime_data
    names = {}
    if data.catalogue is not None:
        names = {device.channel: device.name for device in data.catalogue.devices}

    entities: list[InelnetButtonEntity] = []
    for channel in data.channels:
        client = data.clients[channel]
        for translation_key, act_code in (
            BUTTON_UP_SHORT,
            BUTTON_DOWN_SHORT,
            BUTTON_PROGRAM,
        ):
            entities.append(
                InelnetButtonEntity(
                    entry=entry,
                    client=client,
                    unique_id_suffix=translation_key,
                    action=act_code,
                    translation_key=translation_key,
                    device_name=names.get(channel),
                    enabled_default=translation_key == "program",
                )
            )
    async_add_entities(entities)


class InelnetButtonEntity(ButtonEntity):
    """One button entity for a single INELNET action (short up, short down, program)."""

    _attr_has_entity_name = True

    def __init__(
        self,
        entry: ConfigEntry,
        client: InelnetChannel,
        unique_id_suffix: str,
        action: Action,
        translation_key: str,
        *,
        device_name: str | None = None,
        enabled_default: bool = False,
    ) -> None:
        """Initialize the button."""
        self._entry = entry
        self._client = client
        self._action = action
        ch = client.channel
        self._attr_unique_id = f"{entry.entry_id}-ch{ch}-{unique_id_suffix}"
        self._attr_translation_key = translation_key
        self._attr_entity_registry_enabled_default = enabled_default
        self._attr_device_info = _device_info(entry, ch, device_name)

    async def async_press(self) -> None:
        """Send the REST command for this action."""
        session = async_get_clientsession(self.hass)
        await self._client.send_command(self._action, session=session)
