"""SmartMist power switch."""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import SmartMistCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: SmartMistCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([SmartMistPowerSwitch(coordinator, entry)])


class SmartMistPowerSwitch(CoordinatorEntity[SmartMistCoordinator], SwitchEntity):
    """Non-optimistic power switch: state only ever reflects a real query response."""

    _attr_has_entity_name = True
    _attr_name = "Power"
    # No assumed_state / no optimistic writes - matches the validated protocol,
    # which is stateless across reconnects and must be re-queried after writes.

    def __init__(self, coordinator: SmartMistCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        address = entry.data[CONF_ADDRESS]
        self._attr_unique_id = f"{address}-power"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, address)},
            name=entry.title,
            manufacturer="SmartMist",
            model="SM-150",
        )

    @property
    def is_on(self) -> bool | None:
        return self.coordinator.data.get("power_on")

    async def async_turn_on(self, **kwargs) -> None:
        await self.coordinator.async_power_on()

    async def async_turn_off(self, **kwargs) -> None:
        await self.coordinator.async_power_off()
