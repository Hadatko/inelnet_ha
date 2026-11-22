"""INELNET Blinds integration. One device per channel; no multi-channel (group) control."""

from __future__ import annotations

from dataclasses import dataclass

from inelnet_api import InelnetChannel

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import CONF_CHANNELS
from .dashboard import async_ensure_dashboard_listeners, async_setup_dashboard


@dataclass
class InelnetRuntimeData:
    """Runtime data for INELNET config entry. One client per channel."""

    host: str
    channels: list[int]
    clients: dict[int, InelnetChannel]  # channel -> client


type InelnetConfigEntry = ConfigEntry[InelnetRuntimeData]


async def async_setup_entry(hass: HomeAssistant, entry: InelnetConfigEntry) -> bool:
    """Set up INELNET: one device per channel, each entity controls a single channel only."""
    host = entry.data[CONF_HOST]
    channels = entry.data[CONF_CHANNELS]

    # One client per channel
    clients = {ch: InelnetChannel(host, ch) for ch in channels}

    session = async_get_clientsession(hass)
    try:
        # One ping is enough: all channels use the same controller URL (host).
        if not await clients[channels[0]].ping(session=session):
            raise ConfigEntryNotReady(
                f"Controller at {host} did not respond or returned error"
            ) from None
    except ConfigEntryNotReady:
        raise
    except Exception as err:
        raise ConfigEntryNotReady(f"Cannot connect to controller at {host}") from err

    entry.runtime_data = InelnetRuntimeData(host=host, channels=channels, clients=clients)

    await hass.config_entries.async_forward_entry_setups(
        entry, [Platform.COVER, Platform.BUTTON]
    )
    async_ensure_dashboard_listeners(hass)
    await async_setup_dashboard(hass)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: InelnetConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(
        entry, [Platform.COVER, Platform.BUTTON]
    )
    if unloaded:
        await async_setup_dashboard(hass)
    return unloaded
