"""Pet Piano number entities."""
from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberEntityDescription, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import PetPianoCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: PetPianoCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        PetPianoVolumeNumber(coordinator, entry),
        PetPianoTutorLevelNumber(coordinator, entry),
    ])


class PetPianoVolumeNumber(CoordinatorEntity[PetPianoCoordinator], NumberEntity):
    _attr_has_entity_name = True
    _attr_name = "Volume"
    _attr_icon = "mdi:volume-high"
    _attr_native_min_value = 0
    _attr_native_max_value = 7
    _attr_native_step = 1
    _attr_mode = NumberMode.SLIDER

    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_volume"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.data["address"])},
            "name": "Pet Piano",
            "manufacturer": "Pet Piano",
            "model": "PetPiano BLE",
        }

    @property
    def native_value(self) -> float | None:
        if self.coordinator.data is None:
            return None
        return float(self.coordinator.data.volume)

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.async_set_volume(int(value))
        await self.coordinator.async_request_refresh()


class PetPianoTutorLevelNumber(CoordinatorEntity[PetPianoCoordinator], NumberEntity):
    """Tutor difficulty level — controls how many keys/sequence the cat must play."""

    _attr_has_entity_name = True
    _attr_name = "Tutor Level"
    _attr_icon = "mdi:paw"
    _attr_native_min_value = 0
    _attr_native_max_value = 7
    _attr_native_step = 1
    _attr_mode = NumberMode.SLIDER

    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_tutor_level"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.data["address"])},
            "name": "Pet Piano",
            "manufacturer": "Pet Piano",
            "model": "PetPiano BLE",
        }

    @property
    def native_value(self) -> float | None:
        if self.coordinator.data is None:
            return None
        return float(self.coordinator.data.tutor_level)  # bits 24-26 of CHAR1

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.async_set_tutor_level(int(value))
        await self.coordinator.async_request_refresh()
