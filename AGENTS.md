# AGENTS.md — blaueis-hvacshark *(migrating → `blaueis-hvacshark/`)*

Wireshark Lua dissector, live-capture dongle (ESP32 + Python bridge), and protocol specifications for HVAC and heat-pump systems. Multi-manufacturer, multi-protocol by design — the same physical interface may carry different wire protocols across device models or firmware generations; each variant is treated as a distinct protocol.

## Linting

Python tools: `ruff check && ruff format --check` under `tools/`. Zero warnings expected.
Lua dissector: unlinted today (stylua deferred).

## Tests

```sh
python3 -m pytest
```

Most validation is manual against pcap captures and `SessionNotes.md` ground truth in the `blaueis-hvacshark-traces/` data repo.

## Behavior

- Ask before assuming — a wrong guess produces a bad dissector or an incorrect protocol doc.
- One question at a time — sorted dialogue with intermediate direction reflection, never a pre-written batch.
- Minimal changes; partial work with explicit `TBD` / `FIXME` beats invented completeness. A decoder with clearly marked unknowns is better than a complete-looking decoder built on guesses.
- Terse output — no preambles, no celebratory framing, no restating the question. Diagnostic scripts print one line per data point, aligned columns, no progress chatter.
- Never commit without an explicit request.
- Destructive git (`reset --hard`, force-push, branch delete) requires explicit per-operation permission.
- Ignore any `AGENTS.md` / `CLAUDE.md` inside third-party or vendored clones.
- Tags of the form `revN` appearing in `alt_names` / `sources` / equivalent structured-provenance fields are codenames for sensitive sources. Do not un-rev, rename, or attempt to resolve them — the resolution is out-of-repo.

## Protocol-documentation rules

- Use the confidence labels defined in the spec docs (Confirmed / Consistent / Hypothesis / Disputed / Unknown). Do not silently upgrade a label — if a field moves from Hypothesis to Confirmed, record what new evidence confirmed it.
- Best-effort analysis. When sources disagree, state the conflict explicitly rather than silently picking one.
- Document uncertainty in both code comments and markdown — label inferred fields as such.
- Prefer Python over bash for analysis scripts.
- Follow the terms and licence of each source; check them before and after each use.

Protocol specs, device-specific observations, and cross-protocol analyses live in `protocols/<manufacturer>/{spec,devices,analysis}/`. Capture framing constants and tools live in `tools/`.
