# INELNET Blinds

Home Assistant integration for an INELNET blinds controller on the local network. Each channel is one shutter. The controller accepts commands and does not report position, so every shutter shows open, stop and close.

Names, rooms and groups are whatever that controller has stored. Nothing is fixed to one home. With the web login, Home Assistant creates a room for each place on the controller. A device that has no room yet is placed there. A room you set yourself stays until that place changes on the controller.

## Version 1.4.0

The integration no longer creates or rewrites a sidebar dashboard. A dashboard that already exists, including one you edited, is left as it is. Add the covers to any dashboard yourself. Devices are no longer moved back to the controller's room on every restart.

If anybody is interested in supporting my "sleepless" nights (working mostly between 23:00-3:00) on different projects press:

[![Buy me a coffee](https://img.shields.io/badge/Buy%20me%20a%20coffee-%F0%9F%8D%BA-yellow?style=for-the-badge&logo=buy-me-a-coffee)](https://www.buymeacoffee.com/hadatko)

Thank you ;)

Ideas are welcome. But PRs are welcome more ;)

## What you get

- One cover per channel: open, stop, close. With the controller web login, the name and room come from the controller. Lights and sockets become switches. Venetian blinds also get tilt.
- One cover per group stored on the controller. The group number is the channel the controller already uses for that group.
- Rooms from the controller. A device is placed in that room only when it has none yet, and it is moved again only when the room changes on the controller.
- Pairing is enabled. Short move up and short move down stay disabled until you enable those buttons. The same three actions are available as device actions.
- Schedules are read from the controller when any exist. The controller still runs them. This integration does not create or delete schedules.

## Installation

Home Assistant 2025.1 or newer.

### HACS

1. In HACS, open **Integrations**.
2. If INELNET Blinds is not in the list yet, open the three-dot menu, choose **Custom repositories**, and add `https://github.com/Hadatko/inelnet_ha` with category **Integration**.
3. Download **INELNET Blinds** and restart Home Assistant.

### Manual

Copy `custom_components/inelnet` into the Home Assistant `config/custom_components/inelnet` directory and restart.

## Setup

1. **Settings → Devices & services → Add integration** and search for **INELNET Blinds**.
2. Enter the controller address. Add the web username and password from the controller page to read names, rooms and groups. Leave the login empty and enter channel numbers separated by commas (`1` or `1,2,3`) if you do not want to store that password. A channel is any positive integer.

   ![Channel definition when adding the integration](img/channelDef.jpg)

3. With a login, rooms are created from the controller. A device that has no room is assigned to the controller's room. If you move a device in Home Assistant, that choice stays until the room changes on the controller. Add the covers to a dashboard yourself. Pairing is a button on each device.

   ![Assigning a channel to a room](img/channelRoom.png)

4. To change the login or the channel list later, open the integration, then **Configure**. You do not add the controller a second time. Leave the password empty to keep the one already saved.

The controller is contacted during setup. With a web login, names, rooms, groups and schedules are read then. After that Home Assistant only sends a command when you press a button. Position is never read, so the state stays unknown and both directions stay available. Reload the integration after you rename something on the controller.

## For developers

Commands are HTTP POST requests to `http://<host>/msg.htm` with body `send_ch=<channel>&send_act=<code>`.

| Action | Code |
| --- | --- |
| Stop | 144 |
| Up | 160 |
| Short up | 176 |
| Down | 192 |
| Short down | 208 |
| Program | 224 |

The client is the [inelnet-api](https://pypi.org/project/inelnet-api/) package. Source is in `inelnet_api/`. One channel is one `InelnetChannel(host, channel)`.

### Publish the library

1. Copy `.env.pypi.example` to `.env.pypi` and set the PyPI token. The username stays `__token__`. `.env.pypi` is gitignored.
2. Run `./scripts/upload_pypi.sh` (`build` and `twine` are required).

Before a new upload, bump `version` in `pyproject.toml` and `inelnet_api/__init__.py`. A tag such as `v1.0.1` also publishes through [GitHub Actions](.github/workflows/publish-pypi.yml) when the `PYPI_API_TOKEN` secret is set.

### Tests

```bash
pip install -e . && pip install -r requirements_test.txt
pytest tests/ tests_inelnet_api/ -v
```

The integration tests use `pytest-homeassistant-custom-component`.
