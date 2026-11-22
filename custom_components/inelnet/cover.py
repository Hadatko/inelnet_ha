"""Cover platform for INELNET Blinds."""

from __future__ import annotations

from typing import Any

from inelnet_api import InelnetChannel

from homeassistant.components.cover import (
    CoverDeviceClass,
    CoverEntity,
    CoverEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import InelnetConfigEntry
from .catalogue import is_switch
from .const import DEVICE_NAME_CHANNEL_TEMPLATE, DOMAIN

_DEVICE_CLASS = {
    "z": CoverDeviceClass.BLIND,
    "m": CoverDeviceClass.AWNING,
    "b": CoverDeviceClass.GATE,
    "d": CoverDeviceClass.DOOR,
    "g": CoverDeviceClass.GARAGE,
}


def device_class_for(device_type: str) -> CoverDeviceClass:
    """Cover class for a controller type code. Rollers stay shutters."""
    return _DEVICE_CLASS.get(device_type, CoverDeviceClass.SHUTTER)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: InelnetConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up one cover per shutter, plus one cover per controller group."""
    data = entry.runtime_data
    entities: list[InelnetCoverEntity] = []
    if data.catalogue is None:
        entities.extend(
            InelnetCoverEntity(entry, data.clients[channel]) for channel in data.channels
        )
    else:
        for device in data.catalogue.devices:
            if is_switch(device.device_type):
                continue
            entities.append(
                InelnetCoverEntity(
                    entry,
                    data.clients[device.channel],
                    device_name=device.name,
                    device_class=device_class_for(device.device_type),
                    area=data.catalogue.place_name(device.place),
                    tilt=device.device_type == "z",
                )
            )
        for group in data.catalogue.groups:
            if is_switch(group.device_type):
                continue
            entities.append(
                InelnetCoverEntity(
                    entry,
                    data.clients[group.number],
                    device_name=group.name,
                    device_class=device_class_for(group.device_type),
                    unique_suffix=f"gr{group.number}",
                    model="Group",
                )
            )
    async_add_entities(entities)


class InelnetCoverEntity(CoverEntity):
    """One cover entity for a single channel. One device per channel; commands target this channel only."""

    _attr_device_class = CoverDeviceClass.SHUTTER
    _attr_supported_features = (
        CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE | CoverEntityFeature.STOP
    )
    _attr_has_entity_name = True
    _attr_name = None
    # The controller accepts commands and never reports position.
    _attr_assumed_state = True

    def __init__(
        self,
        entry: ConfigEntry,
        client: InelnetChannel,
        *,
        device_name: str | None = None,
        device_class: CoverDeviceClass = CoverDeviceClass.SHUTTER,
        area: str | None = None,
        unique_suffix: str | None = None,
        model: str = "Blinds controller",
        tilt: bool = False,
    ) -> None:
        """Initialize the cover."""
        self._entry = entry
        self._client = client
        suffix = unique_suffix or f"ch{client.channel}"
        self._attr_unique_id = f"{entry.entry_id}-{suffix}"
        self._attr_device_class = device_class
        features = (
            CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE | CoverEntityFeature.STOP
        )
        if tilt:
            features |= CoverEntityFeature.OPEN_TILT | CoverEntityFeature.CLOSE_TILT
        self._attr_supported_features = features
        info: dict[str, Any] = {
            "identifiers": {(DOMAIN, f"{entry.entry_id}-{suffix}")},
            "name": device_name or DEVICE_NAME_CHANNEL_TEMPLATE.format(channel=client.channel),
            "manufacturer": "INELNET",
            "model": model,
        }
        if area:
            info["suggested_area"] = area
        self._attr_device_info = DeviceInfo(**info)

    @property
    def is_closed(self) -> bool | None:
        """State unknown – device does not report position."""
        return None

    async def async_open_cover(self, **kwargs: Any) -> None:
        """Open the cover (roll up)."""
        session = async_get_clientsession(self.hass)
        await self._client.up(session=session)

    async def async_close_cover(self, **kwargs: Any) -> None:
        """Close the cover (roll down)."""
        session = async_get_clientsession(self.hass)
        await self._client.down(session=session)

    async def async_stop_cover(self, **kwargs: Any) -> None:
        """Stop the cover."""
        session = async_get_clientsession(self.hass)
        await self._client.stop(session=session)

    async def async_open_cover_tilt(self, **kwargs: Any) -> None:
        """Short move up. Venetian blinds use this to tilt."""
        session = async_get_clientsession(self.hass)
        await self._client.up_short(session=session)

    async def async_close_cover_tilt(self, **kwargs: Any) -> None:
        """Short move down. Venetian blinds use this to tilt."""
        session = async_get_clientsession(self.hass)
        await self._client.down_short(session=session)
