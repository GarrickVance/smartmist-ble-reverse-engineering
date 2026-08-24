# SmartMist live-verification sequence

This document is a reusable safety runbook. The original FG31887 verification is
complete; do not repeat controlled mutations without a new validation objective.

Prerequisites:

- Mister physically available and initially OFF.
- OEM Misting System app and BLE Scout closed.
- Do not operate the physical controls during capture.

## Stage 1: read-only baseline

1. Scan and identify the SmartMist peripheral.
2. Connect and subscribe to FFE1 notifications.
3. Send `EE0001.` and require the known OFF response `EE10011.`.
4. Disconnect, reconnect, subscribe again, then send the inferred all-state query `EE000.`.
5. Preserve every notification fragment as both raw hexadecimal bytes and ASCII.
6. Send `EE0001.` again and confirm the mister remains OFF.

Stop if any command changes the physical state or if a response does not end in `.`.

## Stage 2: query-map discovery

Only after Stage 1 is understood, test candidate query sub-IDs individually. Start from the sub-IDs present in the all-state response. Do not brute-force non-query command IDs.

For every candidate:

1. Subscribe.
2. Send one query.
3. Record all fragments.
4. Disconnect.
5. Confirm physical state remains OFF with `EE0001.`.

## Stage 3: controlled mutations

Do not begin until a complete baseline and restoration encoding exist. Test one field at a time, query it back, restore it, and query it a second time. Power ON should be tested last and immediately followed by confirmed OFF.

## Completed FG31887 result

- Power query and full-state query succeeded.
- FFE1 required notification subscription before a Write Without Response.
- Commands 2–7 accepted no-op writes containing their existing values.
- An undersized command-6 payload returned failure `EE161.`.
- The final full-state response was byte-identical to the baseline.
- The mister remained physically and logically OFF throughout the completed run.

Preserve future evidence as timestamped raw hex, ASCII, command intent, physical
observation, decoded result, and pre/post full-state snapshots.
