"""Tests for INELNET Blinds integration setup and unload."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from custom_components.inelnet import async_setup_entry, async_unload_entry
from custom_components.inelnet.const import CONF_CHANNELS, CONF_HOST, DOMAIN
from custom_components.inelnet.dashboard import build_dashboard


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


def test_dashboard_has_one_tile_per_shutter() -> None:
    """Each shutter is its own open/stop/close card, with no group control."""
    config = build_dashboard(
        [
            {"entity_id": "cover.kitchen", "name": "Kitchen", "area": None},
            {"entity_id": "cover.bedroom", "name": "Bedroom", "area": None},
        ],
        "sk",
    )
    cards = config["views"][0]["sections"][0]["cards"]
    assert config["views"][0]["title"] == "Rolety"
    assert [card["entity"] for card in cards] == ["cover.kitchen", "cover.bedroom"]
    assert cards[0]["features"] == [{"type": "cover-open-close"}]


def test_dashboard_groups_rooms() -> None:
    """Assigned rooms become headings. A shutter without a room stays separate."""
    config = build_dashboard(
        [
            {"entity_id": "cover.a", "name": "A", "area": "Kuchyňa"},
            {"entity_id": "cover.b", "name": "B", "area": None},
            {"entity_id": "cover.c", "name": "C", "area": "Kuchyňa"},
        ],
        "en",
    )
    cards = config["views"][0]["sections"][0]["cards"]
    headings = [card["heading"] for card in cards if card["type"] == "heading"]
    entities = [card["entity"] for card in cards if card["type"] == "tile"]
    assert headings == ["Kuchyňa", "No room"]
    assert entities == ["cover.a", "cover.c", "cover.b"]


def test_dashboard_empty_state() -> None:
    """An integration with no covers explains that channels are missing."""
    config = build_dashboard([], "cs")
    assert "Zatím žádné rolety" in config["views"][0]["cards"][0]["content"]
