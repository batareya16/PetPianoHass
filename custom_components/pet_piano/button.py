"""Pet Piano buttons."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import PetPianoCoordinator, pet_piano_device_info

BUTTONS = [
    ButtonEntityDescription(
        key="dispense_now",
        name="Dispense Now",
        icon="mdi:food-drumstick",
    ),
]


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: PetPianoCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(PetPianoButton(coordinator, entry, desc) for desc in BUTTONS)


class PetPianoButton(CoordinatorEntity[PetPianoCoordinator], ButtonEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, entry, description):
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = pet_piano_device_info(entry.data["address"])

    async def async_press(self) -> None:
        await self.coordinator.async_dispense_now()
