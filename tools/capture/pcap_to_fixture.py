"""Extract blaueis test-fixture YAML from an HVAC-shark PCAP.

Reads a PCAP captured by ``passive_capture.py`` (Ethernet/IP/UDP/HVAC_shark
encapsulation), filters frames by type/group, and writes a YAML
fixture in the format the codec tests expect (see existing
``tests/test-cases/xtremesaveblue_s7_frames/c1g1_frames.yaml``).

Usage::

    python pcap_to_fixture.py \\
        --pcap ../../HVAC-shark-dumps/passive_capture_s1/capture.pcap \\
        --frame-filter c1_group1 \\
        --device "Atelier Midea (cap 0x16=4)" \\
        --out /path/to/blaueis-libmidea/.../tests/test-cases/passive_capture_s1/c1g1_frames.yaml

Frame filters:
  c0           — 0xC0 status responses
  c1_group<N>  — 0xC1 Group N responses (N=0..7)
  a1           — 0xA1 heartbeats
  b1           — 0xB1 property responses
  b5           — 0xB5 capability responses
  all          — every frame in the pcap

Cross-project library use: ``--blaueis-lib`` defaults to a sibling
checkout, override if needed. Library is used here only to import
``parse_frame`` for body extraction (the same parser the codec tests
use), so fixtures end up shaped exactly like decoded test data.
"""

from __future__ import annotations

import argparse
import struct
import sys
from pathlib import Path


def _resolve_blaueis_lib(arg_value: str | None) -> Path:
    if arg_value:
        p = Path(arg_value).expanduser().resolve()
    else:
        p = (
            Path(__file__).resolve().parent.parent.parent.parent
            / "blaueis-libmidea"
            / "packages"
            / "blaueis-core"
            / "src"
        )
    if not (p / "blaueis" / "core" / "frame.py").is_file():
        raise SystemExit(f"ERROR: --blaueis-lib path does not contain blaueis/core/frame.py: {p}")
    return p


# ── PCAP reader (matches the writer in passive_capture.py) ─────────────


def read_pcap(pcap_path: Path):
    """Yield ``(ts, payload_bytes)`` for each packet in a PCAP file.

    Strips Ethernet (14 bytes) + IPv4 (variable IHL) + UDP (8 bytes)
    headers, leaves the UDP payload — which is the HVAC_shark layer.
    Skips packets whose framing doesn't match the layout written by
    ``passive_capture.py`` (Ethernet → IPv4 → UDP).
    """
    with open(pcap_path, "rb") as f:
        global_hdr = f.read(24)
        if len(global_hdr) < 24:
            return
        magic = struct.unpack("<I", global_hdr[:4])[0]
        if magic != 0xA1B2C3D4:
            raise SystemExit(f"unsupported pcap magic 0x{magic:08X}")
        while True:
            rec_hdr = f.read(16)
            if len(rec_hdr) < 16:
                return
            ts_sec, ts_usec, incl_len, _orig_len = struct.unpack("<IIII", rec_hdr)
            pkt = f.read(incl_len)
            if len(pkt) < incl_len:
                return
            if len(pkt) < 14 + 20 + 8:
                continue
            ip_start = 14
            ip_ihl = (pkt[ip_start] & 0x0F) * 4
            udp_start = ip_start + ip_ihl
            payload_start = udp_start + 8
            payload = pkt[payload_start:]
            yield ts_sec + ts_usec / 1_000_000, payload


def strip_hvac_shark_header(udp_payload: bytes) -> bytes | None:
    """Return the raw frame body, or None if header doesn't match."""
    if len(udp_payload) < 14:
        return None
    if not udp_payload.startswith(b"HVAC_shark"):
        return None
    # 10 bytes magic + manuf + bus + version
    return udp_payload[13:]


# ── Frame classification ───────────────────────────────────────────────


def classify_frame(parsed_body: bytes) -> str | None:
    """Return a filter key like 'c0', 'c1_group3', 'a1', ... or None."""
    if not parsed_body:
        return None
    tag = parsed_body[0]
    if tag == 0xC0 or tag == 0xA0:
        return "c0"
    if tag == 0xC1 and len(parsed_body) > 3:
        return f"c1_group{parsed_body[3] & 0x0F}"
    if tag == 0xA1:
        return "a1"
    if tag == 0xB1:
        return "b1"
    if tag == 0xB5:
        return "b5"
    return f"raw_0x{tag:02X}"


# ── Fixture writer ─────────────────────────────────────────────────────


def write_fixture(
    out_path: Path, *, device: str, frame_filter: str, frames: list[tuple[float, bytes]], notes_per_frame: list[str]
):
    """Write a YAML fixture matching the existing codec-test format.

    The shape mirrors ``tests/test-cases/xtremesaveblue_s7_frames/c1g1_frames.yaml``:
    a top-level ``device:`` and ``frames:`` list, where each frame has
    ``body_hex`` (the parsed frame body, NOT the on-wire bytes including
    the AA/length header — codec tests consume the body directly) and
    optional ``notes``.
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# Real {frame_filter.upper()} frames — {device}",
        "# Captured passively via HVAC-shark/tools/capture/passive_capture.py",
        "# Source pcap: HVAC-shark-dumps/passive_capture_s1/capture.pcap",
        "",
        f'device: "{device}"',
        "frames:",
    ]
    for (ts, body), note in zip(frames, notes_per_frame, strict=False):
        body_hex = " ".join(f"{b:02x}" for b in body)
        lines.append(f'  - body_hex: "{body_hex}"')
        lines.append(f"    timestamp: {ts:.3f}")
        if note:
            # YAML-safe quoting; keep notes single-line
            note_clean = note.replace('"', "'")
            lines.append(f'    notes: "{note_clean}"')
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ── CLI ────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--pcap", required=True, help="path to capture.pcap")
    parser.add_argument(
        "--frame-filter", required=True, help="frame type to extract: c0, c1_group<N>, a1, b1, b5, or all"
    )
    parser.add_argument("--device", required=True, help="device label for the fixture YAML")
    parser.add_argument("--out", required=True, help="output YAML path")
    parser.add_argument("--blaueis-lib", default=None, help="path to blaueis-core/src (default: sibling checkout)")
    args = parser.parse_args()

    blaueis_lib = _resolve_blaueis_lib(args.blaueis_lib)
    sys.path.insert(0, str(blaueis_lib))
    from blaueis.core.frame import parse_frame

    pcap = Path(args.pcap).expanduser().resolve()
    if not pcap.is_file():
        raise SystemExit(f"pcap not found: {pcap}")
    out = Path(args.out).expanduser().resolve()

    matching: list[tuple[float, bytes]] = []
    matching_notes: list[str] = []
    total = 0
    for ts, udp_payload in read_pcap(pcap):
        wire = strip_hvac_shark_header(udp_payload)
        if wire is None:
            continue
        try:
            parsed = parse_frame(wire)
        except Exception:
            continue
        body = parsed.get("body", b"") if isinstance(parsed, dict) else b""
        if not body:
            continue
        total += 1
        kind = classify_frame(body)
        if args.frame_filter == "all" or kind == args.frame_filter:
            matching.append((ts, body))
            matching_notes.append("")  # filled in by caller-driven post-processing if needed

    print(f"[extract] scanned {total} frames, matched {len(matching)} for '{args.frame_filter}'")
    if not matching:
        raise SystemExit(f"no frames matched filter {args.frame_filter!r}")

    write_fixture(
        out, device=args.device, frame_filter=args.frame_filter, frames=matching, notes_per_frame=matching_notes
    )
    print(f"[extract] wrote {out}")


if __name__ == "__main__":
    main()
