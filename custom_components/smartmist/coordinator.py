"""Data update coordinator for SmartMist."""

from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.components import bluetooth
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, UPDATE_INTERVAL_SECONDS
from .smartmist_ble import SmartMistDevice, SmartMistError

_LOGGER = logging.getLogger(__name__)


class SmartMistCoordinator(DataUpdateCoordinator[dict]):
    """Polls a SmartMist unit for its current state via BLE."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, address: str) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}-{address}",
            update_interval=timedelta(seconds=UPDATE_INTERVAL_SECONDS),
        )
        self.address = address
        self._device: SmartMistDevice | None = None

    def _get_device(self) -> SmartMistDevice:
        ble_device = bluetooth.async_ble_device_from_address(
            self.hass, self.address, connectable=True
        )
        if ble_device is None:
            raise SmartMistError(
                f"SmartMist device {self.address} not visible to any Bluetooth "
                "adapter or proxy right now"
            )
        if self._device is None:
            self._device = SmartMistDevice(ble_device)
        else:
            self._device.update_ble_device(ble_device)
        return self._device

    async def _async_update_data(self) -> dict:
        try:
            return await self._get_device().query_state()
        except SmartMistError as err:
            raise UpdateFailed(str(err)) from err

    async def async_power_on(self) -> None:
        try:
            await self._get_device().power_on()
        except SmartMistError as err:
            raise HomeAssistantError(str(err)) from err
        await self.async_request_refresh()

    async def async_power_off(self) -> None:
        try:
            await self._get_device().power_off()
        except SmartMistError as err:
            raise HomeAssistantError(str(err)) from err
        await self.async_request_refresh()
