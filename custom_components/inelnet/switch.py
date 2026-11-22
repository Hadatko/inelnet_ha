"""Switches for INELNET lights and sockets. The controller does not report state."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import InelnetConfigEntry
from .catalogue import is_switch
from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    entry: InelnetConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up one switch per light or socket, including groups of that type."""
    catalogue = entry.runtime_data.catalogue
    if catalogue is None:
        return
    entities: list[InelnetSwitchEntity] = []
    for device in catalogue.devices:
        if not is_switch(device.device_type):
            continue
        entities.append(
            InelnetSwitchEntity(
                entry,
                device.channel,
                device.name,
                device.device_type,
                catalogue.place_name(device.place),
                f"ch{device.channel}",
            )
        )
    for group in catalogue.groups:
        if not is_switch(group.device_type):
            continue
        entities.append(
            InelnetSwitchEntity(
                entry,
                group.number,
                group.name,
                group.device_type,
                None,
                f"gr{group.number}",
                model="Group",
            )
        )
    async_add_entities(entities)


class InelnetSwitchEntity(SwitchEntity):
    """On is action 160, off is action 144. State is never reported."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_assumed_state = True

    def __init__(
        self,
        entry: ConfigEntry,
        channel: int,
        name: str,
        device_type: str,
        area: str | None,
        suffix: str,
        model: str = "Blinds controller",
    ) -> None:
        """Initialize the switch."""
        self._entry = entry
        self._channel = channel
        self._attr_unique_id = f"{entry.entry_id}-{suffix}"
        self._attr_icon = "mdi:lightbulb" if device_type == "o" else "mdi:power-socket-eu"
        info: dict[str, Any] = {
            "identifiers": {(DOMAIN, f"{entry.entry_id}-{suffix}")},
            "name": name,
            "manufacturer": "INELNET",
            "model": model,
        }
        if area:
            info["suggested_area"] = area
        self._attr_device_info = DeviceInfo(**info)

    @property
    def is_on(self) -> bool | None:
        """The controller does not report whether a light is on."""
        return None

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the output on."""
        client = self._entry.runtime_data.clients[self._channel]
        await client.up(session=async_get_clientsession(self.hass))

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the output off."""
        client = self._entry.runtime_data.clients[self._channel]
        await client.stop(session=async_get_clientsession(self.hass))
