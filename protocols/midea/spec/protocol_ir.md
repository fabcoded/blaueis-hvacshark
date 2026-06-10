# Midea IR Protocol Reference

> **Source Status — Own Hardware Observations + Community Cross-Reference (Partial)**
>
> Primary source: own hardware captures from the `blaueis-hvacshark-traces` repository
> (Midea extremeSaveBlue display board, Session 2 logic-analyser captures).
> Cross-referenced against `IRremoteESP8266` (crankyoldgit) and `ESPHome` midea component.
>
> **This is a best-effort analysis.** Field encodings are inferred from a limited
> capture set (one session, one mode, one fan speed). Discrepancies between sources
> are explicitly noted. A field is only considered confirmed when independently
> verified on hardware with known input values. Everything else is a hypothesis.
>
> Confidence levels: **Confirmed** = multiple data points + source agreement.
> **Consistent** = own data + at least one source agree. **Hypothesis** = own data
> only, no source conflict. **Disputed** = sources disagree or finding contradicts
> own data. **Unknown** = insufficient data.

---

## 1. Protocol Variants — At Least Three Midea IR Families

> **Future file split**: When documentation grows further, each variant should be
> split into its own file (e.g. `protocol_ir_nec_xsb.md`, `protocol_ir_nec_bgh.md`,
> `protocol_ir_wholeframe.md`). Currently all are documented in this single file.

Research across own captures and community sources reveals **at least three distinct
Midea IR protocol families** that share the same physical timing layer (38 kHz,
NEC-like pulse-width encoding) but differ in frame structure and data encoding:

### Variant A: Per-byte complement, extremeSaveBlue NEC (this capture)

- **Hardware**: Midea extremeSaveBlue (XtremeSave Blue) standard IR remote
- **Frame**: 48 bits = 6 bytes, per-byte complement pairs
- **Data bytes**: byte[0]=device ID (0xB2/0xB9/0xD5), byte[2]=fan+state, byte[4]=temp+mode
- **Temperature**: 3-bit field `bits[7:5] + 20` (range 20-27 C, confirmed S2/S10/S12)
- **Mode**: 4-bit field `bits[3:0]`: 0x0=Cool, 0x4=Fan, 0x8=Auto, 0xC=Heat — **Confirmed** (cross-session S2-S13, matches sheinz encoding)
- **D5 follow-up frame**: Sent after B2 control pairs; carries C/F flag (byte[3] bit 0)
- **Bit ordering**: Our decoder stores first-received bit as MSB (see §2a)
- **Sources**: Own captures (Sessions 2, 10, 11, 12, 13)

### Variant B: Per-byte complement, BGH Silent Air NEC (Balbablog)

- **Hardware**: BGH Silent Air (Midea OEM for Argentina market)
- **Frame**: 48 bits = 6 bytes, per-byte complement pairs (identical framing to Variant A)
- **Data bytes**: Same byte[0]=0xB2 device ID, but byte[2] and byte[4] use DIFFERENT encoding
- **Temperature**: 4-bit **reflected Gray code** in byte[4] bits[3:0] (LSB-first wire order), range 17-30 C
- **Mode**: 2-bit field in byte[4] bits[5:4] (LSB-first): 00=Cool, 01=Dry/Fan, 10=Auto, 11=Heat
- **Additional features**: Macros (ECO, Turbo, Self Clean, LED), Sleep (3-frame), Follow Me (binary temp, not Gray code), Timers, Swing toggle, Power OFF pseudo-macro
- **No D5 follow-up frame**: Frame 2 is a mirror of Frame 1 (except Sleep mode)
- **Sources**: alexisbalbachan/blog (2026), sheinz/esp-midea-ir

### Variant C: Whole-frame complement with checksum (IRremoteESP8266 / ESPHome)

- **Hardware**: Pioneer, Comfee, Kaysun, Keystone, MrCool, Danby, Trotec, Lennox, Insignia
- **Frame**: 48 bits data, then entire 48-bit frame repeated inverted = 96 bits on wire
- **Data bytes**: byte[5]=header+type (0xA1/0xA2/0xA4), byte[4]=power+sleep+fan+mode, byte[3]=temp+Fahrenheit flag, byte[0]=checksum
- **Temperature**: 5-bit linear, Celsius offset 17 (range 17-30 C), Fahrenheit offset 62
- **Mode**: 3-bit: 0=Cool, 1=Dry, 2=Auto, 3=Heat, 4=Fan
- **Fahrenheit**: Dedicated flag (byte[3] bit 5)
- **Additional features**: Toggle commands (0xA2 type: swing, ECO, turbo, light, quiet), Follow Me (0xA4 type with sensor temp)
- **Checksum**: Bit-reverse each byte, sum, negate, bit-reverse result
- **Sources**: crankyoldgit/IRremoteESP8266, ESPHome, andrewmv/ac-control-stuff

### Cross-variant comparison

| Property | Variant A (XSB) | Variant B (BGH) | Variant C (IRremoteESP8266) |
|----------|-----------------|-----------------|----------------------------|
| Complement | Per-byte | Per-byte | Whole-frame |
| Temp bits | 3 (bits[7:5]) | 4 (Gray code) | 5 (linear) |
| Temp range | 20-27 C | 17-30 C | 17-30 C (+ Fahrenheit) |
| Mode encoding | 4-bit: 0/4/8/C | 2-bit: 0/1/2/3 | 3-bit: 0/1/2/3/4 |
| Follow-up | D5 frame | No (frame mirror) | No (frame inversion) |
| Fahrenheit | D5 byte[3] bit 0 | Not documented | byte[3] bit 5 |
| Checksum | Per-byte ~complement | Per-byte ~complement | Computed checksum |

**Important**: Variants A and B share the same physical framing (per-byte complement,
byte[0]=0xB2) but use DIFFERENT data encodings. They are NOT interchangeable.
The mode lower-nibble values in Variant A (0x0/0x4/0x8/0xC) superficially look like
Variant B's mode values left-shifted by 2 bits, but the temperature encoding is
completely different (3-bit linear vs 4-bit Gray code).

### Bit ordering note (§2a) {#bit-ordering}

Our pcap converter (`decoder_midea_ir.py`) packs received bits MSB-first:
`val = (val << 1) | bits[b + k]`, where `bits[0]` is the first received bit.
Since NEC transmits LSB-first, our stored byte values are **bit-reversed** compared
to standard NEC byte representation. When comparing against sources that use
standard NEC byte order (like sheinz or Balbablog), each nibble must be bit-reversed.

This does NOT affect our field formulas (`bits[7:5]+20` for temperature, `bits[3:0]`
for mode) — those are defined in terms of our stored byte representation and are
validated directly against operator notes.

---

## 2. Physical Layer

| Property          | Value                                                      | Confidence  |
|-------------------|------------------------------------------------------------|-------------|
| Modulation        | 38 kHz carrier (standard IR), not captured — TSOP receiver used | Confirmed |
| Receiver output   | Active-low (signal inverted by TSOP demodulator)           | Confirmed   |
| Encoding          | NEC-like pulse-width modulation                            | Confirmed   |

### Pulse timings

Measured from Session 2 captures and cross-verified against IRremoteESP8266
`kMideaTick = 80 us` (crankyoldgit/IRremoteESP8266, `ir_Midea.cpp` line 22):

| Symbol    | Formula (IRremoteESP8266)     | Calculated | Measured (Session 2) | Match  |
|-----------|-------------------------------|------------|----------------------|--------|
| Bit mark  | 7 ticks × 80 us               | 560 us     | ~0.56 ms             | ✓      |
| 1-space   | 21 ticks × 80 us              | 1680 us    | ~1.6 ms              | ✓      |
| 0-space   | 7 ticks × 80 us               | 560 us     | ~0.56 ms             | ✓      |
| Header mark | 56 ticks × 80 us            | 4480 us    | ~4.4 ms              | ✓      |
| Header space | 56 ticks × 80 us           | 4480 us    | ~4.4 ms              | ✓      |

The physical timing layer is **confirmed identical** across both protocol variants.
The difference is entirely in the data/frame structure layer.

---

## 3. Frame Structure (extremeSaveBlue NEC variant)

Each frame is **48 bits = 6 bytes**, transmitted MSB-first within each byte.

### Complement integrity check

Bytes are transmitted as NEC-style complement pairs:

| Pair | Bytes            | Relation                  |
|------|------------------|---------------------------|
| 1    | byte[0], byte[1] | byte[0] ^ byte[1] = 0xFF  |
| 2    | byte[2], byte[3] | byte[2] ^ byte[3] = 0xFF  |
| 3    | byte[4], byte[5] | byte[4] ^ byte[5] = 0xFF  |

Exception: the `0xD5` follow-up frame has a non-standard complement pair (see
section 5.3). This is likely intentional to distinguish it from AC control frames.

> **Disputed vs IRremoteESP8266**: In the IRremoteESP8266 MIDEA format, the
> complement is applied to the entire 6-byte frame (whole-frame inversion and repeat),
> not per-byte. The per-byte complement in our captures is a characteristic of the
> NEC variant used by the extremeSaveBlue remote, not of Midea IR in general.

### Button press repetition

A single button press transmits **2–3 frames** separated by ~92 ms gaps:

| Frame type          | Repetition pattern                                     |
|---------------------|--------------------------------------------------------|
| B2 AC control       | 2 identical frames + 1 `0xD5` follow-up frame         |
| B9 setup/installer  | 2 identical frames (no follow-up)                      |

---

## 4. Device IDs (byte[0])

| byte[0] | Complement byte[1] | Frame type          | Confidence |
|---------|--------------------|---------------------|------------|
| `0xB2`  | `0x4D`             | AC control command  | Confirmed  |
| `0xB9`  | `0x46`             | Setup / installer / programming | Confirmed (observed) |
| `0xD5`  | `0x66` (non-standard) | Follow-up / termination | Confirmed (observed) |

These device IDs are specific to the extremeSaveBlue NEC variant. The IRremoteESP8266
MIDEA format does not use device-ID-based addressing — it uses a Header+Type field
in a different byte position. The mapping between the two is unknown.

---

## 5. Frame Types

### 5.1 `0xB2` — AC Control Command

```
Byte  Content           Known encoding
----  -------           --------------
  0   Device ID         0xB2  (fixed)
  1   Complement        0x4D  (= ~0xB2 & 0xFF)
  2   Mode/power/fan    Encodes power, mode, and fan. Varies across sessions:
                        0xBF (S2/10/12: Heat+ON), 0xFF (S13: Auto+ON),
                        0x1F (S13: unknown), 0x7B (S13: Power OFF).
                        bit[7]    = Power (1=ON): consistent (S13: 0x7B has bit7=0, causes OFF)
                        bits[6:4] = Mode: 011=Heat, 111=Auto. Consistent with IRremoteESP8266.
                        bits[3:0] = Fan + state flags. 1111=Auto+ON, 1011=OFF (S13 0x7B).
  3   Complement        ~byte[2] & 0xFF
  4   Temp/mode byte    bits[7:5] = temperature encoding (confirmed, 21-26 C across S2/S12)
                        bit[4]    = toggle/parity bit (alternates between consecutive presses)
                        bits[3:0] = mode: 0x0=Cool, 0x4=Fan, 0x8=Auto, 0xC=Heat (confirmed S2-S13)
  5   Complement        ~byte[4] & 0xFF
```

#### Temperature encoding (byte[4] bits[7:5])

```
temp_c = bits[7:5] + 20
```

Confirmed data points from Sessions 2 and 12:

| byte[4] | bits[7:5] | Decoded  | Session | Operator action           |
|---------|-----------|----------|---------|---------------------------|
| `0x20`  | 1         | 21 deg C | S12     | "21 grad via fernbedienung" |
| `0x5C`  | 2         | 22 deg C | S2      | Initial state             |
| `0x50`  | 2         | 22 deg C | S12     | "use ir to set 22deg c"   |
| `0x60`  | 3         | 23 deg C | S12     | auto swing press          |
| `0x9C`  | 4         | 24 deg C | S2      | Stepped down              |
| `0xCC`  | 6         | 26 deg C | S2      | Stepped up twice          |

Confirmed range: 21–26 deg C (values 1–6). Value 0 (20 deg C) has not been
observed. Value 7 (27 deg C) appears in S13 frames (byte[4]=0xE4/0xE0 on
mode-switch/power presses) but with no operator ground truth for the setpoint,
so it remains unconfirmed.

> **Potential discrepancy vs IRremoteESP8266**: IRremoteESP8266 documents a temperature
> range of 17–30 deg C (with 5-bit field, `Temp:5`, offset 17). Our 3-bit field
> (bits[7:5]+20) covers only 20–27 deg C.
> **[NEEDS CAPTURE: set 20 deg C and 27 deg C on extremeSaveBlue remote]**

#### byte[2] mode / power / fan encoding

Session 13 revealed that byte[2] is NOT constant — it carries mode, power,
and fan state. Four distinct values observed across S2-S13:

| byte[2] | binary     | bit[7] | bits[6:4] | bits[3:0] | Sessions | XYE result      |
|---------|------------|--------|-----------|-----------|----------|-----------------|
| `0xBF`  | 1011 1111  | 1 (ON) | 011 (Heat)| 1111      | S2/10/12 | Heat mode, ON   |
| `0xFF`  | 1111 1111  | 1 (ON) | 111 (Auto)| 1111      | S13      | Auto mode, ON   |
| `0x1F`  | 0001 1111  | 0      | 001       | 1111      | S13      | No mode change  |
| `0x7B`  | 0111 1011  | 0      | 111       | 1011      | S13      | Power OFF       |

Bit-level layout:

| Bits     | Encoding                                      | Confidence  |
|----------|-----------------------------------------------|-------------|
| bit[7]   | Power (1=ON, 0=OFF)                           | Consistent  |
| bits[6:4]| Mode: 011=Heat, 111=Auto. Cool/Dry/Fan TBD.  | Consistent  |
| bits[3:0]| Fan + flags: 1111=Auto+ON, 1011 in OFF frame | Hypothesis  |

> **Note on 0x1F**: At t=129 in S13, byte[2]=0x1F (bit7=0) did NOT cause
> power-off — the unit stayed in Auto mode. Only 0x7B at t=133 triggered
> power-off. The meaning of 0x1F is unclear; it may be a mode query or a
> button press that the AC ignored.
>
> **Source conflict on fan speed**: IRremoteESP8266 encodes Auto fan as `0b00`,
> not `0b11`. Either the extremeSaveBlue variant uses different fan encoding,
> or bits[3:0] encode something other than pure fan speed.

#### byte[4] bit[4] — toggle / parity bit — **Consistent**

Bit 4 alternates between consecutive IR presses at the same temperature.
Session 12 provides the clearest evidence:

| t (s) | byte[4] | bits[7:5] | bit 4 | Context                    |
|-------|---------|-----------|-------|----------------------------|
| 331   | `0x50`  | 2 (22 C)  | 1     | First IR press at 22 C     |
| 449   | `0x20`  | 1 (21 C)  | 0     | Set 21 C                   |
| 451   | `0x30`  | 1 (21 C)  | 1     | Same temp, bit4 toggled    |
| 457   | `0x20`  | 1 (21 C)  | 0     | Same temp, bit4 toggled back |

This pattern is consistent across Sessions 2, 10, and 12. The bit likely
lets the display board distinguish a repeated identical command from a
held button — a **toggle/parity bit**, not a swing state.

> **Swing ruled out**: IRremoteESP8266 implements vertical swing as a
> separate Special-type frame (`0xA201FFFFFF7C`), not a state bit. S12
> confirms the bit toggles without any swing action.

---

### 5.2 `0xB9` — Setup / Installer / Programming Command

```
Byte  Content           Known encoding
----  -------           --------------
  0   Device ID         0xB9  (fixed)
  1   Complement        0x46  (= ~0xB9 & 0xFF)
  2   Function ID       0xF7 = installer/setter mode (only value observed)
  3   Complement        0x08  (= ~0xF7 & 0xFF)
  4   Parameter         Service menu page index (see table below)
                        0xFF      = exit service menu
  5   Complement        ~byte[4] & 0xFF
```

Not present in IRremoteESP8266's MIDEA protocol. Specific to this remote variant.

#### B9 parameter index — service menu sensor mapping — **Confirmed** (logic analyzer Session 11)

Session 11 captured 8 B9 frames stepping through the service menu while R/T 0xC1
Group 1 was simultaneously recording sensor values. Time-aligned cross-check confirms:

| byte[4] | Menu label | R/T Group 1 field | Match |
|---------|-----------|-------------------|-------|
| 0x01    | T1        | body[10] T1 indoor coil, (raw-30)/2 | exact (24 C) |
| 0x02    | T2        | body[11] T2 heat exchanger, (raw-30)/2 | +/-0.5 (drift) |
| 0x03    | T3        | body[12] T3 outdoor coil, (raw-50)/2 | display rounds |
| 0x04    | T4        | body[13] T4 outdoor ambient, (raw-50)/2 | display rounds |
| 0x05    | Tp        | body[14] Tp discharge, raw C | exact (28 C) |
| 0x06    | FT        | body[5] FT target freq (indoor target freq), raw Hz | exact (27 Hz) |
| 0x07    | FR        | body[4] FR running freq (compressor freq), raw Hz | exact (26 Hz) |
| 0xFF    | (exit)    | — | — |

Session 2 previously observed parameters 0x00-0x08 without identifying meanings.
Parameters 0x00 and 0x08 (observed in Session 2) are not yet mapped.

---

### 5.3 `0xD5` — Follow-up / Termination Frame

```
Byte  Content           Known encoding
----  -------           --------------
  0   Device ID         0xD5  (fixed)
  1   Variable pair     0x66 (S2/10/12), 0x14, 0x65 (S13). NOT a fixed complement.
                        May depend on the preceding B2 byte[2] value.
  2   Flags             0x00 normal; 0x20 observed once (see below)
  3   Unit flag         bit 0: Temperature unit (0=Celsius, 1=Fahrenheit) — Consistent (logic analyzer Session 10)
  4   (reserved?)       0x00 in all observations
  5   Checksum?         varies with payload (0x3B, 0x3C, 0x5C, 0xE9, 0x3A observed)
```

Always transmitted immediately after each B2 AC control frame pair. Not observed
after B9 frames. Not present in IRremoteESP8266's MIDEA protocol.

Session 13 revealed that byte[1] is NOT fixed — it varies depending on the
preceding B2 command:

| D5 raw           | byte[1] | Preceding B2 byte[2] | Sessions    |
|------------------|---------|----------------------|-------------|
| `D5660000003B`   | `0x66`  | `0xBF` (Heat+ON)     | S2/10/12    |
| `D514000000E9`   | `0x14`  | `0xFF` (Auto+ON)     | S13         |
| `D5650000003A`   | `0x65`  | `0x1F` (unknown)     | S13         |

The non-standard complement (not `~0xD5`) is likely intentional to distinguish
D5 frames from B2 control frames. The variation with mode suggests byte[1]
carries mode or state context from the preceding command.

#### D5 byte[3] — C/F unit flag — **Consistent** (indirect, logic analyzer Session 10)

Logic analyzer Session 10 captured 6 D5 frames during C/F switching experiments.
D5 byte[3] correlates with the IR remote's display unit setting:

| Grp | Time (s) | D5 raw         | byte[3] | Remote unit | Downstream effect |
|-----|----------|----------------|---------|-------------|-------------------|
| 1   | 178.1    | D5660000003B   | 0x00    | Celsius     | AC switches F→C, setpoint 24°C |
| 2   | 582.5    | D5660001003C   | 0x01    | Fahrenheit  | AC switches C→F, setpoint 79°F (26°C) |
| 3   | 609.8    | D566**20**01005C | 0x01  | Fahrenheit  | AC decrements to 78°F (25.5°C) |
| 4   | 619.4    | D5660001003C   | 0x01    | Fahrenheit  | AC decrements to 77°F (25.0°C) |
| 5   | 664.7    | D5660000003B   | 0x00    | Celsius     | AC switches F→C, setpoint 24°C |
| 6   | 673.4    | D5660000003B   | 0x00    | Celsius     | AC increments to 25°C |

The C/F unit flag is carried in the **D5 follow-up frame, not the B2 control frame**.
The B2 frame carries the temperature command; the D5 frame carries the unit context.
The AC display board uses both frames together to determine the final action.

#### D5 byte[2] — flags

Byte[2] = 0x20 was observed exactly once (Grp 3, the first temperature press after
switching the remote to Fahrenheit). All other frames have byte[2] = 0x00. The 0x20
may signal a swing toggle or a "first press after mode switch" marker. **Hypothesis** —
needs more data points.

#### D5 byte[5] — probable checksum

Byte[5] varies with the payload: 0x3B when bytes[2:4]=`000000`, 0x3C when
`000100`, 0x5C when `200100`. The relationship appears to be additive but the
exact formula is not yet confirmed.

---

## 6. Known Field Summary (confidence table)

| Field              | Byte  | Bits  | Encoding                                     | Confidence  | Source conflict?                              |
|--------------------|-------|-------|----------------------------------------------|-------------|-----------------------------------------------|
| Device type        | 0     | [7:0] | 0xB2=AC, 0xB9=Setup, 0xD5=Follow-up         | Confirmed   | Not in IRremoteESP8266 (different variant)    |
| Complement pairs   | 1,3,5 | [7:0] | ~byte[n-1] & 0xFF (except 0xD5 pair)        | Confirmed   | IRremoteESP8266 uses whole-frame inversion    |
| Temperature        | 4     | [7:5] | bits + 20 = deg C (21-26 C confirmed S2/S12) | **Confirmed** | Variant A only. Balbablog/sheinz Gray code is Variant B (different encoding) |
| Mode (byte[4])     | 4     | [3:0] | 0x0=Cool, 0x4=Fan, 0x8=Auto, 0xC=Heat      | **Confirmed** | S2/10/12/13: matches sheinz. Balbablog uses 2-bit (different variant) |
| Toggle bit         | 4     | [4]   | Alternates between consecutive presses        | Consistent  | S12: toggles 0/1 at same temp. Not swing.     |
| Fan+State (byte[2])| 2     | [7:0] | Upper nibble=fan, lower nibble=state          | Hypothesis  | Only 0xBF (Auto+ON) confirmed; S13 shows 0xFF/0x1F/0x7B for mode/power changes |
| Fan speed          | 2     | [7:4] | 0xB=Auto (confirmed S2-12); others TBD       | Consistent  | sheinz: 0xB=Auto, 0x9=Low, 0x5=Med, 0x3=High |
| Power state        | 2     | [3:0] | 0xF=ON, 0xB=OFF (sheinz)                    | Hypothesis  | S13: 0x7B has lower=0xB, causes power-off     |
| B9 function ID     | 2     | [7:0] | 0xF7 = installer/setter mode                 | Observed    | Not in IRremoteESP8266                        |
| B9 parameter       | 4     | [7:0] | Index 0x00-0x08; 0xFF = settermode query    | Observed    | Not in IRremoteESP8266                        |
| D5 flags           | 2     | [7:0] | 0x00 normal, 0x20 observed once             | Hypothesis  | Not in IRremoteESP8266                        |
| D5 unit flag (C/F) | 3     | bit 0 | 0=Celsius, 1=Fahrenheit                     | Consistent  | Not in IRremoteESP8266 (logic analyzer S10)   |
| D5 reserved        | 4     | [7:0] | 0x00 in all observations                    | Observed    | Not in IRremoteESP8266                        |
| D5 checksum?       | 5     | [7:0] | Varies with payload (0x3B, 0x3C, 0x5C)      | Hypothesis  | Not in IRremoteESP8266                        |

---

## 7. Open Questions

### 7.1 byte[4] bit[4] — toggle/parity bit: Consistent → Confirmed upgrade

Swing is ruled out (§5.1/§6: S12 shows it toggling 0/1 at the same temperature,
and Session 12 findings conclude it is NOT a swing state bit; IRremoteESP8266
uses a Special-type frame for swing, not a state bit). What remains is upgrading
the toggle/parity identification from Consistent to Confirmed.

**To resolve**: capture a session toggling vertical swing ON and OFF with no other changes.

### 7.2 byte[2] bit layout — mode, fan speed, power

Four values observed so far (`0xBF`/`0xFF`/`0x1F`/`0x7B`, S13 — power bit and
Heat/Auto bits identified in §5.1), but no Cool/Dry/Fan-only or non-Auto fan
sweep yet. Fan speed encoding conflicts with IRremoteESP8266 (our Auto=11 vs
IRremoteESP8266 Auto=00).

**To resolve**: capture with Cool, Dry, Fan-only modes and with Auto/High/Medium/Low fan.

### 7.3 Temperature range below 21 deg C and above 26 deg C

Confirmed for 21–26 deg C (six data points, §5.1). IRremoteESP8266 documents
17–30 deg C but uses a different format. Whether our formula extends below 21
or above 26 deg C is unconfirmed (a value-7 bit pattern appears in S13 frames
but without operator ground truth — see §5.1).

**To resolve**: set 17 deg C (Midea minimum) and 30 deg C (maximum).

### 7.4 Protocol variant origin

The extremeSaveBlue remote uses NEC per-byte complement, while IRremoteESP8266
MIDEA uses whole-frame inversion. Whether these are two distinct Midea IR standards
(e.g. "Midea1" vs "Midea2"), a regional variant, or a generation difference is
**unknown**. No public documentation found.

### 7.5 B9 installer mode parameter semantics

Parameters 0x00–0x08 stepped through sequentially. What each controls is unknown.

### 7.6 B2 frame does not carry absolute setpoint — **Consistent** (logic analyzer Session 10)

Session 10 captured 6 B2 control events (all with byte[2]=0xBF, Heat+Auto+ON).
Only byte[4] varies, with just 3 distinct values:

| byte[4] | bits[7:5] | bit4 | Events | Downstream setpoints |
|---------|-----------|------|--------|----------------------|
| 0x4C    | 2 (22°C)  | 0    | Grp 1,5 | 24°C (C mode) |
| 0xDC    | 6 (26°C)  | 1    | Grp 2   | 79°F / 26°C (F mode) |
| 0xCC    | 6 (26°C)  | 0    | Grp 3,4,6 | 78°F, 77°F, 25°C (all different!) |

The same B2 frame (0xCC) produces **three different downstream setpoints** depending
on the AC's current state. This means the B2 frame does not encode an absolute
temperature — the display board interprets the B2+D5 frame pair relative to its
current state, likely treating each IR event as a temperature increment/decrement
from the current setpoint.

The existing 3-bit formula `bits[7:5] + 20` from Session 2 gives 22°C or 26°C for
these frames, but the downstream effects range from 24–26°C (Celsius) and 77–79°F
(Fahrenheit). The formula may represent the **remote's own display value** rather
than the AC's target setpoint. **Further investigation needed.**

---

## References

- Own hardware captures: blaueis-hvacshark-traces repository (Midea XtremeSaveBlue, Sessions 2 and 10)
- Session 2 notes: [SessionNotes.md](../../../../blaueis-hvacshark-traces/Midea-XtremeSaveBlue-logicanalyzer/Session%202/SessionNotes.md)
- Session 2 findings: [findings.md](../../../../blaueis-hvacshark-traces/Midea-XtremeSaveBlue-logicanalyzer/Session%202/findings.md)
- Session 10 findings (C/F analysis): [findings.md](../../../../blaueis-hvacshark-traces/Midea-XtremeSaveBlue-logicanalyzer/Session%2010/findings.md)
- crankyoldgit/IRremoteESP8266 — `src/ir_Midea.h`, `src/ir_Midea.cpp`
- ESPHome midea component — `esphome/components/midea/ir_transmitter.h`
- IRremoteESP8266 protocol spreadsheet: https://docs.google.com/spreadsheets/d/1TZh4jWrx4h9zzpYUI9aYXMl1fYOiqu-xVuOOMqagxrs/
