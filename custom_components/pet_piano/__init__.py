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
    """Called when user changes integration options — update coordinator live.

    We schedule an immediate refresh rather than mutating coordinator.data
    in-place (which would race the 60-second poller reading the same object).
    The BLE poll is fast (~1 s) so the new grams value will appear shortly.
    """
    coordinator: PetPianoCoordinator = hass.data[DOMAIN][entry.entry_id]
    coordinator.grams_per_portion = entry.options.get("grams_per_portion")
    _LOGGER.info("Options updated: grams_per_portion=%s", coordinator.grams_per_portion)
    await coordinator.async_request_refresh()


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
    coordinator: PetPianoCoordinator = hass.data[DOMAIN][entry.entry_id]
    coordinator.cancel_pending_writes()
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
