"""Pet Piano switches."""
from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import PetPianoCoordinator

DEVICE_INFO_KEYS = ("identifiers", "name", "manufacturer", "model")


def _device_info(entry):
    return {
        "identifiers": {(DOMAIN, entry.data["address"])},
        "name": "Pet Piano",
        "manufacturer": "Pet Piano",
        "model": "PetPiano BLE",
    }


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: PetPianoCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        PetPianoScheduleSwitch(coordinator, entry),
        PetPianoMealSwitch(coordinator, entry, 1),
        PetPianoMealSwitch(coordinator, entry, 2),
        PetPianoMealSwitch(coordinator, entry, 3),
    ])


class PetPianoScheduleSwitch(CoordinatorEntity[PetPianoCoordinator], SwitchEntity):
    _attr_has_entity_name = True
    _attr_name = "Schedule"
    _attr_icon = "mdi:calendar-clock"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_schedule"
        self._attr_device_info = _device_info(entry)

    @property
    def is_on(self) -> bool | None:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.schedule_enabled

    async def async_turn_on(self, **kwargs) -> None:
        await self.coordinator.async_set_schedule_enabled(True)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        await self.coordinator.async_set_schedule_enabled(False)
        await self.coordinator.async_request_refresh()


class PetPianoMealSwitch(CoordinatorEntity[PetPianoCoordinator], SwitchEntity):
    """Switch to enable/disable an individual meal slot."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:food"

    def __init__(self, coordinator, entry, meal: int):
        super().__init__(coordinator)
        self._meal = meal
        self._attr_name = f"Meal {meal}"
        self._attr_unique_id = f"{entry.entry_id}_meal{meal}_switch"
        self._attr_device_info = _device_info(entry)

    @property
    def is_on(self) -> bool | None:
        if self.coordinator.data is None:
            return None
        return getattr(self.coordinator.data, f"meal{self._meal}_active", False)

    async def async_turn_on(self, **kwargs) -> None:
        await self.coordinator.async_set_meal_active(self._meal, True)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        await self.coordinator.async_set_meal_active(self._meal, False)
        await self.coordinator.async_request_refresh()
