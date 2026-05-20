"""Pet Piano time entities — set meal schedule times."""
from __future__ import annotations

import logging
from datetime import time

from homeassistant.components.time import TimeEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, QUARTER_HOUR_REVERSE
from .coordinator import PetPianoCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: PetPianoCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        PetPianoMealTime(coordinator, entry, 1),
        PetPianoMealTime(coordinator, entry, 2),
        PetPianoMealTime(coordinator, entry, 3),
    ])


class PetPianoMealTime(CoordinatorEntity[PetPianoCoordinator], TimeEntity):
    """Meal schedule time — 12-hour format, minutes rounded to :00/:15/:30/:45."""

    _attr_has_entity_name = True

    def __init__(self, coordinator, entry, meal: int) -> None:
        super().__init__(coordinator)
        self._meal = meal
        self._attr_name = f"Meal {meal} Time"
        self._attr_icon = "mdi:clock-time-eight-outline"
        self._attr_unique_id = f"{entry.entry_id}_meal{meal}_time"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.data["address"])},
            "name": "Pet Piano",
            "manufacturer": "Pet Piano",
            "model": "PetPiano BLE",
        }

    @property
    def native_value(self) -> time | None:
        d = self.coordinator.data
        if d is None:
            return None
        hour12  = getattr(d, f"meal{self._meal}_hour",   8)
        minute  = getattr(d, f"meal{self._meal}_minute",  0)
        ampm    = getattr(d, f"meal{self._meal}_ampm",    0)
        # Convert 12-hour → 24-hour for HA
        hour24 = self._to_24h(hour12, ampm)
        try:
            return time(hour=hour24, minute=minute)
        except ValueError:
            return None

    async def async_set_value(self, value: time) -> None:
        """User picked a time — convert to 12h and write to CHAR3."""
        hour12, ampm = self._to_12h(value.hour)
        # Round minutes to nearest quarter
        minute = QUARTER_HOUR_REVERSE.get(
            min(QUARTER_HOUR_REVERSE, key=lambda k: abs(k - value.minute)), 0
        )
        _LOGGER.info("Set meal %d time to %02d:%02d %s", self._meal, hour12, minute, "PM" if ampm else "AM")
        await self.coordinator.async_set_meal_time(self._meal, hour12, minute, ampm)
        await self.coordinator.async_request_refresh()

    # ── helpers ────────────────────────────────────────────────────────────

    @staticmethod
    def _to_24h(hour12: int, ampm: int) -> int:
        if ampm == 0:  # AM
            return 0 if hour12 == 12 else hour12
        else:           # PM
            return 12 if hour12 == 12 else hour12 + 12

    @staticmethod
    def _to_12h(hour24: int) -> tuple[int, int]:
        if hour24 == 0:
            return 12, 0   # 12 AM
        elif hour24 < 12:
            return hour24, 0
        elif hour24 == 12:
            return 12, 1   # 12 PM
        else:
            return hour24 - 12, 1
