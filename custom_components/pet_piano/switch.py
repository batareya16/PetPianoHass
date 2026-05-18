"""Pet Piano switches."""
from __future__ import annotations

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
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
    async_add_entities([PetPianoScheduleSwitch(coordinator, entry)])


class PetPianoScheduleSwitch(CoordinatorEntity[PetPianoCoordinator], SwitchEntity):
    _attr_has_entity_name = True
    _attr_name = "Schedule"
    _attr_icon = "mdi:calendar-clock"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_schedule"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.data["address"])},
            "name": "Pet Piano",
            "manufacturer": "Pet Piano",
            "model": "PetPiano BLE",
        }

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
