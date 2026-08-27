"""SmartMist SM-150 BLE transport and protocol handling.

Protocol reverse-engineered from the OEM app and validated live with the
Bleak-based probe. Reference: https://github.com/GarrickVance/smartmist-ble-reverse-engineering

Frame grammar:
    Request:  EE 0 <cmdId> 0 <payload> .
    Response: EE 1 <cmdId> <returnCode> <payload> .

The controller accepts only one active BLE central connection, requires
notifications to be subscribed before any write is honored, and only
supports "write without response" on the control characteristic. State is
not cached across reconnects by design - every consumer must re-query.
"""

from __future__ import annotations

import asyncio
import logging
import re

from bleak.backends.device import BLEDevice
from bleak_retry_connector import BleakClientWithServiceCache, establish_connection

from .const import (
    CHARACTERISTIC_UUID,
    CMD_POWER_OFF,
    CMD_POWER_ON,
    CMD_QUERY_FULL_STATE,
    CONNECT_TIMEOUT_SECONDS,
    RESPONSE_TIMEOUT_SECONDS,
)

_LOGGER = logging.getLogger(__name__)

_ACK_RE = re.compile(r"EE1([1-7])([01])(\d{0,2})")


class SmartMistError(Exception):
    """Raised when a SmartMist BLE transaction fails."""


def _decode_record(record: str) -> tuple[str, object] | None:
    """Decode a single comma-separated response record into (field, value)."""
    ack = _ACK_RE.fullmatch(record)
    if ack:
        command_id, return_code, _echo = ack.groups()
        return (f"ack_{command_id}", return_code == "0")

    if not record.startswith("EE100") or len(record) < 6:
        return None

    sub_id, value = record[5], record[6:]
    if sub_id == "0" and len(value) == 6:
        return ("runtime", f"{value[0:2]}:{value[2:4]}:{value[4:6]}")
    if sub_id == "1" and len(value) == 1:
        return ("power_on", value == "0")
    if sub_id == "2" and len(value) == 1:
        return ("mode", int(value))
    if sub_id == "3" and len(value) == 7:
        return ("weekdays", value)
    if sub_id == "4" and len(value) == 1:
        return ("time_customizable", value == "0")
    if sub_id == "5" and len(value) == 1:
        return ("frequency_customizable", value == "0")
    if sub_id == "6" and len(value) == 11:
        return (
            f"time_slot_{value[0:2]}",
            {
                "enabled": value[2] == "0",
                "from": f"{value[3:5]}:{value[5:7]}",
                "to": f"{value[7:9]}:{value[9:11]}",
            },
        )
    if sub_id == "7" and len(value) == 13:
        return (
            f"frequency_slot_{value[0:2]}",
            {
                "enabled": value[2] == "0",
                "work_seconds": int(value[3:8]),
                "pause_seconds": int(value[8:13]),
            },
        )
    return None


def decode_state(raw: str) -> dict:
    """Decode a (possibly multi-record) SmartMist response into a dict."""
    state: dict = {}
    for record in raw.removesuffix(".").split(","):
        if not record:
            continue
        decoded = _decode_record(record)
        if decoded is None:
            _LOGGER.debug("Unparsed SmartMist record: %r", record)
            continue
        key, value = decoded
        state[key] = value
    return state


class SmartMistDevice:
    """Handles a single connect/transact/disconnect cycle with a SmartMist unit."""

    def __init__(self, ble_device: BLEDevice) -> None:
        self._ble_device = ble_device

    def update_ble_device(self, ble_device: BLEDevice) -> None:
        self._ble_device = ble_device

    async def _transact(self, command: bytes) -> str:
        """Connect, subscribe, write one command, and return the combined response."""
        response = bytearray()
        complete = asyncio.Event()

        def _notified(_handle: int, data: bytearray) -> None:
            response.extend(data)
            if b"." in data:
                complete.set()

        client: BleakClientWithServiceCache = await establish_connection(
            BleakClientWithServiceCache,
            self._ble_device,
            self._ble_device.name or self._ble_device.address,
            timeout=CONNECT_TIMEOUT_SECONDS,
        )
        try:
            await client.start_notify(CHARACTERISTIC_UUID, _notified)
            # Matches the tested sequence: subscribe, brief settle, then write.
            await asyncio.sleep(0.3)
            await client.write_gatt_char(CHARACTERISTIC_UUID, command, response=False)
            try:
                await asyncio.wait_for(complete.wait(), RESPONSE_TIMEOUT_SECONDS)
            except asyncio.TimeoutError as err:
                raise SmartMistError(
                    f"Timed out waiting for a response to {command!r}"
                ) from err
            try:
                await client.stop_notify(CHARACTERISTIC_UUID)
            except Exception:  # noqa: BLE001 - best-effort cleanup only
                pass
        finally:
            await client.disconnect()

        try:
            return bytes(response).decode("ascii")
        except UnicodeDecodeError as err:
            raise SmartMistError(f"Non-ASCII response: {bytes(response)!r}") from err

    async def query_state(self) -> dict:
        """Query full device state (power, runtime, mode, schedule)."""
        raw = await self._transact(CMD_QUERY_FULL_STATE)
        return decode_state(raw)

    async def power_on(self) -> None:
        await self._transact(CMD_POWER_ON)

    async def power_off(self) -> None:
        await self._transact(CMD_POWER_OFF)
