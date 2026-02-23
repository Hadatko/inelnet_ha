# inelnet-api

Async client library for the INELNET blinds controller REST API. One object represents one channel (host + channel number).

## Installation

```bash
pip install inelnet-api
```

## Usage

Create one `InelnetChannel` instance per channel (host + positive channel number):

```python
import asyncio
from inelnet_api import Action, InelnetChannel

async def main():
    channel = InelnetChannel(host="192.168.1.67", channel=1)

    # Check controller availability
    ok = await channel.ping()
    if not ok:
        print("Controller unavailable")
        return

    # Move: open / close / stop
    await channel.up()
    await channel.down()
    await channel.stop()

    # Short move and programming mode
    await channel.up_short()
    await channel.down_short()
    await channel.program()

    # Optional: custom session (e.g. from Home Assistant)
    # await channel.send_command(Action.UP_SHORT, session=hass_session)
    # await channel.up(session=hass_session)

asyncio.run(main())
```

## API

- **`InelnetChannel(host: str, channel: int)`** – channel must be >= 1.
- **`send_command(act, *, session=None, timeout=...)`** – send a command; `act` is an **`Action`** enum member (e.g. `Action.UP`, `Action.DOWN`, `Action.STOP`) or an integer.
- **`ping(*, session=None, timeout=...)`** – GET to the controller, returns `True` if reachable.
- **`up()`, `down()`, `stop()`, `up_short()`, `down_short()`, `program()`** – convenience methods (optional `session=`).

If you do not pass `session`, the library creates a temporary `aiohttp.ClientSession()` per call. In environments like Home Assistant you can pass `async_get_clientsession(hass)` for a shared HTTP client session.

## Publishing to PyPI (for maintainers)

```bash
# One-time
pip install build twine

# Build
python3 -m build

# Upload to PyPI (requires account and token)
twine upload dist/*
# or test PyPI only:
twine upload --repository testpypi dist/*
```

After code changes, update `version` in `pyproject.toml` and `inelnet_api/__init__.py`, then run `python3 -m build` and `twine upload dist/*` again. **Versions published on PyPI should match tagged releases** (e.g. tag `v1.0.0` for version 1.0.0).

## Development / Testing with Home Assistant

To try the library inside Home Assistant before publishing to PyPI (e.g. from the same repo):

1. In your Home Assistant dev environment, activate the virtual environment and install the library in editable mode:

   ```bash
   pip3 install -e /path/to/ha_inelnet
   ```

2. Run Home Assistant without installing the package from PyPI (so your local code is used):

   ```bash
   hass --skip-pip-packages inelnet_api
   ```

See [Building a Python library for an API](https://developers.home-assistant.io/docs/api_lib_index/) for more.
