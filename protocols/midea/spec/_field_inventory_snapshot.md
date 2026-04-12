# Field inventory — direction, cap gating, command frame mapping

Generated from `serial_glossary.yaml`. Snapshot for reference; may go stale.

## Summary

- **Total fields**: 161
- **Direction `in`** (read-only sensors): 104
- **Direction `in/out`** (bidirectional): 50
- **Direction `out`** (write-only protocol bits): 4
- **Direction `—`** (shells, no protocol path): 3
- **Capability-gated**: 32
- **cmd_0x40 fields** (need read-modify-write — shared bytes): 33
- **cmd_0xb0 fields** (independent TLV): 17

## Direction legend

| Direction | Meaning |
|-----------|---------|
| `in` | Read-only sensor — value comes from response frames only |
| `in/out` | Bidirectional — has both decode steps and a settable command |
| `out` | Write-only protocol bits (filler the AC requires but ignores) |
| `—` | Field declared but no protocol path wired |

## Command frame state-dependency

| Frame | Behaviour |
|-------|-----------|
| **cmd_0x40 (RMW)** | Bit-packed 26-byte set body. Shared bytes hold multiple fields — sending requires knowing the current state of ALL siblings, otherwise they get clobbered. Use `build_command.build_command_body(status, changes, glossary)`. |
| **cmd_0xb0 (TLV)** | Independent TLV property records. Each property is self-contained — you can set one without knowing others. |

## Control fields (settable)

| Field | Direction | Cap | Set frame | feature_available |
|-------|-----------|:---:|-----------|------------------|
| `alarm_sleep` | in/out | — | cmd_0x40 (RMW) | readable |
| `anion_ionizer` | in/out | `0x1E` | cmd_0xb0 (TLV) | capability |
| `aqua_wash_manual` | in/out | — | cmd_0xb0 (TLV) | capability |
| `aqua_wash_switch` | in/out | — | cmd_0xb0 (TLV) | capability |
| `aqua_wash_time` | in/out | — | cmd_0xb0 (TLV) | capability |
| `breeze_away` | in/out | `0x33` | cmd_0xb0 (TLV) | capability |
| `breeze_mild` | in/out | `0x43` | cmd_0xb0 (TLV) | capability |
| `breezeless` | in/out | `0x42` | cmd_0xb0 (TLV) | capability |
| `buzzer` | in/out | `0x2C` | cmd_0x40 (RMW) | capability |
| `catch_cold` | in/out | — | cmd_0x40 (RMW) | always |
| `child_sleep` | in/out | — | cmd_0x40 (RMW) | readable |
| `cleanup` | in/out | — | cmd_0x40 (RMW) | readable |
| `cosy_sleep` | in/out | — | cmd_0x40 (RMW) | always |
| `dry_clean` | in/out | — | cmd_0x40 (RMW) | always |
| `eco_mode` | in/out | `0x12` | cmd_0x40 (RMW) | readable |
| `energy_save` | in/out | — | cmd_0x40 (RMW) | always |
| `exchange_air` | out | — | cmd_0x40 (RMW) | readable |
| `fan_speed` | in/out | `0x10` | cmd_0x40 (RMW) | readable |
| `fan_speed_timer_bit` | out | — | cmd_0x40 (RMW) | always |
| `follow_me` | in/out | — | cmd_0x40 (RMW) | always |
| `fresh_air_fan_speed` | in/out | — | cmd_0xb0 (TLV) | capability |
| `fresh_air_switch` | in/out | — | cmd_0xb0 (TLV) | capability |
| `frost_protection` | in/out | `0x13` | cmd_0x40 (RMW) | readable |
| `humidity_setpoint` | in/out | `0x1F` | cmd_0x40 (RMW) | readable |
| `jet_cool` | in/out | `0x67` | cmd_0xb0 (TLV) | capability |
| `low_frequency_fan` | in/out | — | cmd_0x40 (RMW) | readable |
| `night_light` | in/out | — | cmd_0x40 (RMW) | always |
| `operating_mode` | in/out | `0x14` | cmd_0x40 (RMW) | readable |
| `power` | in/out | — | cmd_0x40 (RMW) | always |
| `power_off_time_value` | in/out | — | — | readable |
| `power_off_timer` | in/out | — | cmd_0x40 (RMW) | readable |
| `power_on_time_value` | in/out | — | — | readable |
| `power_on_timer` | in/out | — | cmd_0x40 (RMW) | readable |
| `power_save` | in/out | — | cmd_0x40 (RMW) | always |
| `protocol_bit1` | out | — | cmd_0x40 (RMW) | always |
| `ptc_heater` | in/out | `0x19` | cmd_0x40 (RMW) | readable |
| `rate_select` | in/out | `0x48` | cmd_0xb0 (TLV) | capability |
| `resume` | in/out | — | cmd_0x40 (RMW) | always |
| `screen_display` | in/out | `0x24` | — | readable |
| `self_clean` | in/out | `0x39` | cmd_0xb0 (TLV) | capability |
| `silky_cool` | in/out | `0x18` | — | readable |
| `sleep_mode` | in/out | — | cmd_0x40 (RMW) | always |
| `smart_eye` | in/out | `0x30` | cmd_0xb0 (TLV) | capability |
| `strong_wind` | in/out | — | cmd_0x40 (RMW) | always |
| `swing_horizontal` | in/out | `0x15` | cmd_0x40 (RMW) | readable |
| `swing_reserved` | out | — | cmd_0x40 (RMW) | always |
| `swing_vertical` | in/out | `0x15` | cmd_0x40 (RMW) | readable |
| `target_temperature` | in/out | `0x25` | cmd_0x40 (RMW) | readable |
| `temperature_unit` | in/out | `0x22` | cmd_0x40 (RMW) | readable |
| `turbo_mode` | in/out | `0x1A` | cmd_0x40 (RMW) | readable |
| `water_pump` | in/out | — | cmd_0xb0 (TLV) | capability |
| `wind_straight` | in/out | `0x32` | cmd_0xb0 (TLV) | capability |
| `wind_swing_lr_angle` | in/out | `0x0A` | cmd_0xb0 (TLV) | capability |
| `wind_swing_ud_angle` | in/out | `0x09` | cmd_0xb0 (TLV) | capability |

## Sensor fields (read-only)

| Field | Direction | Cap | feature_available | Description |
|-------|-----------|:---:|-------------------|-------------|
| `ad_calibration_voltage` | in | — | readable | AD calibration voltage (raw x 16). |
| `aqua_wash_stage` | in | — | capability | Evaporator aqua-clean current cycle stage (read-only status). |
| `clean_fan_time` | in | — | readable | Post-run fan / cool fan: keeps fan running after compressor stops t... |
| `compensated_setpoint` | in | — | readable | Compensated temperature setpoint (Tsc). Internal raw value after co... |
| `compressor_cumul_hours_low` | in | — | readable | Compressor cumulative runtime hours low byte (LE 16-bit with body[1... |
| `compressor_current` | in | — | readable | Compressor current draw. Raw value, unit unclear. |
| `compressor_flux` | in | — | readable | Compressor motor magnetic flux (raw x 8). |
| `compressor_frequency` | in | — | readable | Compressor running frequency (FR). 0 Hz when compressor is off. |
| `compressor_peak_current` | in | — | readable | Compressor motor peak current. |
| `compressor_runtime_current` | in | — | readable | Current compressor run time since last start. Encoding: raw x 64 = ... |
| `compressor_target_frequency` | in | — | readable | Compressor target frequency (FT). Set by control logic. 0 Hz when c... |
| `cosy_sleep_switch` | in | — | readable | Cosy sleep switch / self cosy sleep toggle. Separate from cosy_slee... |
| `current_run_power_kwh` | in | `0x16` | capability | Energy consumed in the current run cycle in kWh. Resets on power cy... |
| `current_session_hours` | in | — | readable | Current session hours counter. |
| `current_session_minutes` | in | — | readable | Current session minutes counter. |
| `current_session_seconds` | in | — | readable | Current session seconds counter. |
| `current_work_days` | in | — | readable | Current work time — days component. 16-bit big-endian. |
| `current_work_hours` | in | — | readable | Current work time — hours component. |
| `current_work_minutes` | in | — | readable | Current work time — minutes component. |
| `d_axis_current` | in | — | readable | Compressor motor d-axis current (raw x 64). Signed per JS comment. |
| `defrost_state` | in | — | readable | Defrost cycle state of the outdoor unit. |
| `defrost_step` | in | — | readable | Current defrost cycle stage: 0=none, 1=start, 2=in progress, 3=ending. |
| `discharge_pipe_temp` | in | — | readable | Compressor discharge pipe temperature (Tp thermistor). High values ... |
| `down_no_wind_feel` | — | `0x3E` | capability | Lower vane no-wind-feel mode. Prevents direct airflow from lower lo... |
| `dust_full` | in | — | readable | Dust full indicator: filter needs cleaning. |
| `eev_position` | in | — | readable | Electronic expansion valve position. Encoding: raw x 8 = steps. |
| `eev_target_angle` | in | — | readable | Electronic expansion valve target position. Encoding: raw x 8 = steps. |
| `error_code` | in | — | readable | Device error/fault code (0-33). 0 = no error. |
| `fan_flux` | in | — | readable | Fan motor magnetic flux (raw x 8). |
| `fan_peak_current` | in | — | readable | Fan motor peak current. |
| `fresh_air_temp` | in | — | capability | Fresh air intake temperature reading from the ventilation system. |
| `group12_unknown_byte4` | in | — | readable | Group 12 body[4] — unknown. Constant 0x02 across all runs. |
| `group12_unknown_byte6` | in | — | readable | Group 12 body[6] — unknown. Constant 0x0F across all runs. |
| `group7_unknown_byte10` | in | — | readable | Group 7 body[10] — unknown. Non-monotonic (8F->58->B3). Possibly a ... |
| `group7_unknown_byte11` | in | — | readable | Group 7 body[11] — unknown. Decrements with load (02->01->00). |
| `group7_unknown_byte5` | in | — | readable | Group 7 body[5] — unknown. Increments across probe runs (FD->FE->FF... |
| `group7_unknown_byte6` | in | — | readable | Group 7 body[6] — unknown. Decrements with compressor frequency (07... |
| `group7_unknown_byte7` | in | — | readable | Group 7 body[7] — unknown. Mostly stable (01), jumped to 02 at low ... |
| `group7_unknown_byte8` | in | — | readable | Group 7 body[8] — unknown. Constant 0x06 across all runs. |
| `humidity_actual` | in | — | readable | Current indoor humidity measured by sensor. Distinct from humidity_... |
| `humidity_measured` | in | — | readable | Current indoor humidity from A1 heartbeat sensor. |
| `in_error` | in | — | readable | Error flag: indicates the unit has an active fault condition. |
| `indoor_fan_actual_speed` | in | — | readable | Indoor fan actual speed (raw value; consumer multiplies by 8 for RPM). |
| `indoor_fan_runtime_low` | in | — | readable | Indoor fan runtime low byte (LE 16-bit with body[7] as high byte; f... |
| `indoor_fan_set_speed` | in | — | readable | Indoor fan set speed (raw value; consumer multiplies by 8 for RPM). |
| `indoor_fan_stator_flux` | in | — | readable | Indoor fan motor stator flux (raw sensor value). |
| `indoor_fault_flags_1` | in | — | readable | Indoor unit fault state byte 1 (8 individual fault bits). |
| `indoor_fault_flags_2` | in | — | readable | Indoor unit fault state byte 2 (8 individual fault bits). |
| `indoor_fault_flags_3` | in | — | readable | Indoor unit fault state byte 3 (8 individual fault bits). |
| `indoor_load_flags_1` | in | — | readable | Indoor unit load state byte 1 (8 individual state bits). |
| `indoor_load_flags_2` | in | — | readable | Indoor unit load state byte 2 (8 individual state bits). |
| `indoor_operating_mode` | in | — | readable | Indoor unit actual operating mode as reported in C1 Group 1. Uses t... |
| `indoor_temperature` | in | — | readable | Current room temperature measured by the indoor unit thermistor. Wh... |
| `ipm_module_temp` | in | — | never | IPM (Insulated Power Module) temperature. Raw value — encoding disp... |
| `lifetime_max_current` | in | — | readable | Lifetime maximum current draw recorded by the unit. |
| `lifetime_max_t4_raw` | in | — | readable | Lifetime maximum T4 outdoor ambient temperature (raw sensor value). |
| `lifetime_min_t4_raw` | in | — | readable | Lifetime minimum T4 outdoor ambient temperature (raw sensor value). |
| `light_adc_value` | in | — | readable | Ambient light sensor raw ADC value. |
| `local_body_sense` | in | — | never | Built-in occupancy sensor active. Detects/tracks people in the room. |
| `max_bus_voltage` | in | — | readable | Maximum recorded DC bus voltage. Encoding: raw + 60 = volts. |
| `min_bus_voltage` | in | — | readable | Minimum recorded DC bus voltage. Encoding: raw + 60 = volts. |
| `natural_wind` | in | — | readable | Natural wind / natural breeze: simulates outdoor wind with variable... |
| `nest_filter_check` | — | `0x17` | capability | Nest/filter check and maintenance reminder capability. |
| `outdoor_dc_bus_voltage` | in | — | readable | Outdoor unit DC bus voltage. Raw value in volts. |
| `outdoor_fan_speed` | in | — | readable | Outdoor unit DC fan speed. Encoding: raw x 8 = RPM. |
| `outdoor_fan_stator_flux` | in | — | readable | Outdoor fan motor stator flux (raw sensor value). |
| `outdoor_fan_target_speed` | in | — | readable | Outdoor fan target speed. Encoding: raw x 8 = RPM. |
| `outdoor_return_air_temp` | in | — | never | Outdoor return air temperature as raw ADC value. Needs NTC lookup t... |
| `outdoor_supply_voltage` | in | — | readable | Outdoor unit supply voltage. Raw value. |
| `outdoor_target_compressor_freq` | in | — | readable | Outdoor target compressor frequency (from outdoor controller perspe... |
| `outdoor_temperature` | in | — | readable | Current outdoor ambient temperature reported by the outdoor unit se... |
| `outdoor_total_current` | in | — | readable | Outdoor unit total current. Raw value multiplied by 4. |
| `outdoor_voltage_2` | in | — | readable | Secondary outdoor voltage reading (raw, unit unclear). |
| `peak_elec` | in | — | readable | Peak electricity / demand response flag. |
| `pfc_peak_current` | in | — | readable | PFC (Power Factor Correction) circuit peak current. |
| `pm25_concentration` | in | — | readable | PM2.5 particulate matter concentration. 16-bit big-endian. |
| `pmv_index` | in | — | readable | PMV (Predicted Mean Vote) thermal comfort index. ISO 7730 / ASHRAE ... |
| `power_on_hours` | in | — | readable | Power-on hours counter. |
| `power_on_minutes` | in | — | readable | Power-on minutes counter. |
| `power_on_seconds` | in | — | readable | Power-on seconds counter. |
| `q_axis_current` | in | — | readable | Compressor motor q-axis current (raw x 64). Signed per JS comment. |
| `realtime_power_kw` | in | `0x16` | capability | Instantaneous power draw in kW. |
| `run_status` | in | — | readable | Whether the compressor / indoor fan is currently running (not just ... |
| `t1_indoor_coil` | in | — | readable | Indoor heat exchanger coil temperature (T1 thermistor). |
| `t2_indoor_temp` | in | — | readable | Indoor heat exchanger intermediate temperature (T2 thermistor). Off... |
| `t3_outdoor_coil_temp` | in | — | readable | Outdoor coil temperature (T3 thermistor). Offset 50. |
| `t4_outdoor_ambient_temp` | in | — | readable | Outdoor ambient air temperature (T4 thermistor). Offset 50. |
| `torque_compensation_angle` | in | — | readable | Motor torque compensation angle. Low byte only (body[15]). Full val... |
| `torque_compensation_value` | in | — | readable | Motor torque compensation magnitude (raw x 8). |
| `total_error_count` | in | — | readable | Cumulative error/fault count since installation. |
| `total_power_kwh` | in | `0x16` | capability | Cumulative lifetime energy consumption in kWh. Monotonically increa... |
| `total_run_power_kwh` | in | `0x16` | capability | Cumulative run-mode energy in kWh. Separate from total_power_kwh (w... |
| `total_worked_hours` | in | — | readable | Total worked hours counter (lifetime). |
| `total_worked_minutes` | in | — | readable | Total worked minutes counter (lifetime). |
| `total_worked_seconds` | in | — | readable | Total worked seconds counter (lifetime). |
| `up_no_wind_feel` | — | `0x3D` | capability | Upper vane no-wind-feel mode. Prevents direct airflow from upper lo... |
| `vane_lr_angle` | in | — | readable | Left-right vane current angle position. |
| `vane_lr_lower` | in | — | readable | Left-right vane lower limit. |
| `vane_lr_status` | in | — | readable | Left-right vane strip operating status (2-bit enum). |
| `vane_lr_upper` | in | — | readable | Left-right vane upper limit. |
| `vane_top_status` | in | — | readable | Top vane strip operating status (2-bit enum). |
| `vane_ud_angle` | in | — | readable | Up-down vane current angle position. |
| `vane_ud_cool_lower` | in | — | readable | Up-down vane lower limit in cooling mode. |
| `vane_ud_cool_upper` | in | — | readable | Up-down vane upper limit in cooling mode. |
| `vane_ud_heat_lower` | in | — | readable | Up-down vane lower limit in heating mode. |
| `vane_ud_heat_upper` | in | — | readable | Up-down vane upper limit in heating mode. |
| `vane_ud_status` | in | — | readable | Up-down vane strip operating status (2-bit enum). |

## Capability-gated fields (by cap_id)

| Cap ID | Field(s) | Direction | Notes |
|--------|----------|-----------|-------|
| `0x09` | `wind_swing_ud_angle` (in/out) | |  |
| `0x0A` | `wind_swing_lr_angle` (in/out) | |  |
| `0x10` | `fan_speed` (in/out) | |  |
| `0x12` | `eco_mode` (in/out) | |  |
| `0x13` | `frost_protection` (in/out) | |  |
| `0x14` | `operating_mode` (in/out) | |  |
| `0x15` | `swing_horizontal` (in/out), `swing_vertical` (in/out) | |  |
| `0x16` | `current_run_power_kwh` (in), `realtime_power_kw` (in), `total_power_kwh` (in), `total_run_power_kwh` (in) | | Power monitoring; data from C1 group4 |
| `0x17` | `nest_filter_check` (—) | | Cap-as-value sensor (no B0 property) |
| `0x18` | `silky_cool` (in/out) | |  |
| `0x19` | `ptc_heater` (in/out) | |  |
| `0x1A` | `turbo_mode` (in/out) | |  |
| `0x1E` | `anion_ionizer` (in/out) | |  |
| `0x1F` | `humidity_setpoint` (in/out) | |  |
| `0x22` | `temperature_unit` (in/out) | |  |
| `0x24` | `screen_display` (in/out) | |  |
| `0x25` | `target_temperature` (in/out) | |  |
| `0x2C` | `buzzer` (in/out) | |  |
| `0x30` | `smart_eye` (in/out) | |  |
| `0x32` | `wind_straight` (in/out) | |  |
| `0x33` | `breeze_away` (in/out) | |  |
| `0x39` | `self_clean` (in/out) | |  |
| `0x3D` | `up_no_wind_feel` (—) | | Shell — no documented B0 property ID |
| `0x3E` | `down_no_wind_feel` (—) | | Shell — no documented B0 property ID |
| `0x42` | `breezeless` (in/out) | |  |
| `0x43` | `breeze_mild` (in/out) | |  |
| `0x48` | `rate_select` (in/out) | |  |
| `0x67` | `jet_cool` (in/out) | |  |

## Fields packed into cmd_0x40 (read-modify-write required)

Sending a `cmd_0x40` Set command without knowing the current state of these fields will **clobber siblings** sharing the same byte. Always use `build_command_body(status, changes, glossary)` which loads current state and overlays only the changes.

| Field | Direction | feature_available |
|-------|-----------|-------------------|
| `alarm_sleep` | in/out | readable |
| `buzzer` | in/out | capability |
| `catch_cold` | in/out | always |
| `child_sleep` | in/out | readable |
| `cleanup` | in/out | readable |
| `cosy_sleep` | in/out | always |
| `dry_clean` | in/out | always |
| `eco_mode` | in/out | readable |
| `energy_save` | in/out | always |
| `exchange_air` | out | readable |
| `fan_speed` | in/out | readable |
| `fan_speed_timer_bit` | out | always |
| `follow_me` | in/out | always |
| `frost_protection` | in/out | readable |
| `humidity_setpoint` | in/out | readable |
| `low_frequency_fan` | in/out | readable |
| `night_light` | in/out | always |
| `operating_mode` | in/out | readable |
| `power` | in/out | always |
| `power_off_timer` | in/out | readable |
| `power_on_timer` | in/out | readable |
| `power_save` | in/out | always |
| `protocol_bit1` | out | always |
| `ptc_heater` | in/out | readable |
| `resume` | in/out | always |
| `sleep_mode` | in/out | always |
| `strong_wind` | in/out | always |
| `swing_horizontal` | in/out | readable |
| `swing_reserved` | out | always |
| `swing_vertical` | in/out | readable |
| `target_temperature` | in/out | readable |
| `temperature_unit` | in/out | readable |
| `turbo_mode` | in/out | readable |

## Fields settable via cmd_0xb0 (independent TLV)

Each property is independent — safe to set one without knowing others.

| Field | Cap | feature_available |
|-------|:---:|-------------------|
| `anion_ionizer` | `0x1E` | capability |
| `aqua_wash_manual` | — | capability |
| `aqua_wash_switch` | — | capability |
| `aqua_wash_time` | — | capability |
| `breeze_away` | `0x33` | capability |
| `breeze_mild` | `0x43` | capability |
| `breezeless` | `0x42` | capability |
| `fresh_air_fan_speed` | — | capability |
| `fresh_air_switch` | — | capability |
| `jet_cool` | `0x67` | capability |
| `rate_select` | `0x48` | capability |
| `self_clean` | `0x39` | capability |
| `smart_eye` | `0x30` | capability |
| `water_pump` | — | capability |
| `wind_straight` | `0x32` | capability |
| `wind_swing_lr_angle` | `0x0A` | capability |
| `wind_swing_ud_angle` | `0x09` | capability |
