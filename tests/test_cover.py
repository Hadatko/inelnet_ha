"""Tests for INELNET Blinds cover platform."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from custom_components.inelnet.const import (
    CONF_CHANNELS,
    CONF_HOST,
    DOMAIN,
)
from custom_components.inelnet.cover import InelnetCoverEntity
from inelnet_api import InelnetChannel


@pytest.fixture
def cover_config_entry() -> ConfigEntry:
    """Config entry for cover tests."""
    return ConfigEntry(
        version=1,
        minor_version=0,
        domain=DOMAIN,
        title="INELNET test",
        data={CONF_HOST: "192.168.1.67", CONF_CHANNELS: [1, 2]},
        source="user",
        options={},
        entry_id="test-cover-entry",
        unique_id="192.168.1.67-1,2",
        discovery_keys=set(),
        subentries_data={},
    )


def test_cover_entity_attributes(cover_config_entry: ConfigEntry) -> None:
    """Test cover entity has correct attributes and device info."""
    client = InelnetChannel("192.168.1.67", 1)
    entity = InelnetCoverEntity(cover_config_entry, client)
    assert entity.unique_id == "test-cover-entry-ch1"
    assert entity.device_info is not None
    identifiers = getattr(entity.device_info, "identifiers", entity.device_info.get("identifiers"))
    assert identifiers == {(DOMAIN, "test-cover-entry-ch1")}
    name = getattr(entity.device_info, "name", entity.device_info.get("name"))
    assert name == "INELNET Blinds channel 1"
    assert entity.is_closed is None
    assert entity.assumed_state is True


async def test_cover_open_sends_up_command(
    cover_config_entry: ConfigEntry,
) -> None:
    """Test async_open_cover calls client.up with session."""
    client = MagicMock()
    client.channel = 1
    client.up = AsyncMock(return_value=True)
    entity = InelnetCoverEntity(cover_config_entry, client)
    entity.hass = MagicMock()
    mock_session = MagicMock()
    with patch(
        "custom_components.inelnet.cover.async_get_clientsession",
        return_value=mock_session,
    ):
        await entity.async_open_cover()
    client.up.assert_called_once_with(session=mock_session)


async def test_cover_close_sends_down_command(
    cover_config_entry: ConfigEntry,
) -> None:
    """Test async_close_cover calls client.down with session."""
    client = MagicMock()
    client.channel = 1
    client.down = AsyncMock(return_value=True)
    entity = InelnetCoverEntity(cover_config_entry, client)
    entity.hass = MagicMock()
    mock_session = MagicMock()
    with patch(
        "custom_components.inelnet.cover.async_get_clientsession",
        return_value=mock_session,
    ):
        await entity.async_close_cover()
    client.down.assert_called_once_with(session=mock_session)


async def test_cover_stop_sends_stop_command(
    cover_config_entry: ConfigEntry,
) -> None:
    """Test async_stop_cover calls client.stop with session."""
    client = MagicMock()
    client.channel = 1
    client.stop = AsyncMock(return_value=True)
    entity = InelnetCoverEntity(cover_config_entry, client)
    entity.hass = MagicMock()
    mock_session = MagicMock()
    with patch(
        "custom_components.inelnet.cover.async_get_clientsession",
        return_value=mock_session,
    ):
        await entity.async_stop_cover()
    client.stop.assert_called_once_with(session=mock_session)
