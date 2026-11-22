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
    """Each room is its own section. A shutter without a room stays separate."""
    config = build_dashboard(
        [
            {"entity_id": "cover.a", "name": "A", "area": "Kuchyňa"},
            {"entity_id": "cover.b", "name": "B", "area": None},
            {"entity_id": "cover.c", "name": "C", "area": "Kuchyňa"},
        ],
        "en",
    )
    sections = config["views"][0]["sections"]
    assert sections[0]["cards"][0]["heading"] == "Kuchyňa"
    assert [card["entity"] for card in sections[0]["cards"] if card["type"] == "tile"] == [
        "cover.a",
        "cover.c",
    ]
    assert sections[1]["cards"][0]["heading"] == "No room"
    assert sections[1]["cards"][1]["entity"] == "cover.b"


def test_dashboard_puts_groups_above_rooms_and_pairing_on_its_own_view() -> None:
    """Controller groups are the first section. Pairing is not on the daily view."""
    config = build_dashboard(
        [
            {
                "entity_id": "cover.group",
                "name": "Celý byt",
                "area": None,
                "kind": "group",
                "domain": "cover",
            },
            {
                "entity_id": "cover.room",
                "name": "Okno",
                "area": "Living room",
                "kind": "shutter",
                "domain": "cover",
            },
            {
                "entity_id": "button.pair",
                "name": "Okno",
                "area": "Living room",
                "kind": "pair",
                "domain": "button",
            },
        ],
        "sk",
    )
    home = config["views"][0]
    assert home["sections"][0]["cards"][0]["heading"] == "Skupiny"
    assert home["sections"][0]["cards"][1]["entity"] == "cover.group"
    assert home["sections"][1]["cards"][0]["heading"] == "Living room"
    pairing = config["views"][1]
    assert pairing["title"] == "Párovanie"
    buttons = [
        card
        for section in pairing["sections"]
        for card in section["cards"]
        if card["type"] == "button"
    ]
    assert buttons[0]["entity"] == "button.pair"


def test_dashboard_empty_state() -> None:
    """An integration with no covers explains that channels are missing."""
    config = build_dashboard([], "cs")
    assert "Zatím žádné rolety" in config["views"][0]["cards"][0]["content"]
