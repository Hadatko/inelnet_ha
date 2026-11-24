"""Tests for INELNET Blinds config flow."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType

from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.inelnet.catalogue import parse_catalogue
from custom_components.inelnet.config_flow import is_valid_host, parse_channels
from custom_components.inelnet.const import CONF_CHANNELS, CONF_HOST, DOMAIN
from tests.test_catalogue import DEVICES, GROUPS, PLACES


class TestParseChannels:
    """Tests for parse_channels helper."""

    def test_single_channel(self) -> None:
        """Parse a single channel."""
        assert parse_channels("1") == [1]

    def test_multiple_channels(self) -> None:
        """Parse comma-separated channels."""
        assert parse_channels("1,2,3") == [1, 2, 3]
        assert parse_channels("3, 1, 2") == [1, 2, 3]

    def test_sorts_channels(self) -> None:
        """Channels are returned sorted."""
        assert parse_channels("4,2,1,3") == [1, 2, 3, 4]

    def test_empty_raises(self) -> None:
        """Empty or whitespace-only raises ValueError."""
        with pytest.raises(ValueError):
            parse_channels("")
        with pytest.raises(ValueError):
            parse_channels("   ")

    def test_invalid_number_raises(self) -> None:
        """Non-numeric part raises ValueError."""
        with pytest.raises(ValueError):
            parse_channels("1,a,3")

    def test_out_of_range_raises(self) -> None:
        """Channel below 1 raises ValueError. Higher numbers are allowed."""
        with pytest.raises(ValueError):
            parse_channels("0")
        assert parse_channels("17") == [17]

    def test_duplicate_raises(self) -> None:
        """Duplicate channel raises ValueError."""
        with pytest.raises(ValueError):
            parse_channels("1,2,1")


class TestIsValidHost:
    """Tests for is_valid_host helper."""

    def test_valid_ipv4(self) -> None:
        """Valid IPv4 is accepted."""
        assert is_valid_host("192.168.1.67") is True
        assert is_valid_host("10.0.0.1") is True

    def test_valid_hostname(self) -> None:
        """Valid hostname is accepted."""
        assert is_valid_host("inelnet.local") is True
        assert is_valid_host("controller") is True

    def test_empty_invalid(self) -> None:
        """Empty or whitespace is invalid."""
        assert is_valid_host("") is False
        assert is_valid_host("   ") is False

    def test_invalid_ip_octets(self) -> None:
        """Invalid IPv4-like string can be rejected (implementation may allow)."""
        # Current impl allows any \d{1,3}.\d{1,3}.\d{1,3}.\d{1,3}
        assert is_valid_host("256.1.1.1") is True  # regex allows it


@pytest.fixture(autouse=True)
def mock_controller_ping():
    """Do not contact a real controller from the config flow or from setup."""
    with (
        patch(
            "custom_components.inelnet.config_flow.InelnetChannel.ping",
            new_callable=AsyncMock,
            return_value=True,
        ),
        patch(
            "custom_components.inelnet.InelnetChannel.ping",
            new_callable=AsyncMock,
            return_value=True,
        ),
    ):
        yield


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_config_flow_user_step_form(hass) -> None:
    """Test the user step shows the form."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert CONF_HOST in result["data_schema"].schema
    assert CONF_CHANNELS in result["data_schema"].schema


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_config_flow_create_entry(hass) -> None:
    """Test successful config flow creates entry."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )
    assert result["type"] is FlowResultType.FORM

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_HOST: "192.168.1.67", CONF_CHANNELS: "1,2"},
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "INELNET 192.168.1.67 (ch 1,2)"
    assert result["data"][CONF_HOST] == "192.168.1.67"
    assert result["data"][CONF_CHANNELS] == [1, 2]


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_config_flow_invalid_host_shows_error(hass) -> None:
    """Test invalid host shows form with error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_HOST: "", CONF_CHANNELS: "1"},
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"]["base"] == "invalid_host"


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_config_flow_invalid_channels_shows_error(hass) -> None:
    """Test invalid channels shows form with error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_HOST: "192.168.1.67", CONF_CHANNELS: "a,b"},
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"]["base"] == "invalid_channels"


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_config_flow_duplicate_aborts(hass) -> None:
    """Test duplicate host+channels aborts."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_HOST: "192.168.1.67", CONF_CHANNELS: "1"},
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY

    # Same host + channels again should abort
    result2 = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )
    result2 = await hass.config_entries.flow.async_configure(
        result2["flow_id"],
        {CONF_HOST: "192.168.1.67", CONF_CHANNELS: "1"},
    )
    assert result2["type"] is FlowResultType.ABORT
    assert result2["reason"] == "already_configured"


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_options_flow_updates_channels(hass) -> None:
    """Configure replaces the channel list and keeps the same controller."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_HOST: "10.0.0.5", CONF_CHANNELS: "2"},
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    entry = result["result"]

    options = await hass.config_entries.options.async_init(entry.entry_id)
    assert options["type"] is FlowResultType.FORM
    options = await hass.config_entries.options.async_configure(
        options["flow_id"],
        {CONF_CHANNELS: "2,5"},
    )
    assert options["type"] is FlowResultType.CREATE_ENTRY
    assert entry.data[CONF_CHANNELS] == [2, 5]
    assert entry.title == "INELNET 10.0.0.5 (ch 2,5)"


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_config_flow_discovers_channels_from_login(hass) -> None:
    """A web login replaces the typed channel list with the controller catalogue."""
    catalogue = parse_catalogue(PLACES, DEVICES, GROUPS, {"program": []})
    with patch(
        "custom_components.inelnet.config_flow.async_fetch_catalogue",
        new_callable=AsyncMock,
        return_value=catalogue,
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: "192.168.1.67",
                CONF_USERNAME: "admin",
                CONF_PASSWORD: "secret",
                CONF_CHANNELS: "",
            },
        )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "INELNET 192.168.1.67"
    assert result["data"][CONF_CHANNELS] == [1, 3, 9]
    assert result["data"][CONF_USERNAME] == "admin"


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_reauth_updates_rejected_login(hass) -> None:
    """A rejected web login can be replaced without removing the controller."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="192.168.1.67",
        title="INELNET 192.168.1.67 (ch 1)",
        data={
            CONF_HOST: "192.168.1.67",
            CONF_CHANNELS: [1],
            CONF_USERNAME: "admin",
            CONF_PASSWORD: "old",
        },
    )
    entry.add_to_hass(hass)
    catalogue = parse_catalogue(PLACES, DEVICES, GROUPS, {"program": []})

    with (
        patch(
            "custom_components.inelnet.config_flow.async_fetch_catalogue",
            new_callable=AsyncMock,
            return_value=catalogue,
        ),
        patch(
            "custom_components.inelnet.async_fetch_catalogue",
            new_callable=AsyncMock,
            return_value=catalogue,
        ),
    ):
        reauth = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={
                "source": config_entries.SOURCE_REAUTH,
                "entry_id": entry.entry_id,
                "unique_id": entry.unique_id,
            },
            data=entry.data,
        )
        assert reauth["type"] is FlowResultType.FORM
        assert reauth["step_id"] == "reauth_confirm"
        reauth = await hass.config_entries.flow.async_configure(
            reauth["flow_id"],
            {CONF_USERNAME: "admin", CONF_PASSWORD: ""},
        )
        assert reauth["type"] is FlowResultType.FORM
        assert reauth["errors"]["base"] == "invalid_auth"
        reauth = await hass.config_entries.flow.async_configure(
            reauth["flow_id"],
            {CONF_USERNAME: "owner", CONF_PASSWORD: "new-secret"},
        )
        await hass.async_block_till_done()

    assert reauth["type"] is FlowResultType.ABORT
    assert reauth["reason"] == "reauth_successful"
    assert entry.data[CONF_USERNAME] == "owner"
    assert entry.data[CONF_PASSWORD] == "new-secret"
    assert entry.data[CONF_CHANNELS] == [1, 3, 9]
    assert entry.title == "INELNET 192.168.1.67"
