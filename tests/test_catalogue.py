"""Tests for the INELNET catalogue parser."""

from __future__ import annotations

import json

import pytest

from custom_components.inelnet.catalogue import (
    CatalogueAuthError,
    CatalogueError,
    async_fetch_catalogue,
    parse_catalogue,
    weekday_names,
)
from custom_components.inelnet.sensor import InelnetScheduleSensor

PLACES = {"miejsce": [{"no": "0", "naz": "Bedroom"}, {"no": "2", "naz": "Living room"}]}
DEVICES = {
    "urz": [
        {"no": "1", "typ": "r", "naz": "Bedroom", "w": "0"},
        {"no": "3", "typ": "z", "naz": "Window", "w": "2"},
        {"no": "9", "typ": "o", "naz": "Lamp", "w": "255"},
    ]
}
GROUPS = {
    "grup": [
        {"no": "100", "typ": "r", "naz": "Whole home", "s": ["1", "3"]},
    ]
}
PROGRAMS = {
    "program": [
        {
            "no": "0",
            "ch": "1",
            "day": "3",
            "h": "3",
            "min": "33",
            "act": "160",
            "en": "1",
            "astro": "N",
        }
    ]
}


def test_parse_catalogue_reads_rooms_devices_groups_and_schedules() -> None:
    """The four JSON documents become rooms, outputs, groups and schedules."""
    catalogue = parse_catalogue(PLACES, DEVICES, GROUPS, PROGRAMS)
    assert catalogue.place_name(0) == "Bedroom"
    assert catalogue.place_name(None) is None
    assert catalogue.devices[2].place is None
    assert catalogue.devices[2].device_type == "o"
    assert catalogue.groups[0].members == (1, 3)
    assert catalogue.groups[0].number == 100
    assert catalogue.channel_name(100) == "Whole home"
    program = catalogue.programs[0]
    assert program.enabled is True
    assert program.hour == 3
    assert program.minute == 33
    assert weekday_names(program.days) == ["Mon", "Tue"]


def test_schedule_sensor_lists_programs() -> None:
    """The sensor counts enabled schedules and keeps the clock time."""
    catalogue = parse_catalogue(PLACES, DEVICES, GROUPS, PROGRAMS)
    sensor = InelnetScheduleSensor("entry", catalogue)
    assert sensor.native_value == 1
    listed = sensor.extra_state_attributes["programs"][0]
    assert listed["time"] == "03:33"
    assert listed["name"] == "Bedroom"
    assert listed["days"] == ["Mon", "Tue"]


def test_parse_catalogue_accepts_empty_lists() -> None:
    """A controller with nothing configured still parses."""
    catalogue = parse_catalogue(
        {"miejsce": []},
        {"urz": []},
        {"grup": []},
        {"program": []},
    )
    assert catalogue.devices == ()
    assert catalogue.programs == ()


class _Response:
    def __init__(self, status: int, body: str) -> None:
        self.status = status
        self._body = body

    async def text(self) -> str:
        return self._body

    async def __aenter__(self) -> _Response:
        return self

    async def __aexit__(self, *args: object) -> bool:
        return False


class _Session:
    def __init__(self, responses: dict[str, _Response]) -> None:
        self.responses = responses

    def get(self, url: str, **kwargs: object) -> _Response:
        name = url.rsplit("/", 1)[-1]
        return self.responses[name]


async def test_fetch_catalogue_uses_the_four_documents() -> None:
    """A successful login returns the parsed catalogue."""
    bodies = {
        "gpl.htm": json.dumps(PLACES),
        "gdv.htm": json.dumps(DEVICES),
        "ggr.htm": json.dumps(GROUPS),
        "gpr.htm": json.dumps(PROGRAMS),
    }
    session = _Session({name: _Response(200, body) for name, body in bodies.items()})
    catalogue = await async_fetch_catalogue(session, "192.168.1.67", "admin", "secret")
    assert [device.channel for device in catalogue.devices] == [1, 3, 9]


async def test_fetch_catalogue_rejects_unauthorized() -> None:
    """HTTP 401 is an authentication failure, not a generic catalogue error."""
    session = _Session(
        {name: _Response(401, "no") for name in ("gpl.htm", "gdv.htm", "ggr.htm", "gpr.htm")}
    )
    with pytest.raises(CatalogueAuthError):
        await async_fetch_catalogue(session, "192.168.1.67", "admin", "wrong")


async def test_fetch_catalogue_rejects_invalid_json() -> None:
    """A 200 response that is not JSON is a catalogue error."""
    session = _Session(
        {name: _Response(200, "nope") for name in ("gpl.htm", "gdv.htm", "ggr.htm", "gpr.htm")}
    )
    with pytest.raises(CatalogueError):
        await async_fetch_catalogue(session, "192.168.1.67", "admin", "secret")
