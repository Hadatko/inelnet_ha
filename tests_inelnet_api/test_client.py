"""Tests for inelnet_api client."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from inelnet_api import Action, InelnetChannel


def test_channel_valid() -> None:
    c = InelnetChannel("192.168.1.67", 1)
    assert c.host == "192.168.1.67"
    assert c.channel == 1


def test_channel_invalid() -> None:
    with pytest.raises(ValueError, match=">= 1"):
        InelnetChannel("192.168.1.67", 0)
    with pytest.raises(ValueError, match=">= 1"):
        InelnetChannel("192.168.1.67", -1)


def test_channel_accepts_any_positive() -> None:
    c = InelnetChannel("192.168.1.67", 17)
    assert c.channel == 17


def test_action_enum_values() -> None:
    assert int(Action.STOP) == 144
    assert int(Action.UP) == 160
    assert int(Action.DOWN) == 192


async def test_send_command_payload() -> None:
    post_calls = []
    mock_session = MagicMock()

    class MockResponse:
        status = 200

    class AsyncCtx:
        async def __aenter__(self):
            return MockResponse()
        async def __aexit__(self, *args):
            pass

    def capture_post(url, *args, data=None, **kwargs):
        post_calls.append((url, data))
        return AsyncCtx()

    mock_session.post = capture_post
    channel = InelnetChannel("10.0.0.1", 3)
    result = await channel.send_command(Action.STOP, session=mock_session)
    assert result is True
    assert len(post_calls) == 1
    assert post_calls[0][0] == "http://10.0.0.1/msg.htm"
    assert post_calls[0][1] == "send_ch=3&send_act=144"
