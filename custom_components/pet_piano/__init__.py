"""Pet Piano BLE Integration."""
from __future__ import annotations

import logging
import pathlib

from homeassistant.components.bluetooth import async_ble_device_from_address
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import DOMAIN
from .coordinator import PetPianoCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR, Platform.BUTTON, Platform.SWITCH, Platform.NUMBER, Platform.SELECT, Platform.TIME]

CARD_URL = "/pet_piano/pet-piano-card.js"
CARD_DIR = pathlib.Path(__file__).parent / "www"


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Register static path for the Lovelace card — runs once on HA start."""
    if CARD_DIR.exists():
        await hass.http.async_register_static_paths(
            [StaticPathConfig(CARD_URL.rsplit("/", 1)[0], str(CARD_DIR), cache_headers=False)]
        )
        _LOGGER.info("Pet Piano card available at %s", CARD_URL)
    return True


async def _async_options_updated(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Called when user changes integration options — update coordinator live."""
    coordinator: PetPianoCoordinator = hass.data[DOMAIN][entry.entry_id]
    coordinator.grams_per_portion = entry.options.get("grams_per_portion")
    # Recompute grams_today immediately from cached portions count
    if coordinator.data is not None:
        grams = coordinator.grams_per_portion
        coordinator.data.grams_today = (
            round(coordinator.data.portions_today * grams, 1) if grams is not None else None
        )
        coordinator.async_set_updated_data(coordinator.data)
    _LOGGER.info("Options updated: grams_per_portion=%s", coordinator.grams_per_portion)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Pet Piano from a config entry."""
    address: str = entry.data["address"]

    # Check device is reachable
    if not async_ble_device_from_address(hass, address, connectable=True):
        raise ConfigEntryNotReady(f"PetPiano ({address}) not found — make sure it's on and nearby")

    coordinator = PetPianoCoordinator(
        hass, address,
        grams_per_portion=entry.options.get("grams_per_portion"),  # None if not yet configured
    )
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
