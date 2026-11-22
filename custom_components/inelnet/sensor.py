"""Read-only schedule list. The controller runs the schedules itself."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import InelnetConfigEntry
from .catalogue import Catalogue, weekday_names


async def async_setup_entry(
    hass: HomeAssistant,
    entry: InelnetConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Expose schedules when the controller has at least one."""
    catalogue = entry.runtime_data.catalogue
    if catalogue is None or not catalogue.programs:
        return
    async_add_entities([InelnetScheduleSensor(entry.entry_id, catalogue)])


class InelnetScheduleSensor(SensorEntity):
    """How many schedules are enabled, with the full list as attributes."""

    _attr_has_entity_name = False
    _attr_translation_key = "schedules"
    _attr_icon = "mdi:calendar-clock"
    _attr_should_poll = False

    def __init__(self, entry_id: str, catalogue: Catalogue) -> None:
        """Initialize the sensor."""
        self._attr_unique_id = f"{entry_id}-schedules"
        self._catalogue = catalogue

    @property
    def native_value(self) -> int:
        """Number of enabled schedules."""
        return sum(1 for program in self._catalogue.programs if program.enabled)

    @property
    def extra_state_attributes(self) -> dict[str, list[dict[str, object]]]:
        """Every schedule, including disabled ones."""
        return {
            "programs": [
                {
                    "channel": program.channel,
                    "name": self._catalogue.channel_name(program.channel),
                    "time": f"{program.hour:02d}:{program.minute:02d}",
                    "days": weekday_names(program.days),
                    "action": program.action,
                    "enabled": program.enabled,
                    "astro": program.astro,
                }
                for program in self._catalogue.programs
            ]
        }
