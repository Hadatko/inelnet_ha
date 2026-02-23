"""INELNET channel client: one object per channel (host + channel)."""

from __future__ import annotations

import logging
from enum import IntEnum
from typing import TYPE_CHECKING, Any

import aiohttp

if TYPE_CHECKING:
    from aiohttp import ClientSession

_LOGGER = logging.getLogger(__name__)


class Action(IntEnum):
    """REST API action codes (send_act parameter)."""

    STOP = 144
    UP = 160
    UP_SHORT = 176
    DOWN = 192
    DOWN_SHORT = 208
    PROGRAM = 224

DEFAULT_TIMEOUT = aiohttp.ClientTimeout(total=10)
URL_PATH = "/msg.htm"


class InelnetChannel:
    """
    Client for one INELNET controller channel.
    One instance per (host, channel); all methods target that channel only.
    """

    __slots__ = ("_host", "_channel", "_base_url")

    def __init__(self, host: str, channel: int) -> None:
        if channel < 1:
            raise ValueError("channel must be >= 1")
        self._host = host.strip()
        self._channel = channel
        self._base_url = f"http://{self._host}{URL_PATH}"

    @property
    def host(self) -> str:
        return self._host

    @property
    def channel(self) -> int:
        return self._channel

    def _payload(self, act: Action | int) -> str:
        return f"send_ch={self._channel}&send_act={int(act)}"

    async def send_command(
        self,
        act: Action | int,
        *,
        session: ClientSession | None = None,
        timeout: aiohttp.ClientTimeout = DEFAULT_TIMEOUT,
    ) -> bool:
        """
        Send one REST command to this channel.
        If session is not provided, a temporary session is used for the request.
        """
        payload = self._payload(act)
        if session is not None:
            return await self._post(session, payload, timeout)
        async with aiohttp.ClientSession() as own_session:
            return await self._post(own_session, payload, timeout)

    async def _post(
        self,
        session: ClientSession,
        payload: str,
        timeout: aiohttp.ClientTimeout,
    ) -> bool:
        try:
            async with session.post(
                self._base_url,
                data=payload,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=timeout,
            ) as resp:
                return resp.status == 200
        except (aiohttp.ClientError, OSError) as e:
            _LOGGER.warning("INELNET command failed %s: %s", self._base_url, e)
            return False

    async def ping(
        self,
        *,
        session: ClientSession | None = None,
        timeout: aiohttp.ClientTimeout = DEFAULT_TIMEOUT,
    ) -> bool:
        """
        Check connectivity to the controller (GET to msg.htm).
        If session is not provided, a temporary session is used.
        """
        if session is not None:
            return await self._get(session, timeout)
        async with aiohttp.ClientSession() as own_session:
            return await self._get(own_session, timeout)

    async def _get(
        self,
        session: ClientSession,
        timeout: aiohttp.ClientTimeout,
    ) -> bool:
        try:
            async with session.get(self._base_url, timeout=timeout) as resp:
                return resp.status < 400
        except (aiohttp.ClientError, OSError):
            return False

    # Convenience methods
    async def up(
        self,
        *,
        session: ClientSession | None = None,
        **kwargs: Any,
    ) -> bool:
        """Roll up (open)."""
        return await self.send_command(Action.UP, session=session, **kwargs)

    async def down(
        self,
        *,
        session: ClientSession | None = None,
        **kwargs: Any,
    ) -> bool:
        """Roll down (close)."""
        return await self.send_command(Action.DOWN, session=session, **kwargs)

    async def stop(
        self,
        *,
        session: ClientSession | None = None,
        **kwargs: Any,
    ) -> bool:
        """Stop movement."""
        return await self.send_command(Action.STOP, session=session, **kwargs)

    async def up_short(
        self,
        *,
        session: ClientSession | None = None,
        **kwargs: Any,
    ) -> bool:
        """Short move up."""
        return await self.send_command(Action.UP_SHORT, session=session, **kwargs)

    async def down_short(
        self,
        *,
        session: ClientSession | None = None,
        **kwargs: Any,
    ) -> bool:
        """Short move down."""
        return await self.send_command(Action.DOWN_SHORT, session=session, **kwargs)

    async def program(
        self,
        *,
        session: ClientSession | None = None,
        **kwargs: Any,
    ) -> bool:
        """Programming mode (e.g. for pairing remote)."""
        return await self.send_command(Action.PROGRAM, session=session, **kwargs)
