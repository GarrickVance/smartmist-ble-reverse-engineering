# SmartMist BLE reverse engineering

An independently reverse-engineered BLE protocol for a SmartMist SM-150-class
misting controller advertising as `FG31887`. The primary output is a documented,
physically validated ASCII command protocol plus a conservative Bleak probe for
reproducing queries. An ESPHome/Home Assistant example is included only as an
experimental future-integration starting point; it is not the focus of this
initial publication and has not yet completed deployment validation.

This is an independent interoperability project. No affiliation with or
endorsement by the device manufacturer or app publisher is implied.

## Goals

- Document the protocol reproducibly and separate direct evidence from inference.
- Preserve the reverse-engineering methodology and relevant OEM app symbols.
- Enable independent reproduction without redistributing the proprietary app.
- Provide a read-only-by-default diagnostic tool.
- Establish a reliable foundation for later local-control integrations.

## Project status

The reverse-engineering phase is complete for the documented command family on
the tested FG31887. Transport behavior, power/query traffic, full-state parsing,
and no-op setter encodings were physically verified. Compatibility with other
units remains unverified. ESPHome and Home Assistant work is intentionally
secondary and should be treated as experimental until target deployment testing
is completed.

## What is included

| File | Purpose |
|---|---|
| `SMARTMIST_PROTOCOL.md` | Authoritative wire-protocol specification and evidence labels |
| `smartmist_probe.py` | Bleak scanner/query tool; mutations require an explicit flag |
| `smartmist_esphome.yaml` | Example ESP32 BLE client and Home Assistant power switch |
| `DEPLOYMENT.md` | Setup, validation, and troubleshooting runbook |
| `REVERSE_ENGINEERING.md` | Method, recovered app symbols, and verification boundary |
| `LIVE_VERIFICATION.md` | Conservative physical-device test sequence |
| `HANDOFF.md` | Internal continuation record; intentionally not part of the public repository |

## Protocol at a glance

- Service: `0000ffe0-0000-1000-8000-00805f9b34fb`
- Command/notification characteristic: `0000ffe1-0000-1000-8000-00805f9b34fb`
- Subscribe before writing; write using **Write Without Response**.
- ASCII messages end in `.`.

| Action | Request | Expected response |
|---|---|---|
| Query power | `EE0001.` | `EE10010.` ON, `EE10011.` OFF |
| Power on | `EE0100.` | `EE110.` |
| Power off | `EE0101.` | `EE110.` |
| Query full state | `EE000.` | Comma-separated `EE100…` records ending `,.` |

The value polarity is counterintuitive: `0` means ON/enabled and `1` means
OFF/disabled. Setter acknowledgments report success, not resulting state; query
after a setter.

## Quick start: Python probe

Requirements: Python 3.9+ with a working Bluetooth adapter and `bleak`.

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install bleak
python smartmist_probe.py scan
python smartmist_probe.py query --address DEVICE_ID --command EE0001.
python smartmist_probe.py query --address DEVICE_ID --command EE000.
```

On macOS, Bleak may display a CoreBluetooth UUID rather than a conventional MAC
address. Use exactly the identifier returned by `scan`. Close the OEM app and
other BLE clients first.

Non-query commands are deliberately blocked unless `--allow-mutation` is added.
Do not add that flag until you have read the safety procedure.

## ESPHome and Home Assistant behavior

Copy `smartmist_esphome.yaml`, set the device BLE address and normal Wi-Fi/API
configuration, then compile and flash it for the actual ESP32 board. The example:

- auto-connects to the controller;
- allows notification registration before its first query;
- exposes a non-optimistic `SmartMist Power` switch;
- queries actual state after connect and after each setter;
- polls every 30 seconds to reconcile external changes;
- disables restored switch state so startup cannot replay a stale value.

The YAML defaults to `esp32dev` and ESP-IDF as an example, not a statement about
the user's hardware. Review current ESPHome syntax and board selection before
deployment. See `DEPLOYMENT.md` for the acceptance test.

## OEM / white-label context

The recovered application searches for HMSoft-style peripherals, and the tested
controller uses the common FFE0/FFE1 serial-like BLE profile. These are signs of
an OEM or white-label design, but the available evidence does **not** establish a
manufacturer family, cross-brand compatibility, or protocol identity across
lookalike products. Treat compatibility beyond FG31887 as a hypothesis to test.

The supplied product manual tells users to choose `FGXXXXX` in the app, with the
placeholder representing five digits; its screenshot shows the same pattern.
Accordingly, `FG31887` is an ordinary instance of the documented Bluetooth naming
scheme. It is the tested advertisement name, not the model designation.

## Architecture rationale

The bridge is intentionally query-driven and stateless. BLE connections are
temporary and acknowledgments do not contain the new power value. Reading the
controller on connect and after writes prevents Home Assistant from presenting a
remembered state as truth. Periodic reconciliation covers physical controls and
scheduler changes until unsolicited-notification behavior is established.

## Repository layout for publication

```text
smartmist-ble/
├── README.md
├── LICENSE
├── SECURITY.md
├── CONTRIBUTING.md
├── docs/
│   ├── SMARTMIST_PROTOCOL.md
│   ├── REVERSE_ENGINEERING.md
│   ├── DEPLOYMENT.md
│   └── LIVE_VERIFICATION.md
├── examples/
│   └── smartmist_esphome.yaml
└── tools/
    └── smartmist_probe.py
```

The current handoff keeps everything together under `outputs/` for portability.
Move files only when preparing the public repository, and update relative links.

## Scope and support

The implementation is complete for basic power observation/control on the tested
protocol. Schedule editing and broader device-family support are documented but
not exposed as Home Assistant entities. See the protocol document for known
unknowns and evidence strength.
