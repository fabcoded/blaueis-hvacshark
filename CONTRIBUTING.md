# Contributing to blaueis-hvacshark

Contributions are welcome. This project is CC0 — by submitting a change you agree that your contribution is dedicated to the public domain under the same terms.

## Before you start

- For anything non-trivial, **open an issue first**. Adding a new protocol, manufacturer, or device family is non-trivial by definition.
- Read [`AGENTS.md`](AGENTS.md) — it describes the confidence-label conventions, per-protocol folder structure, and the "source-documented only" rule for capability universes.

## Citation rule — the one that matters

Protocol knowledge in this repo is documented as **our own observation of the wire format**, expressed in our own words. When editing, **never**:

- Reference file paths, function names, or line numbers from external implementations in spec files, analysis docs, dissector comments, or code.
- Copy content from external source code — comments, variable names, logic blocks.

A single README-level acknowledgment line naming community projects (see [README.md#acknowledgements](README.md#acknowledgements)) is the only named attribution in this repo. All protocol claims must trace to captures we have in [blaueis-hvacshark-traces](https://github.com/fabcoded/blaueis-hvacshark-traces) or to our own wire observations.

## Where things live

- `protocols/<manufacturer>/spec/` — normative protocol specifications. One file per protocol layer (UART, XYE, IR, mainboard, R/T).
- `protocols/<manufacturer>/devices/` — device-specific quirks and field inventories.
- `protocols/<manufacturer>/analysis/` — analysis deep-dives that inform the specs.
- `tools/dissector/` — Wireshark Lua dissectors.
- `tools/dongle/` — ESP32 + Python live-capture bridge.

## Adding a new protocol or device

1. File an issue describing the manufacturer, bus/protocol, and what captures you have.
2. Add captures to [blaueis-hvacshark-traces](https://github.com/fabcoded/blaueis-hvacshark-traces) first (or reference existing ones).
3. Draft a spec file — start with `Hypothesis` / `Unknown` confidence; don't mark anything `Confirmed` without round-trip evidence.
4. Dissector support can follow the spec; it doesn't have to land together.

## Confidence labels

```
confirmed > consistent > hypothesis > disputed > unknown
```

Use them rigorously. Downgrading a claim from `confirmed` when contrary evidence appears is always correct behaviour — not a regression.

## License and attribution

By contributing, you dedicate your contribution to the public domain under [CC0 1.0 Universal](LICENSE). If you have attribution or licensing concerns, please open an issue — we will respond promptly.
