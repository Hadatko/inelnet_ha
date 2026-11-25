"""Tests for INELNET Blinds integration setup and unload."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from custom_components.inelnet import area_sync_action, async_setup_entry, async_unload_entry
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
    with (
        patch(
            "homeassistant.config_entries.ConfigEntries.async_forward_entry_setups",
            new_callable=AsyncMock,
        ),
        patch(
            "custom_components.inelnet.InelnetChannel.ping",
            new_callable=AsyncMock,
            return_value=True,
        ),
    ):
        result = await async_setup_entry(hass, mock_config_entry)
    assert result is True
    assert mock_config_entry.runtime_data.host == "192.168.1.67"
    assert mock_config_entry.runtime_data.channels == [1, 2]
    assert set(mock_config_entry.runtime_data.clients) == {1, 2}


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_unload_entry_removes_config(
    hass: HomeAssistant, mock_config_entry: ConfigEntry
) -> None:
    """Test async_unload_entry unloads the platforms."""
    with patch(
        "homeassistant.config_entries.ConfigEntries.async_unload_platforms",
        new_callable=AsyncMock,
        return_value=True,
    ):
        result = await async_unload_entry(hass, mock_config_entry)
    assert result is True


def test_area_sync_fills_an_empty_area_once() -> None:
    """The first observation places a device only when Home Assistant has no room for it."""
    assert area_sync_action(None, 1, None, "kitchen") == ("kitchen", True)
    assert area_sync_action(None, 1, "living", "kitchen") == (None, True)


def test_area_sync_moves_only_when_the_controller_room_changes() -> None:
    """A room set in Home Assistant stays until the controller room changes."""
    assert area_sync_action(1, 1, "living", "kitchen") == (None, False)
    assert area_sync_action(1, 2, "living", "kitchen") == ("kitchen", True)
    assert area_sync_action(1, 2, "kitchen", "kitchen") == (None, True)
