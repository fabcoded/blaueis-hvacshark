#!/usr/bin/env python3
"""
Generate Wireshark dissector Lua tables from serial_glossary.yaml.

Reads the glossary and emits hvac_shark_glossary_gen.lua containing:
  - Lookup tables (from values: maps)
  - Encoding functions (from top-level encodings:)
  - Field registries (from rsp_0xc0, rsp_0xc1_group1/3 decode arrays)
  - B1 property registries (from rsp_0xb1 decode arrays with property_id)
  - Generic decode functions consumed by the main dissector

Usage:
    python generate_dissector_tables.py

The generated file is an artifact that gets committed alongside the
dissector. Re-run after glossary changes to keep them in sync.
"""

import sys
import textwrap
from datetime import date
from pathlib import Path

# Resolve paths relative to this script
SCRIPT_DIR = Path(__file__).resolve().parent
GLOSSARY_DIR = SCRIPT_DIR.parent.parent / "protocols" / "midea"
sys.path.insert(0, str(GLOSSARY_DIR / "tools-serial"))

from midea_codec import build_field_map, load_glossary  # noqa: E402

DISSECTOR = SCRIPT_DIR / "HVAC-shark_mid-xye.lua"
MARKER_START = "-- ── GLOSSARY-GEN-START"
MARKER_END = "-- ── GLOSSARY-GEN-END"


def lua_escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def emit_header(glossary: dict) -> str:
    meta = glossary.get("meta", {})
    ver = meta.get("version", "?")
    return textwrap.dedent(f"""\
    -- ==========================================================================
    -- AUTO-GENERATED from serial_glossary.yaml v{ver}
    -- Date: {date.today().isoformat()}
    -- Do not edit by hand — re-run generate_dissector_tables.py instead.
    -- ==========================================================================

    """)


def emit_lookup_tables(glossary: dict) -> str:
    """Generate Lua lookup tables from fields with values: maps."""
    fields = {}
    for cat in ("control", "sensor"):
        for name, fdef in glossary["fields"][cat].items():
            if not isinstance(fdef, dict):
                continue
            vals = fdef.get("values")
            if not vals or not isinstance(vals, dict):
                continue
            entries = {}
            for vname, vdef in vals.items():
                if isinstance(vdef, dict) and "raw" in vdef:
                    raw = vdef["raw"]
                    if isinstance(raw, int | float):
                        entries[raw] = vname
            if entries:
                fields[name] = entries

    if not fields:
        return "-- No lookup tables generated\n\n"

    lines = ["-- ── Lookup tables (from glossary values: maps) ──────────────\n"]
    lines.append("local GLOSSARY_LOOKUP = {\n")
    for fname, entries in sorted(fields.items()):
        parts = []
        for raw, vname in sorted(entries.items(), key=lambda x: x[0]):
            parts.append(f'[{raw}]="{lua_escape(vname)}"')
        lines.append(f"  {fname} = {{{', '.join(parts)}}},\n")
    lines.append("}\n\n")
    return "".join(lines)


def emit_encoding_functions(glossary: dict) -> str:
    """Generate Lua encoding functions from the top-level encodings: dict."""
    encodings = glossary.get("encodings", {})
    if not encodings:
        return "-- No encoding functions generated\n\n"

    lines = ["-- ── Encoding functions (from glossary encodings:) ───────────\n"]
    lines.append("local GLOSSARY_ENC = {\n")
    for name, edef in sorted(encodings.items()):
        formula = edef.get("formula", "raw")
        offset = edef.get("offset", 0)
        scale = edef.get("scale", 1.0)
        # Generate a Lua function from the formula parameters
        if "bcd" in formula.lower():
            # BCD encodings handled separately at decode time
            lines.append(f"  -- {name}: BCD encoding (handled inline)\n")
            continue
        if offset != 0 and scale != 0:
            lines.append(f"  {name} = function(r) return (r - {offset}) / {1 / scale} end,\n")
        elif "raw" in formula:
            lines.append(f"  {name} = function(r) return r end,\n")
        else:
            lines.append(f'  -- {name}: complex formula "{formula}" (not auto-generated)\n')
    lines.append("}\n\n")
    return "".join(lines)


def emit_field_registry(glossary: dict, protocol_key: str, table_name: str) -> str:
    """Generate a Lua field registry table for a given protocol key."""
    field_map = build_field_map(glossary, protocol_key)
    if not field_map:
        return f"-- No fields for {protocol_key}\n\n"

    # Walk all fields to find those with values: maps for lookup references
    all_fields = {}
    for cat in ("control", "sensor"):
        for name, fdef in glossary["fields"][cat].items():
            if isinstance(fdef, dict):
                all_fields[name] = fdef

    lines = [f"-- ── {table_name} ({len(field_map)} fields from {protocol_key}) ──\n"]
    lines.append(f"local {table_name} = {{\n")

    for field in field_map:
        name = field["name"]
        decode = field["decode"]
        dtype = field["data_type"]
        fdef = all_fields.get(name, {})

        if not decode:
            continue

        # Skip composite/derived fields that have no direct wire position
        if fdef.get("field_class") == "complex_function" and fdef.get("composite"):
            lines.append(f"  -- {name}: composite/derived (decode deferred)\n")
            continue

        # Check for property_id (B0/B1 TLV) — handled in separate registry
        if decode[0].get("property_id"):
            continue

        # Single-step or multi-step?
        if len(decode) == 1:
            step = decode[0]
            entry = _emit_single_step(name, step, dtype, fdef)
            lines.append(f"  {entry},\n")
        else:
            # Multi-step chain (priority decode)
            lines.append(f'  {{name="{name}", dtype="{dtype}", steps={{\n')
            for step in decode:
                entry = _emit_step_inline(step)
                lines.append(f"    {entry},\n")
            lines.append("  }},\n")

    lines.append("}\n\n")
    return "".join(lines)


def _emit_single_step(name: str, step: dict, dtype: str, fdef: dict) -> str:
    """Emit a single-step field entry."""
    parts = [f'name="{name}"']

    if "logic" in step:
        parts.append(f'logic="{step["logic"]}"')
        sources = step.get("sources", [])
        src_strs = []
        for s in sources:
            src_strs.append(f"{{offset={s['offset']},bits={{{s['bits'][0]},{s['bits'][1]}}}}}")
        parts.append(f"sources={{{','.join(src_strs)}}}")
        parts.append(f'dtype="{dtype}"')
        return "{" + ", ".join(parts) + "}"

    parts.append(f"offset={step['offset']}")
    parts.append(f"bits={{{step['bits'][0]},{step['bits'][1]}}}")
    parts.append(f'dtype="{dtype}"')

    if step.get("add"):
        parts.append(f"add={step['add']}")
    if step.get("condition"):
        parts.append(f'condition="{step["condition"]}"')
    if step.get("encoding"):
        parts.append(f'encoding="{step["encoding"]}"')
    if step.get("half_bit"):
        hb = step["half_bit"]
        parts.append(f"half_bit={{offset={hb['offset']},bit={hb['bit']}}}")
    if step.get("tenths_nibble"):
        tn = step["tenths_nibble"]
        parts.append(f'tenths_nibble={{offset={tn["offset"]},nibble="{tn.get("nibble", "low")}"}}')

    # Lookup table reference
    if fdef.get("values"):
        parts.append(f'lookup="{name}"')

    return "{" + ", ".join(parts) + "}"


def _emit_step_inline(step: dict) -> str:
    """Emit a decode step as an inline Lua table (for multi-step chains)."""
    parts = [f"offset={step['offset']}", f"bits={{{step['bits'][0]},{step['bits'][1]}}}"]

    if step.get("add"):
        parts.append(f"add={step['add']}")
    if step.get("condition"):
        parts.append(f'condition="{step["condition"]}"')
    if step.get("encoding"):
        parts.append(f'encoding="{step["encoding"]}"')
    if step.get("half_bit"):
        hb = step["half_bit"]
        parts.append(f"half_bit={{offset={hb['offset']},bit={hb['bit']}}}")
    if step.get("tenths_nibble"):
        tn = step["tenths_nibble"]
        parts.append(f'tenths_nibble={{offset={tn["offset"]},nibble="{tn.get("nibble", "low")}"}}')

    return "{" + ", ".join(parts) + "}"


def emit_b1_property_registry(glossary: dict) -> str:
    """Generate a B1 property registry keyed by property_id."""
    field_map = build_field_map(glossary, "rsp_0xb1")
    if not field_map:
        return "-- No B1 property fields\n\n"

    # Group fields by property_id
    by_prop: dict[str, list] = {}
    for field in field_map:
        decode = field["decode"]
        if not decode:
            continue
        pid = decode[0].get("property_id")
        if not pid:
            continue
        by_prop.setdefault(pid, []).append(field)

    lines = [f"-- ── GLOSSARY_B1 ({len(field_map)} fields across {len(by_prop)} properties) ──\n"]
    lines.append("local GLOSSARY_B1 = {\n")

    for pid, fields in sorted(by_prop.items()):
        lines.append(f'  ["{pid}"] = {{\n')
        for field in fields:
            step = field["decode"][0]
            parts = [
                f'name="{field["name"]}"',
                f"offset={step.get('offset', 0)}",
                f"bits={{{step['bits'][0]},{step['bits'][1]}}}",
                f'dtype="{field["data_type"]}"',
            ]
            lines.append(f"    {{{', '.join(parts)}}},\n")
        lines.append("  },\n")

    lines.append("}\n\n")
    return "".join(lines)


def emit_generic_decoder() -> str:
    """Emit the generic Lua decode function."""
    return textwrap.dedent("""\
    -- ── Generic decode engine ────────────────────────────────────

    local function extract_bits(byte_val, high, low)
        local mask = 0
        for i = low, high do mask = mask + (2 ^ i) end
        return math.floor(byte_val / (2 ^ low)) % (2 ^ (high - low + 1))
    end

    local function decode_step(buf, body_off, body_len, step)
        local offset = step.offset
        if offset >= body_len then return nil end

        local raw_byte = buf(body_off + offset, 1):uint()
        local val = extract_bits(raw_byte, step.bits[1], step.bits[2])

        -- condition check
        if step.condition then
            if step.condition == "!= 0" and val == 0 then return nil end
            if step.condition == "> 0" and val <= 0 then return nil end
        end

        -- add offset
        if step.add then val = val + step.add end

        -- half_bit
        if step.half_bit and step.half_bit.offset < body_len then
            local hb_byte = buf(body_off + step.half_bit.offset, 1):uint()
            if extract_bits(hb_byte, step.half_bit.bit, step.half_bit.bit) ~= 0 then
                val = val + 0.5
            end
        end

        -- encoding
        if step.encoding and GLOSSARY_ENC[step.encoding] then
            val = GLOSSARY_ENC[step.encoding](val)
        end

        -- tenths_nibble
        if step.tenths_nibble and step.tenths_nibble.offset < body_len then
            local tn_byte = buf(body_off + step.tenths_nibble.offset, 1):uint()
            local nibble
            if step.tenths_nibble.nibble == "high" then
                nibble = math.floor(tn_byte / 16) % 16
            else
                nibble = tn_byte % 16
            end
            val = val + nibble / 10
        end

        return val
    end

    local function format_value(val, field)
        if field.dtype == "bool" then
            if field.bits and field.bits[1] == field.bits[2] then
                return val ~= 0 and "true" or "false"
            end
        end
        if field.lookup and GLOSSARY_LOOKUP[field.lookup] then
            local label = GLOSSARY_LOOKUP[field.lookup][val]
            if label then return string.format("%s (%s)", tostring(val), label) end
        end
        if type(val) == "number" then
            if val == math.floor(val) then
                return string.format("%d", val)
            else
                return string.format("%.1f", val)
            end
        end
        return tostring(val)
    end

    function glossary_decode_registry(body_tree, buf, body_off, body_len, registry, label)
        local gtree = body_tree:add(buf(body_off, body_len),
            string.format("%s (%d fields)", label, #registry))
        for _, field in ipairs(registry) do
            local val = nil

            if field.logic then
                -- Logic combiner (OR/AND)
                if field.logic == "or" then
                    val = false
                    for _, src in ipairs(field.sources) do
                        if src.offset < body_len then
                            local sv = extract_bits(buf(body_off + src.offset, 1):uint(),
                                                    src.bits[1], src.bits[2])
                            if sv ~= 0 then val = true end
                        end
                    end
                end
            elseif field.steps then
                -- Multi-step chain: first matching wins
                for _, step in ipairs(field.steps) do
                    val = decode_step(buf, body_off, body_len, step)
                    if val ~= nil then break end
                end
            else
                -- Single step
                val = decode_step(buf, body_off, body_len, field)
            end

            if val ~= nil then
                local display = format_value(val, field)
                local byte_off = field.offset or (field.steps and field.steps[1].offset) or 0
                if byte_off < body_len then
                    gtree:add(buf(body_off + byte_off, 1),
                        string.format("%s: %s", field.name, display))
                end
            end
        end
    end

    -- ── C0 convenience wrapper ───────────────────────────────────

    function glossary_decode_c0(body_tree, buf, body_off, body_len)
        glossary_decode_registry(body_tree, buf, body_off, body_len,
            GLOSSARY_C0, "[Glossary] C0 Status")
    end

    """)


def inject_into_dissector(generated: str) -> None:
    """Replace everything between GLOSSARY-GEN-START and GLOSSARY-GEN-END markers."""
    src = DISSECTOR.read_text(encoding="utf-8")

    start_idx = src.find(MARKER_START)
    end_idx = src.find(MARKER_END)
    if start_idx < 0 or end_idx < 0 or end_idx <= start_idx:
        raise RuntimeError(
            f"Markers not found in {DISSECTOR.name}. Expected:\n"
            f"  {MARKER_START}\n  ...generated code...\n  {MARKER_END}"
        )

    # Find the end of the MARKER_END line
    end_line_end = src.index("\n", end_idx) + 1

    new_src = (
        src[:start_idx]
        + MARKER_START
        + " ──────────────────────────────────────────────────────\n"
        + generated
        + MARKER_END
        + " ────────────────────────────────────────────────────────\n"
    )
    # Append everything after the old end marker line
    new_src += src[end_line_end:]

    DISSECTOR.write_text(new_src, encoding="utf-8")


def main():
    glossary = load_glossary()

    parts = []
    parts.append(emit_header(glossary))
    parts.append(emit_lookup_tables(glossary))
    parts.append(emit_encoding_functions(glossary))
    parts.append(emit_field_registry(glossary, "rsp_0xc0", "GLOSSARY_C0"))
    parts.append(emit_field_registry(glossary, "rsp_0xc1_group1", "GLOSSARY_C1G1"))
    parts.append(emit_field_registry(glossary, "rsp_0xc1_group3", "GLOSSARY_C1G3"))
    parts.append(emit_b1_property_registry(glossary))
    parts.append(emit_generic_decoder())

    generated = "".join(parts)
    inject_into_dissector(generated)

    # Count what was generated
    c0_count = generated.count("{name=")
    print(f"Injected into {DISSECTOR.name}")
    print(f"  ~{c0_count} field entries across C0/C1/B1 registries")
    print(f"  {len(generated)} bytes of generated code")


if __name__ == "__main__":
    main()
