"""INELNET Blinds integration. One device per channel; no multi-channel (group) control."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import CONF_CHANNELS, CONF_HOST, DOMAIN


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up INELNET: one device per channel, each entity controls a single channel only."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        CONF_HOST: entry.data[CONF_HOST],
        CONF_CHANNELS: entry.data[CONF_CHANNELS],
    }

    await hass.config_entries.async_forward_entry_setups(
        entry, [Platform.COVER, Platform.BUTTON]
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(
        entry, [Platform.COVER, Platform.BUTTON]
    ):
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
