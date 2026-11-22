"""Tests for INELNET Blinds button platform."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.config_entries import ConfigEntry

from custom_components.inelnet.button import InelnetButtonEntity
from custom_components.inelnet.const import (
    Action,
    CONF_CHANNELS,
    CONF_HOST,
    DOMAIN,
)
from inelnet_api import InelnetChannel


@pytest.fixture
def button_config_entry() -> ConfigEntry:
    """Config entry for button tests."""
    return ConfigEntry(
        version=1,
        minor_version=0,
        domain=DOMAIN,
        title="INELNET test",
        data={CONF_HOST: "192.168.1.67", CONF_CHANNELS: [1, 2]},
        source="user",
        options={},
        entry_id="test-button-entry",
        unique_id="192.168.1.67-1,2",
        discovery_keys=set(),
        subentries_data={},
    )


def test_button_entity_attributes(button_config_entry: ConfigEntry) -> None:
    """Test button entity has correct unique_id and device info."""
    client = InelnetChannel("192.168.1.67", 2)
    entity = InelnetButtonEntity(
        entry=button_config_entry,
        client=client,
        unique_id_suffix="short_up",
        action=Action.UP_SHORT,
        translation_key="short_up",
    )
    assert entity.unique_id == "test-button-entry-ch2-short_up"
    assert entity.device_info is not None
    identifiers = getattr(entity.device_info, "identifiers", entity.device_info.get("identifiers"))
    assert identifiers == {(DOMAIN, "test-button-entry-ch2")}
    assert entity.entity_registry_enabled_default is False


async def test_button_press_sends_command(button_config_entry: ConfigEntry) -> None:
    """Test async_press calls client.send_command with correct action code."""
    client = MagicMock()
    client.channel = 1
    client.send_command = AsyncMock(return_value=True)
    entity = InelnetButtonEntity(
        entry=button_config_entry,
        client=client,
        unique_id_suffix="program",
        action=Action.PROGRAM,
        translation_key="program",
    )
    entity.hass = MagicMock()
    mock_session = MagicMock()
    with patch(
        "custom_components.inelnet.button.async_get_clientsession",
        return_value=mock_session,
    ):
        await entity.async_press()
    client.send_command.assert_called_once_with(Action.PROGRAM, session=mock_session)


async def test_button_short_down_sends_correct_code(
    button_config_entry: ConfigEntry,
) -> None:
    """Test Short move down button sends ACT_DOWN_SHORT."""
    client = MagicMock()
    client.channel = 3
    client.send_command = AsyncMock(return_value=True)
    entity = InelnetButtonEntity(
        entry=button_config_entry,
        client=client,
        unique_id_suffix="short_down",
        action=Action.DOWN_SHORT,
        translation_key="short_down",
    )
    entity.hass = MagicMock()
    mock_session = MagicMock()
    with patch(
        "custom_components.inelnet.button.async_get_clientsession",
        return_value=mock_session,
    ):
        await entity.async_press()
    client.send_command.assert_called_once_with(Action.DOWN_SHORT, session=mock_session)
