#!/usr/bin/env python3
"""
Midea HVAC UART control — minimal CLI for Raspberry Pi.

Talks to a Midea AC unit over the CN3 Wi-Fi dongle UART port.
Protocol details: HVAC-shark/protocols/midea/spec/protocol_uart.md
                  HVAC-shark/protocols/midea/spec/serial_protocol.md

Boot sequence (per midea_uart_protocol_reference.md):
  1. MSG 0x07 (SN query, broadcast 0xFF) → learn appliance type
  2. MSG 0xA0 (Model query) → learn model number
  3. MSG 0x0D (Network init) → announce presence
  4. Send 0x41 status query, parse 0xC0 response

Raspberry Pi UART prerequisites:
  The serial console and Bluetooth may block UART communication.
  Before using, ensure BOTH are disabled:
  - Serial console: remove 'console=serial0,115200' from /boot/firmware/cmdline.txt
  - Serial login: raspi-config → Interface → Serial → login=No, hardware=Yes
  - Bluetooth on UART (Pi 3/4/5): add 'dtoverlay=disable-bt' to config.txt
  Reboot after changes.
"""

import argparse
import sys
import time

import serial

# ---------------------------------------------------------------------------
# CRC-8/MAXIM lookup table (protocol_uart.md §3.3)
# ---------------------------------------------------------------------------
# fmt: off
CRC8_TABLE = [
    0x00, 0x5E, 0xBC, 0xE2, 0x61, 0x3F, 0xDD, 0x83,
    0xC2, 0x9C, 0x7E, 0x20, 0xA3, 0xFD, 0x1F, 0x41,
    0x9D, 0xC3, 0x21, 0x7F, 0xFC, 0xA2, 0x40, 0x1E,
    0x5F, 0x01, 0xE3, 0xBD, 0x3E, 0x60, 0x82, 0xDC,
    0x23, 0x7D, 0x9F, 0xC1, 0x42, 0x1C, 0xFE, 0xA0,
    0xE1, 0xBF, 0x5D, 0x03, 0x80, 0xDE, 0x3C, 0x62,
    0xBE, 0xE0, 0x02, 0x5C, 0xDF, 0x81, 0x63, 0x3D,
    0x7C, 0x22, 0xC0, 0x9E, 0x1D, 0x43, 0xA1, 0xFF,
    0x46, 0x18, 0xFA, 0xA4, 0x27, 0x79, 0x9B, 0xC5,
    0x84, 0xDA, 0x38, 0x66, 0xE5, 0xBB, 0x59, 0x07,
    0xDB, 0x85, 0x67, 0x39, 0xBA, 0xE4, 0x06, 0x58,
    0x19, 0x47, 0xA5, 0xFB, 0x78, 0x26, 0xC4, 0x9A,
    0x65, 0x3B, 0xD9, 0x87, 0x04, 0x5A, 0xB8, 0xE6,
    0xA7, 0xF9, 0x1B, 0x45, 0xC6, 0x98, 0x7A, 0x24,
    0xF8, 0xA6, 0x44, 0x1A, 0x99, 0xC7, 0x25, 0x7B,
    0x3A, 0x64, 0x86, 0xD8, 0x5B, 0x05, 0xE7, 0xB9,
    0x8C, 0xD2, 0x30, 0x6E, 0xED, 0xB3, 0x51, 0x0F,
    0x4E, 0x10, 0xF2, 0xAC, 0x2F, 0x71, 0x93, 0xCD,
    0x11, 0x4F, 0xAD, 0xF3, 0x70, 0x2E, 0xCC, 0x92,
    0xD3, 0x8D, 0x6F, 0x31, 0xB2, 0xEC, 0x0E, 0x50,
    0xAF, 0xF1, 0x13, 0x4D, 0xCE, 0x90, 0x72, 0x2C,
    0x6D, 0x33, 0xD1, 0x8F, 0x0C, 0x52, 0xB0, 0xEE,
    0x32, 0x6C, 0x8E, 0xD0, 0x53, 0x0D, 0xEF, 0xB1,
    0xF0, 0xAE, 0x4C, 0x12, 0x91, 0xCF, 0x2D, 0x73,
    0xCA, 0x94, 0x76, 0x28, 0xAB, 0xF5, 0x17, 0x49,
    0x08, 0x56, 0xB4, 0xEA, 0x69, 0x37, 0xD5, 0x8B,
    0x57, 0x09, 0xEB, 0xB5, 0x36, 0x68, 0x8A, 0xD4,
    0x95, 0xCB, 0x29, 0x77, 0xF4, 0xAA, 0x48, 0x16,
    0xE9, 0xB7, 0x55, 0x0B, 0x88, 0xD6, 0x34, 0x6A,
    0x2B, 0x75, 0x97, 0xC9, 0x4A, 0x14, 0xF6, 0xA8,
    0x74, 0x2A, 0xC8, 0x96, 0x15, 0x4B, 0xA9, 0xF7,
    0xB6, 0xE8, 0x0A, 0x54, 0xD7, 0x89, 0x6B, 0x35,
]
# fmt: on

MODE_MAP = {1: "Auto", 2: "Cool", 3: "Dry", 4: "Heat", 5: "Fan"}
MODE_NAMES = {"auto": 1, "cool": 2, "dry": 3, "heat": 4, "fan": 5}
FAN_MAP = {102: "Auto", 100: "Turbo", 80: "High", 60: "Medium", 40: "Low", 20: "Silent"}


def crc8(data):
    """CRC-8 over body bytes (frame[10:-2])."""
    crc = 0
    for b in data:
        crc = CRC8_TABLE[crc ^ b]
    return crc


def checksum(frame):
    """Additive checksum over bytes 1..N-2 (protocol_uart.md §3.2)."""
    return (256 - sum(frame[1:])) & 0xFF


def hex_str(data):
    return " ".join(f"{b:02X}" for b in data)


# ---------------------------------------------------------------------------
# Frame construction / validation
# ---------------------------------------------------------------------------


def build_frame(msg_type, body, protocol=0x00):
    """Build a complete UART frame: AA LEN AC SYNC 00 00 00 00 PROTO msg_type body CRC CHK.
    LENGTH includes CRC but not checksum (matches dudanov/MideaUART)."""
    frame = bytearray([0xAA, 0x00, 0xAC, 0x00, 0x00, 0x00, 0x00, 0x00, protocol, msg_type])
    frame.extend(body)
    frame.append(crc8(frame[10:]))  # CRC-8 over body — becomes part of frame
    frame[1] = len(frame)  # LENGTH = header + body + CRC (excludes byte 0 and checksum)
    frame[3] = frame[1] ^ frame[2]  # SYNC
    frame.append(checksum(frame))  # checksum over bytes 1..N-1 (last byte added)
    return bytes(frame)


def validate_frame(data):
    """Validate a received frame. Returns (ok, body, errors)."""
    errors = []
    if len(data) < 12:
        return False, b"", ["Frame too short"]
    if data[0] != 0xAA:
        errors.append(f"Start byte 0x{data[0]:02X} != 0xAA")
    expected_len = data[1]
    if expected_len != len(data) - 1:
        errors.append(f"Length field {expected_len} != actual {len(data) - 1}")

    body = data[10:-2]
    rx_crc = data[-2]
    rx_chk = data[-1]

    calc_crc = crc8(body)
    if rx_crc != calc_crc:
        errors.append(f"CRC 0x{rx_crc:02X} != expected 0x{calc_crc:02X}")

    calc_chk = (256 - sum(data[1:-1])) & 0xFF
    if rx_chk != calc_chk:
        errors.append(f"Checksum 0x{rx_chk:02X} != expected 0x{calc_chk:02X}")

    return len(errors) == 0, body, errors


# ---------------------------------------------------------------------------
# Command builders
# ---------------------------------------------------------------------------


def build_network_notify(protocol=0x00):
    """Network notification (0x0D) — 'I am a dongle, I exist'.
    Matches dudanov/MideaUART NetworkNotifyData."""
    body = bytearray(
        [
            0x01,
            0x01,
            0x00,  # connected, wifi=on, mode
            0x00,
            0x00,
            0x00,
            0x00,  # IP (0.0.0.0 — no real wifi)
            0xFF,  # fixed
            0x01,  # signal strength (1=none, good enough)
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,  # DHCP/DNS
            0x00,
            0x00,
            0x00,
            0x00,  # connection detail + padding
        ]
    )
    return build_frame(0x0D, body, protocol)


def build_network_reply(protocol=0x00):
    """Reply to 0x63 query — same payload as 0x0D but with msg_type 0x63."""
    body = bytearray(
        [
            0x01,
            0x01,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0xFF,
            0x01,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
        ]
    )
    return build_frame(0x63, body, protocol)


def build_query(protocol=0x00):
    """Status query (0x41, serial_protocol.md §3.1.1).
    Body from dudanov/MideaUART QueryStateData — community UART path."""
    body = bytearray(
        [
            0x41,
            0x81,
            0x00,
            0xFF,
            0x03,
            0xFF,
            0x00,
            0x02,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x03,
            0x00,  # body[20]=0x03, body[21]=MSG_ID (0 for now)
        ]
    )
    return build_frame(0x03, body, protocol)


def build_set(temp, mode_name, power=True, protocol=0x00):
    """Set status command (0x40, serial_protocol.md §3.2)."""
    mode_val = MODE_NAMES.get(mode_name)
    if mode_val is None:
        raise ValueError(f"Unknown mode '{mode_name}', use: {', '.join(MODE_NAMES)}")
    if not (16 <= temp <= 30):
        raise ValueError(f"Temperature {temp} out of range 16-30°C")

    body = bytearray(26)
    body[0] = 0x40
    # body[1]: power(bit0) + always-set(bit1) + beep(bit6)
    body[1] = 0x42 | (0x01 if power else 0x00)
    # body[2]: mode(bits 7:5) + temp-16(bits 3:0)
    temp_int = int(temp)
    temp_half = 1 if (temp % 1) >= 0.5 else 0
    body[2] = (mode_val << 5) | (temp_half << 4) | (temp_int - 16)
    # body[3]: fan auto
    body[3] = 102
    # body[7]: swing defaults
    body[7] = 0x30
    return build_frame(0x02, body, protocol)


# ---------------------------------------------------------------------------
# Response parser
# ---------------------------------------------------------------------------


def is_status_response(body):
    """Check if body is a status response (0xC0 or 0xA0 variant)."""
    return len(body) > 0 and body[0] in (0xC0, 0xA0)


def ts():
    """Timestamp string for logging."""
    return time.strftime("%H:%M:%S") + f".{int(time.time() * 1000) % 1000:03d}"


def parse_c0(body):
    """Parse 0xC0 / 0xA0 status response (serial_protocol.md §4.1).
    0xA0 (msg_type 0x05) uses the same field layout as 0xC0."""
    if not is_status_response(body):
        return {"error": f"Not a status response (got 0x{body[0]:02X})"}

    power = bool(body[1] & 0x01)
    mode_val = (body[2] >> 5) & 0x07
    temp_int = (body[2] & 0x0F) + 16
    temp_half = 0.5 if (body[2] & 0x10) else 0.0
    setpoint = temp_int + temp_half
    fan_raw = body[3] & 0x7F
    fan = FAN_MAP.get(fan_raw, str(fan_raw))

    indoor = (body[11] - 50) / 2.0 if len(body) > 11 and body[11] != 0xFF else None
    outdoor = (body[12] - 50) / 2.0 if len(body) > 12 and body[12] != 0xFF else None

    # decimal precision (body[15] if present)
    if len(body) > 15 and body[15] > 0:
        t1_dot = body[15] & 0x0F
        t4_dot = (body[15] >> 4) & 0x0F
        if indoor is not None and t1_dot > 0:
            sign = 1 if (body[11] - 50) >= 0 else -1
            indoor = ((body[11] - 50) // 2) + sign * t1_dot * 0.1
        if outdoor is not None and t4_dot > 0:
            sign = 1 if (body[12] - 50) >= 0 else -1
            outdoor = ((body[12] - 50) // 2) + sign * t4_dot * 0.1

    eco = bool(body[9] & 0x10) if len(body) > 9 else False
    turbo = bool(body[10] & 0x02) if len(body) > 10 else False

    return {
        "power": power,
        "mode": MODE_MAP.get(mode_val, f"?({mode_val})"),
        "setpoint": setpoint,
        "fan": fan,
        "indoor": indoor,
        "outdoor": outdoor,
        "eco": eco,
        "turbo": turbo,
    }


def print_status(info):
    pwr = "ON" if info["power"] else "OFF"
    parts = [f"Power: {pwr}", f"Mode: {info['mode']}", f"Setpoint: {info['setpoint']:.1f}°C", f"Fan: {info['fan']}"]
    if info["eco"]:
        parts.append("ECO")
    if info["turbo"]:
        parts.append("TURBO")
    print("    " + " | ".join(parts))
    temps = []
    if info["indoor"] is not None:
        temps.append(f"Indoor: {info['indoor']:.1f}°C")
    if info["outdoor"] is not None:
        temps.append(f"Outdoor: {info['outdoor']:.1f}°C")
    if temps:
        print("    " + " | ".join(temps))


# ---------------------------------------------------------------------------
# Serial I/O — persistent connection
# ---------------------------------------------------------------------------


def read_frame(ser):
    """Read one complete frame from the serial port. Returns bytes or None on timeout."""
    # Scan for 0xAA start byte
    while True:
        b = ser.read(1)
        if not b:
            return None
        if b[0] == 0xAA:
            break

    # Read length byte
    length_byte = ser.read(1)
    if not length_byte:
        return None

    # Read remaining bytes: length includes itself, we already read it
    remaining = length_byte[0] - 1
    if remaining < 0 or remaining > 250:
        return None
    rest = ser.read(remaining)
    if len(rest) < remaining:
        return None

    return bytes([0xAA]) + length_byte + rest


def send_frame(ser, frame):
    """Send a frame and print it."""
    print(f"[{ts()}] TX: {hex_str(frame)}")
    ser.write(frame)
    ser.flush()


def print_rx(data):
    """Print received frame with validation."""
    print(f"[{ts()}] RX: {hex_str(data)}")
    ok, body, errors = validate_frame(data)
    crc_ok = not any("CRC" in e for e in errors)
    chk_ok = not any("Checksum" in e for e in errors)
    print(f"    CRC: {'OK' if crc_ok else 'FAIL'} | Checksum: {'OK' if chk_ok else 'FAIL'}")
    for e in errors:
        print(f"    ERROR: {e}")
    return ok, body


def get_msg_type(data):
    """Extract msg_type from a raw frame."""
    if len(data) > 9:
        return data[9]
    return None


# ---------------------------------------------------------------------------
# Main loop — listen, handshake, then command
# ---------------------------------------------------------------------------


def get_protocol(data):
    """Extract PROTOCOL byte (offset 8) from a raw frame."""
    return data[8] if len(data) > 8 else 0x00


def send_and_read(ser, frame, proto, retries=3):
    """Send frame, read responses, skip non-status frames.
    Returns (ok, body) or (False, b'') on failure."""
    for attempt in range(retries):
        send_frame(ser, frame)
        for _ in range(5):
            rx = read_frame(ser)
            if rx is None:
                break
            ok, body = print_rx(rx)
            msg_type = get_msg_type(rx)
            if msg_type == 0x63:
                print("    -> 0x63 query, replying...")
                send_frame(ser, build_network_reply(proto))
                continue
            if ok and is_status_response(body):
                return True, body
            body0 = f"0x{body[0]:02X}" if body else "?"
            print(f"    (skipping msg_type=0x{msg_type:02X} body[0]={body0})")
        if attempt < retries - 1:
            print(f"    Retry {attempt + 2}/{retries}...")
            time.sleep(1.0)
    return False, b""


def build_sn_query():
    """SN query (0x07) — first boot frame, broadcast Appliance=0xFF."""
    frame = bytearray([0xAA, 0x00, 0xFF, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x07])
    frame.extend([0x00])  # body = 1 byte
    frame.append(crc8(frame[10:]))
    frame[1] = len(frame)
    frame[3] = frame[1] ^ frame[2]
    frame.append(checksum(frame))
    return bytes(frame)


def build_rac_sn_query():
    """RAC SN query (0x65) — fallback for multi-split, broadcast."""
    frame = bytearray([0xAA, 0x00, 0xFF, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x65])
    frame.extend([0x00] * 20)  # body = 20 zero bytes
    frame.append(crc8(frame[10:]))
    frame[1] = len(frame)
    frame[3] = frame[1] ^ frame[2]
    frame.append(checksum(frame))
    return bytes(frame)


def build_model_query(appliance=0xAC, protocol=0x00):
    """Model query (0xA0) — uses discovered appliance type."""
    frame = bytearray([0xAA, 0x00, appliance, 0x00, 0x00, 0x00, 0x00, 0x00, protocol, 0xA0])
    frame.extend([0x00] * 20)  # body = 20 zero bytes
    frame.append(crc8(frame[10:]))
    frame[1] = len(frame)
    frame[3] = frame[1] ^ frame[2]
    frame.append(checksum(frame))
    return bytes(frame)


def run_handshake(ser, timeout=30):
    """Standard dongle boot sequence per midea_uart_protocol_reference.md.

    Step 1: MSG 0x07 (SN query, broadcast) → learn appliance, proto, sub, SN
    Step 2: MSG 0xA0 (Model query) → learn model number
    Step 3: MSG 0x0D (Network init) → announce presence

    Returns (appliance, proto, sub, model, sn) or raises on total failure.
    """
    appliance = 0xFF
    proto = 0x00
    sub = 0x00
    model = 0
    sn = ""

    # ── Step 1: DISCOVER — SN query ──────────────────────────────
    print("\n--- Step 1: DISCOVER (SN query 0x07, broadcast) ---")
    for attempt in range(6):
        if attempt > 0:
            print(f"    Retry {attempt + 1}/6...")
            time.sleep(0.3)

        send_frame(ser, build_sn_query())
        rx = read_frame(ser)

        if rx is None:
            # Try RAC SN query (0x65) as fallback
            print(f"[{ts()}] No response to 0x07, trying 0x65...")
            send_frame(ser, build_rac_sn_query())
            rx = read_frame(ser)

        if rx is not None:
            ok, body = print_rx(rx)
            msg_type = get_msg_type(rx)

            # Any response tells us the device type
            appliance = rx[2] if len(rx) > 2 else 0xAC
            proto = rx[8] if len(rx) > 8 else 0x00
            sub = rx[7] if len(rx) > 7 else 0x00  # SUB at offset 7 per reference

            if msg_type in (0x07, 0x65) and body:
                sn = body.decode("ascii", errors="replace").rstrip("\x00")
                print(f"    -> SN: {sn[:32]}")

            print(f"    -> Learned: appliance=0x{appliance:02X} proto=0x{proto:02X}")
            break

        # Handle AC-initiated frames during discovery
        if rx is not None:
            msg_type = get_msg_type(rx)
            if msg_type == 0x63:
                print("    -> 0x63 during discover, replying...")
                send_frame(ser, build_network_reply(proto))
    else:
        print("    No response after 6 attempts")
        # Continue with defaults — AC might still respond to later frames

    # ── Step 2: MODEL — model query ──────────────────────────────
    if appliance != 0xFF:
        print(f"\n--- Step 2: MODEL query (0xA0, appliance=0x{appliance:02X}) ---")
        send_frame(ser, build_model_query(appliance, proto))
        rx = read_frame(ser)
        if rx is not None:
            ok, body = print_rx(rx)
            if ok and len(body) >= 4:
                model = body[2] | (body[3] << 8)
                print(f"    -> Model: {model} (0x{model:04X})")
            # Handle 0x63 if AC queries during model
            if get_msg_type(rx) == 0x63:
                send_frame(ser, build_network_reply(proto))
        else:
            print("    No response (continuing)")
    else:
        print("\n--- Step 2: MODEL skipped (no device found) ---")

    # ── Step 3: ANNOUNCE — network init ──────────────────────────
    print("\n--- Step 3: ANNOUNCE (0x0D network init) ---")
    send_frame(ser, build_network_notify(proto))
    # Give AC a moment to process
    time.sleep(0.3)

    # Drain any immediate responses (0x63, heartbeats)
    for _ in range(3):
        rx = read_frame(ser)
        if rx is None:
            break
        ok, body = print_rx(rx)
        msg_type = get_msg_type(rx)
        if msg_type == 0x63:
            print("    -> 0x63 query, replying...")
            send_frame(ser, build_network_reply(proto))
        else:
            body0 = f"0x{body[0]:02X}" if body else "?"
            print(f"    -> msg_type=0x{msg_type:02X} body[0]={body0}")

    print(f"\n--- Handshake complete: appliance=0x{appliance:02X} proto=0x{proto:02X} model=0x{model:04X} ---")
    return appliance, proto, sub, model, sn


def run_session(port, action, action_args=None, timeout_handshake=30):
    """
    Standard boot sequence per midea_uart_protocol_reference.md:
    1. MSG 0x07 (SN query, broadcast) → learn device
    2. MSG 0xA0 (Model query) → learn model
    3. MSG 0x0D (Network init) → announce
    4. Execute action
    """
    ser = serial.Serial(port, 9600, timeout=2.0)
    print(f"[{ts()}] Opened {port} @ 9600 8N1")

    # Run standard handshake
    appliance, proto, sub, model, sn = run_handshake(ser, timeout=timeout_handshake)

    print(f"\n--- PROTOCOL=0x{proto:02X}, executing: {action} ---")
    time.sleep(0.5)

    # Step 3: Execute action
    if action == "detect":
        ok, body = send_and_read(ser, build_query(proto), proto)
        if ok:
            print("    Midea AC detected and responding!")
            print_status(parse_c0(body))
            result = 0
        else:
            print("    No status response.")
            result = 1

    elif action == "status":
        ok, body = send_and_read(ser, build_query(proto), proto)
        if ok:
            print_status(parse_c0(body))
            result = 0
        else:
            print("    No status response.")
            result = 1

    elif action == "set":
        ok, body = send_and_read(ser, build_set(action_args["temp"], action_args["mode"], protocol=proto), proto)
        if ok:
            print("    Applied:")
            print_status(parse_c0(body))
            result = 0
        else:
            print("    No status response after set.")
            result = 1

    elif action == "loop":
        interval = action_args.get("interval", 5.0)
        print(f"    Polling every {interval}s — Ctrl+C to stop\n")
        result = 0
        try:
            while True:
                # Drain incoming
                ser.timeout = 0.3
                while True:
                    rx = read_frame(ser)
                    if rx is None:
                        break
                    ok, body = print_rx(rx)
                    if get_msg_type(rx) == 0x63:
                        print("    -> Replying to 0x63...")
                        send_frame(ser, build_network_reply(proto))
                    elif ok and is_status_response(body):
                        print_status(parse_c0(body))

                # Query
                ser.timeout = 2.0
                print(f"\n--- poll @ {time.strftime('%H:%M:%S')} ---")
                ok, body = send_and_read(ser, build_query(proto), proto, retries=1)
                if ok:
                    print_status(parse_c0(body))

                time.sleep(interval)
        except KeyboardInterrupt:
            print("\nStopped.")

    elif action == "listen":
        # Raw bus listener — no handshake, no queries, just print everything
        print("    Listening for raw UART traffic — Ctrl+C to stop\n")
        result = 0
        baud_rates = action_args.get("scan_bauds") if action_args else None
        if baud_rates:
            # Baud rate scan mode
            for baud in baud_rates:
                ser.close()
                ser = serial.Serial(port, baud, timeout=3.0)
                ser.reset_input_buffer()
                time.sleep(0.1)
                data = ser.read(200)
                if data:
                    aa_count = data.count(0xAA)
                    print(f"  {baud:>6} baud: {len(data):3d} bytes, {aa_count} x 0xAA  |  {hex_str(data[:30])}")
                else:
                    print(f"  {baud:>6} baud: nothing")
                time.sleep(0.3)
            print("\n  If one rate shows 0xAA with clean framing, that's correct.")
        else:
            ser.timeout = 5.0
            try:
                while True:
                    rx = read_frame(ser)
                    if rx is not None:
                        print_rx(rx)
                    else:
                        # Also show raw bytes if no valid frame
                        ser.timeout = 0.5
                        raw = ser.read(100)
                        if raw:
                            print(f"[{ts()}] RAW ({len(raw)}B): {hex_str(raw)}")
                        ser.timeout = 5.0
            except KeyboardInterrupt:
                print("\nStopped.")

    else:
        result = 1

    ser.close()
    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main():
    p = argparse.ArgumentParser(description="Midea HVAC UART control")
    p.add_argument("--port", default="/dev/serial0", help="Serial port (default: /dev/serial0)")
    p.add_argument("--timeout", type=float, default=30, help="Handshake timeout in seconds (default: 30)")
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("detect", help="Standard handshake (0x07→0xA0→0x0D) + status query")
    sub.add_parser("status", help="Handshake + query current AC status")

    sp_set = sub.add_parser("set", help="Handshake + set temperature and mode")
    sp_set.add_argument("--temp", type=float, required=True, help="Target temperature 16-30°C")
    sp_set.add_argument("--mode", required=True, choices=list(MODE_NAMES.keys()), help="Operating mode")

    sp_loop = sub.add_parser("loop", help="Continuous polling loop")
    sp_loop.add_argument("--interval", "-i", type=float, default=5.0, help="Poll interval in seconds (default: 5)")

    sp_listen = sub.add_parser("listen", help="Raw UART listener (no handshake, no queries)")
    sp_listen.add_argument("--scan", action="store_true", help="Scan multiple baud rates for activity")

    args = p.parse_args()

    if args.command == "set":
        action_args = {"temp": args.temp, "mode": args.mode}
    elif args.command == "loop":
        action_args = {"interval": args.interval}
    elif args.command == "listen":
        action_args = {"scan_bauds": [4800, 9600, 19200, 38400, 57600, 115200]} if args.scan else None
    else:
        action_args = None

    sys.exit(run_session(args.port, args.command, action_args, args.timeout))


if __name__ == "__main__":
    main()
