"""Passive WebSocket frame capture for blaueis-gw deployments.

Connects to a deployed blaueis-gateway (the WebSocket bridge running
alongside the dongle), performs the encrypted handshake, then listens
for ``type:"frame"`` messages without sending anything itself. The
gateway is already polling the AC continuously, so passive listening
yields full bidirectional bus traffic without injecting probes.

Output:
  - capture.jsonl        — raw gateway messages, one per line, schema-
                           preserving (ts, dir, hex). Survives format
                           changes in the PCAP encapsulation; the
                           authoritative archive.
  - capture.pcap         — Ethernet/IP/UDP-wrapped frames with the
                           HVAC_shark protocol header, decodable by
                           the tools/dissector/HVAC-shark_mid-xye.lua
                           Wireshark dissector.

Cross-project library use: imports blaueis.core.crypto via a sys.path
prepend. By default looks for blaueis-libmidea as a sibling checkout;
override with --blaueis-lib if it lives elsewhere. No pip-install
required — works on any layout that has the source tree present.

Usage::

    python passive_capture.py \\
        --gateway ws://192.168.210.30:8765 \\
        --psk-file /tmp/blaueis_psk \\
        --output-dir ../../blaueis-hvacshark-traces/passive_capture_s1 \\
        --duration 360

The script writes ``capture.jsonl`` continuously while running, then
builds ``capture.pcap`` and runs a tshark sanity-decode on shutdown.
Pass ``--skip-tshark`` to omit the verification step.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import struct
import subprocess
import sys
import time
from pathlib import Path

# ── Cross-project import of blaueis-libmidea ───────────────────────────


def _resolve_blaueis_lib(arg_value: str | None) -> Path:
    """Resolve the blaueis-libmidea source path.

    Default is sibling-checkout layout
    (``blaueis-hvacshark/`` and ``blaueis-libmidea/`` next to each other).
    Validate by checking that ``blaueis/core/frame.py`` exists at the
    resolved path so the failure is surfaced early with a clear message
    rather than as a cryptic ImportError later.
    """
    if arg_value:
        p = Path(arg_value).expanduser().resolve()
    else:
        # script lives at blaueis-hvacshark/tools/capture/passive_capture.py
        # default sibling: ../../../blaueis-libmidea/packages/blaueis-core/src
        p = (
            Path(__file__).resolve().parent.parent.parent.parent
            / "blaueis-libmidea"
            / "packages"
            / "blaueis-core"
            / "src"
        )
    if not (p / "blaueis" / "core" / "frame.py").is_file():
        raise SystemExit(
            f"ERROR: --blaueis-lib path does not contain blaueis/core/frame.py: {p}\n"
            "       Pass --blaueis-lib pointing at <repo>/packages/blaueis-core/src"
        )
    return p


# ── PCAP writer (no scapy required for the simple wrap) ────────────────

# Little-endian PCAP magic + global header.
_PCAP_MAGIC = 0xA1B2C3D4
_DLT_EN10MB = 1  # Ethernet, what tshark uses for the existing dumps
_HVAC_SHARK_MAGIC = b"HVAC_shark"  # 10 bytes
_MANUF_MIDEA = 0x01
_BUS_UART = 0x01
_HDR_VERSION_LEGACY = 0x00


def _write_pcap_global_header(f):
    f.write(
        struct.pack(
            "<IHHiIII",
            _PCAP_MAGIC,
            2,
            4,  # major, minor version
            0,
            0,  # thiszone, sigfigs
            65535,  # snaplen
            _DLT_EN10MB,
        )
    )


def _build_eth_ip_udp(ts_sec: float, payload: bytes) -> tuple[bytes, bytes]:
    """Wrap ``payload`` in Ethernet/IP/UDP for tshark decoding.

    Returns ``(pcap_record_header, packet_bytes)``. The packet uses
    locally-administered MAC sources, the gateway's IP as IPv4 src, and
    the broadcast IP as dst — the existing blaueis-hvacshark dumps use the
    same broadcast pattern. UDP src/dst port 22222 is what the
    dissector hooks.
    """
    # Ethernet — broadcast (matches existing blaueis-hvacshark pcap convention)
    eth_dst = b"\xff\xff\xff\xff\xff\xff"
    eth_src = b"\x02\x00\x00\x00\x00\x01"  # locally-administered
    eth_type = struct.pack("!H", 0x0800)  # IPv4

    # IPv4 — src = 192.168.210.30 (gateway), dst = 255.255.255.255
    ip_src = bytes([192, 168, 210, 30])
    ip_dst = bytes([255, 255, 255, 255])
    udp_len = 8 + len(payload)
    ip_total_len = 20 + udp_len

    ip_hdr = struct.pack(
        "!BBHHHBBH4s4s",
        0x45,  # version 4 + IHL 5
        0x00,  # DSCP/ECN
        ip_total_len,
        0x0000,  # ID
        0x0000,  # flags + fragment offset
        64,  # TTL
        17,  # protocol = UDP
        0x0000,  # checksum (filled below)
        ip_src,
        ip_dst,
    )
    # Replace IP checksum (one's complement of the 16-bit sum of header words).
    s = 0
    for i in range(0, len(ip_hdr), 2):
        s += (ip_hdr[i] << 8) | ip_hdr[i + 1]
    while s > 0xFFFF:
        s = (s & 0xFFFF) + (s >> 16)
    ip_checksum = (~s) & 0xFFFF
    ip_hdr = ip_hdr[:10] + struct.pack("!H", ip_checksum) + ip_hdr[12:]

    # UDP — checksum 0 (legal for IPv4, dissector ignores)
    udp_hdr = struct.pack("!HHHH", 22222, 22222, udp_len, 0)

    pkt = eth_dst + eth_src + eth_type + ip_hdr + udp_hdr + payload

    sec = int(ts_sec)
    usec = int((ts_sec - sec) * 1_000_000)
    rec = struct.pack("<IIII", sec, usec, len(pkt), len(pkt))
    return rec, pkt


def _build_hvac_shark_payload(frame_body: bytes) -> bytes:
    """Wrap raw Midea UART frame body in the HVAC_shark UDP-payload header."""
    return _HVAC_SHARK_MAGIC + bytes([_MANUF_MIDEA, _BUS_UART, _HDR_VERSION_LEGACY]) + frame_body


def jsonl_to_pcap(jsonl_path: Path, pcap_path: Path) -> int:
    """Read the JSONL capture, write a tshark-readable PCAP. Returns frame count."""
    n = 0
    with open(pcap_path, "wb") as out:
        _write_pcap_global_header(out)
        with open(jsonl_path, encoding="utf-8") as inp:
            for line in inp:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if rec.get("type") != "frame":
                    continue
                hex_str = rec.get("hex", "").replace(" ", "")
                if not hex_str:
                    continue
                try:
                    frame_body = bytes.fromhex(hex_str)
                except ValueError:
                    continue
                ts = rec.get("ts") or time.time()
                payload = _build_hvac_shark_payload(frame_body)
                rec_hdr, pkt = _build_eth_ip_udp(ts, payload)
                out.write(rec_hdr)
                out.write(pkt)
                n += 1
    return n


# ── tshark verification ────────────────────────────────────────────────


def verify_with_tshark(pcap_path: Path, dissector_path: Path | None) -> tuple[bool, str]:
    """Run tshark on the pcap, return (ok, summary).

    Strategy: rely on a system-installed copy of the blaueis-hvacshark
    dissector (Wireshark's plugins dir), since loading the same
    dissector twice via ``-X lua_script:`` errors with "two protocols
    with the same description". Only fall back to ``-X`` if the system
    copy is absent. ``dissector_path`` is the explicit override path.

    ``ok`` is False if tshark reports malformed/error decode or if the
    HVAC_shark protocol layer didn't show up. ``summary`` is a short
    human-readable report.
    """
    cmd = ["tshark", "-r", str(pcap_path), "-V"]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    except FileNotFoundError:
        return False, "tshark not installed (sudo apt install tshark)"
    except subprocess.TimeoutExpired:
        return False, "tshark timed out"
    if r.returncode != 0:
        return False, f"tshark exit={r.returncode}: {r.stderr.strip()[:200]}"
    out = r.stdout

    # Did the dissector run? If not, try loading it explicitly.
    if "HVAC Shark Protocol Data" not in out:
        if dissector_path is not None and dissector_path.is_file():
            cmd2 = ["tshark", "-r", str(pcap_path), "-X", f"lua_script:{dissector_path}", "-V"]
            r = subprocess.run(cmd2, capture_output=True, text=True, timeout=60)
            out = r.stdout
        if "HVAC Shark Protocol Data" not in out:
            return False, (
                "blaueis-hvacshark dissector did not run — install it as a "
                "Wireshark plugin or pass --dissector PATH (and ensure "
                "no duplicate system plugin shadows it)"
            )

    bad_markers = ("Malformed Packet", "[Expert Info (Error)", "[Malformed]")
    for m in bad_markers:
        if m in out:
            idx = out.find(m)
            ctx = out[max(0, idx - 80) : idx + 200].replace("\n", " ")
            return False, f"tshark flagged {m!r}: …{ctx}…"

    # Count frames decoded by the HVAC_shark layer specifically.
    hvac_frames = out.count("HVAC Shark Protocol Data")
    bus_uart = out.count("Bus Type: 1 (Bus = UART)")
    bus_xye = out.count("Bus Type: 0 (Bus = XYE)")
    crc_invalid = out.count("(Invalid)")
    return True, (
        f"clean — {hvac_frames} HVAC_shark layers decoded (UART={bus_uart}, XYE={bus_xye}, invalid-CRCs={crc_invalid})"
    )


# ── Capture loop ───────────────────────────────────────────────────────


async def capture_loop(args, jsonl_out):
    """Connect, handshake, stream frames into ``jsonl_out`` until duration elapses."""
    import websockets

    # Defer the blaueis import until after sys.path is populated.
    from blaueis.core.crypto import (
        complete_handshake_client,
        create_hello,
        psk_to_bytes,
    )

    psk_hex = Path(args.psk_file).read_text().strip()
    psk = psk_to_bytes(psk_hex)

    print(f"[capture] connecting to {args.gateway}…")
    async with websockets.connect(args.gateway, open_timeout=10) as ws:
        hello_msg, client_rand = create_hello()
        await ws.send(json.dumps(hello_msg))
        reply = json.loads(await asyncio.wait_for(ws.recv(), timeout=5.0))
        session = complete_handshake_client(psk, client_rand, reply)
        print(f"[capture] handshake ok — listening for {args.duration}s")

        deadline = time.monotonic() + args.duration
        n_frame = 0
        n_other = 0
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=remaining)
            except TimeoutError:
                break
            try:
                msg = session.decrypt_json(raw)
            except Exception as e:
                print(f"[capture] decrypt error: {e}", file=sys.stderr)
                continue
            jsonl_out.write(json.dumps(msg, ensure_ascii=False) + "\n")
            jsonl_out.flush()
            if msg.get("type") == "frame":
                n_frame += 1
            else:
                n_other += 1
        print(f"[capture] done: {n_frame} frames, {n_other} other messages")
        return n_frame, n_other


# ── CLI ────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--gateway", required=True, help="ws://host:port of the blaueis-gw")
    parser.add_argument("--psk-file", required=True, help="path to a file containing the PSK (single line)")
    parser.add_argument("--output-dir", required=True, help="directory to write capture.jsonl + capture.pcap")
    parser.add_argument("--duration", type=int, default=300, help="capture duration in seconds (default: 300)")
    parser.add_argument("--blaueis-lib", default=None, help="path to blaueis-core/src (default: sibling checkout)")
    parser.add_argument(
        "--dissector", default=None, help="path to HVAC-shark_mid-xye.lua (default: sibling tools/dissector)"
    )
    parser.add_argument("--skip-tshark", action="store_true", help="skip the post-capture tshark verification step")
    args = parser.parse_args()

    # Resolve and inject the blaueis-libmidea source path.
    blaueis_lib = _resolve_blaueis_lib(args.blaueis_lib)
    sys.path.insert(0, str(blaueis_lib))

    out_dir = Path(args.output_dir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    jsonl_path = out_dir / "capture.jsonl"
    pcap_path = out_dir / "capture.pcap"

    print(f"[capture] writing to {out_dir}")
    print(f"[capture] blaueis lib: {blaueis_lib}")

    # Capture
    with open(jsonl_path, "w", encoding="utf-8") as jsonl_out:
        n_frame, n_other = asyncio.run(capture_loop(args, jsonl_out))

    if n_frame == 0:
        print("[capture] WARNING: zero frames captured. Skipping pcap conversion.")
        return 1

    # Convert
    print(f"[convert] {jsonl_path.name} → {pcap_path.name}")
    n_written = jsonl_to_pcap(jsonl_path, pcap_path)
    print(f"[convert] wrote {n_written} frames to {pcap_path}")

    # Verify
    if args.skip_tshark:
        print("[verify] skipped (--skip-tshark)")
        return 0

    if args.dissector is None:
        diss = Path(__file__).resolve().parent.parent / "dissector" / "HVAC-shark_mid-xye.lua"
    else:
        diss = Path(args.dissector).expanduser().resolve()
    ok, summary = verify_with_tshark(pcap_path, diss if diss.is_file() else None)
    tag = "[verify] OK" if ok else "[verify] FAIL"
    print(f"{tag} — {summary}")
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
