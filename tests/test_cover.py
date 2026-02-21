"""Tests for INELNET Blinds cover platform."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from custom_components.inelnet.const import (
    ACT_DOWN,
    ACT_STOP,
    ACT_UP,
    CONF_CHANNELS,
    CONF_HOST,
    DOMAIN,
)
from custom_components.inelnet.cover import InelnetCoverEntity, send_command


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


async def test_send_command_payload() -> None:
    """Test send_command uses correct URL and payload with shared session."""
    post_calls = []
    mock_hass = MagicMock()

    class MockResponse:
        status = 200

    class AsyncCtx:
        async def __aenter__(self):
            return MockResponse()

        async def __aexit__(self, *args):
            pass

    def capture_post(self, url, *args, data=None, **kwargs):
        post_calls.append((url, data))
        return AsyncCtx()

    class MockSession:
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            pass
        post = capture_post

    with patch(
        "custom_components.inelnet.cover.async_get_clientsession",
        return_value=MockSession(),
    ):
        result = await send_command(mock_hass, "10.0.0.1", 3, ACT_STOP)

    assert result is True
    assert len(post_calls) == 1
    assert post_calls[0][0] == "http://10.0.0.1/msg.htm"
    assert post_calls[0][1] == "send_ch=3&send_act=144"


def test_cover_entity_attributes(cover_config_entry: ConfigEntry) -> None:
    """Test cover entity has correct attributes and device info."""
    entity = InelnetCoverEntity(cover_config_entry, "192.168.1.67", 1)
    assert entity.unique_id == "test-cover-entry-ch1"
    assert entity.device_info is not None
    identifiers = getattr(entity.device_info, "identifiers", entity.device_info.get("identifiers"))
    assert identifiers == {(DOMAIN, "test-cover-entry-ch1")}
    name = getattr(entity.device_info, "name", entity.device_info.get("name"))
    assert name == "Blind channel 1"
    assert entity.is_closed is None


async def test_cover_open_sends_up_command(
    cover_config_entry: ConfigEntry,
) -> None:
    """Test async_open_cover calls send_command with ACT_UP."""
    entity = InelnetCoverEntity(cover_config_entry, "192.168.1.67", 1)
    entity.hass = MagicMock()
    with patch(
        "custom_components.inelnet.cover.send_command",
        new_callable=AsyncMock,
    ) as mock_send:
        await entity.async_open_cover()
    mock_send.assert_called_once_with(entity.hass, "192.168.1.67", 1, ACT_UP)


async def test_cover_close_sends_down_command(
    cover_config_entry: ConfigEntry,
) -> None:
    """Test async_close_cover calls send_command with ACT_DOWN."""
    entity = InelnetCoverEntity(cover_config_entry, "192.168.1.67", 1)
    entity.hass = MagicMock()
    with patch(
        "custom_components.inelnet.cover.send_command",
        new_callable=AsyncMock,
    ) as mock_send:
        await entity.async_close_cover()
    mock_send.assert_called_once_with(entity.hass, "192.168.1.67", 1, ACT_DOWN)


async def test_cover_stop_sends_stop_command(
    cover_config_entry: ConfigEntry,
) -> None:
    """Test async_stop_cover calls send_command with ACT_STOP."""
    entity = InelnetCoverEntity(cover_config_entry, "192.168.1.67", 1)
    entity.hass = MagicMock()
    with patch(
        "custom_components.inelnet.cover.send_command",
        new_callable=AsyncMock,
    ) as mock_send:
        await entity.async_stop_cover()
    mock_send.assert_called_once_with(entity.hass, "192.168.1.67", 1, ACT_STOP)
