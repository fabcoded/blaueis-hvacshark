# UART Timing Analysis — Plan

> **Status: Executed (2026-04-14).** The analysis has been run and the
> results landed in `blaueis-hvacshark-traces/data-analysis/midea/uart/timing-analysis.md`.
> Headline outcome: `frame_spacing_ms` default raised from 100 to 150 ms
> (floor 80 ms, OEM median 116 ms, p95 775 ms). The rest of this doc is
> retained as a historical record of the plan — read
> `timing-analysis.md` for the actual numbers, conclusions, and
> confidence labels. The follow-ons in §7 (controlled cadence
> experiment, dissector delta column) remain open.

Related: `blaueis-libmidea/docs/flight_recorder.md` (in-memory debug buffer; built 2026-04-14 and now the preferred tool for gateway self-timing).

---

## 1. The open question

Is the blaueis gateway sending UART frames at a cadence the AC tolerates, and does it match what the OEM Wi-Fi dongle does? We currently run with `frame_spacing_ms = 100` (post-TX pause) and have never compared against OEM captures.

Concrete sub-questions the analysis must answer:

1. **Post-TX silence** — after an OEM dongle sends a frame, how long before it sends the next one? Min / median / p95 / max.
2. **Request→response latency** — how long does the AC take to start replying after the last byte of a query? (Spec says ~50 ms; we have one data point.)
3. **Poll period** — how often does the OEM dongle issue the full polling cycle? (Session 1 logic-analyzer: ~5.5 s; is this universal?)
4. **Per-message-type variance** — does the spacing differ by msg_type (e.g. B5 capability vs C0 query vs B1 property)?
5. **Collision / retry evidence** — any captures showing an AC NAK, missed reply, or device stall when the poller pushed harder?

---

## 2. What we have

| Source | Count | Format | Timing resolution | Notes |
|---|---|---|---|---|
| Logic-analyzer captures (Midea XtremeSaveBlue) | Sessions 1–15 (13 with data) | pcapng + `session.csv` | byte-level | `session.csv` has absolute `start_time`; both bus directions visible |
| Wi-Fi dongle captures (OEM) | 2 sessions | pcapng | frame-level (pcapng ts) | **Primary source for OEM cadence question** — 118 KB + 29 KB |
| External captures (mdrobnak, rymo) | 9 | hand-transcribed | **unusable** — no timing | Skip for this analysis |
| Live gateway probe dumps | Sessions 14–16 | JSON (`*_probe.json`) | gateway-recorded `ts` | Our own cadence; baseline for "what we do today" |

Existing timing mentions (scattered, not systematic):

- `Midea-XtremeSaveBlue-logicanalyzer/Session 1/findings.md:170-171` — "~0.198 s request/response; 5.5 s poll cycle".
- `protocols/midea/spec/protocol_uart.md:290` — "~50 ms echo delay" (single aside).
- Gateway constants: `uart_protocol.py:41-46, 121, 341`, `server.py:82`.

---

## 3. What we do not have

- Any per-capture timing summary.
- Any cross-capture comparison.
- A dedicated `timing.md` in `protocols/midea/spec/`.
- A dissector field that exposes inter-frame deltas (Wireshark has native frame timestamps; our Lua dissector does not compute deltas).
- Any controlled experiment varying our own cadence to find the minimum gap the AC tolerates.

---

## 4. Script — `tools/timing_analysis/analyze_timing.py`

Location: `blaueis-hvacshark/tools/timing_analysis/` (new directory).

### 4.1 Inputs

- Path to a capture directory or single file.
- Capture type auto-detected: pcapng, pcap, `session.csv`, probe JSON.
- Optional filter by msg_type (hex byte or name).

### 4.2 Per-capture metrics

For every capture, emit:

| Metric | Definition | Unit |
|---|---|---|
| `post_tx_gap` | time from end of TX frame to start of next TX frame from the same side | ms |
| `req_resp_latency` | time from end of request last byte to start of response first byte | ms |
| `resp_gap` | time from end of response to start of next request | ms |
| `poll_period` | time between identical msg_type queries from the polling side | s |
| `frame_on_wire` | duration of one frame at the bus baud (sanity cross-check) | ms |

Output per metric: count, min, p5, median, p95, max, stdev. Broken down by `(direction, msg_type)` pair.

### 4.3 Cross-capture aggregation

A second pass groups by capture source (OEM dongle / logic-analyzer / our gateway) and produces the comparison table that lands in `timing.md`.

### 4.4 Outputs

1. **Per-capture report** — one `<session>/timing_report.md` with tables + optional histograms (png, matplotlib).
2. **Combined CSV** — `timing_all.csv` with every observed gap, one row per observation, tagged `(source, session, direction, msg_type)`. Enables re-analysis without re-parsing pcaps.
3. **Summary doc** — `protocols/midea/spec/timing.md` (see §5).

### 4.5 Dependencies

- `pyshark` or `scapy` for pcapng. `pyshark` is simpler for Midea over USB-UART captures; `scapy` if we need tighter control.
- `pandas` for aggregation.
- `matplotlib` optional.
- All stay in the `blaueis-hvacshark/tools/` subtree; no new top-level deps.

### 4.6 Non-goals

- **No live probing of the AC** to find the minimum tolerable gap. That is a separate controlled experiment (§7), not this analysis. This pass is read-only on existing captures.
- No dissector changes. Delta-time fields in the Lua dissector are a nice-to-have, not required to answer the question.

---

## 5. Output doc — `protocols/midea/spec/timing.md`

Skeleton:

```
# Midea UART — Bus Timing Reference

> Source: own captures (logic-analyzer Sessions 1–15, OEM dongle Sessions 1–2)
> + gateway probe dumps. Confidence per row.

## 1. Headline cadences

| Source | Post-TX gap (median) | Req→Resp (median) | Poll period | Confidence |
|---|---|---|---|---|
| OEM Wi-Fi dongle | TBD | TBD | TBD | — |
| Logic-analyzer (Midea XtremeSaveBlue) | TBD | TBD | ~5.5 s | Consistent (one device) |
| blaueis gateway (current default) | 100 ms (configured) | n/a | TBD | Confirmed |

## 2. Per-msg_type breakdown
...
## 3. Tolerance envelope
...
## 4. Unresolved
...
```

Confidence labels per row. Any cell that cites only one session is **[Hypothesis]**; agreement across OEM + logic-analyzer is **[Consistent]**; disagreement is **[Disputed]** and stated as such.

---

## 6. Decisions that ride on the answer

| If OEM observes… | Then gateway should… |
|---|---|
| Post-TX gap ≥ 150 ms (median) | Raise `frame_spacing_ms` default to match OEM; 100 ms is risky on unknown devices. |
| Post-TX gap ≤ 80 ms consistently | Current 100 ms is conservative; no change. Document as validated. |
| High variance / bimodal distribution | Stay conservative at 100 ms but flag in `timing.md` that the OEM adapts — our fixed spacing may be suboptimal for some states. |
| Any NAK / retry / missed-reply evidence in any capture | Document the msg_type and state; add the minimum observed tolerant gap as the new floor. |

Per the §1.1 stateless invariant in `flight_recorder.md`: we do not assume all device variants behave identically. If OEM and logic-analyzer disagree, we pick the more conservative (slower) value and record the disagreement.

---

## 7. Follow-on (out of scope here, captured to not forget)

- **Controlled cadence experiment** on a live gateway — once the flight recorder is built, vary `frame_spacing_ms` downward in steps, watch the ring for missed replies. This is the only way to find the real floor. Must be opt-in and gated by a config flag.
- **Dissector delta-time column** in `HVAC-shark_mid-xye.lua` — exposes the existing pcap timestamps as a visible column, trivial change, makes manual eyeballing useful.
- **Gateway self-timing** — the flight recorder's `tx_seq` + `ts` already captures our own cadence for free once built; no extra work needed to baseline the gateway.

---

## 8. Steps — ordered

1. Create `blaueis-hvacshark/tools/timing_analysis/` — script skeleton, README, no parsing yet.
2. Implement `session.csv` ingestion (easiest; absolute timestamps, both directions).
3. Implement pcapng ingestion (via `pyshark`).
4. Implement metrics (§4.2) on one capture, sanity-check numbers against Session 1's existing "0.198 s / 5.5 s" note.
5. Batch across all 15 logic-analyzer sessions + 2 Wi-Fi dongle sessions; emit per-capture reports.
6. Produce `timing_all.csv`.
7. Write `protocols/midea/spec/timing.md` from the aggregated data.
8. If the answer changes our recommended `frame_spacing_ms`, open a separate change against `blaueis-gateway` config defaults — **not** in this pass.

---

## 9. Open questions — resolve before starting

1. **pyshark vs scapy** — pyshark is easier but requires tshark on the analyst's box; scapy is self-contained but verbose for UART-over-USB captures. Default to pyshark unless a quick prototype shows it misses frames.
2. **`session.csv` vs pcapng priority** — for logic-analyzer captures, CSV is faster to parse; pcapng is authoritative. Run both, assert they agree, flag any session where they don't.
3. **Minimum meaningful gap** — at 9600 bps + UART framing, one byte ≈ 1.04 ms. Sub-millisecond gaps are noise. Histogram bin at 1 ms; treat anything < 5 ms as "back-to-back" rather than a separate frame event.
4. **Do we include Q11 probe JSONs?** They are our own gateway's output, so they show only our cadence, not OEM. Include as the "current gateway" baseline row in the final table — yes, but labelled clearly.
