"""Config flow for INELNET Blinds integration."""

from __future__ import annotations

import re
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

from .const import CONF_CHANNELS, CONF_HOST, DOMAIN


def parse_channels(value: str) -> list[int]:
    """Parse comma-separated channel string to list of ints 1-16."""
    if not value or not value.strip():
        raise ValueError("empty")
    parts = [p.strip() for p in value.split(",") if p.strip()]
    channels: list[int] = []
    for p in parts:
        try:
            ch = int(p)
        except ValueError:
            raise ValueError("invalid")
        if ch < 1 or ch > 16:
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

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
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
                except ValueError as e:
                    if str(e) == "empty":
                        errors["base"] = "invalid_channels"
                    elif str(e) == "invalid":
                        errors["base"] = "invalid_channels"
                    elif str(e) == "out_of_range":
                        errors["base"] = "invalid_channels"
                    elif str(e) == "duplicate":
                        errors["base"] = "invalid_channels"
                    else:
                        errors["base"] = "invalid_channels"
                else:
                    # Unique id per host + channels so multiple configs can use the same IP
                    unique_id = f"{host}-{','.join(str(c) for c in channels)}"
                    await self.async_set_unique_id(unique_id)
                    self._abort_if_unique_id_configured()

                    return self.async_create_entry(
                        title=f"INELNET {host} (ch {','.join(str(c) for c in channels)})",
                        data={
                            CONF_HOST: host,
                            CONF_CHANNELS: channels,
                        },
                    )

        data_schema = vol.Schema(
            {
                vol.Required(CONF_HOST, default="192.168.1.67"): str,
                vol.Required(CONF_CHANNELS, default="1"): str,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )
