"""Tests for INELNET Blinds integration setup and unload."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from custom_components.inelnet import async_setup_entry, async_unload_entry
from custom_components.inelnet.const import CONF_CHANNELS, CONF_HOST, DOMAIN


@pytest.fixture
def mock_config_entry() -> ConfigEntry:
    """Create a mock config entry."""
    return ConfigEntry(
        version=1,
        minor_version=0,
        domain=DOMAIN,
        title="INELNET 192.168.1.67 (ch 1,2)",
        data={CONF_HOST: "192.168.1.67", CONF_CHANNELS: [1, 2]},
        source="user",
        options={},
        entry_id="test-entry-id",
        unique_id="192.168.1.67-1,2",
        discovery_keys=set(),
        subentries_data={},
    )


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_setup_entry_stores_config(
    hass: HomeAssistant, mock_config_entry: ConfigEntry
) -> None:
    """Test async_setup_entry stores host and channels in hass.data."""
    with patch(
        "homeassistant.config_entries.ConfigEntries.async_forward_entry_setups",
        new_callable=AsyncMock,
    ):
        result = await async_setup_entry(hass, mock_config_entry)
    assert result is True
    assert DOMAIN in hass.data
    assert mock_config_entry.entry_id in hass.data[DOMAIN]
    assert hass.data[DOMAIN][mock_config_entry.entry_id][CONF_HOST] == "192.168.1.67"
    assert hass.data[DOMAIN][mock_config_entry.entry_id][CONF_CHANNELS] == [1, 2]


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_unload_entry_removes_config(
    hass: HomeAssistant, mock_config_entry: ConfigEntry
) -> None:
    """Test async_unload_entry removes data and returns True."""
    hass.data.setdefault(DOMAIN, {})[mock_config_entry.entry_id] = {
        CONF_HOST: "192.168.1.67",
        CONF_CHANNELS: [1, 2],
    }
    with patch(
        "homeassistant.config_entries.ConfigEntries.async_unload_platforms",
        new_callable=AsyncMock,
        return_value=True,
    ):
        result = await async_unload_entry(hass, mock_config_entry)
    assert result is True
    assert mock_config_entry.entry_id not in hass.data.get(DOMAIN, {})
