#!/usr/bin/env python3
"""Read-only-by-default SmartMist BLE protocol probe.

Install dependency with: python3 -m pip install bleak
Run near the device with: python3 smartmist_probe.py scan
Then: python3 smartmist_probe.py query --address DEVICE_ID --command EE0001.

Writes other than known queries require --allow-mutation.
"""

from __future__ import annotations

import argparse
import asyncio
from datetime import datetime
import re

from bleak import BleakClient, BleakScanner

SERVICE_UUID = "0000ffe0-0000-1000-8000-00805f9b34fb"
CHAR_UUID = "0000ffe1-0000-1000-8000-00805f9b34fb"
SAFE_QUERY_PATTERN = re.compile(r"EE000(?:[0-7])?\.")


def decode_response(raw: str) -> None:
    """Print known single-query or full-state records."""
    records = [part for part in raw.removesuffix(".").split(",") if part]
    for record in records:
        ack = re.fullmatch(r"EE1([1-7])([01])(\d{0,2})", record)
        if ack:
            command_id, return_code, echo = ack.groups()
            suffix = f" echo={echo}" if echo else ""
            print(
                f"decoded ack command={command_id} "
                f"success={return_code == '0'}{suffix}"
            )
            continue
        if not record.startswith("EE100") or len(record) < 6:
            print(f"unparsed record={record!r}")
            continue
        sub_id, value = record[5], record[6:]
        if sub_id == "0" and len(value) == 6:
            print(f"decoded runtime={value[0:2]}:{value[2:4]}:{value[4:6]}")
        elif sub_id == "1" and len(value) == 1:
            print(f"decoded power={'ON' if value == '0' else 'OFF' if value == '1' else value}")
        elif sub_id == "2" and len(value) == 1:
            print(f"decoded mode={value}")
        elif sub_id == "3" and len(value) == 7:
            print(f"decoded weekdays={value} (0=enabled)")
        elif sub_id == "4" and len(value) == 1:
            print(f"decoded time_customizable={'enabled' if value == '0' else 'disabled'}")
        elif sub_id == "5" and len(value) == 1:
            print(f"decoded frequency_customizable={'enabled' if value == '0' else 'disabled'}")
        elif sub_id == "6" and len(value) == 11:
            print(
                f"decoded time_slot={value[0:2]} enabled={value[2] == '0'} "
                f"from={value[3:5]}:{value[5:7]} to={value[7:9]}:{value[9:11]}"
            )
        elif sub_id == "7" and len(value) == 13:
            print(
                f"decoded frequency_slot={value[0:2]} enabled={value[2] == '0'} "
                f"work={int(value[3:8])} pause={int(value[8:13])}"
            )
        else:
            print(f"unparsed sub_id={sub_id!r} value={value!r}")


async def scan(timeout: float, show_all: bool = False) -> None:
    devices = await BleakScanner.discover(timeout=timeout, return_adv=True)
    for address, (device, adv) in devices.items():
        uuids = {u.lower() for u in (adv.service_uuids or [])}
        likely = SERVICE_UUID in uuids or "hmsoft" in (device.name or "").lower()
        if show_all or likely:
            marker = "MATCH" if likely else "     "
            print(
                f"{marker}\t{address}\t{device.name or '(unnamed)'}"
                f"\tRSSI={adv.rssi}\tservices={','.join(sorted(uuids)) or '-'}"
            )


async def transact(address: str, command: str, timeout: float, mutate: bool) -> None:
    if not command.startswith("EE") or not command.endswith(".") or not command.isascii():
        raise SystemExit("Command must be ASCII, start with EE, and end with a period")
    if not SAFE_QUERY_PATTERN.fullmatch(command) and not mutate:
        raise SystemExit("Refusing a non-query write without --allow-mutation")

    response = bytearray()
    complete = asyncio.Event()

    def notified(_: int, data: bytearray) -> None:
        response.extend(data)
        stamp = datetime.now().isoformat(timespec="milliseconds")
        print(f"{stamp} notify bytes={bytes(data).hex(' ')} ascii={bytes(data)!r}")
        if b"." in response:
            complete.set()

    async with BleakClient(address) as client:
        # Required ordering for this controller: subscribe, then write.
        await client.start_notify(CHAR_UUID, notified)
        print(f"subscribed {CHAR_UUID}")
        # FFE1 exposes Write Without Response; a response-mode GATT write is
        # rejected with ATT error 0x03 before reaching the controller.
        await client.write_gatt_char(CHAR_UUID, command.encode("ascii"), response=False)
        print(f"wrote-without-response {command!r}")
        try:
            await asyncio.wait_for(complete.wait(), timeout)
        except TimeoutError:
            print("timed out waiting for a period-terminated response")
        finally:
            await client.stop_notify(CHAR_UUID)

    combined = bytes(response)
    print(f"combined bytes={combined.hex(' ')} ascii={combined!r}")
    try:
        decode_response(combined.decode("ascii"))
    except (UnicodeDecodeError, ValueError) as exc:
        print(f"decode error: {exc}")


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="action", required=True)
    scan_parser = sub.add_parser("scan")
    scan_parser.add_argument("--timeout", type=float, default=8.0)
    scan_parser.add_argument("--all", action="store_true", dest="show_all")
    query_parser = sub.add_parser("query")
    query_parser.add_argument("--address", required=True)
    query_parser.add_argument("--command", default="EE0001.")
    query_parser.add_argument("--timeout", type=float, default=5.0)
    query_parser.add_argument("--allow-mutation", action="store_true")
    args = parser.parse_args()

    if args.action == "scan":
        asyncio.run(scan(args.timeout, args.show_all))
    else:
        asyncio.run(
            transact(args.address, args.command, args.timeout, args.allow_mutation)
        )


if __name__ == "__main__":
    main()
