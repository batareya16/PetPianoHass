"""Config flow for Pet Piano."""
from __future__ import annotations

import voluptuous as vol

from homeassistant.components.bluetooth import (
    BluetoothServiceInfoBleak,
    async_discovered_service_info,
)
from homeassistant.config_entries import ConfigFlow
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN, SERVICE_UUID, DEVICE_NAME


class PetPianoConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle config flow for Pet Piano."""

    VERSION = 1

    def __init__(self) -> None:
        self._discovered: dict[str, str] = {}   # address → name
        self._address: str | None = None

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> FlowResult:
        """Handle BLE device discovered automatically."""
        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()
        self._address = discovery_info.address
        return await self.async_step_confirm()

    async def async_step_confirm(self, user_input=None) -> FlowResult:
        """Ask user to confirm the discovered device."""
        if user_input is not None:
            return self.async_create_entry(
                title=f"Pet Piano ({self._address})",
                data={"address": self._address},
            )
        return self.async_show_form(
            step_id="confirm",
            description_placeholders={"address": self._address},
        )

    async def async_step_user(self, user_input=None) -> FlowResult:
        """Manual setup — show list of discovered PetPiano devices."""
        if user_input is not None:
            address = user_input["address"]
            await self.async_set_unique_id(address)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=f"Pet Piano ({address})",
                data={"address": address},
            )

        # Scan for devices advertising our service UUID
        self._discovered = {
            info.address: info.name or DEVICE_NAME
            for info in async_discovered_service_info(self.hass, connectable=True)
            if SERVICE_UUID in info.service_uuids
            or (info.name and DEVICE_NAME.lower() in info.name.lower())
        }

        if not self._discovered:
            return self.async_abort(reason="no_devices_found")

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required("address"): vol.In(
                        {addr: f"{name} ({addr})" for addr, name in self._discovered.items()}
                    )
                }
            ),
        )
