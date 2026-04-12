# AGENTS.md — HVAC-shark

> Shared conventions (confidence labels, working style, toolchain) are in the
> workspace-level `AGENTS.md` in the parent directory. This file covers
> repo-specific details only.

## Architecture

**Multi-manufacturer, multi-protocol by design.** The capture framing (see
Protocol constants) explicitly encodes manufacturer and bus type, making it
straightforward to add new vendors and bus types over time. Currently the
primary focus is the Midea/Carrier family, but the architecture does not assume
a single vendor or a single protocol per interface.

**Same interface technology, different wire protocols.** The same physical
interface (hardware and signalling layer) may carry entirely different data
protocols depending on device model or firmware generation. For example, IR
interfaces from the same manufacturer family can use different frame encodings
across product lines — but this is not limited to IR. Each such variant must be
treated as a distinct protocol and documented separately, clearly identifying
the device scope it applies to.

## Components

| Component | Path | Description |
|-----------|------|-------------|
| Wireshark Lua dissectors | `tools/dissector/` | Dissects HVAC_shark UDP frames (one per manufacturer family) |
| ESP32 / Python dongle | `tools/dongle/mid-xye/` | Live-capture firmware + Python serial-to-UDP bridge |
| Protocol documentation | `protocols/<manufacturer>/` | Organised by: `spec/`, `devices/`, `comparison/`, `analysis/` |

## Protocol constants

HVAC_shark UDP framing (port 22222):

| Offset | Size | Field          | Values                                      |
|--------|------|----------------|---------------------------------------------|
| 0      | 10   | Magic          | `HVAC_shark` (ASCII)                        |
| 10     | 1    | Manufacturer   | `0x01` = Midea                              |
| 11     | 1    | Bus type       | `0x00`=XYE, `0x01`=UART, `0x02`=disp-mb, `0x03`=r-t, `0x04`=IR |
| 12     | 1    | Header version | `0x00`=legacy, `0x01`=extended              |
| 13+    | var  | Metadata       | len-prefixed: channel name, board, comment  |
| ...    | var  | Protocol data  | bus-specific payload                        |

Bus type `0x04` (IR) payload: 6 decoded bytes per frame (NEC-like encoding,
active-low TSOP receiver). See `SessionNotes.md` in session folders for
known field mappings.
