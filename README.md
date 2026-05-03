# blaueis-hvacshark

Part of the [Blaueis](https://github.com/fabcoded) project umbrella.
Protocol library and gateway code lives in
[blaueis-libmidea](https://github.com/fabcoded/blaueis-libmidea).
Capture sessions live in
[blaueis-hvacshark-traces](https://github.com/fabcoded/blaueis-hvacshark-traces).

> Blaueis is a small glacier in the Bavarian Alps, retreating year by year.
> Use energy responsibly — climate change is real.

Open-source protocol research toolkit for HVAC and heat pump systems.
Captures, decodes, and dissects the internal communication buses of air
conditioning and heat pump units to build open, well-documented knowledge of
how these systems communicate — enabling better user experiences and advanced
integrations: Home Assistant automations, PV-optimised operation, improved
eco-friendliness, and more.

Multi-manufacturer and multi-protocol by design: the same physical interface
may carry different data protocols across device models or generations, and the
project treats each such variant as a distinct protocol. Currently focused on
the Midea/Carrier family, with the architecture ready for additional
manufacturers.

## Disclaimer and intended use

This code is provided for research and educational purposes only. There is absolutely
no warranty that it works as intended. Use of this code should not encourage anyone
to work on their HVAC systems, as doing so carries risks of personal injury or
property damage. The author is not responsible for any harm or damage resulting
from the use of this code.

**Brand names and trademarks**: Any manufacturer, product, or model names mentioned
in this repository are used solely to identify the hardware under test. Their use is
purely descriptive — to specify which physical device was captured — and does not
imply affiliation, endorsement, or any commercial relationship with the respective
trademark holders. All trademarks remain the property of their respective owners.

This repository aggregates publicly available information for research and debugging
purposes. If you have concerns about brand name usage or attribution, please open an
issue or contact the author directly.

## Components

| Component | Path | Description |
|-----------|------|-------------|
| Wireshark Lua dissectors | `tools/dissector/` | Dissects HVAC_shark UDP frames in Wireshark (one per manufacturer family) |
| ESP32 / Python dongle | `tools/dongle/mid-xye/` | Live-capture firmware + Python serial-to-UDP bridge |
| Protocol documentation | `protocols/<manufacturer>/` | Protocol documentation organised into `spec/`, `devices/`, `analysis/` |

## Currently supported protocols

- **mid-xye** — Midea XYE RS-485 inter-unit bus (4800 baud, 16/32-byte frames)
  - Includes UART (WiFi module ↔ mainboard), R/T (indoor ↔ outdoor extension board),
    Display–Mainboard internal bus, and IR remote protocols

## Repository layout

```
tools/
  dissector/            Lua dissectors loaded into Wireshark (one per manufacturer family)
  dongle/mid-xye/       ESP32 firmware + Python serial-to-UDP bridge
    mid_xye/            Arduino project (PlatformIO)
    py-mid-xye/         Python equivalent bridge
protocols/
  midea/                Midea family protocols
    spec/               Protocol specifications (UART, R/T, XYE, IR, Display-Mainboard)
    devices/            Device-specific behaviour documentation
    analysis/           Special function deep-dives
```

## Companion repository: blaueis-hvacshark-traces

Capture sessions, raw logic-analyser exports, and session documentation live in a
separate repository to keep binary data out of the main codebase:

**[blaueis-hvacshark-traces](https://github.com/fabcoded/blaueis-hvacshark-traces)**

Contents:
- `.pcap` files converted from Saleae logic-analyser exports, ready to open in Wireshark
- Raw Saleae CSV exports and `.sal` session files
- `SessionNotes.md` (operator logs) and `findings.md` (analysis results) per session
- `channels.yaml` configuration files used by the offline pcap converter

Each device has its own subfolder (e.g. `Midea-extremeSaveBlue-display/`) with a
README describing the hardware, captured buses, and session index.

The offline pcap converter (`logicanalyzer-tools/logic_analyzer_midea_to_pcap.py`)
lives in the dumps repository next to the data it processes.

## Conventions

- **Temperature**: all temperature values are in **°C (Celsius)** unless explicitly
  noted otherwise in the relevant file or field description.

## AI-assisted research

This project doubles as an experiment in using AI tools to consolidate scattered
protocol research — multiple codebases, forum posts, hardware captures — into a
single cross-referenced protocol reference. All protocol knowledge traces back
to community work or own captures; AI assists with organisation and validation.

## Contributing

Contributions are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) — covers the citation rule, confidence-label conventions, where new protocol / device / analysis content belongs, and what good PRs look like. For anything non-trivial (new protocol, new manufacturer, new device family), open an issue first.

## Acknowledgements

A huge thank you to the open-source and home-automation community — especially the
contributors around **Home Assistant**, **ESPHome**, and the broader maker community —
for their tireless research work and for publishing their findings openly.

Projects that made this research possible:
- [crankyoldgit/IRremoteESP8266](https://github.com/crankyoldgit/IRremoteESP8266) — IR protocol reference for Midea remotes.
- [dudanov/MideaUART](https://github.com/dudanov/MideaUART) — ESP/Arduino library for Midea UART.
- [chemelli74/midea-local](https://github.com/chemelli74/midea-local) — Python client for the Midea LAN protocol.
- [reneklootwijk/node-mideahvac](https://github.com/reneklootwijk/node-mideahvac) — Node.js driver for Midea AC.
- [NeoAcheron/midea-ac-py](https://github.com/NeoAcheron/midea-ac-py) — early Python Midea AC implementation, historical reference.
- [wuwentao/midea_ac_lan](https://github.com/wuwentao/midea_ac_lan) — HA integration covering a broad Midea device set.
- [codeberg.org/xye/xye](https://codeberg.org/xye/xye) — XYE bus reference documentation.
- [wtahler/esphome-mideaXYE-rs485](https://github.com/wtahler/esphome-mideaXYE-rs485) — ESPHome RS-485 Midea XYE component.
- The countless forum threads, GitHub issues, and pull requests in the HA and ESPHome communities.

### Related projects in this ecosystem

- [blaueis-libmidea](https://github.com/fabcoded/blaueis-libmidea) — Python library consuming the protocol knowledge this repository documents.
- [blaueis-ha-midea](https://github.com/fabcoded/blaueis-ha-midea) — Home Assistant integration.
- [blaueis-esphome](https://github.com/fabcoded/blaueis-esphome) — ESP32 gateway port (placeholder).
- [blaueis-hvacshark-traces](https://github.com/fabcoded/blaueis-hvacshark-traces) — companion capture archive.

If you believe your work is referenced here without proper attribution, if you would
like code or findings removed, or if you have any licensing concerns, please open an
issue or get in touch directly via this GitHub repository. We will respond promptly.

## For AI agents

AI agents working in this repository should follow the instructions in
[AGENTS.md](AGENTS.md). Unless otherwise advised by the repository owner,
`AGENTS.md` is the authoritative guide for coding style, working conventions,
protocol documentation standards, and confidence labelling.
