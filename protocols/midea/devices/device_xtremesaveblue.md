# Midea XtremeSaveBlue — Device-Specific Observations

> These observations are specific to the **Midea XtremeSaveBlue Q11 platform**
> (indoor model MSAGBU-09HRFN8-QRD0GW). Other Midea models or PCB revisions
> may behave differently.

For the generic serial protocol, see [serial_protocol.md](serial_protocol.md).
For capture sessions, see the `HVAC-shark-dumps` repository.

---

## 1. Bus Data Rates (Confirmed)

| Bus | Connector | Baud | Encoding | ms/byte | 38-byte frame TX |
|-----|-----------|------|----------|---------|-----------------|
| Display↔Mainboard | CN1 grey/blue | 9600 | 8N1 | 1.04 ms | ~40 ms |
| UART wifi dongle | CN3 brown/orange | 9600 | 8N1 | 1.04 ms | ~40 ms |
| R/T pin | CN1 R/T | **2400** | 8N1 | 4.17 ms | **~158 ms** |
| HA/HB RS-485 | Adapter board | **48000** | 8N1 nibble-pair | 0.21 ms | ~8 ms (physical) |

R/T at 2400 baud is 4× slower than UART — a 38-byte R/T frame takes ~158 ms to
transmit. HA/HB uses nibble-pair encoding (2 physical bytes per logical byte,
XOR 0xFF), so the effective logical data rate is ~2400 bytes/s.

---

## 2. Command Relay Timing (Session 8)

A Set Status command from the wall controller traverses:
**bus adapter → R/T (2400 baud) → display → internal bus (9600 baud) → mainboard**

Observed timing (t relative to R/T 0x40 frame start):

```
t+0.000s  R/T    toACdisplay     0x40 Set (Mode=Auto, from wall controller)
t+0.004s  DISP   toACmainboard   D_set (Mode=Auto, 30°C, forwarded to mainboard)
t+0.197s  R/T    fromACdisplay   C0 Status (response with current state)
```

The 4 ms between R/T frame start and D_set forwarding is shorter than one R/T
frame TX time (~158 ms at 2400 baud). This means the display starts forwarding
to the mainboard **before the R/T frame has finished transmitting** — the display
processes the R/T frame incrementally, not after full receipt.

Note: timestamps mark the first byte on the wire. When correlating across buses,
always account for frame TX time at the respective baud rate.

---

## 3. Mode Mismatch: Auto → Heat Sub-Mode (Session 8)

Cross-bus direction analysis revealed a consistent mode discrepancy:

| Bus | Direction | Frame | Mode field |
|-----|-----------|-------|------------|
| Display→Mainboard | toACmainboard | D_set (0x20 Grey) | **Auto, 30°C** |
| Mainboard→Display | fromACmainboard | D_sts (0x20 Blue) | **Heat** |
| R/T fromACdisplay | fromACdisplay | C0 Status | **Auto, 30°C** |

The display continuously sends the **user-requested** mode (Auto) to the mainboard.
The mainboard responds with the **actual operating sub-mode** (Heat) — selected
automatically based on current temperature conditions.

The R/T and UART status frames report the user-requested mode, not the actual
sub-mode. To determine the real operating mode, read the display-mainboard internal
bus (D_sts) or C1 Group 1 "indoor operating mode" field.

---

## 4. Polling Rates

| Bus | Rate | Cycle time |
|-----|------|------------|
| Display↔Mainboard | ~4 Hz | ~250 ms |
| R/T (bus adapter) | ~0.18 Hz | ~5.5 s |
| UART (wifi dongle) | Sporadic | Seconds between heartbeats |

The display↔mainboard bus at ~4 Hz is the primary data exchange. The display
caches mainboard state and redistributes it to the slower R/T and UART buses
on their respective schedules.

---

## 5. Device Capability Profile (0xB5)

Observed in Sessions 1, 7, 8, 9 (UART, new protocol msg_type=0x03).
The dongle issues two TLV queries; the device responds to each. Values decoded
per [serial_protocol.md §3.4](serial_protocol.md) and cross-checked against
dudanov/MideaUART `Capabilities.cpp` and node-mideahvac `B5.js`.

### 5.1 Query 1 (body=[0xB5, 0x01, 0x00]) — 8 records

Raw response body (Session 1, t=30.43 s):
```
B5 08  12 02 01 01  14 02 01 01  15 02 01 01  16 02 01 00
       1A 02 01 01  10 02 01 01  25 02 07 20 3C 20 3C 20 3C 00
       24 02 01 01
```

| Cap ID | Name | val | Decoded | Confidence |
|--------|------|-----|---------|------------|
| 0x12 | Eco Mode | 1 | Eco supported (no special eco) | Consistent |
| 0x14 | Operating Modes | 1 | All four modes (cool / dry / heat / auto) | Confirmed |
| 0x15 | Swing/Fan Direction | 1 | Both axes (UD + LR) | Consistent |
| 0x16 | Power Calculation | 0 | Not supported | Consistent |
| 0x1A | Turbo Mode | 1 | Both cool and heat turbo | Consistent |
| 0x10 | Wind Speed Type | 1 | Stepless (continuously variable) fan speed — app shows a percentage slider rather than named step buttons (Low/Mid/High). See community protocol research (community protocol research) | Confirmed |
| 0x25 | Temperature Ranges | 7 bytes | cool=16–30°C, auto=16–30°C, heat=16–30°C; byte[6]=0x00 → decimals=false (1°C steps only) | Consistent |
| 0x24 | Light/LED Control | 1 | Supported | Consistent |

**Note on 0x10 (Wind Speed Type):** val=1 means stepless (continuously variable) fan
speed. The Midea app shows a percentage slider (0–100 %) instead of named step buttons
(Mute/Low/Mid/High/Auto). Confirmed by Session 11: arbitrary percentages (1%, 8%, 21%,
96%, 100%) are accepted and echoed in 0xC0 body[3]. Some third-party implementations
misinterpret val=1 as "no fan speed control" due to the original property name
translating to "has no wind speed" — this actually means "has no named wind speed
steps". Source: community protocol research.

**Note on 0x25 byte[6]=0x00:** when dlen=7 the extra byte encodes a `decimals` flag at
bit 0 (per node-mideahvac). Value 0x00 → `decimals=false` — device only supports 1°C
setpoint steps, not 0.5°C.

### 5.2 Query 2 (body=[0xB5, 0x01, 0x01, 0x01]) — 9 records

Raw response body (Session 1, t=31.00 s, repeated at t=32.24 s):
```
B5 09  1E 02 01 01  13 02 01 01  22 02 01 00  19 02 01 00
       39 00 01 01  42 00 01 01  09 00 01 01  0A 00 01 01
       48 00 01 01
```

| Cap ID | Name | val | Decoded | Confidence |
|--------|------|-----|---------|------------|
| 0x1E | Anion / Ionizer (`b5_anion`) | 1 | Supported — ionizer/anion air purifier feature (community protocol research) | Consistent |
| 0x13 | Frost Protection | 1 | Supported | Consistent |
| 0x22 | Unit Changeable | 0 | val=0 → C/F switchable (inverted logic) | Consistent |
| 0x19 | Aux Electric Heat | 0 | Not supported | Consistent |
| 0x39 | Active Clean | 1 | Supported | Consistent |
| 0x42 | One-Key No Wind | 1 | Supported | Consistent |
| 0x09 | Unknown simple | 1 | Not in reference model | Unknown |
| 0x0A | Unknown simple | 1 | Not in reference model | Unknown |
| 0x48 | Unknown simple | 1 | Not in reference model | Unknown |

### 5.3 Old Protocol B5 (msg_type=0x05)

Old-protocol B5 frames (msg_type=0x05) appear on wifiOrange/wifiBrown in Sessions 7
and 8 — echoed on both wires. These use TLV-like framing but differ from the new
protocol:

- Cap IDs 0x09 and 0x0A appear with varying single-byte values (0x00, 0x01, 0x32=50,
  0x4B=75, 0x64=100) — values change across frames in Session 8, suggesting these may
  encode a numeric property (energy %, temperature, or status) rather than a binary flag.
- Cap ID 0x10 appears with type=0x06 (not a standard type), val=0x01 or 0x00.

The old-protocol 0xB5 semantics for this device are not yet decoded. These frames may
represent a separate property-reporting mechanism that shares the 0xB5 command byte.
See Session 7/8 CSVs for raw examples.

---

## 6. Observed Commanded States (0x40 → 0xC0 Confirmation)

Empirical summary of fields successfully set via 0x40 Set Status and confirmed in
subsequent 0xC0 Status Response frames. All 0xC0 data is from wifiOrange
(fromACdisplay) frames. Sessions 1, 8, 10, 11, 12 contain confirming pairs;
Sessions 7, 9, 13 were captured on other channels with no wifiOrange 0xC0.

### 6.1 Power (body[1] bit0)

| Value | Sessions | Confirmed |
|-------|----------|-----------|
| ON (1) | 1, 8, 10, 11, 12 | Yes — 0xC0 body[1]=0x01 |
| OFF (0) | 11 | Yes — 0xC0 body[1]=0x00 |

### 6.2 Operating Mode (body[2] bits[7:5])

| Mode | Code | Sessions | Confirmed |
|------|------|----------|-----------|
| Heat | 4 | 1, 8, 10, 11 | Yes |
| Cool | 1 | 1, 8 | Yes |
| Dry  | 2 | 12 | Yes |
| Fan  | 5 | 8 | Yes |

All four modes confirmed. Heat was dominant across sessions (winter heating use).

### 6.3 Temperature Setpoint (body[2] bits[3:0], integer; bit4 = 0.5°C step)

Observed integer setpoints commanded and confirmed: 16, 21, 22, 23, 24, 25, 26,
27, 28, 29, 30 °C. The 0.5°C step bit (body[2] bit4) was not set in any 0x40
command across all sessions — consistent with B5 cap 0x25 `decimals=false`.

### 6.4 Fan Speed (body[3] bits[6:0])

Session 11 contains a systematic fan speed sweep where each value was commanded
and confirmed in the immediately following 0xC0 response. The commanded value
was held by the device across multiple subsequent 0xC0 cycles (no override
observed under test conditions):

| Commanded (0x40 body[3]) | bits[6:0] | Confirmed (0xC0 body[3]) | Session |
|--------------------------|-----------|--------------------------|---------|
| `0xE6` | 102 = Auto | `0x66` = 102 | 1, 8, 10, 11, 12 |
| `0xE5` | 101 = Fixed | `0x65` = 101 | 1, 8 |
| `0xE0` | 96 % | `0x60` = 96 | 11 |
| `0xE4` | 100 % | `0x64` = 100 | 11 |
| `0x95` | 21 % | `0x15` = 21 | 11 |
| `0x88` | 8 % | `0x08` = 8 | 11 |
| `0x81` | 1 % | `0x01` = 1 | 11 |

The high bit (bit7) of 0x40 body[3] is set in all commands above; the 0xC0
response strips it, returning only the lower 7 bits. All commanded speeds were
accepted and echoed back with no modification. Note: the device also has internal
airflow management (e.g. anti-cold wind protection) that may override the effective
fan speed under certain operating conditions; such overrides are not visible in the
basic 0xC0 status field.

### 6.5 Feature Flags

| Feature | 0x40 body/bit | Confirmed in 0xC0 | Sessions |
|---------|--------------|-------------------|----------|
| Turbo | body[8] bit5 | Yes — body[8]=`0x20` | 11, 12 |
| Follow Me | body[8] bit7 | Yes — body[8]=`0x80` | 1 |
| Eco mode | body[9] bit4 | Not reflected in 0xC0 body[9] | 1, 8, 10, 11, 12 |

Eco mode was included in nearly all 0x40 commands across all active sessions
(body[9]=`0x10`) but body[9]=`0x00` in all corresponding 0xC0 responses —
the device does not reflect eco state in the basic status frame. Turbo and
Follow Me are correctly mirrored.

Swing bits (body[7] bits[3:0]) were not set in any 0x40 command across all
sessions — UD and LR swing not exercised.

### 6.6 Sensor Readings (0xC0 body[11–14])

Indoor and outdoor temperatures present in all 0xC0 responses, encoding
`(byte − 50) / 2 = °C`:

| Sensor | Field | Range observed | Sessions |
|--------|-------|----------------|----------|
| Indoor temp | body[11] | 24.0 – 28.0 °C | 1, 10, 11, 12 |
| Outdoor temp | body[12] | 3.5 – 9.0 °C | 1, 10, 11 |

No error flag (body[1] bit7) set in any captured 0xC0 response.

### 6.7 Display State (0xC0 body[14] bits[6:4])

| body[14] | bits[6:4] | State | Example sessions |
|----------|-----------|-------|-----------------|
| `0x70` | 111 = 7 | Display ON | Session 1 (all), Session 11 t≈145 s |
| `0x00` | 000 = 0 | Display OFF | Session 11 early/mid, Session 12 |

In Session 1 (dongle-driven heating from cold start) the display was on throughout.
In Session 11 the display started off, then turned on at t≈145 s and returned to off
later. The transition conditions are not yet identified.

---

## 7. App State Desync Quirks (Session 12)

### 7.1 LED / display state loss

The Midea app repeatedly lost the LED/display state during Session 12.
The operator noted: "app hat wieder das led bit verlernt" (app forgot the
LED bit again), "somewhere inbetween the led was turned off? app fault?"

**Root cause (hypothesis)**: the app caches the LED state locally and
writes body[1] bit 6 (buzzer) and body[14] bits (display) on every
subsequent 0x40 SET command. If the app's cached state is stale, every
temperature or mode change silently overwrites the LED/display state
with the wrong value. The AC has no way to reject the stale bit — it
accepts whatever the 0x40 frame carries.

This is a state-management bug in the app, not a protocol issue. Any
integration that writes 0x40 SET commands should read the current 0xC0
state before composing the command frame (`build_command_body` does this
via the `status` parameter).

### 7.2 ECO mode cancelled by temperature change

Session 12 confirmed: sending a temperature setpoint via 0x40 SET while
ECO mode is active causes the AC to silently disable ECO. The 0xC0
response after the temp change shows ECO=no (body[9] bit 4 = 0). This
is device-side behavior, not an app bug — the AC treats the new setpoint
as overriding the ECO program.

Enabling Turbo also disables ECO (confirmed S12 t=84). The two modes
are mutually exclusive on this hardware.

### 7.3 Beep inconsistency

The unit intermittently stopped beeping during Session 12 without an
explicit buzzer-off command. This may be related to the LED state desync
(§7.1) — if the app writes body[1] bit 6 = 0 (buzzer off) in a stale
0x40 frame, the beep stops until the bit is explicitly restored.
