"""Config flow for INELNET Blinds integration."""

from __future__ import annotations

import re
from typing import Any

import voluptuous as vol

from inelnet_api import InelnetChannel

from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.const import CONF_HOST
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

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


class InelnetConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for INELNET Blinds."""

    VERSION = 1
    MINOR_VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host = (user_input.get(CONF_HOST) or "").strip()
            channels_str = (user_input.get(CONF_CHANNELS) or "").strip()

            if not is_valid_host(host):
                errors["base"] = "invalid_host"
            else:
                try:
                    channels = parse_channels(channels_str)
                except ValueError:
                    errors["base"] = "invalid_channels"
                else:
                    if any(
                        entry.data.get(CONF_HOST) == host
                        for entry in self._async_current_entries()
                    ):
                        return self.async_abort(reason="already_configured")
                    # Test connection to controller before creating entry
                    session = async_get_clientsession(self.hass)
                    client = InelnetChannel(host, channels[0])
                    try:
                        if await client.ping(session=session):
                            await self.async_set_unique_id(host)
                            self._abort_if_unique_id_configured()

                            return self.async_create_entry(
                                title=f"INELNET {host} (ch {','.join(str(c) for c in channels)})",
                                data={
                                    CONF_HOST: host,
                                    CONF_CHANNELS: channels,
                                },
                            )
                        errors["base"] = "cannot_connect"
                    except Exception:
                        errors["base"] = "cannot_connect"

        data_schema = vol.Schema(
            {
                vol.Required(CONF_HOST): str,
                vol.Required(CONF_CHANNELS, default="1"): str,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
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
    """Edit the channel list of an existing controller."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Let the user add or remove channels."""
        errors: dict[str, str] = {}
        current = list(self.config_entry.data[CONF_CHANNELS])
        if user_input is not None:
            try:
                channels = parse_channels(user_input.get(CONF_CHANNELS) or "")
            except ValueError:
                errors["base"] = "invalid_channels"
            else:
                if channels != current:
                    host = self.config_entry.data[CONF_HOST]
                    self.hass.config_entries.async_update_entry(
                        self.config_entry,
                        data={CONF_HOST: host, CONF_CHANNELS: channels},
                        title=(
                            f"INELNET {host} "
                            f"(ch {','.join(str(c) for c in channels)})"
                        ),
                    )
                    await self.hass.config_entries.async_reload(
                        self.config_entry.entry_id
                    )
                return self.async_create_entry(title="", data={})

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_CHANNELS,
                        default=",".join(str(channel) for channel in current),
                    ): str,
                }
            ),
            errors=errors,
        )
