# `tools/capture/` — passive frame capture for blaueis-gw deployments

Two scripts for capturing live frames from a deployed blaueis-gateway,
wrapping them in blaueis-hvacshark PCAP encapsulation, and extracting them
into the codec-test fixture format that lives in `blaueis-libmidea`.

## `passive_capture.py`

Connects to the gateway WebSocket, performs the encrypted handshake,
listens for `type:"frame"` messages, and writes both a JSONL archive
and a tshark-readable PCAP. The gateway is already polling the AC
continuously, so passive listening yields full bidirectional bus
traffic without injecting probes.

```bash
python passive_capture.py \
    --gateway ws://192.168.210.30:8765 \
    --psk-file /tmp/blaueis_psk \
    --output-dir ../../blaueis-hvacshark-traces/passive_capture_s1 \
    --duration 420
```

Output:

- `capture.jsonl` — raw gateway messages, one per line (`type`, `dir`,
  `hex`, `ts`). The authoritative archive — survives any later
  changes to the PCAP encapsulation.
- `capture.pcap` — Ethernet/IP/UDP/HVAC_shark wrapping, decodable by
  the bundled `tools/dissector/HVAC-shark_mid-xye.lua`.

The script verifies the PCAP with `tshark` after writing it; pass
`--skip-tshark` to omit. The PSK lives in a file passed via
`--psk-file` so it doesn't end up in process arguments / shell
history.

## `pcap_to_fixture.py`

Reads a captured PCAP, filters frames by type/group, writes a YAML
fixture in the format the `blaueis-libmidea` codec tests consume.

```bash
python pcap_to_fixture.py \
    --pcap ../../blaueis-hvacshark-traces/passive_capture_s1/capture.pcap \
    --frame-filter c1_group1 \
    --device "Atelier Midea" \
    --out /workspaces/hvac-shark-dev/blaueis-libmidea/.../tests/test-cases/passive_capture_s1/c1g1_frames.yaml
```

`--out` is required and explicit — no hidden writes into other repos.
The `--device` label goes into the fixture YAML; use the product-line
label or the deployment label, not internal model codes (per
`feedback_device_identity_is_caps`).

## `--blaueis-lib` argument (both scripts)

Both scripts cross-import `blaueis.core` for handshake/parse helpers.
They default to a sibling-checkout layout
(`../../../blaueis-libmidea/packages/blaueis-core/src` from this
directory). Override with `--blaueis-lib PATH` if your layout differs.
The path is validated by checking that `blaueis/core/frame.py` exists
inside it, so misconfiguration fails loudly with a clear message
rather than as an `ImportError`.

## Layout convention

- **Raw captures live in `blaueis-hvacshark-traces/passive_capture_sN/`** —
  one directory per session, with `capture.pcap`, `capture.jsonl`,
  and `notes.md`.
- **Codec test fixtures live in `blaueis-libmidea/.../tests/test-cases/passive_capture_sN/`**
  — derivatives extracted by `pcap_to_fixture.py`, consumed by the
  codec test suite.

This split keeps the heavy raw archive out of the protocol library
while still letting tests reference the curated frames.
