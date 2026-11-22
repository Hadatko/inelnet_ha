"""Config flow for INELNET Blinds integration."""

from __future__ import annotations

import re
from typing import Any

import voluptuous as vol

from inelnet_api import InelnetChannel

from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .catalogue import CatalogueAuthError, CatalogueError, async_fetch_catalogue
from .const import CONF_CHANNELS, DOMAIN


def parse_channels(value: str) -> list[int]:
    """Parse comma-separated channel string to list of positive ints."""
    if not value or not value.strip():
        raise ValueError("empty")
    parts = [p.strip() for p in value.split(",") if p.strip()]
    channels: list[int] = []
    for p in parts:
        try:
            ch = int(p)
        except ValueError as err:
            raise ValueError("invalid") from err
        if ch < 1:
            raise ValueError("out_of_range")
        if ch in channels:
            raise ValueError("duplicate")
        channels.append(ch)
    return sorted(channels)


def is_valid_host(host: str) -> bool:
    """Basic validation of host (IP or hostname)."""
    host = host.strip()
    if not host:
        return False
    # Allow IPv4, simple hostname
    if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", host):
        return True
    if re.match(r"^[a-zA-Z0-9][a-zA-Z0-9.-]{0,62}$", host):
        return True
    return False


def _title(host: str, channels: list[int], discovered: bool) -> str:
    """Entry title. A discovered controller is named without the channel list."""
    if discovered:
        return f"INELNET {host}"
    return f"INELNET {host} (ch {','.join(str(channel) for channel in channels)})"


def _entry_data(
    host: str, channels: list[int], username: str, password: str
) -> dict[str, Any]:
    """Config entry data. The password is the controller web login."""
    return {
        CONF_HOST: host,
        CONF_CHANNELS: channels,
        CONF_USERNAME: username,
        CONF_PASSWORD: password,
    }


async def async_resolve_setup(
    hass: Any,
    host: str,
    user_input: dict[str, Any],
    *,
    previous_password: str = "",
) -> tuple[dict[str, Any] | None, str | None]:
    """Return entry data, or an error key when the form must be shown again."""
    username = (user_input.get(CONF_USERNAME) or "").strip()
    password = user_input.get(CONF_PASSWORD) or ""
    if username and not password:
        password = previous_password
    if username or password:
        if not username or not password:
            return None, "invalid_auth"
        session = async_get_clientsession(hass)
        try:
            catalogue = await async_fetch_catalogue(session, host, username, password)
        except CatalogueAuthError:
            return None, "invalid_auth"
        except CatalogueError:
            return None, "cannot_connect"
        channels = sorted(device.channel for device in catalogue.devices)
        if not channels:
            return None, "no_devices"
        return _entry_data(host, channels, username, password), None
    try:
        channels = parse_channels(user_input.get(CONF_CHANNELS) or "")
    except ValueError:
        return None, "invalid_channels"
    return _entry_data(host, channels, "", ""), None


def _login_fields(username: str, channels: str) -> dict[Any, Any]:
    """Web login and the manual channel list."""
    return {
        vol.Optional(CONF_USERNAME, default=username): str,
        vol.Optional(CONF_PASSWORD, default=""): TextSelector(
            TextSelectorConfig(type=TextSelectorType.PASSWORD)
        ),
        vol.Optional(CONF_CHANNELS, default=channels): str,
    }


class InelnetConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for INELNET Blinds."""

    VERSION = 1
    MINOR_VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        host = ""
        if user_input is not None:
            host = (user_input.get(CONF_HOST) or "").strip()
            if not is_valid_host(host):
                errors["base"] = "invalid_host"
            elif any(
                entry.data.get(CONF_HOST) == host
                for entry in self._async_current_entries()
            ):
                return self.async_abort(reason="already_configured")
            else:
                data, error = await async_resolve_setup(self.hass, host, user_input)
                if error is not None:
                    errors["base"] = error
                else:
                    assert data is not None
                    session = async_get_clientsession(self.hass)
                    client = InelnetChannel(host, data[CONF_CHANNELS][0])
                    try:
                        reachable = await client.ping(session=session)
                    except Exception:
                        reachable = False
                    if not reachable:
                        errors["base"] = "cannot_connect"
                    else:
                        await self.async_set_unique_id(host)
                        self._abort_if_unique_id_configured()
                        discovered = bool(data[CONF_USERNAME])
                        return self.async_create_entry(
                            title=_title(host, data[CONF_CHANNELS], discovered),
                            data=data,
                        )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST, default=host): str,
                    **_login_fields(
                        (user_input or {}).get(CONF_USERNAME) or "",
                        (user_input or {}).get(CONF_CHANNELS) or "1",
                    ),
                }
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Channel list can change without adding the controller again."""
        return InelnetOptionsFlow()


class InelnetOptionsFlow(config_entries.OptionsFlow):
    """Edit the login or the manual channel list."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Save a web login, or replace the channel list when there is no login."""
        errors: dict[str, str] = {}
        current = list(self.config_entry.data[CONF_CHANNELS])
        host = self.config_entry.data[CONF_HOST]
        username = self.config_entry.data.get(CONF_USERNAME) or ""
        if user_input is not None:
            data, error = await async_resolve_setup(
                self.hass,
                host,
                user_input,
                previous_password=self.config_entry.data.get(CONF_PASSWORD) or "",
            )
            if error is not None:
                errors["base"] = error
            else:
                assert data is not None
                discovered = bool(data[CONF_USERNAME])
                if data != {
                    CONF_HOST: host,
                    CONF_CHANNELS: current,
                    CONF_USERNAME: username,
                    CONF_PASSWORD: self.config_entry.data.get(CONF_PASSWORD) or "",
                }:
                    self.hass.config_entries.async_update_entry(
                        self.config_entry,
                        data=data,
                        title=_title(host, data[CONF_CHANNELS], discovered),
                    )
                    await self.hass.config_entries.async_reload(
                        self.config_entry.entry_id
                    )
                return self.async_create_entry(title="", data={})

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                _login_fields(username, ",".join(str(channel) for channel in current))
            ),
            errors=errors,
        )
