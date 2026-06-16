"""Pet Piano sensors."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MODE_MAP
from .coordinator import PetPianoCoordinator, PetPianoData


@dataclass
class PetPianoSensorDescription(SensorEntityDescription):
    value_fn: Callable[[PetPianoData], str | int | float | None] = lambda d: None


SENSORS: tuple[PetPianoSensorDescription, ...] = (
    PetPianoSensorDescription(
        key="battery",
        name="Battery",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.battery,
    ),
    PetPianoSensorDescription(
        key="portions_today",
        name="Portions Today",
        icon="mdi:bowl",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.portions_today,
    ),
    PetPianoSensorDescription(
        key="grams_today",
        name="Grams Today",
        icon="mdi:weight-gram",
        native_unit_of_measurement="g",
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda d: d.grams_today,
    ),
    PetPianoSensorDescription(
        key="mode",
        name="Mode",
        icon="mdi:music",
        value_fn=lambda d: MODE_MAP.get(d.mode, f"Unknown({d.mode})"),
    ),
    PetPianoSensorDescription(
        key="volume",
        name="Volume",
        icon="mdi:volume-high",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.volume,
    ),
    PetPianoSensorDescription(
        key="rtc_time",
        name="Device Time",
        icon="mdi:clock-outline",
        value_fn=lambda d: (
            f"{d.rtc_hour:02d}:{d.rtc_minute:02d} {'PM' if d.rtc_ampm else 'AM'}"
            f" {d.rtc_day:02d}/{d.rtc_month:02d}"
        ),
    ),
    PetPianoSensorDescription(
        key="meal1_time",
        name="Meal 1 Time",
        icon="mdi:clock-time-eight",
        value_fn=lambda d: (
            f"{d.meal1_hour:02d}:{d.meal1_minute:02d} {'PM' if d.meal1_ampm else 'AM'}"
            if d.meal1_active else "Disabled"
        ),
    ),
    PetPianoSensorDescription(
        key="meal2_time",
        name="Meal 2 Time",
        icon="mdi:clock-time-twelve",
        value_fn=lambda d: (
            f"{d.meal2_hour:02d}:{d.meal2_minute:02d} {'PM' if d.meal2_ampm else 'AM'}"
            if d.meal2_active else "Disabled"
        ),
    ),
    PetPianoSensorDescription(
        key="meal3_time",
        name="Meal 3 Time",
        icon="mdi:clock-time-six",
        value_fn=lambda d: (
            f"{d.meal3_hour:02d}:{d.meal3_minute:02d} {'PM' if d.meal3_ampm else 'AM'}"
            if d.meal3_active else "Disabled"
        ),
    ),
    PetPianoSensorDescription(
        key="raw_char1",
        name="Raw CHAR1",
        icon="mdi:bug",
        entity_registry_enabled_default=False,
        value_fn=lambda d: d.raw.get("CHAR1", ""),
    ),
    PetPianoSensorDescription(
        key="raw_char2",
        name="Raw CHAR2 (RTC)",
        icon="mdi:bug",
        entity_registry_enabled_default=False,
        value_fn=lambda d: d.raw.get("CHAR2", ""),
    ),
    PetPianoSensorDescription(
        key="raw_char3",
        name="Raw CHAR3 (Schedule)",
        icon="mdi:bug",
        entity_registry_enabled_default=False,
        value_fn=lambda d: d.raw.get("CHAR3", ""),
    ),
    PetPianoSensorDescription(
        key="raw_char4",
        name="Raw CHAR4",
        icon="mdi:bug",
        entity_registry_enabled_default=False,
        value_fn=lambda d: d.raw.get("CHAR4", ""),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: PetPianoCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(PetPianoSensor(coordinator, entry, desc) for desc in SENSORS)


class PetPianoSensor(CoordinatorEntity[PetPianoCoordinator], SensorEntity):
    entity_description: PetPianoSensorDescription
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
    def native_value(self):
        if self.coordinator.data is None:
            return None
        return self.entity_description.value_fn(self.coordinator.data)
