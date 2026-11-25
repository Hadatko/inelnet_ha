"""INELNET Blinds integration."""

from __future__ import annotations

from dataclasses import dataclass

from inelnet_api import InelnetChannel

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity_registry import RegistryEntryDisabler
from homeassistant.helpers.storage import Store

from .catalogue import Catalogue, CatalogueAuthError, CatalogueError, async_fetch_catalogue
from .const import CONF_CHANNELS, DOMAIN

PLATFORMS = [Platform.COVER, Platform.BUTTON, Platform.SWITCH, Platform.SENSOR]
_AREA_STORE_VERSION = 1
_AREA_STORE_KEY = f"{DOMAIN}_area_sync"


@dataclass
class InelnetRuntimeData:
    """Runtime data for one controller. Clients include group numbers."""

    host: str
    channels: list[int]
    clients: dict[int, InelnetChannel]
    catalogue: Catalogue | None = None


type InelnetConfigEntry = ConfigEntry[InelnetRuntimeData]


async def async_setup_entry(hass: HomeAssistant, entry: InelnetConfigEntry) -> bool:
    """Set up covers, groups and lights for one controller."""
    host = entry.data[CONF_HOST]
    stored_channels = list(entry.data[CONF_CHANNELS])
    session = async_get_clientsession(hass)
    probe = InelnetChannel(host, stored_channels[0] if stored_channels else 1)
    try:
        if not await probe.ping(session=session):
            raise ConfigEntryNotReady(
                f"Controller at {host} did not respond or returned error"
            ) from None
    except ConfigEntryNotReady:
        raise
    except Exception as err:
        raise ConfigEntryNotReady(f"Cannot connect to controller at {host}") from err

    catalogue: Catalogue | None = None
    username = entry.data.get(CONF_USERNAME) or ""
    password = entry.data.get(CONF_PASSWORD) or ""
    if username and password:
        try:
            catalogue = await async_fetch_catalogue(session, host, username, password)
        except CatalogueAuthError as err:
            raise ConfigEntryAuthFailed("INELNET web login was rejected") from err
        except CatalogueError as err:
            raise ConfigEntryNotReady(
                f"Cannot read the INELNET catalogue at {host}"
            ) from err

    if catalogue is not None and catalogue.devices:
        channels = [device.channel for device in catalogue.devices]
    else:
        channels = stored_channels
    group_channels = [group.number for group in catalogue.groups] if catalogue else []
    clients = {
        channel: InelnetChannel(host, channel) for channel in [*channels, *group_channels]
    }
    entry.runtime_data = InelnetRuntimeData(
        host=host,
        channels=channels,
        clients=clients,
        catalogue=catalogue,
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await _async_sync_areas(hass, entry)
    _async_enable_pairing(hass, entry)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: InelnetConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


def area_sync_action(
    previous: int | None,
    place: int,
    current_area_id: str | None,
    target_area_id: str,
) -> tuple[str | None, bool]:
    """Return the area to assign, and whether this controller room should be stored.

    The first time a channel is seen, only an empty area is filled. After that
    the device moves only when the controller's room changed. A room chosen in
    Home Assistant stays while the controller room stays the same.
    """
    if previous is None:
        assigned = target_area_id if current_area_id is None else None
        return assigned, True
    if previous == place:
        return None, False
    assigned = target_area_id if current_area_id != target_area_id else None
    return assigned, True


async def _async_sync_areas(hass: HomeAssistant, entry: InelnetConfigEntry) -> None:
    """Create rooms from the controller and assign a device only when allowed."""
    catalogue = entry.runtime_data.catalogue
    if catalogue is None:
        return
    areas = ar.async_get(hass)
    devices = dr.async_get(hass)
    area_ids: dict[int, str] = {}
    for place in catalogue.places:
        area = areas.async_get_area_by_name(place.name)
        if area is None:
            area = areas.async_create(place.name)
        area_ids[place.number] = area.id

    store = Store(hass, _AREA_STORE_VERSION, _AREA_STORE_KEY)
    stored = await store.async_load() or {}
    remembered = {
        str(channel): int(place)
        for channel, place in (stored.get(entry.entry_id) or {}).items()
    }
    changed = False
    for device in catalogue.devices:
        if device.place is None:
            continue
        target_area_id = area_ids.get(device.place)
        if target_area_id is None:
            continue
        ha_device = devices.async_get_device(
            identifiers={(DOMAIN, f"{entry.entry_id}-ch{device.channel}")}
        )
        if ha_device is None:
            continue
        key = str(device.channel)
        assigned, remember = area_sync_action(
            remembered.get(key),
            device.place,
            ha_device.area_id,
            target_area_id,
        )
        if assigned is not None:
            devices.async_update_device(ha_device.id, area_id=assigned)
        if remember:
            remembered[key] = device.place
            changed = True
    if changed:
        stored[entry.entry_id] = remembered
        await store.async_save(stored)


def _async_enable_pairing(hass: HomeAssistant, entry: InelnetConfigEntry) -> None:
    """Turn on pairing buttons that the integration itself had disabled."""
    registry = er.async_get(hass)
    for entity in list(registry.entities.values()):
        if entity.config_entry_id != entry.entry_id:
            continue
        if not entity.unique_id or not str(entity.unique_id).endswith("-program"):
            continue
        if entity.disabled_by is RegistryEntryDisabler.INTEGRATION:
            registry.async_update_entity(entity.entity_id, disabled_by=None)
