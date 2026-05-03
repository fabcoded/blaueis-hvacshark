# Midea XYE Protocol — Byte-Level Reference

> **Source Status — Community and Open-Source Only**
> Based on open-source repositories, community forum discussions, and own hardware
> captures. No official Midea specification is publicly available. Uncertainties are
> flagged explicitly. A discrepancy is only considered resolved after independent
> hardware verification.
>
> For shared protocol elements across Midea buses, see [protocol_shared.md](protocol_shared.md).

---

## 1. Introduction

### 1.1 Purpose and Scope

This document defines the **XYE protocol** — the application-level command set used
by Midea wired controllers and indoor units on the XYE RS-485 bus and its HAHB
transport variant.

The XYE protocol uses **fixed-length frames** (16-byte commands, 32-byte responses)
with a simple request-response polling model. A controller (wired room controller or
automation device) queries and commands one or more indoor units on a shared bus.

| Transport | Physical Path | Framing |
|-----------|--------------|---------|
| **XYE (RS-485 direct)** | Controller ↔ indoor unit via MFB-C adapter | Native XYE frames |
| **HAHB (adapter board)** | Controller ↔ indoor unit via MFB-X adapter on HA/HB bus | XYE frames wrapped in nibble-pair encoding (§3) |

Both transports carry the same XYE command set. Differences are documented in §3.

### 1.2 Hardware Under Test

| Property | Value |
|----------|-------|
| Unit | Midea XtremeSaveBlue (Q11 platform) |
| Indoor model | MSAGBU-09HRFN8-QRD0GW |
| XYE adapter (HAHB) | MFB-X (HA/HB differential, transformer-coupled, rotary address switch 0-F) |
| XYE adapter (direct) | MFB-C (XYE RS-485, 4-terminal) |
| Wired controllers | KJR-120M (HAHB path), KJR-120X (XYE path) |
| Capture tool (HAHB) | Saleae logic analyzer on HA/HB differential pair |
| Capture tool (XYE) | blaueis-hvacshark ESP32 RS-485 dongle (passive, receive-only) |
| Dissector | blaueis-hvacshark Lua dissector (`HVAC-shark_mid-xye.lua`) |

**Capture path note**: Own HAHB captures (logic analyzer Sessions 3–13) are recorded
on the HA/HB bus between the KJR-120M room controller and the MFB-X adapter board.
The MFB-X adapter board also handles the R/T bus connection to the indoor unit's
display board. HAHB and R/T data therefore share the same adapter board path and
correlate temporally — changes on the R/T bus appear on the HAHB bus within one
polling cycle and vice versa. This correlation is used for cross-bus validation
throughout this document, but it is **not** ground truth: the adapter board is a
translation layer and may introduce its own behaviors.

Own dongle captures (Sessions 1–2) are direct XYE RS-485 sniffs of the KJR-120X
controller talking to the indoor unit via MFB-C — no adapter board in the path.

### 1.3 Confidence Labels

| Label | Meaning |
|-------|---------|
| **Confirmed** | Multiple independent sources agree AND own captures validate |
| **Consistent** | One source + own captures agree, or 2+ sources agree without own data |
| **Hypothesis** | Single source only, no own validation |
| **Disputed** | Sources disagree with each other or with own captures |
| **Unknown** | Insufficient data to form a hypothesis |

Labels are never silently upgraded. When upgrading, the new evidence is recorded.

### 1.4 Sources

| ID | Source | Language | Coverage | Notes |
|----|--------|----------|----------|-------|
| **CB-erl** | codeberg.org/xye/xye Erlang emulator | Erlang | Frame structure, encodings | Most reliable codeberg source — actual running code |
| **CB-readme** | codeberg.org/xye/xye README | Markdown | Protocol overview | Contains errors (temp offset, fan low speed, CRC placement) |
| **ESPHome** | esphome-mideaXYE-rs485 | C++/YAML | XYE controller impl | Working code but has bugs (MASTER_FLAG, temp encoding) |
| **mdrobnak** | external-captures/01_mdrobnak_ch36ahu | Captures | Emergency heat, CH-36AHU unit | Single source for emergency heat; Variant B C6 sub-commands |
| **rymo** | external-captures/02_rymo_static_pressure | Captures | Static pressure control | Single source for SP features; Variant B C6 sub-commands |
| **Own HAHB** | Logic analyzer Sessions 3–13 | Captures | Full protocol coverage | Via MFB-X adapter on HA/HB bus; KJR-120M controller |
| **Own XYE** | Dongle Sessions 1–2 | Captures | Basic polling + Follow-Me | Direct RS-485 sniff; KJR-120X controller |

### 1.5 Own Capture Sessions

| Session | Source | Bus | Controller | Key Data | XYE Frames |
|---------|--------|-----|------------|----------|------------|
| LA-S03 | Logic analyzer | HAHB | KJR-120M | First HAHB capture, C6 Follow-Me | 127 |
| LA-S04 | Logic analyzer | HAHB | KJR-120M | Cold boot + Follow-Me ON, all buses | 503 |
| LA-S05 | Logic analyzer | HAHB | KJR-120M | Follow-Me with variable temp (11→10°C) | 368 |
| LA-S06 | Logic analyzer | HAHB | KJR-120M | Service menu ground truth (T1/T3/T4/Tp) | 488 |
| LA-S07 | Logic analyzer | HAHB | KJR-120M | Mode sweep, fan sweep, FM disable, swing | 4,186 |
| LA-S08 | Logic analyzer | HAHB | KJR-120M | Dedicated swing testing, Auto sub-modes | 1,631 |
| LA-S09 | Logic analyzer | HAHB | KJR-120M | Cold boot + Follow-Me OFF | 432 |
| LA-S10 | Logic analyzer | HAHB | KJR-120M | C/F unit switching, addr=5, FM disable | 3,591 |
| LA-S11 | Logic analyzer | HAHB | KJR-120M | Fan gear %, stepless capability | 4,696 |
| LA-S12 | Logic analyzer | HAHB | KJR-120M | Cool mode, ECO/turbo, FM enable | 3,372 |
| LA-S13 | Logic analyzer | HAHB | KJR-120M | Short session | 709 |
| Dongle-S1 | ESP32 dongle | XYE | KJR-120X | Follow-Me + mode changes, 167 s | 1,070 |
| Dongle-S2 | ESP32 dongle | XYE | KJR-120X | Follow-Me toggle, pure FM on/off | 256 |
| mdrobnak S01–S08 | External | XYE | Unknown | Emergency heat, CH-36AHU unit | 38 |
| rymo S01 | External | XYE | Unknown | Static pressure control | 10 |
| **Total** | | | | **CRC-valid (1 CRC failure rejected)** | **21,458** |

### 1.6 Notation Conventions

- Byte offsets are **frame-absolute** (byte[0] = first byte of frame = preamble 0xAA)
- Temperatures are always in **°C** unless explicitly noted as °F
- Hex values are prefixed with `0x`
- Frame examples show raw hex bytes without spaces: `AAC000000000...`
- Confidence labels appear in **bold** after field descriptions

---

## 2. Physical Layer and Framing

### 2.1 XYE Bus (RS-485)

| Property | Value |
|----------|-------|
| Interface | RS-485 differential |
| Connector | 3-terminal: X (A+), Y (B−), E (GND) |
| Baud rate | **4800 bps** |
| Data format | 8N1 (8 data bits, no parity, 1 stop bit) |
| Topology | Multi-drop bus, up to 16 units observed (addresses 0x00–0x0F) |
| Preamble | `0xAA` (all frames) |
| Epilogue | `0x55` (all frames) |
| Frame sizes | Fixed: 16 bytes (command) or 32 bytes (response/broadcast) |

### 2.2 Frame Structure — Command Frame (16 bytes, controller → unit)

Sent by the controller (KJR-120M, KJR-120X, or automation device) to query or
command an indoor unit.

```
Offset  Field          Value / Description                                    Sources
------  -----          -------------------                                    -------
  0     PREAMBLE       0xAA                                                   All
  1     COMMAND        Command code (§4)                                      All
  2     DEST_ID        Target unit address 0x00-0x0F                          CB-erl, own
  3     SRC_ID         Controller address                                     CB-erl, own
  4     FLAGS          See note below                                         Disputed
  5     SRC_ID_repeat  Same as byte 3                                         CB-erl, own
  6-12  PAYLOAD        Command-specific data (7 bytes, §5)                    Per command
 13     CMD_CHECK      0xFF - COMMAND (e.g. 0xC0 → 0x3F)                     CB-erl, own
 14     CRC            Integrity check (§2.4)                                 All
 15     EPILOGUE       0x55                                                   All
```

**byte[2] — DEST_ID**: Unit address, 0x00–0x0F observed. The KJR-120M controller
sweeps addresses 0x00–0x0F during cold boot (C4 enumeration) and steady-state
polling. The KJR-120X only targets 0x00. Address is set by the MFB-X rotary switch
(Sessions 10–13: switch at position 5, dest=0x05 for C0/C3/C6).
**Confirmed** (own HAHB + own XYE + external, 21,458 CRC-valid frames).

**byte[4] — FLAGS**:

| Source | Claim | Observed |
|--------|-------|----------|
| CB-readme | 0x80 = "from master" | — |
| CB-erl | 0x80 in command frames | — |
| ESPHome | 0x80 in C0/C3, but 0x00 in C6 (inconsistent within codebase) | — |
| Own HAHB S03–S13 | **0x00** in all 10,773 command frames | 0x00 constant |
| Own XYE Dongle S1–S2 | **0x00** in all 659 command frames | 0x00 constant |
| mdrobnak | **0x00** | 0x00 |

**Resolution**: Always 0x00 on all observed hardware. Codeberg/ESPHome claim of 0x80
is not observed in any real capture. Both values appear to be accepted by indoor units
(ESPHome users report functioning with 0x80). **Corrected** — use 0x00.

### 2.3 Frame Structure — Response / Broadcast Frame (32 bytes, unit → controller)

Sent by the indoor unit in response to a command, or autonomously as a D0 broadcast
(HAHB only). The common header occupies bytes 0–5; the payload structure depends on
the command type (§6).

```
Offset  Field          Value / Description                                    Sources
------  -----          -------------------                                    -------
  0     PREAMBLE       0xAA                                                   All
  1     RESPONSE_CODE  Echoes command code (§4.2)                             CB-erl, own
  2     DIR_FLAG       See note below                                         Disputed
  3     DEST_ID        Controller address                                     CB-erl, own
  4     SRC_ID         Unit address                                           CB-erl, own
  5     SRC_ID_repeat  Same as byte 4                                         CB-erl, own
  6-29  PAYLOAD        Response-specific data (24 bytes, §6)                  Per response type
 30     CRC            Integrity check (§2.4)                                 CB-erl, own
 31     EPILOGUE       0x55                                                   All
```

**byte[2] — DIR_FLAG**:

| Source | Claim | Observed |
|--------|-------|----------|
| CB-readme | 0x80 = "slave to master" | — |
| ESPHome | Validates for 0x80 in `checkData()` | — |
| Own HAHB S03–S13 | **0x00** in all 7,464 response frames | 0x00 constant |
| Own XYE Dongle S1–S2 | **0x00** in all 665 response frames | 0x00 constant |
| mdrobnak | **0x00** | 0x00 |

**Resolution**: Always 0x00 on all observed hardware. Same situation as byte[4] in
commands — codeberg spec claims 0x80 but no real capture shows it. The ESPHome
validation check (`checkData`) would never trigger on real hardware. **Corrected**.

For protocol discrimination on shared buses, see §2.6.

### 2.4 Checksum Algorithm

XYE uses a single integrity byte covering the frame body. Two equivalent formulations:

```
Formulation A (twos complement of inner bytes):
  CRC = (-sum(bytes[1..N-2])) % 256

  where N = frame length (16 or 32), so:
    16-byte frame: CRC = (-sum(bytes[1..13])) & 0xFF
    32-byte frame: CRC = (-sum(bytes[1..29])) & 0xFF

Formulation B (ones complement of all bytes, used by ESPHome):
  CRC = 0xFF - (sum(all bytes except CRC) & 0xFF)
```

These are algebraically identical because preamble (0xAA) + epilogue (0x55) = 0xFF.
Adding 0xFF to the inner sum before ones complement yields the same result as twos
complement of the inner sum alone. The blaueis-hvacshark dissector uses formulation A.

**Sources**: CB-erl (formulation A), ESPHome (formulation B), own dissector (A).
All three produce identical CRC values. **Confirmed**.

### 2.5 Command Check Byte

Byte[13] in 16-byte command frames contains `0xFF - command_code`:

| Command | byte[13] |
|---------|----------|
| 0xC0 (Query) | 0x3F |
| 0xC3 (Set) | 0x3C |
| 0xC4 (Ext.Query) | 0x3B |
| 0xC6 (Follow-Me) | 0x39 |
| 0xCC (Lock) | 0x33 |
| 0xCD (Unlock) | 0x32 |

This byte is separate from the CRC and serves as a command integrity check.
**Confirmed** (CB-erl + own captures, all 11,432 command frames).

### 2.6 Protocol Discrimination (XYE vs UART)

On connectors that may carry either protocol (e.g., CN3 on some units), byte[1]
unambiguously identifies XYE vs UART — their valid value ranges never overlap.
See [protocol_shared.md](protocol_shared.md) §9 for full discrimination logic.

---

## 3. HAHB Transport Variant

### 3.1 Physical Layer

The HAHB bus uses HA/HB differential signaling (transformer-coupled) instead of
RS-485. The MFB-X adapter board translates between the HAHB physical layer and
the indoor unit's R/T bus interface. The XYE protocol content is identical — only
the physical encoding differs.

| Property | XYE (RS-485) | HAHB |
|----------|-------------|------|
| Signaling | RS-485 differential | HA/HB transformer-coupled differential |
| Adapter | MFB-C (4-terminal) | MFB-X (with rotary address switch) |
| Encoding | Native bytes | Nibble-pair encoding (§3.2) |
| Effective data rate | 4800 bps | ~2400 logical bytes/s (see §3.2) |
| D0 broadcast | Not observed | Present (~1.2 s interval) |

### 3.2 Nibble-Pair Encoding

On the HAHB bus, each logical XYE byte is transmitted as two physical bytes using
nibble-pair encoding: the byte is split into high and low nibbles, each XOR'd with
0xFF and transmitted separately. This doubles the physical byte count, halving the
effective data rate to ~2400 logical bytes/s.

The blaueis-hvacshark pcap converter handles the nibble-pair decode transparently — all
frame data in the pcap files is already decoded to logical XYE bytes.

### 3.3 Functional Differences

| Aspect | XYE (RS-485 direct) | HAHB (adapter board) |
|--------|--------------------|-----------------------|
| D0 broadcast | **Not observed** (0 frames in 1,326 dongle frames) | **Present** (4,175 frames across Sessions 3–13, ~1.2 s interval) |
| C6 sub-command variant | Variant B (0x06/0x02/0x04) — KJR-120X | Variant A (0x46/0x42/0x44) — KJR-120M |
| Address sweep at boot | Not observed (KJR-120X: addr 0x00 only) | KJR-120M sweeps 0x00–0x0F |
| MFB-X address switch | N/A | Rotary switch selects unit address (0-F) |

**D0 broadcast origin**: D0 frames have src=0x01 and dest=0x20 — neither matches
the indoor unit address or any controller address. D0 is likely generated by the
MFB-X adapter board itself (or relayed from the indoor unit's internal bus), not
by the controller. Its absence on direct XYE supports this — the MFB-C adapter
has no equivalent broadcast mechanism.

**C6 variant correlation**: Variant A (bit 0x40 set) is observed exclusively on
HAHB (KJR-120M via MFB-X). Variant B (bit 0x40 clear) is observed on direct XYE
(KJR-120X via MFB-C) and in external captures (mdrobnak, rymo). Whether this
difference is controller-dependent or adapter-dependent is not yet determined.
Both variants are accepted by the indoor unit. **Hypothesis**.

### 3.4 Capture Methodology Notes

- **HAHB captures** (logic analyzer): Saleae probes on the HA/HB differential pair.
  Raw nibble-pair data is decoded by the pcap converter before analysis. The
  resulting pcap contains logical XYE frames identical to what would appear on a
  direct RS-485 bus.
- **XYE captures** (dongle): ESP32 with RS-485 transceiver in receive-only mode,
  passively sniffing the XYE bus between KJR-120X and MFB-C adapter. No address
  filtering — all frames between 0xAA and 0x55 are captured.

---

## 4. Message Types and Dispatch

### 4.1 Command Summary Table

| Cmd | Who Sends | Who Responds | Req | Resp | Purpose | Observed In | Frames | Confidence | Section |
|-----|-----------|-------------|-----|------|---------|-------------|--------|------------|---------|
| 0xC0 | KJR-120M, KJR-120X | Indoor unit | 16B | 32B | Status query | CB-erl, ESPHome, own HAHB S03–S13, own XYE D-S1/S2 | 7,242 | **Confirmed** | §5.1, §6.1 |
| 0xC3 | KJR-120M, KJR-120X | Indoor unit | 16B | 32B | Set parameters | CB-erl, ESPHome, own HAHB S03–S12, own XYE D-S1 | 256 | **Confirmed** | §5.2, §6.1 |
| 0xC4 | KJR-120M, KJR-120X | Indoor unit | 16B | 32B | Extended query / enumeration | Own HAHB S03–S13, own XYE D-S1/S2 | 9,453 | **Confirmed** | §5.3, §6.2 |
| 0xC6 | KJR-120M, KJR-120X | Indoor unit | 16B | 32B | Follow-Me + swing | ESPHome, own HAHB S03–S09, own XYE D-S1/S2 | 293 | **Confirmed** | §5.4, §6.2 |
| 0xCC | (not captured) | (not captured) | 16B | 32B | Lock (disable local remote) | CB-erl only | 0 | **Hypothesis** | §5.5 |
| 0xCD | (not captured) | (not captured) | 16B | 32B | Unlock (enable local remote) | CB-erl only | 0 | **Hypothesis** | §5.6 |
| 0xD0 | Indoor unit (autonomous) | — | — | 32B | Periodic status broadcast | Own HAHB S03–S13 only | 4,175 | **Confirmed** | §6.4 |

**Frame size distribution** (from `data-analysis/midea/xye/frame_survey.py`, 21,458 CRC-valid frames):

| Command | 16-byte | 31-byte | 32-byte |
|---------|---------|---------|---------|
| C0 Query | 3,944 (cmd) | 9 (truncated?) | 3,289 (resp) |
| C3 Set | 130 (cmd) | — | 126 (resp) |
| C4 Ext.Query | 5,415 (cmd) | — | 4,038 (resp) |
| C6 Follow-Me | 146 (cmd) | — | 147 (resp) |
| D0 Broadcast | — | — | 4,175 |

Note: C4 has more commands (5,415) than responses (4,038) because many C4 probes to
non-existent unit addresses go unanswered during the KJR-120M address sweep.

### 4.2 Response Code Construction — **Hypothesis**

The codeberg Erlang emulator constructs response codes by echoing the command code:

| Command | Response code | Pattern |
|---------|--------------|---------|
| 0xC0 (Query) | 0xC0 | Echo |
| 0xC3 (Set) | 0xC3 | Echo |
| 0xC4 (Ext.Query) | 0xC4 | Echo |
| 0xC6 (Follow-Me) | 0xC6 | Echo |
| 0xCC (Lock) | 0xCC | `0xC0 | 0x0C` |
| 0xCD (Unlock) | 0xCD | `0xC0 | 0x0D` |

Own captures confirm: C0/C3/C4/C6 responses echo the command code in byte[1].
CC/CD not captured. **Consistent** (CB-erl + own captures).

### 4.3 Request-Response Pairing

| Pattern | Description | Observed |
|---------|-------------|----------|
| C0 → C0 | Status query → status response | Every polling cycle |
| C3 → C3 | Set parameters → set acknowledgment | On operator action |
| C4 → C4 | Extended query → extended response | Every polling cycle + boot sweep |
| C6 → C6 | Follow-Me/swing → extended response | On FM toggle/update or settings change |
| C3+C6 → C3+C6 | Atomic pair: set + FM handshake | KJR-120M: every settings change |
| D0 (unsolicited) | Periodic broadcast, no trigger | HAHB only, ~1.2 s interval |

---

## 5. Commands (Controller → Indoor Unit)

Each command is a 16-byte frame. Bytes 0–5 and 13–15 are the common header (§2.2).
Bytes 6–12 are the command-specific payload, documented per command below.

For each field, sources are listed and conflicts discussed. Own capture observations
note the bus type (HAHB = logic analyzer via MFB-X adapter, XYE = dongle via MFB-C).

### 5.1 Command 0xC0 — Query

**Sent by**: KJR-120M (HAHB, Sessions 3–13), KJR-120X (XYE, Dongle Sessions 1–2)
**Purpose**: Request current operating status from an indoor unit.
**Response**: 32-byte C0 status response (§6.1).

The C0 query carries **no payload data** — bytes 6–12 are always 0x00.

```
Byte  Field        Value     Sources & Evidence
----  -----        -----     ------------------
 0    PREAMBLE     0xAA      All
 1    COMMAND      0xC0      All
 2    DEST_ID      0x00-0x0F Sweep: KJR-120M cycles 0x00-0x0F; KJR-120X: 0x00 only
 3    SRC_ID       0x00      All own captures
 4    FLAGS        0x00      Corrected (§2.2): codeberg claims 0x80, never observed
 5    SRC_repeat   0x00      All own captures
 6    (unused)     0x00      3,944 frames, all sessions — constant
 7    (unused)     0x00      3,944 frames — constant
 8    (unused)     0x00      3,944 frames — constant
 9    (unused)     0x00      3,944 frames — constant
10    (unused)     0x00      3,944 frames — constant
11    (unused)     0x00      3,944 frames — constant
12    (unused)     0x00      3,944 frames — constant
13    CMD_CHECK    0x3F      0xFF - 0xC0
14    CRC          (calc)    Twos complement (§2.4)
15    EPILOGUE     0x55      All
```

**Frame example** (dest=0x00): `AAC000000000 00000000000000 3F0155`
**Frame example** (dest=0x05): `AAC005000000 00000000000000 3FFC55`

The only varying byte is DEST_ID (byte[2]). CRC changes accordingly.
**Confirmed** — 3,944 CRC-valid C0 command frames across all sessions.

### 5.2 Command 0xC3 — Set Parameters

**Sent by**: KJR-120M (HAHB), KJR-120X (XYE)
**Purpose**: Write operating parameters (mode, fan speed, setpoint, flags, timers).
**Response**: 32-byte C3 status response (§6.1, same layout as C0 response).

```
Byte  Field        Encoding                                Sources & Evidence
----  -----        --------                                ------------------
 0    PREAMBLE     0xAA                                    All
 1    COMMAND      0xC3                                    All
 2    DEST_ID      0x00-0x0F                               Same as C0
 3    SRC_ID       0x00                                    All own captures
 4    FLAGS        0x00                                    Corrected (§2.2)
 5    SRC_repeat   0x00                                    All own captures
 6    MODE         Operating mode (§8.1)                   CB-erl, ESPHome, own
 7    FAN          Fan speed (§8.2)                        CB-erl, ESPHome, own (Disputed: §8.2 note)
 8    SETPOINT     Temperature (§8.3)                      CB-erl, ESPHome, own (dual C/F encoding)
 9    MODE_FLAGS   See bit table below                     CB-erl, own
10    TIMER_START  Timer start bitmask                     CB-erl only (never exercised in own captures)
11    TIMER_STOP   Timer stop bitmask                      CB-erl only (never exercised in own captures)
12    (reserved)   0x00                                    All own captures — constant
13    CMD_CHECK    0x3C                                    0xFF - 0xC3
14    CRC          (calc)                                  Twos complement (§2.4)
15    EPILOGUE     0x55                                    All
```

**byte[6] — MODE**: One-hot encoding with power bit (§8.1).

| Value | Mode | Source | Own captures |
|-------|------|--------|-------------|
| 0x00 | Off | CB-erl, ESPHome | S07, S09: mode off |
| 0x81 | Fan | CB-erl, ESPHome | S07, S09: fan mode |
| 0x82 | Dry | CB-erl, ESPHome | S07, S09: dry mode |
| 0x84 | Heat | CB-erl, ESPHome | S04, S07, S09: heat mode |
| 0x88 | Cool | CB-erl, ESPHome | S07, S08, S12: cool mode |
| 0x90 | Auto | ESPHome, own | S07, S08: auto mode |

**Confirmed** — all 6 modes observed in own captures, matching CB-erl + ESPHome.
Note: CB-readme lists Auto as 0x80 (incorrect — that's just power-on with no mode bits).

**byte[7] — FAN**: One-hot bitmask (§8.2).

| Source | Low value | Evidence |
|--------|-----------|----------|
| CB-readme | 0x03 | — |
| CB-erl | 0x04 | Erlang emulator code |
| ESPHome | 0x03 / 0x04 | Original YAML uses 0x03 (bug); debugger variant uses 0x04 |
| Own HAHB S07 | **0x04** | Fan sweep: Auto→Low→Mid→High, 14 transitions |
| R/T correlation | XYE 0x04 ↔ R/T body[3]=40 (Low) | Same timestamp |

**Resolution**: Low = 0x04. CB-readme value 0x03 is incorrect.
**Confirmed** (S07 fan sweep + R/T cross-bus).

**byte[8] — SETPOINT**: Dual Celsius/Fahrenheit encoding (§8.3).
- Celsius (bit 7 = 0): `(byte & 0x7F) - 0x40 = °C`
- Fahrenheit (bit 7 = 1): `(byte & 0x7F) - 0x07 = °F`
- Example: 0x56 = 22°C, 0xD0 = 73°F
**Confirmed** (S07 full 16–30°C sweep + S10 Fahrenheit transitions).

**byte[9] — MODE_FLAGS** (C3 command):

| Source | Bit | Meaning | Own captures |
|--------|-----|---------|-------------|
| CB-erl | 0x01 | ECO / sleep | Not exercised (always 0x00 in S03–S13) |
| CB-erl | 0x02 | Turbo / auxiliary heat | S07, S12: turbo toggle |
| CB-erl | 0x04 | Swing vertical | S07, S08: swing toggle |
| CB-erl | 0x88 | Ventilate (combined: bits 7+3, not a single bit) | Not observed |

**Consistent** — turbo and swing confirmed in own captures. ECO/ventilate not
exercised. See §8.7 for the response-side flags (byte[20]).

**bytes[10–11] — TIMER_START / TIMER_STOP** (CB-erl only):
Bitmask encoding — each bit represents a time increment:
`0x01=15min, 0x02=30min, 0x04=1h, 0x08=2h, 0x10=4h, 0x20=8h, 0x40=16h, 0x80=invalid`.
**Hypothesis** — never exercised in own captures (always 0x00 across 130 C3 command frames).

### 5.3 Command 0xC4 — Extended Query / Device Enumeration

**Sent by**: KJR-120M (HAHB), KJR-120X (XYE)
**Purpose**: Extended status query and device address enumeration at boot.
**Response**: 32-byte C4 extended response (§6.2).

```
Byte  Field        Value                       Sources & Evidence
----  -----        -----                       ------------------
 0    PREAMBLE     0xAA                        All
 1    COMMAND      0xC4                        Own captures (not in CB-erl/CB-readme)
 2    DEST_ID      0x00-0x0F                   KJR-120M sweeps all 16; KJR-120X: 0x00 only
 3    SRC_ID       0x00                        All own captures
 4    FLAGS        0x00                        All own captures
 5    SRC_repeat   0x00                        All own captures
 6    MAGIC_HI     0xA5 (HAHB) / 0x00 (XYE)   See note below
 7    MAGIC_LO     0x5A (HAHB) / 0x00 (XYE)   See note below
 8    (reserved)   0x00                        5,415 frames — constant
 9    (reserved)   0x00                        5,415 frames — constant
10    (reserved)   0x00                        5,415 frames — constant
11    (reserved)   0x00                        5,415 frames — constant
12    (reserved)   0x00                        5,415 frames — constant
13    CMD_CHECK    0x3B                        0xFF - 0xC4
14    CRC          (calc)                      Twos complement (§2.4)
15    EPILOGUE     0x55                        All
```

**bytes[6–7] — Magic marker**:

| Source | byte[6] | byte[7] | Frames |
|--------|---------|---------|--------|
| Own HAHB S03–S13 (KJR-120M) | **0xA5** | **0x5A** | 5,097 |
| Own XYE Dongle S1–S2 (KJR-120X) | **0x00** | **0x00** | 318 |

The KJR-120M (HAHB path) always sends the 0xA5/0x5A marker. The KJR-120X (direct
XYE) sends all zeros. Both receive valid C4 responses from the indoor unit.
The marker's purpose is unknown — it may be an adapter board feature or a controller
firmware difference. No reference source documents it. **Hypothesis**.

**C4 is not documented by codeberg or ESPHome** — it was discovered entirely through
own captures. See §7.1 for the cold boot enumeration sequence.

### 5.4 Command 0xC6 — Follow-Me + Swing

**Sent by**: KJR-120M (HAHB), KJR-120X (XYE)
**Purpose**: Dual-function command carrying Follow-Me handshake and swing activation.
**Response**: 32-byte C6 extended response (§6.2, same layout as C4 response).

```
Byte  Field        Encoding                              Sources & Evidence
----  -----        --------                              ------------------
 0    PREAMBLE     0xAA                                  All
 1    COMMAND      0xC6                                  ESPHome, own
 2    DEST_ID      0x00-0x0F                             Same as C0
 3    SRC_ID       0x00                                  All own captures
 4    FLAGS        0x00                                  All own captures (ESPHome agrees for C6)
 5    SRC_repeat   0x00                                  All own captures
 6    SWING        Swing activation state (see table)    Own S07, S08
 7    (reserved)   0x00                                  All own captures — constant (146 frames)
 8    C6_MODE      Multi-purpose flags (see table)       Own + mdrobnak + rymo
 9    (reserved)   0x00                                  All own captures — constant
10    SUB_CMD      Follow-Me sub-command (see table)     ESPHome, own, mdrobnak, rymo
11    FM_TEMP      Follow-Me temperature, direct °C      ESPHome, own, mdrobnak
12    (reserved)   0x00                                  All own captures — constant
13    CMD_CHECK    0x39                                  0xFF - 0xC6
14    CRC          (calc)                                Twos complement (§2.4)
15    EPILOGUE     0x55                                  All
```

**byte[6] — SWING activation**:

| Value | Meaning | Source | Own captures |
|-------|---------|--------|-------------|
| 0x00 | Swing off | Own captures | S03–S09: 262 frames |
| 0x10 | Vertical swing (up/down) | Own captures | S07: 1 frame, S08: 1 frame, D-S1: 1 frame |
| 0x20 | Horizontal swing (L/R) | Own captures | S07: 1 frame, S08: 1 frame |

**Confirmed** (S07 Phase 6 swing toggle + S08 dedicated swing session).
Note: horizontal swing state is **only** reported in D0 broadcast byte[11] and C6
byte[6] — the C0/C3 response byte[20] only carries vertical swing (bit 2).

**byte[8] — C6_MODE** (multi-purpose):

| Value | Meaning | Source | Own captures |
|-------|---------|--------|-------------|
| 0x00 | Normal operation | Own HAHB+XYE | 293 C6 frames, all sessions — constant 0x00 |
| 0x80 | Emergency heat request | mdrobnak (1 frame) | Never observed on own HW |
| 0x10–0x14 | Static pressure SP0–SP4 | rymo (5 frames) | Never observed on own HW |

Emergency heat: mdrobnak's CH-36AHU unit confirms via C4 response byte[15] bit 0x40.
**Hypothesis** (single source each, CRC-valid, internally consistent).

**byte[10] — SUB_CMD (Follow-Me sub-command)**:

Two variants exist, distinguished by bit 0x40:

| Sub-command | Variant A (bit 0x40 set) | Variant B (bit 0x40 clear) |
|-------------|------------------------|---------------------------|
| START | 0x46 | 0x06 |
| UPDATE | 0x42 | 0x02 |
| STOP | 0x44 | 0x04 |

| Source | Variant | Evidence |
|--------|---------|----------|
| Own HAHB S03–S09 (KJR-120M) | **A** | 84× START, 4× UPDATE, 19× STOP |
| ESPHome C++ code | **A** | `0x46` start, `0x42` update, `0x44` stop |
| Own XYE Dongle S1–S2 (KJR-120X) | **B** | 12× START, 1× UPDATE, 6× STOP |
| mdrobnak | **B** | 3× START, 1× UPDATE |
| rymo | **B** | 5× STOP (static pressure config) |

The lower nibble encodes the sub-command: 0x06=start, 0x02=update, 0x04=stop.
Bit 0x40 distinguishes the controller or adapter path. Both variants are accepted
by the indoor unit. **Confirmed** (multiple sources, both variants independently validated).

**byte[11] — FM_TEMP**: Room temperature in direct °C (no offset).

| Source | Evidence |
|--------|----------|
| ESPHome | `sendFollowMeData[11] = static_cast<uint8_t>(std::round(followMeTemp))` |
| Own HAHB S04 | 8× at 13°C (KJR-120M sensor reading, room ~13°C) |
| Own HAHB S07 | 69× at 24°C (KJR-120M sensor, room ~24°C) |
| Own XYE D-S1 | Values 19–21°C (KJR-120X sensor, plausible room temps) |
| mdrobnak | Values match room temperature context |

**Confirmed** (ESPHome + own captures, multiple sessions, temperatures physically plausible).

#### C6 framing patterns

C6 appears in two contexts:

**Paired with C3** (atomic C3+C6 pair, ~60 ms gap):
```
C3 Set (controller → unit) → C3 Response → C6 (controller → unit) → C6 Response
```
KJR-120M: every operator action triggers a C3+C6 pair (START when FM active, STOP when FM inactive).
KJR-120X: paired when operator changes settings while toggling FM.

**Standalone** (C6 without preceding C3):
```
C0/C4 Response → C6 (controller → unit) → C6 Response
```
Both controllers: UPDATE is always standalone (periodic FM temperature refresh, ~3–5 min intervals).
KJR-120X: START and STOP can also be standalone for pure FM toggle.

See §9.2 for the full Follow-Me lifecycle.

### 5.5 Command 0xCC — Lock

**Source**: CB-erl only. **Never captured** on own hardware.
**Purpose**: Disable local remote control on the indoor unit.
**Response**: 32-byte response echoing 0xCC (per CB-erl). **Hypothesis**.

Payload bytes 6–12: undocumented. CB-erl constructs the response but does not
specify the command payload beyond the standard header.

### 5.6 Command 0xCD — Unlock

**Source**: CB-erl only. **Never captured** on own hardware.
**Purpose**: Re-enable local remote control.
**Response**: 32-byte response echoing 0xCD (per CB-erl). **Hypothesis**.

Same limitations as 0xCC — no payload documentation available.

---

## 6. Responses (Indoor Unit → Controller) and Broadcast

All responses are 32-byte frames. The common header (bytes 0–5) and trailer
(bytes 30–31) are shared across response types. Payload structure depends on
the command that triggered the response.

Frame counts below are CRC-valid only (21,458 total, 1 CRC failure rejected).
Value distributions include all own sessions (HAHB S03–S13, XYE Dongle S1–S2)
plus external captures (mdrobnak S01–S08, rymo S01).

### 6.1 Response to 0xC0/0xC3 — Status (32 bytes)

Sent by the indoor unit in response to a C0 Query or C3 Set command. Both
response types use the same 32-byte layout — only byte[1] (response code)
differs (0xC0 vs 0xC3).

**Total CRC-valid frames**: 3,303 (C0) + 126 (C3) = 3,429 status responses.

```
Byte  Field          Encoding / Observed                               Confidence
----  -----          --------------------                              ----------
 0    PREAMBLE       0xAA constant (3429/3429)                         Confirmed
 1    RESP_CODE      0xC0 or 0xC3 (echoes command)                     Confirmed
 2    DIR_FLAG       0x00 constant (3429/3429) — NOT 0x80 (§2.3)       Corrected
 3    DEST_ID        0x00 constant — controller address                Confirmed
 4    SRC_ID         0x00 or 0x05 — unit address (MFB-X switch)        Confirmed
 5    SRC_repeat     0x00 constant                                     Confirmed
```

**bytes[6–7] — Capabilities / marker pair**:

Survey data (3,429 CRC-valid C0+C3 responses):

| HW variant | byte[6] | byte[7] | Frames |
|------------|---------|---------|--------|
| Own Q11 | 0x10 | 0x30 | 3,289 |
| mdrobnak CH-36AHU | 0x30 | 0x14 | 14 |

CB-erl documents byte[6]=0x30 (fixed marker) and byte[7] as capabilities
(bit 7 = extended temp range, bit 4 = swing). Own Q11 shows a different
pair (0x10, 0x30). The values differ by hardware variant — the role of
each byte is not resolved. See OQ-09.

```
Byte  Field          Encoding / Observed                               Confidence
----  -----          --------------------                              ----------
 6    CAPABILITIES_1 0x10 (Q11: 3289×), 0x30 (mdrobnak: 14×)          Disputed
 7    CAPABILITIES_2 0x30 (Q11: 3289×), 0x14 (mdrobnak: 14×)          Disputed
```

**bytes[8–10] — Operating state**:

```
Byte  Field          Encoding / Observed                               Confidence
----  -----          --------------------                              ----------
 8    OPER_MODE      One-hot mode encoding (§8.1)                      Confirmed
                     9 distinct values observed (3,429 frames):
                     0x84:2148 0x88:596 0x94:238 0x81:115 0x98:88
                     0x00:77 0x82:33 0x91:6 0x80:2
 9    FAN_SPEED      One-hot fan encoding (§8.2)                       Confirmed
                     6 values: 0x80:3090 0x08:110 0x01:80 0x04:8
                     0x02:8 0x00:7
10    SETPOINT       Dual C/F encoding (§8.3)                          Confirmed
                     24 distinct values, range 0x50–0x5E (16–30°C)
                     + 0xD0+ (Fahrenheit, S10)
```

**byte[9] FAN_SPEED — unexpected value 0x08**:

| Source | Values documented |
|--------|------------------|
| CB-erl | 0x80, 0x01, 0x02, 0x04 |
| ESPHome | 0x80, 0x01, 0x02, 0x04, 0x81, 0x82, 0x84 |
| Own captures | 0x80 (3090×), **0x08** (110×), 0x01 (80×), 0x04 (8×), 0x02 (8×), 0x00 (7×) |

The value 0x08 (bit 3) appears in 110 frames. No source documents this value.
In one-hot encoding, bit 3 sits between Low (bit 2) and Auto (bit 7). See OQ-01.

**bytes[11–14] — Temperature sensors**:

```
Byte  Field          Encoding                                          Confidence
----  -----          --------                                          ----------
11    T1_INDOOR      (raw - 40) / 2.0 = °C                            Confirmed
                     Follow-Me dependent: FM sensor when active,
                     unit thermistor when inactive (§8.4, §9.2)
                     27 distinct values, range 0x42–0x62 (1–17°C..24°C)
12    T2A_COIL_IN    (raw - 40) / 2.0 = °C                            Confirmed
                     Indoor coil inlet temperature
                     100 distinct values (wide range — tracks refrigerant)
13    T2B_COIL_OUT   0x00 constant (3303/3303) on Q11                  Consistent
                     Not reported on test hardware
                     (raw - 40) / 2.0 = °C formula applies when non-zero
14    T3_OUTDOOR     (raw - 40) / 2.0 = °C                            Confirmed
                     Outdoor coil temperature
                     40 distinct values, range 0x27–0x3C (−6.5–10°C)
```

Temperature formula **Confirmed**: (raw - 40) / 2 = °C. Evidence:
- Session 4: T1 raw=0x42 → (66−40)/2 = 13°C (Erlang), R/T UART confirmed 13°C ✓
- Session 6: T1 raw=0x4C → 18°C, service menu T1=18°C ✓ (exact)
- Session 6: T3 raw=0x2C → 2°C, service menu T3=2°C ✓ (exact)
See §8.4 for full evidence chain.

**bytes[15–18] — Diagnostics / timers**:

```
Byte  Field          Observed (3,429 frames)                           Confidence
----  -----          -----------------------                           ----------
15    CURRENT        0x00 (3262×), 0x01 (27×), 0xFF (14×)             Consistent
                     CB-erl: "0-99 Amps, direct value"
                     Q11: always 0x00. mdrobnak: 0xFF (14×), 0x01 (27×).
                     Hardware-variant dependent.
16    UNKNOWN_16     0xFF (3289×), 0x00 (14×)                          Unknown
                     CB-erl: possibly "frequency". Q11: constant 0xFF.
                     mdrobnak: 0x00. Purpose undetermined.
17    TIMER_START    0x00 constant (3429/3429)                         Hypothesis
                     CB-erl: bitmask timer encoding. Never exercised.
18    TIMER_STOP     0x00 constant (3429/3429)                         Hypothesis
                     CB-erl: bitmask timer encoding. Never exercised.
```

**bytes[19–21] — Status flags**:

```
Byte  Field          Observed (3,429 frames)                           Confidence
----  -----          -----------------------                           ----------
19    RUN_STATUS     0x20 (2626×), 0x00 (650×), 0x01 (27×)            Consistent
                     CB-erl: bit 0 = "unit running"
                     Own Q11: 0x20 (running), 0x00 (off). Bit 5 set
                     when unit is operating — differs from CB-erl bit 0.
                     mdrobnak: 0x01 (27×) — bit 0 set, matching CB-erl.
                     Hardware-variant dependent run flag position.
20    MODE_FLAGS     0x00 (3193×), 0x04 (86×), 0x01 (24×)             Confirmed
                     Bit 2 = vertical swing active (86×, S07/S08)
                     Bit 0 = ECO/sleep (24×, S12 ECO toggle)
                     Bit 1 = turbo (cross-bus confirmed: 332 pairs PASS)
                     NOTE: horizontal swing NOT here — only in D0 byte[11]
21    OP_FLAGS       0x00 (3265×), 0x08 (38×)                         Consistent
                     CB-erl: bit 2 = pump, bit 7 = locked
                     **bit 3 (0x08) = window contact / CP protection flag**
                     S11: 38 frames with 0x08 set during MFB-X dry contact
                     open events (2 open/close cycles). Set on contact open,
                     cleared on close. See §9.4.
                     Pump and lock never activated in own captures.
```

**bytes[22–29] — Error codes and unknown trailing bytes**:

```
Byte  Field          Observed (3,429 frames)                           Confidence
----  -----          -----------------------                           ----------
22    ERROR_1        0x00 constant (3429/3429)                         Hypothesis
                     CB-erl: error bitmask E0–E7. Never triggered.
23    ERROR_2        0x00 constant (3429/3429)                         Hypothesis
                     CB-erl: error bitmask E8–EF. Never triggered.
24    ERROR_3        0x00 constant (3429/3429)                         Hypothesis
                     CB-erl: protection bitmask P0–P7. Never triggered.
25    ERROR_4        0x00 constant (3429/3429)                         Hypothesis
                     CB-erl: protection bitmask P8–PF. Never triggered.
26    COMM_ERROR     0x00 constant (3429/3429)                         Hypothesis
                     CB-erl: CCM comm error 0–2. Never triggered.
27    L1             0xFF (Q11: 3289×), 0x14 (mdrobnak: 14×)           Disputed
                     CB-readme: 0x00. CB-erl: "L1" field.
                     Own Q11: constant 0xFF — contradicts CB-readme.
                     mdrobnak: 0x14 — yet another value. HW-variant.
28    L2             0x00 (3291×), 0xE0 (8×), 0x03/0x05/0x12 (1× ea)  Unknown
                     CB-erl: "L2" field. Mostly 0x00, occasional
                     non-zero values (mdrobnak startup sequence?).
29    L3             0x00 (3293×), 0x01 (9×), 0x02 (1×)               Unknown
                     CB-erl: "L3" field. Mostly 0x00.
30    CRC            (calculated) — 194 distinct values                Confirmed
31    EPILOGUE       0x55 constant (3429/3429)                         Confirmed
```

### 6.2 Response to 0xC4/0xC6 — Extended Status (32 bytes)

Sent by the indoor unit in response to C4 Extended Query or C6 Follow-Me commands.
Both use the same 32-byte layout (only byte[1] differs).

**Total CRC-valid frames**: 4,044 (C4) + 157 (C6) = 4,201 extended responses.

The extended response carries additional sensor data not available in C0/C3
responses: T4 outdoor ambient (byte[21]), Tp discharge temperature (byte[22]),
and static pressure readback (byte[24]).

```
Byte  Field          Observed / Encoding                               Confidence
----  -----          -------------------                               ----------
 0    PREAMBLE       0xAA constant                                     Confirmed
 1    RESP_CODE      0xC4 or 0xC6                                      Confirmed
 2    DIR_FLAG       0x00 constant                                     Corrected
 3    DEST_ID        0x00 constant                                     Confirmed
 4    SRC_ID         0x00 or 0x05 (unit address)                       Confirmed
 5    SRC_repeat     0x00 constant                                     Confirmed
 6    FLAGS_6        0x05 (Q11: 4038×), 0x00 (mdrobnak: 6×)            Unknown
 7    FLAGS_7        0x00 constant (4044/4044)                          Unknown
 8    FLAGS_8        0x02 (Q11: 4038×), 0x00 (mdrobnak: 6×)            Unknown
 9    MARKER         0x30 constant (4044/4044)                          Confirmed
10    FLAGS_10       0x0E (Q11: 4038×), 0x98 (mdrobnak: 6×)            Unknown
                     HW-variant dependent
11    SWING_STATE    0x00 (3939×), 0x10 (64×), 0x20 (34×), 0x30 (7×)  Confirmed
                     Same encoding as C6 byte[6] and D0 byte[11]
12    (reserved)     0x00 constant                                     Confirmed
13    (reserved)     0x00 constant                                     Confirmed
14    FLAGS_14       0x00 (4040×), 0x01 (4×)                           Unknown
15    EXT_STATUS     See table below                                   Consistent
16    OPER_MODE      Same as C0 byte[8] (§8.1)                         Confirmed
                     Includes NV mode at boot: 0x04 (S04), 0x01 (S09)
17    FAN_SPEED      Same as C0 byte[9] (§8.2)                         Confirmed
18    SETPOINT       Same as C0 byte[10] (§8.3)                        Confirmed
19    DEVICE_TYPE    0xBC constant (4044/4044)                          Confirmed
                     NOT a temperature — previously misidentified as Tp
20    UNKNOWN_20     0xD6 constant (4044/4044)                          Unknown
                     Identity undetermined (87°C if sensor formula)
21    T4_OUTDOOR     (raw - 40) / 2.0 = °C — outdoor ambient           Confirmed
                     10 distinct values, range 0x00–0x44
                     S06: raw≈0x30 → 4°C, service menu T4=4°C ✓
22    Tp_DISCHARGE   (raw - 40) / 2.0 = °C — compressor discharge      Confirmed
                     46 distinct values, range 0x3C–0xBC (10–74°C)
                     S06: raw=0xBC → 74°C, service menu Tp=74°C ✓
                     329 matched pairs vs R/T C1-G1 body[14]: mean diff −0.02°C
23    (reserved)     0x00 constant                                     Confirmed
24    SP_READBACK    0x00 (Q11: 4038×), 0xFF (mdrobnak: 6×)            Consistent
                     rymo: 0x20–0x24 (SP0–SP4 echo)
                     Own HW: always 0x00 (no static pressure feature)
25    (reserved)     0x00 (Q11: 4038×)                                 Confirmed
26-29 TRAILING       See table below                                   See notes
30    CRC            (calculated)                                      Confirmed
31    EPILOGUE       0x55 constant                                     Confirmed
```

**byte[15] — EXT_STATUS**:

| Source | Value | Interpretation | Frames |
|--------|-------|---------------|--------|
| Own Q11 | 0x00 | Baseline (no emergency heat) | 3,772 |
| Own Q11 | 0x08 | Unknown flag (266 frames, S11–S12) | 266 |
| mdrobnak | 0x20 | Normal operation | 5 |
| mdrobnak | 0x60 | Emergency heat active (0x20 + 0x40) | 1 |

Bit 0x40 = emergency heat active (mdrobnak only, **Hypothesis**).
Bit 0x08 = unknown (own captures only, appears in later sessions). **Unknown**.
Bit 0x20 = normal operation baseline on mdrobnak HW; 0x00 on own HW. **HW-variant**.

**bytes[26–29] — Trailing bytes**:

| Byte | Own Q11 | mdrobnak |
|------|---------|----------|
| 26 | 0x00 (4038×) | 0x80 (6×) |
| 27 | 0x00 (4038×) | 0x80 (6×) |
| 28 | 0x00 (4038×) | 0x80 (6×) |
| 29 | 0x00 (4037×), 0x08 (1×) | 0x80 (6×) |

mdrobnak's CH-36AHU consistently shows 0x80 in bytes 26–29, while own Q11 shows
all zeros. These trailing bytes may carry startup status or device-specific flags.
**Unknown** — HW-variant dependent.

### 6.3 Response to 0xCC/0xCD — Lock/Unlock ACK

**Source**: CB-erl only. **Never captured.** Response code echoes 0xCC or 0xCD.
Layout assumed identical to C0 status response (§6.1). **Hypothesis**.

### 6.4 Broadcast 0xD0 — Periodic Status (32 bytes, HAHB only)

D0 is a 32-byte unsolicited broadcast observed **only on the HAHB bus** (logic
analyzer Sessions 3–13). Zero D0 frames in dongle Sessions 1–2 (direct XYE) or
external captures (mdrobnak, rymo). See §3.3 for origin analysis.

**Total CRC-valid frames**: 4,175 across Sessions 3–13.
Timing: one D0 per polling cycle, ~1.2 s intervals.

```
Byte  Field          Observed (4,175 frames)                           Confidence
----  -----          -----------------------                           ----------
 0    PREAMBLE       0xAA constant                                     Confirmed
 1    COMMAND        0xD0 constant                                     Confirmed
 2    DEST_D0        0x20 constant — broadcast destination             Confirmed
 3    SRC_D0         0x01 constant — broadcast source                  Confirmed
 4    (reserved)     0x00 constant                                     Confirmed
 5    OPER_MODE      User-set mode (§8.1), no Auto sub-modes           Confirmed
                     S07: all 5 modes tracked correctly
 6    FAN_SPEED      Same one-hot encoding as C0 byte[9]               Confirmed
                     0x80 (3880×), 0x04 (214×), 0x01 (79×), 0x02 (2×)
                     NOTE: 0x08 absent (unlike C0 byte[9])
 7    SETPOINT       Same dual C/F encoding as C0 byte[10] (§8.3)     Confirmed
                     S10: transitions 0x57→0xD0 (C→F) with +5.4s delay
 8    (reserved)     0x00 constant (4174/4174)                         Confirmed
 9    (reserved)     0x00 constant (4174/4174)                         Confirmed
10    FLAGS_10       0x00 (4131×), 0x01 (44×)                          Unknown
                     Bit 0 occasionally set — purpose undetermined
11    SWING_STATE    0x00 (4064×), 0x10 (55×), 0x20 (51×), 0x30 (5×)  Confirmed
                     Same encoding as C6 byte[6] (§5.4) and C4 byte[11]
                     Only place horizontal swing appears in a broadcast
12-14 (reserved)     0x00 constant (4174/4174)                         Confirmed
15    FLAGS_1        0x04 (2487×), 0x06 (1402×), 0x0C (286×)          Unknown
                     3 values. Bit pattern suggests status flags.
                     No source documents this byte for D0.
16    T1_INDOOR      Indoor temperature, direct °C (no formula)        Confirmed
17    (reserved)     0x00 constant (4174/4174)                         Confirmed
18    UNKNOWN_A      0x60 (2635×), 0xA1 (562×), 0xA2 (425×),          Unknown
                     0xA0 (362×), 0x97 (167×), 0x61 (24×)
                     Stable within session, varies across sessions.
19    UNKNOWN_B      25 distinct values, highly variable               Unknown
                     Possibly counter or status word.
20-28 (reserved)     0x00 constant (4174/4174)                         Confirmed
29    INNER_CRC?     85 distinct values, highly variable               Hypothesis
                     Separate from frame CRC (byte[30]). Algorithm unknown.
30    CRC            Frame CRC (§2.4)                                  Confirmed
31    EPILOGUE       0x55 constant                                     Confirmed
```

**byte[16] — T1_INDOOR (indoor temperature, direct °C)**:

| Value | Count | Temperature |
|-------|-------|-------------|
| 0x18 | 2190 | 24°C |
| 0x19 | 1610 | 25°C |
| 0x13 | 105 | 19°C |
| 0x17 | 103 | 23°C |
| 0x0D | 90 | 13°C |
| 0x0A | 67 | 10°C |
| 0x0B | 10 | 11°C |

Cross-validated against XYE C0 byte[11] (T1), XYE C4 byte[21] (T4 outdoor),
R/T C0 body[11] (indoor), and R/T C0 body[12] (outdoor) using
`data-analysis/midea/xye/validate_d0_byte16_temp.py` (4,175 D0 frames, 11 sessions).

D0 byte[16] matches **indoor temperature (T1)** as direct °C — no sensor
formula. Mean |Δ| vs XYE T1: 1.05°C, vs R/T indoor: 1.04°C. Session 3 shows
an exact match (24/24 frames, 0.00°C deviation). Outdoor temperature (T4) was
decisively ruled out: mean |Δ| = 19.8°C (T4 was consistently 3–5°C while
byte[16] ranged 10–25°C).

**Encoding note**: Unlike C0 byte[11] which uses `(raw−40)/2`, D0 byte[16]
carries the indoor temperature in direct integer °C. The ~1°C mean deviation
across sessions is consistent with the quantization difference (0.5°C steps
in the sensor formula vs 1°C integer in D0).

Previously hypothesised as outdoor temperature — the values appeared
plausible for winter conditions but were actually indoor temperatures.
**Confirmed** (cross-bus validated, 4,175 frames, OQ-04 resolved).

---

## 7. Bus Operation and Polling Cycles

### 7.1 Cold Boot Sequence — KJR-120M

**Confirmed** (own HAHB captures, Sessions 4 and 9 — identical behavior).

**Phase 1 — Fast C4 scan (~3.2 s)**: The KJR-120M sends C4 to addresses 0x00
through 0x0F in sequence. Each unanswered probe is followed by a 200 ms silence
(response window). 16 addresses × 200 ms = 3.2 s per full sweep. During Phase 1
no unit has booted its communication stack yet — all 16 probes go unanswered.

**Phase 2 — First response**: On the second sweep, address 0x00 responds to C4
within ~19 ms. The controller immediately sends a C0 Query (~40 ms after C4
response ends), gets a C0 response with mode 0x00 (OFF/standby), then continues
probing remaining addresses (0x01–0x0F) with 200 ms timeouts.

```
+  0 ms  Controller→Unit  C4 addr=0x00       ← probe that gets answered
+ 19 ms  Unit→Controller  C4 response        ← unit responds in ~19 ms
+ 60 ms  Controller→Unit  C0 addr=0x00       ← immediate status query
+ 80 ms  Unit→Controller  C0 response (OFF)  ← unit reports OFF
+130 ms  Controller→Unit  C4 addr=0x01       ← resume sweep
+330 ms  Controller→Unit  C4 addr=0x02       ← 200 ms timeout, no response
  …                                           ← 0x03–0x0F, all unanswered
```

**Phase 3 — Steady-state polling**: The KJR-120M enters a repeating cycle
(~1.8 s per full cycle). The non-zero probe address N cycles 0x01 → 0x0F → 0x01:

```
C4 addr=0x00 → response (19 ms) → [280 ms gap] →
C0 addr=0x00 → response (20 ms) → [280 ms gap] →
C4 addr=0x00 → response (19 ms) → [280 ms gap] →
[D0 broadcast from indoor unit] → [300 ms gap] →
C4 addr=N   → (no response, 300 ms timeout) → [next cycle]
```

**Phase 4 — First operator action**: C3+C6 pair appears when operator presses a
button. If pressed during boot, the controller queues and sends once steady-state
is established.

**C4 byte[16] — NV mode memory**: The C4 response at boot reveals the unit's
NV-stored operating mode without the power-on bit:
- S04: byte[16]=0x04, first C3 sends 0x84 (Heat) — consistent (0x04 + 0x80 = 0x84)
- S09: byte[16]=0x01, first C3 sends 0x81 — consistent (0x01 + 0x80 = 0x81)

This contrasts with C0 byte[8] = 0x00 (OFF) at boot. Note: the mode label for
0x81 is ambiguous — SessionNotes label it "Dry" but §8.1 maps 0x81 to Fan (bit 0).
See OQ-16.

### 7.2 Steady-State Polling — KJR-120M

The KJR-120M (HAHB path) polls in a fixed cycle:

| Slot | Frame | Response | Gap to next |
|------|-------|----------|-------------|
| 1 | C4 addr=0x00 | C4 response (~19 ms) | ~280 ms |
| 2 | C0 addr=0x00 | C0 response (~20 ms) | ~280 ms |
| 3 | C4 addr=0x00 | C4 response (~19 ms) | ~280 ms |
| 4 | D0 broadcast (autonomous) | — | ~300 ms |
| 5 | C4 addr=N (non-zero) | No response (300 ms timeout) | → next cycle |

Full cycle: ~1.8 s. D0 broadcasts are interleaved — one per cycle.

### 7.3 Steady-State Polling — KJR-120X (via Dongle)

The KJR-120X (direct XYE path) uses a simpler pattern:

```
C0 addr=0x00 → response (~20 ms) → C4 addr=0x00 → response (~20 ms) → …
```

Inter-command spacing: ~300 ms typical (range 150–700 ms). No address sweep.
No D0 broadcasts (direct XYE bus, not HAHB). Full cycle: ~600 ms.

**No cold boot data** — KJR-120X was captured mid-operation only. **Hypothesis**:
likely skips C4 address enumeration and assumes a single unit at address 0x00.

### 7.4 Controller Comparison

| Behavior | KJR-120M (HAHB) | KJR-120X (XYE) |
|----------|-----------------|----------------|
| Boot address sweep | C4 scan 0x00–0x0F, 200 ms/probe | Not observed (Hypothesis: none) |
| Steady-state non-zero probing | Yes, 1 per cycle cycling 0x01–0x0F | No |
| Polling cadence | ~1.8 s full cycle | ~600 ms (C0+C4 pair) |
| C6 Follow-Me variant | Variant A (0x46/0x44/0x42) | Variant B (0x06/0x04/0x02) |
| C3+C6 pairing when FM off | Always pairs (STOP on every C3) | Only when FM explicitly toggled |
| D0 broadcasts visible | Yes (src=0x01, dest=0x20) | No |
| Bus adapter | MFB-X (HA/HB, transformer-coupled) | MFB-C (XYE RS-485, 4-terminal) |

### 7.5 Operator Action Insertion

When the operator presses a button on the controller, a C3+C6 pair is injected
into the polling cycle:

```
… C0 response → C3 Set → C3 response (~20 ms) → C6 → C6 response → C0 …
```

The C3+C6 pair has ~60 ms between the C3 response and the C6 command.
KJR-120M: every operator action triggers a pair. KJR-120X: only FM-related
actions or settings changes paired with FM toggle.

### 7.6 Timing Parameters

| Parameter | Value | Source |
|-----------|-------|--------|
| Response latency (all commands) | ~19–20 ms | Own S04, S09 |
| Unanswered probe spacing | 200 ms ±1 ms | Own S04, S09 |
| Answered probe → next command | ~40 ms | Own S04, S09 |
| KJR-120M full cycle period | ~1.8 s | Own S03–S13 |
| KJR-120X C0+C4 pair period | ~600 ms | Own Dongle S1–S2 |
| D0 broadcast interval | ~1.2 s (one per KJR-120M cycle) | Own S03–S13 |
| C3→C6 gap (within pair) | ~60 ms | Own S07 |
| 16-byte frame at 4800 bps | ~33 ms transmit time | Calculated |
| 32-byte frame at 4800 bps | ~66 ms transmit time | Calculated |

### 7.7 HAHB vs XYE Timing Differences

The HAHB nibble-pair encoding (§3.2) doubles the physical byte count, so a
16-byte logical frame requires ~66 ms physical transmission on HAHB (vs ~33 ms
on direct XYE). Response latencies measured from the HAHB logic analyzer
therefore include the encoding overhead.

D0 broadcasts appear only on the HAHB bus. Their ~1.2 s interval matches the
KJR-120M polling cycle — one D0 per cycle, inserted between the last C4 response
and the next non-zero address probe.

---

## 8. Encoding Reference

### 8.1 Operating Mode — **Confirmed** (S07/S08/S09)

One-hot encoding with bit 7 = power on:

| Value | Mode | Bit pattern | Context |
|-------|------|-------------|---------|
| 0x00 | Off | 0000 0000 | Commands + responses |
| 0x81 | Fan | 1000 0001 | Commands + responses |
| 0x82 | Dry | 1000 0010 | Commands + responses |
| 0x84 | Heat | 1000 0100 | Commands + responses |
| 0x88 | Cool | 1000 1000 | Commands + responses |
| 0x90 | Auto | 1001 0000 | Commands only (responses use sub-modes below) |

**Auto sub-modes** (responses only):

| Value | Meaning | Source |
|-------|---------|--------|
| 0x10 | Auto (startup, no power bit) | ESPHome, rymo C4 response |
| 0x91 | Auto + Fan (idle) | Own S09: cold boot |
| 0x94 | Auto + Heat | Own S08: room < setpoint |
| 0x98 | Auto + Cool | Own S08: room > setpoint |

Sub-mode = 0x90 | actual_operating_bits. The D0 broadcast (byte[5]) always
carries the user-set mode (0x90 for Auto), never the sub-mode.

### 8.2 Fan Speed — **Confirmed** (S07)

One-hot bitmask:

| Value | Speed | Bit | Source |
|-------|-------|-----|--------|
| 0x80 | Auto | bit 7 | All sources + own |
| 0x01 | High | bit 0 | All sources + own |
| 0x02 | Medium | bit 1 | All sources + own |
| 0x04 | Low | bit 2 | CB-erl + ESPHome + own (**not** 0x03 per CB-readme) |

**Auto sub-speeds** (responses only, ESPHome + mdrobnak):
0x81 = Auto+High, 0x82 = Auto+Medium, 0x84 = Auto+Low.
Not observed in own captures but consistent with the pattern.

**Undocumented value 0x08** (bit 3): observed in 110 C0 response frames (§6.1).
Purpose unknown — possibly turbo fan or silent mode. **Unknown**.

### 8.3 Temperature — Setpoint (Dual C/F)

**Confirmed** (S07 full sweep + S10 Fahrenheit transitions).

```
bit 7 = 0 (Celsius):     T_C = (byte & 0x7F) - 0x40     (offset 64)
bit 7 = 1 (Fahrenheit):  T_F = (byte & 0x7F) - 0x07     (offset 7)
```

Celsius range: 0x50–0x5E = 16–30°C. Fahrenheit examples: 0xD0 = 73°F, 0xD5 = 78°F.

This encoding applies to: C3 command byte[8], C0/C3 response byte[10],
C4/C6 response byte[18], D0 broadcast byte[7].

**Disputed variant**: mdrobnak's C0 response byte[10] uses raw = direct °C
(0x15 = 21°C, 0x18 = 24°C — no offset). Own Q11 data uses the offset formula.
May be firmware-variant dependent. mdrobnak's C3 command data (Session 5) does
use the offset range (0x56 = 22°C), suggesting the discrepancy may be
response-side only.

### 8.4 Temperature — Sensors (T1–T4, Tp)

**Confirmed** (S04/S05/S06 + service menu ground truth).

**Formula**: `temp_c = (raw - 40) / 2.0`

| Sensor | Byte (C0/C3) | Byte (C4/C6) | Notes |
|--------|-------------|-------------|-------|
| T1 indoor air | [11] | — | Follow-Me dependent (§9.2) |
| T2A coil in | [12] | — | Evaporator/condenser inlet |
| T2B coil out | [13] | — | 0x00 = not reported on Q11 |
| T3 outdoor coil | [14] | — | Outdoor heat exchanger |
| T4 outdoor ambient | — | [21] | Not in C0/C3, only in C4/C6 |
| Tp discharge | — | [22] | Compressor pipe temp, 329 cross-bus pairs validated |

Evidence chain for formula confirmation:
1. S04: T1 raw=0x42 → (66−40)/2 = 13°C, R/T UART confirms 13°C ✓
2. S06: T1 raw=0x4C → 18°C, service menu T1=18°C ✓ (exact)
3. S06: T3 raw=0x2C → 2°C, service menu T3=2°C ✓ (exact)
4. S06: Tp raw=0xBC → 74°C, service menu Tp=74°C ✓ (exact)

**Source conflict resolved**: CB-readme claims offset 48 (0x30), ESPHome treats
raw as direct °F. Both incorrect. CB-erl offset 40 (0x28) is correct.

Sensor temperatures are **always Celsius** regardless of the display unit setting
(C/F flag only affects the setpoint byte). **Confirmed** (S10).

### 8.5 Swing

Three-state encoding, consistent across C6 command byte[6], C4/C6 response
byte[11], and D0 broadcast byte[11]:

| Value | Meaning |
|-------|---------|
| 0x00 | Swing off |
| 0x10 | Vertical (up/down oscillation) |
| 0x20 | Horizontal (left/right oscillation) |
| 0x30 | Both (observed in C4 response, 7 frames) |

C0/C3 response byte[20] bit 2 only reports vertical swing — horizontal swing
state is exclusively visible in C6/D0/C4 frames. **Confirmed** (S07 + S08).

### 8.6 Follow-Me Sub-commands

| Sub-command | Variant A (HAHB/KJR-120M) | Variant B (XYE/KJR-120X) |
|-------------|--------------------------|--------------------------|
| START | 0x46 | 0x06 |
| UPDATE | 0x42 | 0x02 |
| STOP | 0x44 | 0x04 |

Lower nibble: 0x06=start, 0x02=update, 0x04=stop.
Bit 0x40: set on HAHB path (KJR-120M), clear on direct XYE (KJR-120X, mdrobnak, rymo).
Both variants accepted by indoor units. **Confirmed** (§5.4).

### 8.7 Status Flags — RUN_STATUS, MODE_FLAGS, OP_FLAGS

**C0/C3 response byte[19] — RUN_STATUS**:

| Bit | Meaning | Source | Own Q11 | mdrobnak |
|-----|---------|--------|---------|----------|
| bit 0 | Unit running | CB-erl | Not observed (bit 5 used instead) | 0x01 (27×) |
| bit 5 | Unit running | Own captures | 0x20 when running, 0x00 when off | Not observed |

HW-variant dependent: Q11 uses bit 5, CH-36AHU uses bit 0. **Disputed**.

**C0/C3 response byte[20] — MODE_FLAGS**:

| Bit | Meaning | Source | Own captures |
|-----|---------|--------|-------------|
| bit 0 | ECO / sleep | CB-erl | 24× set in S12 (ECO toggle) |
| bit 1 | Turbo | CB-erl | Cross-bus confirmed: 332 pairs PASS |
| bit 2 | Vertical swing active | CB-erl | 86× set in S07/S08 |

**Confirmed** — turbo and vertical swing cross-bus validated.

**C0/C3 response byte[21] — OP_FLAGS**:

| Bit | Meaning | Source | Own captures |
|-----|---------|--------|-------------|
| bit 2 | Water pump running | CB-erl | Never observed (0x00) |
| bit 3 | **Window contact / CP protection** | Own S11 | 38× set during MFB-X dry contact open (§9.4) |
| bit 7 | Unit locked | CB-erl | Never observed (0x00) |

### 8.8 Error / Protection Bitmasks

CB-erl documents error codes at bytes[22–26]:

| Byte | Field | Encoding |
|------|-------|----------|
| [22] | ERROR_1 | E + bit position (bits 0–7) |
| [23] | ERROR_2 | E + bit position (bits 8–F) |
| [24] | PROTECT_1 | P + bit position (bits 0–7) |
| [25] | PROTECT_2 | P + bit position (bits 8–F) |
| [26] | COMM_ERROR | 0–2 |

**All constant 0x00** across 3,429 own response frames + 14 mdrobnak responses.
No error condition was ever triggered in any capture session. **Hypothesis** (CB-erl
only source, never validated against real error conditions).

---

## 9. XYE-Exclusive Features

### 9.1 Multi-Unit Addressing

XYE supports up to 16 units on one bus (addresses 0x00–0x0F). The address is set
by the MFB-X rotary switch (HAHB path) or configured in the unit (XYE path).

Own Sessions 10–13: MFB-X switch at position 5. Effects:
- Commands: byte[2] (dest) = 0x05 for C0/C3/C6
- Responses: byte[4] (src) = 0x05
- D0 broadcast addresses unchanged: src=0x01, dest=0x20
- KJR-120M polls **all 16 addresses** with C0 in steady state (not just C4 sweep)

CB-erl documents 0x00–0x3F (64 addresses), but only 0x00–0x0F observed.

### 9.2 Follow-Me Lifecycle

**Activation (START)**: Operator enables FM on controller. Controller sends C6
with SUB_CMD=START and byte[11]=current room temperature in °C. On KJR-120M,
always paired with C3. On KJR-120X, can be standalone.

**Steady-state**: Every operator action on KJR-120M triggers C3+C6 with START.
Periodically (~3–5 min), a standalone C6 UPDATE refreshes the FM temperature.

**Deactivation (STOP)**: Operator disables FM. Controller sends C6 with
SUB_CMD=STOP. KJR-120M sends STOP after every C3 even when FM is inactive
(clearing stale state). KJR-120X only sends STOP on explicit FM toggle.

**Effect on T1**: When FM active, C0 byte[11] (T1) reports the controller's
sensor temperature. When FM disabled, T1 reverts to the unit's own thermistor.
S07: T1 dropped 24.0°C → 20.5°C on FM disable (controller sensor vs thermistor).

**Boot persistence**: KJR-120M remembers FM state across power cycles. S04
(FM was ON before power loss): first C6 sends START with remembered temp.
S09 (FM was OFF): every C6 sends STOP, clearing any stale NV state.

### 9.3 Device Enumeration via C4

The KJR-120M uses C4 to discover units at boot (§7.1). It sweeps addresses
0x00–0x0F, noting which respond. In steady state, it continues probing non-zero
addresses (one per cycle) to detect hot-plugged units. The KJR-120X skips
enumeration and assumes address 0x00. See §7.4 for comparison.

### 9.4 Window Contact / CP Protection — **Consistent** (S11)

The MFB-X adapter board has a dry contact input ("window contact"). When the
contact opens (e.g., window sensor triggers), the unit enters CP protection
mode — the compressor shuts down and both the indoor unit display and the
KJR-120M room controller show "CP".

**XYE C0 response byte[21] bit 3 (0x08)**: Set when the window contact is open
(CP protection active), cleared when the contact closes (normal operation).
**Consistent** — 2 complete open/close cycles captured in S11 (38 frames with
bit 3 set, matching the SessionNotes operator action log exactly).

**XYE C0 byte[8] (mode)**: Drops to 0x00 (shutdown) on contact open, recovers
to the previous mode (0x84 Heat) on contact close. The mode transition sequence
is: 0x84 → 0x00 (shutdown) → 0x80 (recovery pending) → 0x84 (normal).

**Primary signal carrier is the R/T 0x93 extension board frame** (not the XYE
C0 response). The MFB-X adapter detects the dry contact directly and signals
via 0x93 request body[1] bit 5 (0x20). The XYE C0 byte[21] reflects this
~0.9 s later via the display board relay path.

**R/T C0 body[16] (error code) does NOT carry the CP state** — it remains 0x00
("none") throughout the window contact event. The CP condition is only visible
in the 0x93 frame, XYE C0 byte[21] bit 3, and the display-mainboard bus.

Propagation order (S11, t=755 s):
```
0x93 request (MFB-X adapter, t=755.0) →
0x93 response (display board, t=755.2) →
R/T C0 + XYE C0 byte[21]=0x08 (t=755.9) →
display-mainboard bus (t=756-757)
```

See `analysis_0x93_extension_board.md` for the full 0x93 frame analysis.

### 9.5 Emergency Heat — **Hypothesis** (mdrobnak only)

C6 byte[8] = 0x80 requests emergency (auxiliary-only) heat. The unit confirms
via C4 response byte[15] bit 0x40. Observed in 1 frame from mdrobnak's CH-36AHU
unit (CRC-valid). Not observed on own Q11 hardware (emergency heat never activated).

### 9.6 Static Pressure Control — **Hypothesis** (rymo only)

C6 byte[8] = 0x10–0x14 sets static pressure level SP0–SP4. C6 response byte[24]
echoes the level as 0x20–0x24 (lower nibble). 5 CRC-valid command/response pairs
from rymo. Not observed on own Q11 hardware (no static pressure feature).

### 9.7 Lock / Unlock — **Hypothesis** (CB-erl only)

Commands 0xCC (Lock) and 0xCD (Unlock) disable/enable local remote control.
Documented only in the codeberg Erlang emulator. Never captured. See §5.5/§5.6.

---

## 10. Cross-Bus Encoding Notes

### 10.1 XYE ↔ Serial Protocol Field Mapping

| Concept | XYE Field | Serial Protocol Field |
|---------|-----------|----------------------|
| Indoor temp | C0 byte[11], (raw−40)/2 | C0 body[11], (raw−50)/2 |
| Outdoor temp | C4 byte[21], (raw−40)/2 | C0 body[12], (raw−50)/2 |
| Tp discharge | C4 byte[22], (raw−40)/2 | C1 Group1 body[14], direct °C |
| Setpoint | C0 byte[10], raw−0x40 | C0 body[2] bits[3:0]+16 |
| Fan speed | C0 byte[9], one-hot | C0 body[3], integer 0–102 |
| Mode | C0 byte[8], one-hot | C0 body[2] bits[7:5] |
| Follow-Me enable | C6 SUB_CMD | body[8] bit 7 |
| Follow-Me temp | C6 byte[11], direct °C | 0x41 body[5], T×2+50 |
| Turbo | byte[20] bit 1 | body[10] bit 1 |
| Swing (vertical) | byte[20] bit 2 | body[7] lower nibble |

### 10.2 Temperature Formula Differences

| Bus | Sensor formula | Setpoint formula |
|-----|---------------|-----------------|
| XYE | (raw − 40) / 2 (offset 40) | (raw & 0x7F) − 0x40 (offset 64) |
| Serial (UART/R/T) | (raw − 50) / 2 (offset 50) | body[2] bits[3:0] + 16 |
| Serial C1 Group1 | (raw − 30) / 2 for T1/T2, (raw − 50) / 2 for T3/T4 | — |
| Serial Tp | direct °C (no formula) | — |

### 10.3 Fan Speed Mapping

| XYE | Serial UART | Speed |
|-----|-------------|-------|
| 0x80 | 102 | Auto |
| 0x01 | 80 | High |
| 0x02 | 60 | Medium |
| 0x04 | 40 | Low |
| 0x00 | 0 | Off |

R/T UART also reports fan=101 during Auto/Dry modes (system-forced Auto vs
user-set Auto=102). See `protocol_shared.md` §6.1.

### 10.4 Known Implementation Bugs

**ESPHome esphome-mideaXYE-rs485**:
- **MASTER_FLAG**: Sets byte[4]=0x80 in C0/C3 (per codeberg) but 0x00 in C6.
  Real hardware always uses 0x00. Both accepted by units.
- **Temperature encoding**: Sends raw Fahrenheit values without bit 7 flag or
  offset conversion. Displays response byte[10] as °F without applying raw−0x40.
  Works accidentally due to roundtrip echo on some firmware variants.
- **Fan Low speed**: Original YAML (`esphome-mideaXYE.yaml`) uses 0x03 (per
  CB-readme, incorrect). The debugger variant (`debugger_method.yaml`) was
  corrected to 0x04 (matching CB-erl and own captures).

### 10.5 VRF Service Menu Cross-Reference (KJR-86S/BK)

The Midea VRF wired controller KJR-86S/BK service menu (Table 4.3 in the V8 VRF
Indoor Units manual) lists indoor unit parameters queryable via the XYE bus. This
confirms the **XYE bus is shared between consumer split systems and professional
VRF systems** — the same protocol, with a larger address space.

**Address space**: The KJR-86S/BK supports `n00–n63` (64 IDU addresses) and
`u00–u03` (4 ODU addresses), confirming CB-erl's 0x00–0x3F range. Our KJR-120M
only sweeps 0x00–0x0F — a controller limitation, not a protocol limit.

**Parameter cross-reference** (VRF check # → our documented fields):

| Check # | VRF manual description | XYE field | R/T serial field | Notes |
|---------|----------------------|-----------|-----------------|-------|
| 1 | IDU/ODU comm address | byte[2] DEST_ID | — | VRF: 0–63, own: 0–15 |
| 3 | Actual set temperature Ts | C0 byte[10] | C0 body[2] | Dual C/F encoding (§8.3) |
| 5 | Actual T1 indoor temp | C0 byte[11] | C0 body[11] | (raw−40)/2 °C |
| 6 | Modified indoor temp T1_modify | — | — | Not observed in XYE or R/T |
| 7 | T2 heat exchanger mid temp | C0 byte[12]? | — | See naming note below |
| 8 | T2A liquid pipe temp | C0 byte[12] T2A | — | — |
| 9 | T2B gas pipe temp | C0 byte[13] T2B | — | 0x00 on Q11 (not reported) |
| 14 | Compressor discharge temp | C4 byte[22] Tp | C1-G3 body[14]? | (raw−40)/2 for XYE |
| **16** | **EEV opening (actual/8)** | **Not in XYE** | **C1-G3 body[11]** | raw × 8 = steps |

**T2 naming**: The VRF manual lists three heat exchanger temperatures — T2
(intermediate), T2A (liquid pipe), T2B (gas pipe). XYE only exposes T2A (byte[12])
and T2B (byte[13]). "T2 intermediate" may be a VRF-specific computed value or a
third physical sensor not present on consumer split units.

**EEV position**: The expansion valve opening (check #16, "actual opening/8") is
**not exposed in XYE C0/C3 or C4/C6 responses** — it is only available via the
R/T serial bus C1 Group 3 response body[11] (see serial_protocol.md §4.2.3).
The `×8` encoding in the VRF manual matches the community protocol research analysis
(`raw × 8 = steps`; see community protocol research). Cross-validated
in own captures: 648 C1-G3 frames across
Sessions 3–13 show EEV range 0–496 steps, with physically plausible behavior
(valve opens wider when compressor runs, closes at idle). See
`data-analysis/midea/xye/analyze_eev_position.py` for the full analysis.

---

## Appendix A — Cross-Source Consistency

### A.1 Confirmed Matches (all sources agree)

| Field | Encoding | Sources |
|-------|----------|---------|
| Preamble | 0xAA | All |
| Epilogue | 0x55 | All |
| Checksum | Twos complement (algebraically equivalent forms) | CB-erl, ESPHome, own |
| Mode one-hot | bit7=power, bit0=fan, bit1=dry, bit2=heat, bit3=cool, bit4=auto | All (except CB-readme Auto=0x80) |
| Fan Auto | 0x80 | All |
| Fan High | 0x01 | All |
| Fan Medium | 0x02 | All |
| Temperature sensor formula | (raw − 40) / 2 = °C | CB-erl + own S04/S06 |
| C6 Follow-Me temp | byte[11] = direct °C | ESPHome + own + mdrobnak |
| C6 START/UPDATE/STOP | Lower nibble 0x06/0x02/0x04 | All (variant bit differs) |

### A.2 Conflicts and Resolutions

| Field | CB-readme | CB-erl | ESPHome | Own captures | Resolution |
|-------|-----------|--------|---------|-------------|------------|
| Fan Low | 0x03 | 0x04 | 0x03 / 0x04 | **0x04** (S07) | 0x04 correct. **Confirmed**. |
| Auto mode | 0x80 | 0x80 | 0x90 | **0x90** (S07) | 0x90 correct. **Confirmed**. |
| Temp sensor offset | 48 (0x30) | 40 (0x28) | none (raw °F) | 40 (0x28, S06 service menu) | Offset 40 correct. **Confirmed**. |
| byte[4] FLAGS | 0x80 | 0x80 | 0x80/0x00 mixed | **0x00** (11,432 frames) | 0x00 correct. **Corrected**. |
| byte[2] DIR_FLAG | 0x80 | — | validates 0x80 | **0x00** (8,129 frames) | 0x00 correct. **Corrected**. |
| CRC at byte | 0x0E (13) | 0x1E (30) | 0x1E | **0x1E** (30) | byte[30] for 32B frames. **Confirmed**. |
| C0 response byte[27] (L1) | 0x00 | "L1" field | — | **0xFF** (Q11), **0x14** (mdrobnak) | HW-variant. **Disputed**. |
| Setpoint encoding | direct °C integer | — | raw °F | **(raw & 0x7F) − 0x40** (S07+S10) | Dual C/F with offset. **Confirmed**. |

---

## Appendix B — Open Questions

| ID | Topic | Section | Status | Notes |
|----|-------|---------|--------|-------|
| OQ-01 | byte[9] value 0x08 (fan) | §6.1, §8.2 | Unknown | 110 frames, no source documents this fan speed |
| OQ-02 | byte[19] RUN_STATUS bit position | §8.7 | Disputed | Q11 uses bit 5 (0x20), CH-36AHU uses bit 0 (0x01) |
| OQ-03 | byte[21] OP_FLAGS bit 3 | §8.7, §9.4 | **Consistent S11** | Window contact / CP protection flag — set on dry contact open, cleared on close |
| OQ-04 | D0 byte[16] ~~outdoor~~ indoor temp | §6.4 | **Confirmed** | Indoor T1 in direct °C. Cross-validated vs XYE T1 + R/T indoor (4,175 frames). Outdoor hypothesis falsified (mean |Δ|=19.8°C vs T4). |
| OQ-05 | D0 byte[18] UNKNOWN_A | §6.4 | Unknown | Stable within session, varies across — possibly compressor state? |
| OQ-06 | D0 byte[19] UNKNOWN_B | §6.4 | Unknown | 25 distinct values, highly variable |
| OQ-07 | D0 byte[29] inner CRC | §6.4 | Hypothesis | 85 distinct values, algorithm unknown |
| OQ-08 | C4 bytes[6–7] magic 0xA5/0x5A | §5.3 | Hypothesis | HAHB only, purpose unknown |
| OQ-09 | bytes[6–7] CAPABILITIES swap | §6.1 | Disputed | Q11: (0x10, 0x30), mdrobnak: (0x30, 0x14) |
| OQ-10 | C4 EXT_STATUS byte[15] bit 0x08 | §6.2 | Unknown | 266 frames in S11–S12, no source documents this |
| OQ-11 | KJR-120X cold boot behavior | §7.3 | Hypothesis | No cold boot capture available |
| OQ-12 | Emergency heat protocol | §9.5 | Hypothesis | mdrobnak single source, 1 frame |
| OQ-13 | Static pressure protocol | §9.6 | Hypothesis | rymo single source, 5 frames |
| OQ-14 | Lock/Unlock payload | §5.5/5.6, §9.7 | Hypothesis | CB-erl only, never captured |
| OQ-15 | Setpoint encoding variant (mdrobnak) | §8.3 | Disputed | mdrobnak suggests direct °F, own S10 shows offset 7 |
| OQ-16 | NV mode label for 0x01/0x81 | §7.1 | Disputed | S09 SessionNotes label 0x81 as "Dry" but §8.1 maps 0x81 (bit 0) to Fan. Raw value 0x01 at boot / 0x81 after power-on. Correct mode name needs verification. |

---

## Appendix C — Planned Experiments

- [x] **Change XYE unit address** — Done (S10–S13, MFB-X switch position 5).
- [x] **Fahrenheit mode test** — Done (S10, dual C/F encoding confirmed).
- [ ] **KJR-120X cold boot capture** — power-cycle with dongle recording.
- [ ] **Lock/Unlock (CC/CD)** — exercise via codeberg emulator or manual command.
- [ ] **Trigger error condition** — induce fault to validate error bitmask fields.
- [ ] **MFB-C relay toggle** — determine relay control command on XYE bus.
- [ ] **MFB-X relay toggle** — same test on HAHB variant.
- [x] **D0 byte[16] identification** — Resolved: indoor T1 in direct °C (cross-bus validated, outdoor hypothesis falsified).

---

## References

- XYE protocol research: https://codeberg.org/xye/xye
- ESPHome XYE implementation: https://github.com/wtahler/esphome-mideaXYE-rs485
- HA Community XYE thread: https://community.home-assistant.io/t/midea-a-c-via-local-xye/857679
- Discoveries from community protocol research (community protocol research)
- georgezhao2010/midea_ac_lan — device type definitions
- Midea Serial Protocol reference: [serial_protocol.md](serial_protocol.md)
- Shared protocol elements: [protocol_shared.md](protocol_shared.md)
