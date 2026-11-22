"""Sidebar dashboard with one control per shutter.

The controller never reports position, so each shutter is a tile with open, stop
and close. Shutters are grouped by room when a room is assigned. Short moves and
programming stay off this dashboard; those buttons are for pairing and are
disabled until the user enables them.
"""

from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN

LOGGER = logging.getLogger(__name__)

DASHBOARD_PATH = "inelnet-blinds"
DASHBOARD_VERSION = 1
_COPY = {
    "en": {
        "view": "Shutters",
        "empty": "No shutters yet. Add channels in the INELNET integration.",
        "unassigned": "No room",
    },
    "sk": {
        "view": "Rolety",
        "empty": "Zatiaľ žiadne rolety. Kanály pridáš v integrácii INELNET.",
        "unassigned": "Bez miestnosti",
    },
    "cs": {
        "view": "Rolety",
        "empty": "Zatím žádné rolety. Kanály přidáš v integraci INELNET.",
        "unassigned": "Bez místnosti",
    },
}


def _copy(language: str) -> dict[str, str]:
    """Dashboard strings for the Home Assistant language, otherwise English."""
    return _COPY.get(language.split("-")[0], _COPY["en"])


def build_dashboard(shutters: list[dict[str, str | None]], language: str) -> dict:
    """Build the Lovelace config. One tile per shutter, rooms as headings."""
    copy = _copy(language)
    if not shutters:
        return {
            "views": [
                {
                    "title": copy["view"],
                    "path": "shutters",
                    "icon": "mdi:window-shutter",
                    "cards": [{"type": "markdown", "content": copy["empty"]}],
                }
            ]
        }

    groups: dict[str | None, list[dict[str, str | None]]] = {}
    for shutter in shutters:
        groups.setdefault(shutter["area"], []).append(shutter)
    named = sorted((area for area in groups if area), key=str.casefold)
    order: list[str | None] = named + ([None] if None in groups else [])
    show_headings = len(order) > 1 or (len(order) == 1 and order[0] is not None)

    cards: list[dict] = []
    for area in order:
        if show_headings:
            cards.append(
                {
                    "type": "heading",
                    "heading": area or copy["unassigned"],
                    "heading_style": "title",
                    "icon": "mdi:window-shutter",
                    "grid_options": {"columns": 12},
                }
            )
        for shutter in groups[area]:
            cards.append(
                {
                    "type": "tile",
                    "entity": shutter["entity_id"],
                    "name": shutter["name"],
                    "features": [{"type": "cover-open-close"}],
                    "grid_options": {"columns": 6, "rows": 2},
                }
            )

    return {
        "views": [
            {
                "title": copy["view"],
                "path": "shutters",
                "icon": "mdi:window-shutter",
                "type": "sections",
                "max_columns": 4,
                "sections": [{"type": "grid", "column_span": 4, "cards": cards}],
            }
        ]
    }


def _shutters(hass: HomeAssistant) -> list[dict[str, str | None]]:
    """Enabled INELNET covers, with the device name and room."""
    entities = er.async_get(hass)
    devices = dr.async_get(hass)
    areas = ar.async_get(hass)
    found: list[dict[str, str | None]] = []
    for entry in entities.entities.values():
        if entry.domain != "cover" or entry.platform != DOMAIN or entry.disabled_by:
            continue
        device = devices.async_get(entry.device_id) if entry.device_id else None
        area_id = entry.area_id or (device.area_id if device else None)
        area_name = None
        if area_id:
            area = areas.async_get_area(area_id)
            area_name = area.name if area else None
        if entry.name:
            name = entry.name
        elif device is not None:
            name = device.name_by_user or device.name or entry.entity_id
        else:
            name = entry.original_name or entry.entity_id
        found.append({"entity_id": entry.entity_id, "name": name, "area": area_name})
    return sorted(found, key=lambda item: ((item["area"] or ""), item["name"] or ""))


async def async_setup_dashboard(hass: HomeAssistant) -> None:
    """Create or update the shutter dashboard from the current covers."""
    shutters = _shutters(hass)
    language = hass.config.language or "en"
    signature = (
        DASHBOARD_VERSION,
        language,
        tuple(
            (item["entity_id"], item["name"], item["area"])
            for item in shutters
        ),
    )
    store = hass.data.setdefault(DOMAIN, {})
    if store.get("dashboard_signature") == signature:
        return
    if await _save_dashboard(hass, build_dashboard(shutters, language)):
        store["dashboard_signature"] = signature


def async_ensure_dashboard_listeners(hass: HomeAssistant) -> None:
    """Refresh the dashboard when a room or entity name changes."""
    store = hass.data.setdefault(DOMAIN, {})
    if store.get("dashboard_listeners"):
        return

    async def _refresh(_event) -> None:
        await async_setup_dashboard(hass)

    store["dashboard_listeners"] = [
        hass.bus.async_listen(dr.EVENT_DEVICE_REGISTRY_UPDATED, _refresh),
        hass.bus.async_listen(er.EVENT_ENTITY_REGISTRY_UPDATED, _refresh),
    ]


async def _save_dashboard(hass: HomeAssistant, config: dict) -> bool:
    """Write the dashboard. Returns False when Lovelace is not ready yet."""
    collection = _live_dashboard_collection(hass)
    if collection is None:
        LOGGER.debug("Lovelace dashboard collection is not available yet")
        return False
    from homeassistant.components.lovelace.const import (
        CONF_ICON,
        CONF_TITLE,
        CONF_URL_PATH,
        LOVELACE_DATA,
    )

    existing = next(
        (
            item
            for item in collection.async_items()
            if item.get(CONF_URL_PATH) == DASHBOARD_PATH
        ),
        None,
    )
    if existing is None:
        await collection.async_create_item(
            {
                CONF_ICON: "mdi:window-shutter",
                CONF_TITLE: "INELNET",
                CONF_URL_PATH: DASHBOARD_PATH,
            }
        )
    dashboard = hass.data[LOVELACE_DATA].dashboards.get(DASHBOARD_PATH)
    if dashboard is None:
        return False
    await dashboard.async_save(config)
    return True


def _live_dashboard_collection(hass: HomeAssistant):
    """The Lovelace collection that is already listening for new dashboards."""
    handlers = hass.data.get("websocket_api") or {}
    registered = handlers.get("lovelace/dashboards/create")
    if not registered:
        return None
    handler = registered[0]
    wrapped = getattr(handler, "__wrapped__", None)
    method = getattr(wrapped, "__wrapped__", None)
    owner = getattr(method, "__self__", None)
    return getattr(owner, "storage_collection", None)
