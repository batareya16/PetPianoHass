"""Pet Piano binary sensors."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import PetPianoCoordinator, PetPianoData


@dataclass
class PetPianoBinarySensorDescription(BinarySensorEntityDescription):
    value_fn: Callable[[PetPianoData], bool] = lambda d: False


BINARY_SENSORS: tuple[PetPianoBinarySensorDescription, ...] = (
    PetPianoBinarySensorDescription(
        key="motor_jam",
        name="Motor Jam",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=lambda d: d.motor_jam,
    ),
    PetPianoBinarySensorDescription(
        key="power_source",
        name="Wall Power",
        device_class=BinarySensorDeviceClass.PLUG,
        value_fn=lambda d: d.power_source,
    ),
    PetPianoBinarySensorDescription(
        key="schedule_enabled",
        name="Schedule Active",
        icon="mdi:calendar-clock",
        value_fn=lambda d: d.schedule_enabled,
    ),
    PetPianoBinarySensorDescription(
        key="meal1_active",
        name="Meal 1 Pending",
        icon="mdi:food",
        value_fn=lambda d: d.meal1_active,
    ),
    PetPianoBinarySensorDescription(
        key="meal2_active",
        name="Meal 2 Pending",
        icon="mdi:food",
        value_fn=lambda d: d.meal2_active,
    ),
    PetPianoBinarySensorDescription(
        key="meal3_active",
        name="Meal 3 Pending",
        icon="mdi:food",
        value_fn=lambda d: d.meal3_active,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: PetPianoCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        PetPianoBinarySensor(coordinator, entry, desc) for desc in BINARY_SENSORS
    )


class PetPianoBinarySensor(CoordinatorEntity[PetPianoCoordinator], BinarySensorEntity):
    entity_description: PetPianoBinarySensorDescription
    _attr_has_entity_name = True

    def __init__(self, coordinator, entry, description):
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
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
        return self.entity_description.value_fn(self.coordinator.data)
