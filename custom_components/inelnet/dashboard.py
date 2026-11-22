"""Sidebar dashboard with one control per shutter.

The controller never reports position, so each shutter is a tile with open, stop
and close. Rooms are separate sections. Groups from the controller sit above
them. Pairing is a second view, away from the daily buttons.
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
DASHBOARD_VERSION = 2
_COPY = {
    "en": {
        "view": "Shutters",
        "empty": "No shutters yet. Add channels in the INELNET integration.",
        "unassigned": "No room",
        "groups": "Groups",
        "pairing": "Pairing",
        "pairing_hint": (
            "Pairing puts that channel into programming mode. "
            "Then press the button on the remote you want to add."
        ),
    },
    "sk": {
        "view": "Rolety",
        "empty": "Zatiaľ žiadne rolety. Kanály pridáš v integrácii INELNET.",
        "unassigned": "Bez miestnosti",
        "groups": "Skupiny",
        "pairing": "Párovanie",
        "pairing_hint": (
            "Párovanie prepne kanál do programovacieho režimu. "
            "Potom stlač tlačidlo na ovládači, ktorý chceš pridať."
        ),
    },
    "cs": {
        "view": "Rolety",
        "empty": "Zatím žádné rolety. Kanály přidáš v integraci INELNET.",
        "unassigned": "Bez místnosti",
        "groups": "Skupiny",
        "pairing": "Párování",
        "pairing_hint": (
            "Párování přepne kanál do programovacího režimu. "
            "Potom stiskni tlačítko na ovladači, který chceš přidat."
        ),
    },
}


def _copy(language: str) -> dict[str, str]:
    """Dashboard strings for the Home Assistant language, otherwise English."""
    return _COPY.get(language.split("-")[0], _COPY["en"])


def build_dashboard(shutters: list[dict[str, str | None]], language: str) -> dict:
    """Build the Lovelace config. Rooms are sections, groups sit above them."""
    copy = _copy(language)
    controls = [item for item in shutters if item.get("kind", "shutter") != "pair"]
    pairing = [item for item in shutters if item.get("kind") == "pair"]
    if not controls and not pairing:
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

    group_items = [item for item in controls if item.get("kind") == "group"]
    room_items = [item for item in controls if item.get("kind") != "group"]
    sections: list[dict] = []
    if group_items:
        sections.append(
            _section(
                [_heading(copy["groups"], "mdi:blinds-horizontal")]
                + [_control_card(item, 6) for item in group_items],
                4,
            )
        )
    by_room: dict[str | None, list[dict[str, str | None]]] = {}
    for item in room_items:
        by_room.setdefault(item["area"], []).append(item)
    named = sorted((area for area in by_room if area), key=str.casefold)
    order: list[str | None] = named + ([None] if None in by_room else [])
    show_headings = len(order) > 1 or (len(order) == 1 and order[0] is not None)
    room_span = 2 if len(order) > 1 else 4
    tile_columns = 12 if room_span == 2 else 6
    for area in order:
        cards: list[dict] = []
        if show_headings:
            cards.append(_heading(area or copy["unassigned"], "mdi:window-shutter"))
        cards.extend(_control_card(item, tile_columns) for item in by_room[area])
        sections.append(_section(cards, room_span))

    views = [
        {
            "title": copy["view"],
            "path": "shutters",
            "icon": "mdi:window-shutter",
            "type": "sections",
            "max_columns": 4,
            "sections": sections,
        }
    ]
    if pairing:
        views.append(_pairing_view(pairing, copy))
    return {"views": views}


def _heading(text: str, icon: str) -> dict:
    """Section heading card."""
    return {
        "type": "heading",
        "heading": text,
        "heading_style": "title",
        "icon": icon,
        "grid_options": {"columns": 12},
    }


def _section(cards: list[dict], column_span: int) -> dict:
    """One sections-view column."""
    return {"type": "grid", "column_span": column_span, "cards": cards}


def _control_card(item: dict[str, str | None], columns: int) -> dict:
    """A large open/stop/close tile, or a light tile."""
    domain = item.get("domain") or "cover"
    card: dict = {
        "type": "tile",
        "entity": item["entity_id"],
        "name": item["name"],
        "vertical": True,
        "grid_options": {"columns": columns, "rows": 3 if domain == "cover" else 2},
    }
    if domain == "cover":
        icon = "mdi:blinds-horizontal" if item.get("kind") == "group" else "mdi:window-shutter"
        card["icon"] = icon
        card["features"] = [{"type": "cover-open-close"}]
        card["features_position"] = "bottom"
    else:
        card["icon"] = "mdi:lightbulb"
    return card


def _pairing_view(buttons: list[dict[str, str | None]], copy: dict[str, str]) -> dict:
    """A separate view so pairing is not next to the daily open and close buttons."""
    by_room: dict[str | None, list[dict[str, str | None]]] = {}
    for button in buttons:
        by_room.setdefault(button["area"], []).append(button)
    named = sorted((area for area in by_room if area), key=str.casefold)
    order: list[str | None] = named + ([None] if None in by_room else [])
    show_headings = len(order) > 1 or (len(order) == 1 and order[0] is not None)
    sections = [
        _section(
            [
                {
                    "type": "markdown",
                    "content": copy["pairing_hint"],
                    "grid_options": {"columns": 12},
                }
            ],
            4,
        )
    ]
    for area in order:
        cards: list[dict] = []
        if show_headings:
            cards.append(_heading(area or copy["unassigned"], "mdi:remote"))
        for button in by_room[area]:
            cards.append(
                {
                    "type": "button",
                    "entity": button["entity_id"],
                    "name": button["name"],
                    "icon": "mdi:remote",
                    "show_state": False,
                    "grid_options": {"columns": 4, "rows": 2},
                }
            )
        sections.append(_section(cards, 4))
    return {
        "title": copy["pairing"],
        "path": "pairing",
        "icon": "mdi:remote",
        "type": "sections",
        "max_columns": 4,
        "sections": sections,
    }


def _kind(domain: str, unique_id: str | None) -> str | None:
    """Dashboard role for one entity. None means it stays off the dashboard."""
    token = (unique_id or "").rsplit("-", 1)[-1]
    if domain == "button" and token == "program":
        return "pair"
    if domain == "cover" and token.startswith("gr"):
        return "group"
    if domain in {"cover", "switch"}:
        return "shutter"
    return None


def _shutters(hass: HomeAssistant) -> list[dict[str, str | None]]:
    """Enabled covers, lights and pairing buttons, with the device name and room."""
    entities = er.async_get(hass)
    devices = dr.async_get(hass)
    areas = ar.async_get(hass)
    found: list[dict[str, str | None]] = []
    for entry in entities.entities.values():
        if entry.platform != DOMAIN or entry.disabled_by:
            continue
        kind = _kind(entry.domain, entry.unique_id)
        if kind is None:
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
        found.append(
            {
                "entity_id": entry.entity_id,
                "name": name,
                "area": area_name,
                "kind": kind,
                "domain": entry.domain,
            }
        )
    return sorted(
        found,
        key=lambda item: ((item["area"] or ""), item["kind"] or "", item["name"] or ""),
    )


async def async_setup_dashboard(hass: HomeAssistant) -> None:
    """Create or update the shutter dashboard from the current covers."""
    shutters = _shutters(hass)
    language = hass.config.language or "en"
    signature = (
        DASHBOARD_VERSION,
        language,
        tuple(
            (item["entity_id"], item["name"], item["area"], item.get("kind"))
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
