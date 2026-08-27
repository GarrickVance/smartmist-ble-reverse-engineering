# SmartMist BLE reverse engineering

An independently reverse-engineered BLE protocol for a SmartMist SM-150-class
misting controller advertising as `FG31887`. The primary output is a documented,
physically validated ASCII command protocol plus a conservative Bleak probe for
reproducing queries. A native Home Assistant integration (`custom_components/smartmist`)
implements the validated power/query commands and has completed a live deployment
test: connect through an ESPHome Bluetooth Proxy, subscribe, write, and confirm
resulting state by query, in both directions. An ESPHome/Home Assistant `ble_client`
example is also included as a secondary, experimental starting point for anyone who
would rather not run a custom component.

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
units remains unverified.

The native Home Assistant integration has completed one live deployment test on
the tested FG31887: power on, power off, and full-state query, each round-tripped
through an ESPHome Bluetooth Proxy rather than a directly attached adapter. Long-run
reliability (extended polling, proxy reconnect churn, multiple BLE devices sharing
one proxy) has not been exercised. Timer/frequency/weekday **write** support is not
implemented; those fields are decoded read-only. The `ble_client`-based ESPHome
example remains secondary and experimental, and has not itself completed the
acceptance test in `DEPLOYMENT.md`.

## What is included

| File | Purpose |
|---|---|
| `SMARTMIST_PROTOCOL.md` | Authoritative wire-protocol specification and evidence labels |
| `smartmist_probe.py` | Bleak scanner/query tool; mutations require an explicit flag |
| `custom_components/smartmist/` | Native Home Assistant integration (recommended) |
| `smartmist_esphome.yaml` | Secondary/experimental ESP32 BLE client example |
| `DEPLOYMENT.md` | Setup, validation, and troubleshooting runbook |
| `REVERSE_ENGINEERING.md` | Method, recovered app symbols, and verification boundary |
| `LIVE_VERIFICATION.md` | Conservative physical-device test sequence |

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

## Native Home Assistant integration (recommended)

`custom_components/smartmist` is a standard Home Assistant custom integration.
It does not require dedicating an ESP32 to this one device: it uses Home
Assistant's core `bluetooth` integration, which transparently routes the BLE
connection through any adapter or registered ESPHome Bluetooth Proxy that has
the controller in range. One proxy can be shared across this and other,
unrelated BLE devices.

Install:

1. Copy `custom_components/smartmist/` into your Home Assistant `config/custom_components/` directory.
2. Restart Home Assistant Core (custom integrations are only imported at startup).
3. The controller is discovered automatically by local-name prefix (`FG3*`) or
   by its `0000ffe0-0000-1000-8000-00805f9b34fb` service UUID; accept the
   discovery card under Settings → Devices & Services, or add it manually from
   there if discovery doesn't fire.

Behavior:

- Connects, subscribes to `FFE1`, and sends the full-state query `EE000.` on a
  fixed poll interval (60 s) — connect-per-poll, not a held-open connection, so
  a shared proxy's limited connection slots stay available for other devices.
- Exposes `switch.<device>_power`: strictly non-optimistic, exactly as
  `smartmist_esphome.yaml` intends — the entity state is only ever set from a
  parsed query response, never assumed from the write.
- Exposes `sensor.<device>_runtime` and `sensor.<device>_mode` (both read-only,
  diagnostic); `weekdays`, `time_customizable`, and `frequency_customizable` are
  surfaced as attributes on the mode sensor. Time-slot and frequency-slot
  records are decoded internally but not yet exposed as entities.
- Does not implement any setter beyond power on/off. Schedule/timer editing is
  intentionally out of scope until those command payloads are reverse-engineered
  and validated the same way power/query were.

See `DEPLOYMENT.md` for the acceptance test this integration was run against.

## ESPHome and Home Assistant behavior (secondary, experimental)

This path dedicates a single ESP32 to this one device rather than sharing a
Bluetooth Proxy; prefer the native integration above unless there's a specific
reason to run a standalone bridge. Copy `smartmist_esphome.yaml`, set the device
BLE address and normal Wi-Fi/API configuration, then compile and flash it for
the actual ESP32 board. The example:

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

### Likely original manufacturer

The strongest available evidence points to **Taizhou Fog Machine Co., Ltd.**
(also branded **FG Machine**) in Zhejiang, China, as the likely original equipment
manufacturer or platform supplier. The company was formerly known as **Linhai
Dex Machinery Co., Ltd.**

The evidence chain is:

1. The analyzed OEM app has bundle identifier `com.spw.MistingApp` and version
   `1.20.07`.
2. Archived store metadata for that exact bundle/version lists Linhai Dex
   Machinery as publisher and says the app was developed by Taizhou Fog Machine
   to control the FG-100, FG-150, FG-200, and FG-300.
3. [Taizhou Fog Machine's official product catalog](https://www.tzfog.com/)
   lists those same four FG models as its commercial 70-bar misting-system family,
   including an FG-150 rated at 1.5 L/min and 70 bar/1000 PSI.
4. The company's [official history](https://www.tzfog.com/about-us) identifies
   Linhai Dex Machinery as its former name.
5. Older FG-family manuals explicitly thank customers for purchasing a fog
   machine from Taizhou Fog Machine and show the same model family and app flow.

This attribution is substantially stronger than enclosure resemblance alone,
but it remains an evidence-based identification rather than documented proof of
the supply-chain relationship for this particular Smart Mist-branded FG31887.
Smart Mist USA should therefore be described as the tested retail brand/vendor,
and Taizhou Fog Machine as the **likely OEM**.

## Product names and likely related models

This controller appears under multiple product, reseller, and application names.
The following terms are included to help owners find this research:

- **Smart Mist / SmartMist USA:** `SM-100`, `SM-150`, `SM-200`, and `SM-300`
  app-controlled high-pressure misting pumps and systems.
- **Bluetooth identity:** names matching `FG#####` (the manuals render this as
  `FGXXXXX`).
- **Application/generic names:** `Misting System`, `Misting Machine`, `Fog
  Machine`, app-controlled misting pump, fogging pump, fog-cooling system, and
  high-pressure misting system.
- **JOSTechnik:** `Nebelanlage FG-100/150` / `Fog Cooling FG-100/150`. Its
  published instructions independently describe selecting an `FGXXXXX` device
  through the misting/fog-machine app and reproduce the same connection rules.
- **HEATSail:** `BEEM with Misting` and the misting system supplied with `LEAF`.
  Their manuals show the same distinctive `POWER`, `MODE SELECT`, `NONSTOP
  SPRAYING`, `APP MODE`, `OIL LAMP RESET`, `CHANGE OIL`, and `WATER LACK`
  controls. This establishes a close hardware/UI resemblance, not protocol proof.

Sources: the [Smart Mist product family](https://www.smartmistusa.com/collections/app-controlled-pumps-and-others),
the [Smart Mist SM-100/150/200/300 manual](https://manuals.plus/m/8bd1263eb672d69f191b78cb11feeab3d851e6ef32419b4124f14ff644e80f95),
the [JOSTechnik FG-100/150 instructions](https://jost-technik.de/Nebelanlage_FG-100-150-_-51.html),
and the [HEATSail product site](https://www.heatsail.com/).

### Expected compatibility, not yet confirmed

The shared Smart Mist manual presents SM-100, SM-150, SM-200, and SM-300 as one
product family and gives them a common touch-panel and app-operation procedure.
That is meaningful evidence that multiple models use the same controller-board
or firmware family, so this BLE protocol is **likely** to apply to other models
that advertise as `FG#####` and use the same panel/app. It is not proof that every
model, production revision, or white-label unit has identical firmware.

Only the FG31887 unit associated with the SM-150-class system has been physically
verified. For any candidate device, begin with service discovery and the safe
power query `EE0001.`. Require FFE0/FFE1 and a recognized response before trying
the full-state query. Do not send setter commands merely because the enclosure,
panel, model number, or app looks identical.

## Architecture rationale

The bridge is intentionally query-driven and stateless. BLE connections are
temporary and acknowledgments do not contain the new power value. Reading the
controller on connect and after writes prevents Home Assistant from presenting a
remembered state as truth. Periodic reconciliation covers physical controls and
scheduler changes until unsolicited-notification behavior is established.

## Repository contents

```text
smartmist-ble-reverse-engineering/
├── README.md
├── SMARTMIST_PROTOCOL.md
├── REVERSE_ENGINEERING.md
├── LIVE_VERIFICATION.md
├── DEPLOYMENT.md
├── smartmist_probe.py
├── smartmist_esphome.yaml
└── custom_components/
    └── smartmist/
        ├── manifest.json
        ├── __init__.py
        ├── const.py
        ├── smartmist_ble.py
        ├── coordinator.py
        ├── config_flow.py
        ├── switch.py
        ├── sensor.py
        ├── strings.json
        └── translations/en.json
```

The documentation remains flat in the initial release so the protocol evidence
and reproduction tool are immediately visible. The ESPHome YAML is retained as
a secondary, experimental example; `custom_components/smartmist/` is the
deployment-validated path.

## Scope and support

The implementation is complete for basic power observation/control on the tested
protocol, and the native Home Assistant integration has completed one live
on/off/query round trip through an ESPHome Bluetooth Proxy on the tested FG31887.
Schedule editing and broader device-family support are documented but not
exposed as Home Assistant entities. See the protocol document for known
unknowns and evidence strength.
