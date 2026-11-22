"""Read the INELNET controller catalogue.

The movement API on msg.htm needs no login. Names, rooms, groups and schedules
are separate JSON files and require the web login (HTTP basic auth).
"""

from __future__ import annotations

import json
from dataclasses import dataclass

import aiohttp

_TIMEOUT = aiohttp.ClientTimeout(total=10)
_UNASSIGNED_PLACE = 255
WEEKDAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
COVER_TYPES = frozenset({"r", "z", "m", "b", "d", "g"})
SWITCH_TYPES = frozenset({"o", "w"})


class CatalogueError(Exception):
    """The catalogue could not be read."""


class CatalogueAuthError(CatalogueError):
    """The controller rejected the web login."""


@dataclass(frozen=True)
class Place:
    """A room stored on the controller."""

    number: int
    name: str


@dataclass(frozen=True)
class Device:
    """One output. place is None when the controller leaves it unassigned."""

    channel: int
    name: str
    device_type: str
    place: int | None


@dataclass(frozen=True)
class Group:
    """A controller group. Its number is the channel used to move every member."""

    number: int
    name: str
    device_type: str
    members: tuple[int, ...]


@dataclass(frozen=True)
class Program:
    """A schedule. astro N is a clock time; W and Z are sunrise and sunset."""

    number: int
    channel: int
    days: int
    hour: int
    minute: int
    action: int
    enabled: bool
    astro: str


@dataclass(frozen=True)
class Catalogue:
    """Everything the controller lists for one login."""

    places: tuple[Place, ...]
    devices: tuple[Device, ...]
    groups: tuple[Group, ...]
    programs: tuple[Program, ...]

    def place_name(self, number: int | None) -> str | None:
        """Room name for a place id."""
        if number is None:
            return None
        for place in self.places:
            if place.number == number:
                return place.name
        return None

    def channel_name(self, channel: int) -> str:
        """Device or group name for a channel number."""
        for device in self.devices:
            if device.channel == channel:
                return device.name
        for group in self.groups:
            if group.number == channel:
                return group.name
        return str(channel)


def weekday_names(mask: int) -> list[str]:
    """Monday is bit 0, matching the controller day checkboxes."""
    return [name for bit, name in enumerate(WEEKDAYS) if mask & (1 << bit)]


def is_switch(device_type: str) -> bool:
    """Lights and sockets are switches. Everything else is a cover."""
    return device_type in SWITCH_TYPES


def parse_catalogue(
    places_payload: dict,
    devices_payload: dict,
    groups_payload: dict,
    programs_payload: dict,
) -> Catalogue:
    """Build a catalogue from the four JSON documents."""
    return Catalogue(
        places=tuple(_places(places_payload)),
        devices=tuple(_devices(devices_payload)),
        groups=tuple(_groups(groups_payload)),
        programs=tuple(_programs(programs_payload)),
    )


def _places(payload: dict) -> list[Place]:
    return [
        Place(number=int(item["no"]), name=str(item["naz"]))
        for item in payload.get("miejsce") or []
    ]


def _devices(payload: dict) -> list[Device]:
    devices: list[Device] = []
    for item in payload.get("urz") or []:
        place = int(item["w"])
        devices.append(
            Device(
                channel=int(item["no"]),
                name=str(item["naz"]),
                device_type=str(item["typ"]),
                place=None if place == _UNASSIGNED_PLACE else place,
            )
        )
    return devices


def _groups(payload: dict) -> list[Group]:
    return [
        Group(
            number=int(item["no"]),
            name=str(item["naz"]),
            device_type=str(item.get("typ") or "r"),
            members=tuple(int(member) for member in item.get("s") or []),
        )
        for item in payload.get("grup") or []
    ]


def _programs(payload: dict) -> list[Program]:
    return [
        Program(
            number=int(item["no"]),
            channel=int(item["ch"]),
            days=int(item["day"]),
            hour=int(item["h"]),
            minute=int(item["min"]),
            action=int(item["act"]),
            enabled=str(item.get("en")) == "1",
            astro=str(item.get("astro") or "N"),
        )
        for item in payload.get("program") or []
    ]


async def async_fetch_catalogue(
    session: aiohttp.ClientSession,
    host: str,
    username: str,
    password: str,
) -> Catalogue:
    """Download places, devices, groups and schedules."""

    async def _get(path: str) -> dict:
        try:
            async with session.get(
                f"http://{host.strip()}/{path}",
                auth=aiohttp.BasicAuth(username, password),
                timeout=_TIMEOUT,
            ) as response:
                if response.status == 401:
                    raise CatalogueAuthError
                if response.status >= 400:
                    raise CatalogueError(f"HTTP {response.status}")
                body = await response.text()
        except CatalogueError:
            raise
        except (aiohttp.ClientError, OSError, TimeoutError) as err:
            raise CatalogueError(str(err)) from err
        try:
            parsed = json.loads(body)
        except json.JSONDecodeError as err:
            raise CatalogueError("Catalogue was not JSON") from err
        if not isinstance(parsed, dict):
            raise CatalogueError("Catalogue was not an object")
        return parsed

    places, devices, groups, programs = (
        await _get("gpl.htm"),
        await _get("gdv.htm"),
        await _get("ggr.htm"),
        await _get("gpr.htm"),
    )
    # Sequential on purpose: the controller is a small embedded web server.
    return parse_catalogue(places, devices, groups, programs)
