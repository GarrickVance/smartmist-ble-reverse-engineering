# SmartMist SM-150 BLE protocol (tested advertisement: FG31887)

> **Status:** Authoritative protocol reference for this project. Last consolidated
> 2026-08-24. Distinguish **device-verified**, **binary-derived**, and **inferred**
> statements as marked below.

Static analysis source: `/Applications/Misting System.app/Wrapper/MistingApp.app/MistingApp`

Binary SHA-256: `6b4ae10b53cf7bc2c08445ecfa146a475f7c9e0cb2702d730bad05ff71d5d8a4`

The product manual instructs users to select a Bluetooth device named
`FGXXXXX`, where the `X` characters represent digits. Its screenshot also shows
an `FG` followed by five digits. `FG31887` is therefore recorded as the tested
unit's BLE advertising name, not as a product model number or secret identifier.

## BLE transport (confirmed on device)

- Service: `0000ffe0-0000-1000-8000-00805f9b34fb`
- Characteristic: `0000ffe1-0000-1000-8000-00805f9b34fb`
- Subscribe to characteristic notifications before writing.
- FFE1 requires GATT **Write Without Response**. A write-with-response attempt is rejected locally with ATT error `0x03` (`Write Not Permitted`).
- Commands and responses are ASCII and terminate with `.`.
- The OEM app searches for HMSoft-style peripherals.

The controller exposes one relevant service/characteristic pair. The same FFE1
characteristic is used for commands and notifications; there is no separate
read characteristic in the recovered implementation.

## Envelope

Requests use:

```text
EE 0 C 0 PAYLOAD .
```

`C` is a one-character command ID. The first `0` is the request phase and the second `0` is the operation/return-code position.

Responses use phase `1`:

```text
EE 1 C R PAYLOAD .
```

`R=0` indicates success. For example, power command ID `1` acknowledges with `EE110.`.

## Command IDs recovered from the OEM binary

| ID | OEM class | Payload |
|---:|---|---|
| 0 | `MistingDevQueryCmd` | Empty for all-state query; a query sub-ID for one field; optional clock synchronization suffix |
| 1 | `MistingDevPowerCmd` | One character: `0` on, `1` off |
| 2 | `MistingDevCustomizationModeCmd` | `0` always-spray/non-stop; `1` nimble/simplified timer; `2` advanced timer |
| 3 | `MistingDevWeekdaySetCmd` | Weekday index followed by `0` enabled / `1` disabled |
| 4 | `MistingDevTimeCustomizableCmd` | One character: `0` enabled / `1` disabled |
| 5 | `MistingDevFreqCustomizableCmd` | One character: `0` enabled / `1` disabled |
| 6 | `MistingDevTimeSetCmd` | 11-character schedule-window record |
| 7 | `MistingDevFreqSetCmd` | 13-character frequency-slot record |

## Confirmed power and query commands

| Operation | Request | Response |
|---|---|---|
| Power on | `EE0100.` | `EE110.` |
| Power off | `EE0101.` | `EE110.` |
| Query power | `EE0001.` | `EE10010.` on; `EE10011.` off |

## Confirmed setter commands and acknowledgements

Each setter was verified on FG31887 by writing its existing value back unchanged.
The full state afterward was identical and power remained OFF.

| Operation tested | Request | Response |
|---|---|---|
| Mode 0 | `EE0200.` | `EE120.` |
| Weekday index 0 enabled | `EE03000.` | `EE1300.` (echoes weekday index) |
| Time customization enabled | `EE0400.` | `EE140.` |
| Frequency customization enabled | `EE0500.` | `EE150.` |
| Time slot 00 enabled, 00:00–23:59 | `EE06000000002359.` | `EE16000.` (echoes slot) |
| Frequency slot 00 enabled, work 10, pause 10 | `EE0700000001000010.` | `EE170.` |

The undersized command-6 record `EE0600.` was rejected with `EE161.`. Return
code `1` means failure; return code `0` means success.

The single-field query response decomposes as `EE 1 00 1 VALUE .`: response phase `1`, query command `00`, sub-ID `1`, then its value.

## Schedule-window record (command 6)

Exactly 11 ASCII characters:

```text
SS E FH FM TH TM
```

- `SS`: zero-padded slot/sequence number
- `E`: `0` enabled, `1` disabled
- `FH`, `FM`: from hour and minute, each two digits
- `TH`, `TM`: to hour and minute, each two digits
- Hours and minutes are clamped by the app to `0...99`, although valid UI time values are narrower.

Example shape: `00008001200` means slot 00, enabled, 08:00 through 12:00.

## Frequency record (command 7)

Exactly 13 ASCII characters:

```text
SS E WWWWW PPPPP
```

- `SS`: zero-padded slot/sequence number
- `E`: `0` enabled, `1` disabled
- `WWWWW`: zero-padded mist/work duration
- `PPPPP`: zero-padded pause duration

The binary defaults an absent frequency slot to enabled flag `1`, work `00003`, pause `00005`.

## Query behavior

- Empty query payload requests the device's complete state: `EE000.`.
- A one-character sub-ID requests one state field. Power is sub-ID `1`: `EE0001.`.
- On the first all-state query per remembered device ID, the OEM app can append:

```text
+YYYYMMDDhhmmssW
```

This synchronizes the controller clock. `W` is the app's weekday value.
- The full-state response is a concatenation of subrecords; the parser validates header, response phase, command ID, subrecord lengths, and final `.`.

Queries are active command writes, not GATT reads. A client must subscribe to
FFE1, write the ASCII query without response, and assemble notification
fragments until the terminating period arrives. Do not assume one notification
equals one logical response.

### Query sub-IDs (confirmed from `EE000.` on FG31887)

| Sub-ID | Value |
|---:|---|
| 0 | Six digits: running hours, minutes, seconds (`HHMMSS`) |
| 1 | Power: `0` on, `1` off |
| 2 | Customization mode: `0`, `1`, or `2` |
| 3 | Seven weekday flags, index order 0 through 6; `0` enabled |
| 4 | Overall time-window customization: `0` enabled, `1` disabled |
| 5 | Overall frequency customization: `0` enabled, `1` disabled |
| 6 | One 11-character time-window record; repeated once per slot |
| 7 | One 13-character frequency record; repeated once per slot |

The verified full-state response is comma-separated and ends with `,.`:

```text
EE1000000006,EE10011,EE10020,EE10030000000,EE10040,EE10050,
EE100600000002359,EE100601100000001,EE100602100000001,
EE100603100000001,EE10070000001000010,.
```

It decoded to runtime `00:00:06`, power off, mode `0`, all weekdays enabled,
time and frequency customization enabled, time slot 00 enabled for 00:00–23:59,
time slots 01–03 disabled, and frequency slot 00 enabled with work 10 / pause 10.

## Device model recovered from the app

- running hours, minutes, seconds
- power state
- customization mode
- seven weekday flags
- overall time-window customization enable
- overall frequency customization enable
- indexed time-window records
- indexed mist/pause frequency records
- maximum supported time and frequency slot counts
- controller date/time and device ID

## Connection and state semantics

- **Device-verified:** notification subscription must precede the command write.
- **Device-verified:** reconnecting and repeating the subscription/query sequence
  returns current controller state.
- **Implementation policy:** clients should be stateless. Do not restore a cached
  power value after reconnect; query `EE0001.` and publish the returned value.
- **Implementation policy:** after a power setter acknowledgment, query power
  again. `EE110.` confirms command acceptance but does not itself encode ON/OFF.
- **Unknown:** whether the controller emits unsolicited state changes caused by
  its physical controls or scheduler. Periodic polling is therefore retained in
  the ESPHome example.

## Evidence classification

| Claim | Evidence | Status |
|---|---|---|
| FFE0/FFE1 UUIDs, notify-before-write, write-without-response | Live FG31887 BLE session | Confirmed |
| Power/query bytes and responses | Live FG31887 session | Confirmed |
| Full-state response and subrecord decoding | OEM parser plus live FG31887 response | Confirmed for captured state |
| Commands 2–7 and record shapes | OEM binary plus no-op writes and unchanged state | Confirmed encoding/acceptance |
| Clock suffix and first-query behavior | OEM binary control flow | Binary-derived; not live-tested |
| UI bounds, defaults, model fields | OEM binary/model behavior | Binary-derived |
| Compatibility with other branded units | Shared HMSoft/OEM indicators only | Inferred; unverified |

## Known unknowns and limitations

- Only one physical controller, advertising as `FG31887`, was tested. The manual
  supports the general `FG` plus five digits naming pattern, but not protocol
  compatibility among every device using that pattern.
- No claim is made that every SmartMist, SM-150, HMSoft, or visually identical
  white-label device uses this protocol or the same polarity.
- Power ON was not required for the final no-op verification run; the recorded
  safe state remained OFF. Operational ON/OFF testing should be supervised.
- Setter failure codes other than the observed `1` are unknown.
- Maximum slot counts, accepted numeric ranges at firmware level, clock weekday
  convention, unsolicited-notification behavior, authentication, and behavior
  under malformed or rapid commands remain unverified.
- Fragmentation across notifications is possible. The Python probe accumulates
  fragments; the compact ESPHome example compares each callback string and may
  need a small receive buffer if a particular ESPHome/firmware combination
  fragments these short power responses.

## Safety and operational guidance

- Keep the mister OFF and physically observed during discovery or deployment.
- Use read-only queries first. The supplied probe rejects mutations unless
  `--allow-mutation` is explicit.
- Never brute-force setter command IDs or payloads on an unattended unit.
- Before schedule/frequency experiments, capture a full baseline and prepare the
  exact restoration commands.
- Water, pumps, electrical equipment, and unintended spraying can create damage
  or injury risks. Use appropriate isolation and a reachable physical cutoff.

## Confidence and live verification

UUIDs, transport behavior, power, single/full queries, all command IDs, and all setter record shapes were confirmed directly. Setters 2 through 7 were exercised as no-op writes using existing values, followed by a byte-identical full-state query. The mister remained physically and logically OFF throughout verification.

“Confirmed” is scoped to the tested FG31887. See `LIVE_VERIFICATION.md` for the
safe test sequence and `HANDOFF.md` for the continuation boundary.
