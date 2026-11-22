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

from .catalogue import Catalogue, CatalogueAuthError, CatalogueError, async_fetch_catalogue
from .const import CONF_CHANNELS, DOMAIN
from .dashboard import async_ensure_dashboard_listeners, async_setup_dashboard

PLATFORMS = [Platform.COVER, Platform.BUTTON, Platform.SWITCH, Platform.SENSOR]


@dataclass
class InelnetRuntimeData:
    """Runtime data for one controller. Clients include group numbers."""

    host: str
    channels: list[int]
    clients: dict[int, InelnetChannel]
    catalogue: Catalogue | None = None


type InelnetConfigEntry = ConfigEntry[InelnetRuntimeData]


async def async_setup_entry(hass: HomeAssistant, entry: InelnetConfigEntry) -> bool:
    """Set up covers, groups, lights and the dashboard for one controller."""
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
    async_ensure_dashboard_listeners(hass)
    await async_setup_dashboard(hass)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: InelnetConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        await async_setup_dashboard(hass)
    return unloaded


async def _async_sync_areas(hass: HomeAssistant, entry: InelnetConfigEntry) -> None:
    """Create rooms from the controller and assign each device to its room."""
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
    for device in catalogue.devices:
        if device.place is None:
            continue
        ha_device = devices.async_get_device(
            identifiers={(DOMAIN, f"{entry.entry_id}-ch{device.channel}")}
        )
        area_id = area_ids.get(device.place)
        if ha_device is None or area_id is None or ha_device.area_id == area_id:
            continue
        devices.async_update_device(ha_device.id, area_id=area_id)


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
