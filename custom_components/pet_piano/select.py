"""Pet Piano select entities."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MODE_MAP
from .coordinator import PetPianoCoordinator, pet_piano_device_info

MODE_OPTIONS = ["Normal", "Tutor", "Concert"]


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: PetPianoCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([PetPianoModeSelect(coordinator, entry)])


class PetPianoModeSelect(CoordinatorEntity[PetPianoCoordinator], SelectEntity):
    _attr_has_entity_name = True
    _attr_name = "Mode"
    _attr_icon = "mdi:music"
    _attr_options = MODE_OPTIONS

    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_mode_select"
        self._attr_device_info = pet_piano_device_info(entry.data["address"])

    @property
    def current_option(self) -> str | None:
        if self.coordinator.data is None:
            return None
        return MODE_MAP.get(self.coordinator.data.mode, "Normal")

    async def async_select_option(self, option: str) -> None:
        mode_reverse = {"Normal": 0, "Tutor": 1, "Concert": 2}
        await self.coordinator.async_set_mode(mode_reverse.get(option, 0))
