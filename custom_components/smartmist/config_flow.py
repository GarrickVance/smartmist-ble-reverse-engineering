"""Config flow for SmartMist."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.components.bluetooth import (
    BluetoothServiceInfoBleak,
    async_discovered_service_info,
)
from homeassistant.config_entries import ConfigFlow
from homeassistant.const import CONF_ADDRESS

from .const import DOMAIN


class SmartMistConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for SmartMist."""

    VERSION = 1

    def __init__(self) -> None:
        self._discovered_address: str | None = None
        self._discovered_name: str | None = None

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> Any:
        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()

        self._discovered_address = discovery_info.address
        self._discovered_name = discovery_info.name or discovery_info.address
        self.context["title_placeholders"] = {"name": self._discovered_name}
        return await self.async_step_confirm()

    async def async_step_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> Any:
        assert self._discovered_address is not None
        if user_input is not None:
            return self.async_create_entry(
                title=self._discovered_name or self._discovered_address,
                data={CONF_ADDRESS: self._discovered_address},
            )

        self._set_confirm_only()
        return self.async_show_form(
            step_id="confirm",
            description_placeholders={"name": self._discovered_name},
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> Any:
        if user_input is not None:
            address = user_input[CONF_ADDRESS]
            await self.async_set_unique_id(address, raise_on_progress=False)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title=f"SmartMist ({address})", data={CONF_ADDRESS: address})

        current_addresses = self._async_current_ids()
        candidates = {
            info.address: f"{info.name or 'SmartMist'} ({info.address})"
            for info in async_discovered_service_info(self.hass, connectable=True)
            if info.address not in current_addresses
            and (info.name or "").upper().startswith("FG")
        }

        if not candidates:
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema({vol.Required(CONF_ADDRESS): str}),
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_ADDRESS): vol.In(candidates)}),
        )
