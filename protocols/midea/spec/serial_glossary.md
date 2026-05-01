# Midea HVAC Serial Protocol — Field Glossary

> **Hand-curated skeleton** — representative fields with conceptual
> annotations (see §8 Ambiguities and Disputes). The full, machine-readable
> glossary (161 fields) lives at
> `blaueis-libmidea/packages/blaueis-core/src/blaueis/core/data/glossary.yaml`
> and is the canonical source; the auto-generated per-field inventory is at
> [_field_inventory_snapshot.md](_field_inventory_snapshot.md).

______________________________________________________________________

## 1. User-Settable Fields

### 1.1 Climate Control

| Canonical Name       | Type  | Unit | Range   | Description                               | Confidence |
| -------------------- | ----- | ---- | ------- | ----------------------------------------- | ---------- |
| `power`              | bool  | —    | —       | Master power on/off                       | Confirmed  |
| `operating_mode`     | enum  | —    | 1-6     | auto/cool/dry/heat/fan/smart_dry          | Confirmed  |
| `target_temperature` | float | °C   | 16-30.5 | Room temperature setpoint                 | Confirmed  |
| `fan_speed`          | uint8 | —    | 0-102   | Fan speed (discrete levels or stepless %) | Confirmed  |

### 1.2 Swing

| Canonical Name   | Type | Description                         | Confidence |
| ---------------- | ---- | ----------------------------------- | ---------- |
| `swing_vertical` | bool | Vertical (up/down) vane oscillation | Consistent |

### 1.3 Comfort Features

| Canonical Name | Type | Description                        | Confidence |
| -------------- | ---- | ---------------------------------- | ---------- |
| `eco_mode`     | bool | Energy-saving ECO mode             | Confirmed  |
| `turbo_mode`   | bool | High-performance turbo/strong wind | Confirmed  |

______________________________________________________________________

## 2. Frame Flags (Per-Frame Transport Metadata)

| Canonical Name | Type | Description                                                 | Confidence |
| -------------- | ---- | ----------------------------------------------------------- | ---------- |
| `buzzer`       | bool | Request beep on command receipt (per-frame, not persistent) | Confirmed  |

______________________________________________________________________

## 3. Sensor Values

### 3.1 Temperature Sensors

| Canonical Name        | Type  | Unit | Encoding              | Frame   | Byte                   | Device  | Confidence |
| --------------------- | ----- | ---- | --------------------- | ------- | ---------------------- | ------- | ---------- |
| `indoor_temperature`  | float | °C   | `(raw-50)/2 + tenths` | 0xC0    | body[11] + body[15] lo | Indoor  | Confirmed  |
| `outdoor_temperature` | float | °C   | `(raw-50)/2 + tenths` | 0xC0    | body[12] + body[15] hi | Outdoor | Confirmed  |
| `t1_indoor_coil`      | float | °C   | `(raw-30)/2`          | 0xC1 G1 | body[10]               | Indoor  | Confirmed  |
| `discharge_pipe_temp` | uint8 | °C   | direct integer        | 0xC1 G1 | body[14]               | Outdoor | Confirmed  |

______________________________________________________________________

## 4. Status Flags

### 4.1 Operational

| Canonical Name  | Type | Description                                                  | Confidence |
| --------------- | ---- | ------------------------------------------------------------ | ---------- |
| `run_status`    | bool | Compressor/fan currently running (not just powered on)       | Hypothesis |
| `defrost_state` | enum | Defrost cycle state (0=none, 1=starting, 2=active, 3=ending) | Hypothesis |

______________________________________________________________________

## 5. Inline Capabilities (B5 Query)

Capabilities are inlined on the fields they describe, not in a separate category.

| Field            | Cap ID | Cap ID (16-bit) | Describes                                | Confidence |
| ---------------- | ------ | --------------- | ---------------------------------------- | ---------- |
| `fan_speed`      | 0x10   | 0x0210          | Stepless slider vs discrete named levels | Confirmed  |
| `operating_mode` | 0x14   | 0x0214          | Available modes for this device          | Consistent |
| `buzzer`         | 0x2C   | 0x022C          | Buzzer control supported                 | Consistent |

______________________________________________________________________

## 6. Cross-Reference: Source Name Mapping

| Canonical             | dudanov     | node_mideahvac     | midea_local         |
| --------------------- | ----------- | ------------------ | ------------------- |
| `power`               | powerState  | powerOn            | power               |
| `operating_mode`      | m_mode      | mode               | mode                |
| `target_temperature`  | targetTemp  | setpoint           | target_temperature  |
| `fan_speed`           | m_fanSpeed  | fanSpeed           | fan_speed           |
| `eco_mode`            | m_ecoMode   | ecoMode            | eco                 |
| `turbo_mode`          | m_turbo     | —                  | turbo               |
| `buzzer`              | m_buzzer    | —                  | prompt_tone         |
| `indoor_temperature`  | indoorTemp  | indoorTemperature  | indoor_temperature  |
| `outdoor_temperature` | outdoorTemp | outdoorTemperature | outdoor_temperature |
| `t1_indoor_coil`      | —           | —                  | —                   |
| `discharge_pipe_temp` | —           | —                  | —                   |

> See `glossary.yaml` field `alt_names:` blocks (in the libmidea package) for the full provenance set, including codename-tagged entries from sources not surfaced in this table.

______________________________________________________________________

## 7. Encoding Reference

All temperature values are in **°C** unless explicitly noted.

| Encoding Key           | Formula                     | Scale  | Offset | Used In                           |
| ---------------------- | --------------------------- | ------ | ------ | --------------------------------- |
| `temp_offset50_half`   | `(raw - 50) / 2.0`          | 0.5 °C | 50     | C0 body[11-12], C1 G1 body[12-13] |
| `temp_offset30_half`   | `(raw - 30) / 2.0`          | 0.5 °C | 30     | C1 G1 body[10] (T1 coil)          |
| `temp_setpoint_legacy` | `bits[3:0] + 16 + 0.5*bit4` | 0.5 °C | -16    | 0x40/0xC0 body[2]                 |
| `temp_setpoint_new`    | `bits[4:0] + 12`            | 1.0 °C | -12    | 0x40 body[18], 0xC0 body[13]      |
| `temp_direct_integer`  | `raw`                       | 1.0 °C | 0      | C1 G1 body[14] (Tp)               |
| `temp_follow_me`       | `(raw - 50) / 2.0`          | 0.5 °C | 50     | 0x41 optCmd=0x01 body[5]          |
| `power_bcd`            | pseudo-BCD nibble pairs     | —      | —      | C1 Group 4 body[4-18]             |

**Cross-bus temperature encoding comparison** (same physical sensor, different raw values):

| Sensor          | Serial (UART/R/T)    | XYE                               | Mainboard                          |
| --------------- | -------------------- | --------------------------------- | ---------------------------------- |
| Indoor room     | offset 50, scale 0.5 | offset 40, scale 0.5              | direct integer °C (D0)             |
| Outdoor ambient | offset 50, scale 0.5 | offset 40, scale 0.5 (C4/C6 only) | raw / 2.0 (AA30), offset 40 (AA31) |
| Setpoint        | +16, 0.5°C steps     | +0x40, 1°C steps (dual C/F)       | offset 30, scale 0.5               |
| Discharge pipe  | direct integer       | offset 40, scale 0.5              | direct integer (candidate)         |

______________________________________________________________________

## 8. Ambiguities and Disputes

### 8.1 ECO Mode — Read/Write Bit Position Mismatch

**Write** (0x40 Set): `body[9] bit 7` (0x80)
**Read** (0xC0 Response): `body[9] bit 4` (0x10)

This asymmetry is unique to the Lua/Midea reference implementation and confirmed
by dudanov and midea-local. All three agree on the different bit positions.
Source: community protocol research.

### 8.2 Fan Speed — Hardware Variant Remapping

Standard protocol: Low=40, Medium=60. Some hardware variants (reported by
dudanov/MideaUART) return Low=30, Medium=50 in UART responses. Commands
should always use 40/60; parsers should defensively remap 30→40, 50→60.
**[Hypothesis]** — community report, not confirmed on own hardware.

### 8.3 T2 Sensor — Name Overloading

| Context                  | T2 Meaning                                            |
| ------------------------ | ----------------------------------------------------- |
| Serial/UART (C1 Group 1) | Indoor heat exchanger coil (single sensor, called T1) |
| XYE protocol             | T2A = coil inlet, T2B = coil outlet (two sensors)     |
| VRF service manuals      | T2 = intermediate, T2A = liquid pipe, T2B = gas pipe  |

The same label "T2" refers to different physical sensors depending on the
context. The glossary uses descriptive names (`t1_indoor_coil`,
`t2a_coil_inlet`, `t2b_coil_outlet`) to avoid ambiguity.

### 8.4 Turbo Mode — Dual Byte Location

Turbo appears at **two** bit positions in the 0x40 Set command:

- `body[8] bit 5` (strong wind)
- `body[10] bit 1` (turbo mode, primary)

The 0xC0 response reads turbo from `body[10] bit 1` only. Both write
positions are observed in community implementations.

### 8.5 Fan Speed Control Capability — Inverted Boolean

dudanov/MideaUART interprets B5 cap 0x10 value=1 as "fan speed control
not supported" (`m_fanSpeedControl = uval != 1`). This is incorrect —
value=1 means **stepless** (continuously variable 0-100% — "no limits").
The correct interpretation: value=1 is a valid and more capable fan
speed control mode.

### 8.6 Target Temperature — Three Response Encodings

The 0xC0 response may encode the setpoint temperature in one of three formats:

| Format        | Location          | Formula       |
| ------------- | ----------------- | ------------- |
| Standard      | body[2] bits[3:0] | value + 16 °C |
| Alternative A | body[1] bits[6:2] | value + 12 °C |
| Alternative B | body[1] bits[5:1] | value + 12 °C |

The trigger condition is unknown. Treat alternatives as **[Hypothesis]**
(possible older protocol versions). Not observed in own captures.

______________________________________________________________________

## Fields Not Yet Included

The following field groups are planned but omitted from this skeleton pending
format review:

- **User-settable**: sleep_mode, follow_me, natural_wind, silky_cool, comfort_sleep,
  on_timer, off_timer, screen_display, night_light, temperature_unit,
  swing_horizontal, humidity_setpoint, frost_protection
- **Sensor values**: t3_outdoor_coil, t4_outdoor_ambient, compressor_frequency,
  total_energy, realtime_power, indoor_humidity
- **Status flags**: error_code, window_contact, dust_full, power_state (in_error)
- **Inline capabilities** (on future fields): cap_eco, cap_turbo, cap_swing,
  cap_temperatures, cap_humidity, cap_power_calc, cap_unit_changeable,
  cap_screen_display, cap_anion, cap_frost_protection, cap_aux_heat

______________________________________________________________________

## References

- `blaueis-libmidea/packages/blaueis-core/src/blaueis/core/data/glossary.yaml` — machine-readable source (canonical; 161 fields)
- `blaueis-libmidea/packages/blaueis-core/src/blaueis/core/data/glossary_schema.json` — JSON Schema for validation
- [_field_inventory_snapshot.md](_field_inventory_snapshot.md) — auto-generated inventory of all fields by direction / cap / frame
- [serial_protocol.md](serial_protocol.md) — Serial protocol command reference
- [protocol_shared.md](protocol_shared.md) — Cross-bus encoding variants
