# Deployment and validation

## Before starting

Keep the mister visible, initially OFF, and within reach of its physical cutoff.
Close the OEM application and BLE inspection tools; many peripherals accept only
one active client. Do not operate physical controls during a baseline capture.

## Validate with the Bleak probe

1. Create a virtual environment and install `bleak`.
2. Run `python smartmist_probe.py scan --timeout 10` near the controller.
3. Record the identifier shown for the likely FFE0/HMSoft device.
4. Run `python smartmist_probe.py query --address DEVICE_ID`.
5. Require `EE10011.` before proceeding if the intended safe state is OFF.
6. Run the full-state query with `--command EE000.` and retain the raw output as
   a baseline.
7. Disconnect/reconnect by running the power query again. Confirm state recovery.

The probe subscribes before writing, writes without response, timestamps each
notification fragment, combines fragments through `.`, and decodes known fields.
Its safe allowlist accepts `EE000.`, plus query sub-IDs 0 through 7. Any other
write requires `--allow-mutation`.

## Configure ESPHome

1. Copy `smartmist_esphome.yaml` into the ESPHome configuration directory.
2. Replace `XX:XX:XX:XX:XX:XX` with the BLE address appropriate to the ESPHome
   platform. A macOS CoreBluetooth UUID is not necessarily usable as an ESP32 MAC.
3. Change `esp32.board` to the actual board and add normal `wifi`, `api`, and
   credential/secrets configuration.
4. Validate and compile with the ESPHome version used by the deployment.
5. Flash the ESP32 and position it within reliable BLE range.
6. Watch logs for connection, `subscribed` behavior from the component, outgoing
   queries, and `RX: EE10011.` (or the actual current state).

## Home Assistant acceptance test

1. Add/adopt the ESPHome node and confirm `SmartMist Power` appears.
2. With the mister OFF, restart the bridge. The entity must become OFF from a
   query; it must not briefly command or restore ON.
3. Supervised test only: turn the entity ON, observe the physical unit, then turn
   it OFF immediately. Each action should be followed by a state query.
4. Change state using a physical control, if safe, and verify reconciliation by
   the next 30-second poll. Restore OFF.
5. Power-cycle the mister, then the bridge. Verify reconnect and correct queried
   state after each cycle.
6. Restart Home Assistant and verify no stale state is written to the controller.

## Expected entity semantics

- The template switch is non-optimistic: UI state is published only from a
  recognized query response.
- `restore_mode: DISABLED` prevents replaying a remembered power state.
- `EE110.` is accepted silently as a setter acknowledgment; the follow-up query
  determines truth.
- Unknown responses are logged and do not change the entity.

## Troubleshooting

| Symptom | Likely cause / action |
|---|---|
| Device absent from scan | Move closer, confirm power, increase scan timeout, close competing BLE apps |
| Connect fails repeatedly | Forget/disconnect other clients; power-cycle the controller; check address type |
| Write fails with ATT `0x03` | The client used Write With Response; FFE1 requires Write Without Response |
| Write succeeds but no reply | Ensure notifications were enabled first; allow registration delay; inspect fragments |
| macOS identifier fails on ESP32 | Re-scan from ESP32; CoreBluetooth UUIDs differ from BLE MAC addresses |
| HA switch stays unavailable/unchanged | Inspect ESPHome logs, UUID/address, BLE range, and exact ASCII response |
| Responses appear split | Add a receive buffer that accumulates until `.`; do not parse callbacks independently |
| Frequent disconnects | Reduce radio interference, shorten distance, avoid multiple central clients |
| State changes unexpectedly | Disable schedules in the OEM UI only after recording them; inspect full state |

Do not “fix” a timeout by repeatedly sending setters. Return to `EE0001.` and
`EE000.` read-only queries, capture logs, and compare with the protocol reference.
