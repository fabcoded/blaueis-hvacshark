# Analysis: 0x93 Extension Board R/T Frame — Cross-Session

> **Confidence**: body[1] and body[3] interpretations are **Consistent** (logic
> analyzer Sessions 1, 3, 4, 9, 10, 11). Window contact (CP) findings based on
> Session 11 only (two complete open/close cycles). Cold boot sequence from
> Session 9 (one capture with full intermediate states).

## Overview

The 0x93 frame is the extension board (bus adapter) status exchange on the R/T
bus. It carries the operational state of the MFB-X/MFB-C adapter board, including
window contact state and power/boot status. The frame is exchanged between the
bus adapter and the display board approximately every 5.5 seconds as part of the
R/T polling cycle.

This analysis covers 6 sessions with R/T captures: Sessions 1, 3, 4, 9, 10, 11.

## Frame structure

### 0x93 Request (bus adapter → display, 38 bytes)

```
R/T Header (11 bytes): AA BC 22 AC 00000000 00 PP QQ
  PP = Protocol Version (02 or 03)
  QQ = Message Type (02=Command, 03=Response/Notification)

Body (23 bytes):
  [0]  0x93     Command ID (fixed)
  [1]  flags    Bus adapter state flags (see below)
  [2]  0x80     Fixed (all sessions)
  [3]  status   Operational state (see below)
  [4]  FM       0x00 or 0x05 — Follow Me indicator (see below)
  [5..20]       0x00 (zero in all observed requests)
  [21]          Varies — possible FM temp or operational (only non-zero in S1)
  [22]          MSG_ID — incrementing message counter

Trailer: CRC8, Checksum, Padding(0x00), FrameCheck
```

### 0x93 Response (display → bus adapter, 44 bytes)

```
R/T Header (11 bytes): 55 BC 28 AC 00000000 00 PP QQ

Body (30 bytes):
  [0]  0x93     Command ID (fixed)
  [1]  flags    Echo of request body[1] (0x00 or 0x20)
  [2]  0x00     Fixed (all sessions)
  [3]  status   Operational state echo (see below)
  [4..8]        0x00 (zero in all sessions)
  [9..28]       Operational data (temperatures, zone status — see serial_protocol.md §4.4)

Trailer: Checksum, Padding(0x00), End Marker(0xEF)
```

## body[1] — bus adapter state flags

| Bit | Mask | Meaning | Evidence |
|-----|------|---------|----------|
| bit 7 | 0x80 | Periodic alternating flag | All sessions: toggles every ~3 polling cycles. Purpose unclear — possibly a handshake keep-alive or polling variant selector |
| bit 5 | 0x20 | Window contact open | S11 only: set when MFB-X dry contact opens, cleared when closes. The initial trigger frame has both bit 7 + bit 5 (0xA0) |
| bits 6,4,3,2,1,0 | | Not observed set | All sessions: always 0 |

### body[1] values observed across sessions

| Value | Binary   | Sessions | Context |
|-------|----------|----------|---------|
| 0x00  | 00000000 | All      | Normal polling |
| 0x80  | 10000000 | All      | Periodic alternate (~every 3rd cycle) |
| 0x20  | 00100000 | S11      | Window contact open (persistent state) |
| 0xA0  | 10100000 | S11      | Window contact initial trigger (one frame per event) |

### body[1] in response

The response echoes body[1] but only the window contact bit:
- Request 0x00 → Response 0x00
- Request 0x80 → Response 0x00 (bit 7 NOT echoed)
- Request 0x20 → Response 0x20 (bit 5 echoed)
- Request 0xA0 → Response 0x20 (only bit 5 echoed)

## body[3] — operational state

### State values observed

| Value | Binary   | Sessions | Context |
|-------|----------|----------|---------|
| 0x00  | 00000000 | S4,S9,S11 | OFF (power off, shutdown complete) |
| 0x01  | 00000001 | S9       | Cold boot pre-handshake (unit off, bus adapter initializing) |
| 0x04  | 00000100 | S1,S4,S11 | Protection / standby (CP trigger, or initial cold boot state) |
| 0x80  | 10000000 | S11      | Recovery (contact closed, restarting — intermediate state) |
| 0x81  | 10000001 | S9       | Cold boot stage 1 (power on, initializing) |
| 0x82  | 10000010 | S9       | Cold boot stage 3 (late initialization) |
| 0x84  | 10000100 | All      | Normal running |
| 0x90  | 10010000 | S1,S9    | Boot intermediate / mode change (S9 cold boot stage 2; S1 during mode transition) |
| 0x91  | 10010001 | S9       | Cold boot stage 2 (response only — request shows 0x90) |

### Bit-level decomposition (Hypothesis)

```
bit 7 = power ON / starting
bit 4 = intermediate boot flag (cold boot transitions only)
bit 2 = operational ready (compressor/heat system active)
bit 1 = late initialization flag (cold boot stage 3)
bit 0 = early initialization flag (cold boot stages 1-2)

Special: 0x04 (bit 2 alone, without bit 7) = protection state
         (unit is being forced off, not a voluntary power-off)
```

### State machine — cold boot (Session 9)

```
              0x00 (OFF)
                |  power applied
                v
              0x01 (pre-handshake, ~2.5s)
                |  bus adapter handshake
                v
              0x81 (boot stage 1, ~3s)
                |
                v
              0x91 (boot stage 2, ~3s)
                |
                v
              0x82 (boot stage 3, ~1.5s)
                |
                v
              0x84 (RUNNING)
```

Total cold boot time: ~13 seconds (0x00 → 0x84).
Session 4 shows only 0x00 → 0x84 (23s gap — intermediate states missed due to
polling timing).

### State machine — normal power on/off (Session 11)

```
   0x84 (RUNNING) ←→ 0x04 (standby) ←→ 0x00 (OFF)
                       ↑                    ↑
                  app/ctrl OFF          power cut
                       |
                  0x84 (direct, no intermediate boot stages)
```

Normal power on: 0x00 → 0x84 directly (no 0x80/0x81/0x82 intermediate stages).

### State machine — window contact CP (Session 11)

```
   0x84 (RUNNING)
     |  contact opens → body[1]=0xA0 trigger
     v
   0x04 (CP PROTECTION)     body[1]=0x20 persistent
     |  ~2s
     v
   0x00 (SHUTDOWN)          body[1]=0x20 persistent
     |  contact closes → body[1]=0x80
     v
   0x80 (RECOVERY)          body[1]=0x00
     |  ~1.5s
     v
   0x84 (RUNNING)           body[1]=0x00
```

CP recovery uses 0x80 as intermediate (not seen in normal power-on).

## body[4] — Follow Me indicator (Hypothesis)

| Value | Sessions | Follow Me state during session |
|-------|----------|-------------------------------|
| 0x00  | S1, S3, S4, S9 | FM not active |
| 0x05  | S10, S11 | FM was active (or recently active) |

Sessions 10 and 11 had Follow Me enabled via the KJR-120M wall controller.
The 0x05 value persists even after FM is disabled mid-session (S11), suggesting
it may indicate FM *capability* rather than current state.

## msg_type field

The R/T header msg_type is normally 0x03 (Response/Notification) for both
request and response. It switches to **0x02 (Command)** in specific cases:

| msg_type | Context | Sessions |
|----------|---------|----------|
| 0x03     | Normal polling | All |
| 0x02     | Active trigger: window contact open, Follow Me write | S1, S3, S4, S9, S10, S11 |

The 0x02 msg_type appears when the bus adapter is actively sending a state
change notification (not just polling). In Session 1, msg_type=0x02 appears
periodically even without window contact — possibly triggered by Follow Me
temperature updates or other adapter-initiated events.

## Cross-bus correlation

When the window contact opens, the signal propagates:

| Bus | Frame | Field | Normal | CP triggered | Delay |
|-----|-------|-------|--------|-------------|-------|
| R/T 0x93 req | body[1] | 0x00 | 0xA0 then 0x20 | 0.0s (origin) |
| R/T 0x93 rsp | body[3] | 0x84 | 0x04 then 0x00 | +0.2s |
| R/T 0xC0 | body[1] bit 0 (Power) | ON | OFF | +0.7s |
| R/T 0xC0 | body[16] (Error Code) | none | **none** (not carried!) | — |
| XYE C0 | byte[21] bit 3 | 0x00 | 0x08 | +0.9s |
| XYE C0 | byte[8] (mode) | 0x84 | 0x00 | +2.7s |
| XYE D0 | — | — | **unchanged** | — |
| disp-mb 0x20 | byte[9] bit 6 | set | cleared | +1-2s |
| disp-mb 0x30 | frame | 64-byte operational | 10-byte short (`AA300A00FF03...`) | +1-2s |

## Previous documentation status

`serial_protocol.md` OQ-09: "Extension board 0x93 field meanings — Unknown. All
payload fields unidentified." This analysis partially resolves OQ-09: body[1]
(flags), body[3] (operational state), and body[4] (FM indicator) are now
identified. The remaining body[5..20] payload in requests and body[4..28]
operational data in responses still need analysis.

## Data sources

- Session 1: R/T captures, normal operation + Follow Me (83 seconds)
- Session 3: R/T + HAHB, normal operation + Follow Me
- Session 4: Cold boot capture (power-on from off state)
- Session 9: Cold boot capture (full intermediate state sequence)
- Session 10: C/F switching, Follow Me active — 0x93 body[4]=0x05
- Session 11: Turbo, power on/off, window contact CP, Follow Me — 0x93 body[4]=0x05
