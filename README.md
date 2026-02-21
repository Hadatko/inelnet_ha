# inelnet_ha

Home Assistant integration for controlling INELNET blinds via REST API. Each controller channel is a separate device (cover) with open/close/stop; additional actions (short move, programming mode) are available as Device Actions in automations and scenes.

## Installation

1. Copy the `custom_components/inelnet` folder into your Home Assistant `<config>/custom_components/inelnet` (or clone the repo and symlink).
2. Restart Home Assistant.
3. **Settings → Devices & services → Add integration** → search for "INELNET Blinds".
4. Enter the controller **IP address** (e.g. `192.168.1.67`) and **channels** comma-separated (e.g. `1` or `1,2,3`). Channels are numbers 1–16.
5. After saving, one device with a cover entity is created per channel.

## Usage

- **Cover** – standard open/close/stop (UI buttons or services `cover.open_cover`, `cover.close_cover`, `cover.stop_cover`).
- **Device Actions** – in **Automation / Scene** when choosing a device action you also have:
  - **Short move up** (`up_short`)
  - **Short move down** (`down_short`)
  - **Programming mode** (`program`) – for pairing a remote control

## Technical details

The integration sends POST requests to `http://<host>/msg.htm` with body `send_ch=<channel>&send_act=<code>`. Codes: 144 stop, 160 up, 176 up_short, 192 down, 208 down_short, 224 program.

---

If anybody is interested in supporting my "sleepless" nights (working mostly between 23:00-3:00) on different projects press:

[![Buy me a coffee](https://img.shields.io/badge/Buy%20me%20a%20coffee-%F0%9F%8D%BA-yellow?style=for-the-badge&logo=buy-me-a-coffee)](https://www.buymeacoffee.com/hadatko)

Thank you ;)

Ideas are welcome. But PRs are welcome more ;)
