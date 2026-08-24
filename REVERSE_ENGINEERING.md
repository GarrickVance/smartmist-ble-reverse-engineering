# Reverse-engineering notes

## Inputs and provenance

Static analysis used the arm64 Mach-O executable at:

```text
/Applications/Misting System.app/Wrapper/MistingApp.app/MistingApp
```

Recorded SHA-256:

```text
6b4ae10b53cf7bc2c08445ecfa146a475f7c9e0cb2702d730bad05ff71d5d8a4
```

The physical validation target advertised as `FG31887`. The product manual's app
instructions use `FGXXXXX`, and its screenshot shows `FG` followed by five digits.
This supports treating `FG31887` as an instance of the documented advertising-name
pattern rather than a model number. Publication should still avoid personal BLE
addresses, host paths in executable examples, and binary/app redistribution.

## Method

1. Locate BLE discovery, notification, and write paths in the OEM binary.
2. Recover command-building classes, fixed ASCII envelope, field widths, enum
   polarity, and query parser behavior.
3. Build a read-only-by-default Bleak client that logs raw bytes and ASCII.
4. Validate service and characteristic UUIDs, notification ordering, write type,
   single power query, and full-state query against the physical controller.
5. Decode the live full-state record using the recovered parser structure.
6. Exercise commands 2–7 only as no-op writes of their existing values.
7. Re-query full state and require a byte-identical result with power still OFF.

This sequence avoids treating decompiled intent as device behavior and minimizes
physical side effects.

## Relevant recovered app symbols

Command classes:

- `MistingDevQueryCmd`
- `MistingDevPowerCmd`
- `MistingDevCustomizationModeCmd`
- `MistingDevWeekdaySetCmd`
- `MistingDevTimeCustomizableCmd`
- `MistingDevFreqCustomizableCmd`
- `MistingDevTimeSetCmd`
- `MistingDevFreqSetCmd`

Relevant BLE selectors/strings retained in the binary include:

- `findHMSoftPeripherals:`
- `write:data:`
- `writeValue:characteristicUUID:p:data:`
- `writeValue:forCharacteristic:type:`
- `notify:on:`
- `Try to open notifyn`

These names are useful anchors for reproducing the analysis. Stable virtual
addresses are intentionally not asserted here: no address map was retained in
the handoff, and offsets can differ by binary build or loader. Use the recorded
hash to establish whether an address from a future disassembly refers to the same
binary.

## Static versus physical evidence

Static analysis supplied the command family, payload layouts, clock suffix,
defaults, UI constraints, and parser model. Physical tests established the BLE
transport, exact power/query traffic, full captured state, error response for an
undersized command-6 payload, and acceptance of no-op setter encodings.

No-op acceptance proves that the tested firmware recognizes those encodings. It
does not prove every possible value, boundary, schedule effect, or other product
variant. The precise classification is maintained in `SMARTMIST_PROTOCOL.md`.

## Reproduction guidance

- Hash the local executable before comparing symbols or disassembly.
- Capture notification fragments as hex and ASCII with timestamps.
- Preserve the pre-test full state and the post-test full state.
- Test queries before setters; test a single field at a time.
- Do not brute-force write commands.
- Report device label, firmware information if independently discoverable, host
  OS, BLE library/version, and whether another client was connected.
- Redact unique Bluetooth addresses from public logs unless explicitly useful and
  consented to.
