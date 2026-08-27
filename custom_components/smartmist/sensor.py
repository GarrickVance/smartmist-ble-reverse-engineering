"""SmartMist diagnostic sensors."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import SmartMistCoordinator

# Fields folded into query_state() that aren't schedule-editing related and are
# safe to surface as read-only context on the mode sensor. Time/frequency slot
# and weekday *editing* is intentionally not implemented (unproven writes).
_EXTRA_ATTR_KEYS = (
    "weekdays",
    "time_customizable",
    "frequency_customizable",
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: SmartMistCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            SmartMistRuntimeSensor(coordinator, entry),
            SmartMistModeSensor(coordinator, entry),
        ]
    )


class _SmartMistSensorBase(CoordinatorEntity[SmartMistCoordinator], SensorEntity):
    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: SmartMistCoordinator, entry: ConfigEntry, key: str, name: str) -> None:
        super().__init__(coordinator)
        address = entry.data[CONF_ADDRESS]
        self._key = key
        self._attr_name = name
        self._attr_unique_id = f"{address}-{key}"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, address)})

    @property
    def native_value(self):
        return self.coordinator.data.get(self._key)


class SmartMistRuntimeSensor(_SmartMistSensorBase):
    """Cumulative runtime reported by the controller, as HH:MM:SS."""

    def __init__(self, coordinator: SmartMistCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "runtime", "Runtime")


class SmartMistModeSensor(_SmartMistSensorBase):
    """Current customization mode index."""

    def __init__(self, coordinator: SmartMistCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "mode", "Mode")

    @property
    def extra_state_attributes(self) -> dict:
        return {
            key: self.coordinator.data[key]
            for key in _EXTRA_ATTR_KEYS
            if key in self.coordinator.data
        }
