"""Tests for INELNET Blinds button platform."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.config_entries import ConfigEntry

from custom_components.inelnet.button import InelnetButtonEntity
from custom_components.inelnet.const import (
    ACT_DOWN_SHORT,
    ACT_PROGRAM,
    ACT_UP_SHORT,
    CONF_CHANNELS,
    CONF_HOST,
    DOMAIN,
)


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
    entity = InelnetButtonEntity(
        entry=button_config_entry,
        host="192.168.1.67",
        channel=2,
        unique_id_suffix="short_up",
        action_code=ACT_UP_SHORT,
        entity_name="Short move up",
    )
    assert entity.unique_id == "test-button-entry-ch2-short_up"
    assert entity.name == "Short move up"
    assert entity.device_info is not None
    identifiers = getattr(entity.device_info, "identifiers", entity.device_info.get("identifiers"))
    assert identifiers == {(DOMAIN, "test-button-entry-ch2")}
    assert entity.entity_registry_enabled_default is False


async def test_button_press_sends_command(button_config_entry: ConfigEntry) -> None:
    """Test async_press calls send_command with correct action code."""
    entity = InelnetButtonEntity(
        entry=button_config_entry,
        host="192.168.1.67",
        channel=1,
        unique_id_suffix="program",
        action_code=ACT_PROGRAM,
        entity_name="Programming mode",
    )
    entity.hass = MagicMock()
    with patch(
        "custom_components.inelnet.button.send_command",
        new_callable=AsyncMock,
    ) as mock_send:
        await entity.async_press()
    mock_send.assert_called_once_with(entity.hass, "192.168.1.67", 1, ACT_PROGRAM)


async def test_button_short_down_sends_correct_code(
    button_config_entry: ConfigEntry,
) -> None:
    """Test Short move down button sends ACT_DOWN_SHORT."""
    entity = InelnetButtonEntity(
        entry=button_config_entry,
        host="10.0.0.1",
        channel=3,
        unique_id_suffix="short_down",
        action_code=ACT_DOWN_SHORT,
        entity_name="Short move down",
    )
    entity.hass = MagicMock()
    with patch(
        "custom_components.inelnet.button.send_command",
        new_callable=AsyncMock,
    ) as mock_send:
        await entity.async_press()
    mock_send.assert_called_once_with(entity.hass, "10.0.0.1", 3, ACT_DOWN_SHORT)
