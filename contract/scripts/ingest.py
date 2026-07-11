#!/usr/bin/env python3
"""Contract ingest (pipeline stage 1) — pinned USR records -> hardware IO map.

Reads the vendored, pinned Unified Sensor Registry snapshot under
``contract/upstream/sensors/`` and emits:

  * ``contract/io_map.json``  — machine-readable per-sensor electrical facts
  * ``contract/io_map.md``    — human review table

Fails fast (non-zero exit) on: unknown schema_version, duplicate sensor_type,
duplicate wire_token, or a record missing its electrical facet. Sensors whose
electrical facet is still ``pending`` are ingested but flagged — the IO map is
explicit about which facts are not yet sign-off grade (USR-3), so nothing
downstream can silently treat them as truth.

Usage:  python3 contract/scripts/ingest.py [--check]
        --check: validate only, write nothing (CI mode).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
SENSORS_DIR = REPO_ROOT / "contract" / "upstream" / "sensors"
PIN_FILE = REPO_ROOT / "contract" / "upstream" / "PIN.json"
OUT_JSON = REPO_ROOT / "contract" / "io_map.json"
OUT_MD = REPO_ROOT / "contract" / "io_map.md"

SUPPORTED_SCHEMA = "sensor-registry-0"


class IngestError(Exception):
    pass


def load_records(sensors_dir: Path = SENSORS_DIR) -> list[dict]:
    files = sorted(sensors_dir.glob("*.yaml"))
    if not files:
        raise IngestError(f"no USR records found under {sensors_dir}")
    records = []
    for f in files:
        rec = yaml.safe_load(f.read_text())
        if not isinstance(rec, dict):
            raise IngestError(f"{f.name}: not a mapping")
        if rec.get("schema_version") != SUPPORTED_SCHEMA:
            raise IngestError(
                f"{f.name}: schema_version={rec.get('schema_version')!r}, "
                f"this ingester supports {SUPPORTED_SCHEMA!r} only"
            )
        if "sensor_type" not in rec or "identity" not in rec:
            raise IngestError(f"{f.name}: missing sensor_type/identity")
        rec["_file"] = f.name
        records.append(rec)
    return records


def build_io_map(records: list[dict], pin: dict) -> dict:
    seen_types: set[str] = set()
    seen_tokens: set[str] = set()
    entries = []
    for rec in records:
        st = rec["sensor_type"]
        ident = rec["identity"]
        token = ident.get("wire_token", st)
        if st in seen_types:
            raise IngestError(f"duplicate sensor_type {st}")
        if token in seen_tokens:
            raise IngestError(f"duplicate wire_token {token}")
        seen_types.add(st)
        seen_tokens.add(token)

        facets = rec.get("facets", {})
        elec = facets.get("electrical")
        if elec is None:
            raise IngestError(f"{st}: electrical facet missing entirely")
        mech = facets.get("mechanical", {})
        assets = rec.get("assets", {})

        val = elec.get("validation", {}) or {}
        entries.append(
            {
                "sensor_type": st,
                "part_number": ident.get("part_number"),
                "vendor": ident.get("vendor"),
                "wire_token": token,
                "class": ident.get("class"),
                "adoption_status": ident.get("adoption_status"),
                "bus": elec.get("bus"),
                "i2c_addresses": elec.get("i2c_addresses", []),
                "logic_level_v": elec.get("logic_level_v"),
                "electrical_status": val.get("status", "pending"),
                "electrical_tier": val.get("evidence_tier", "E0"),
                "electrical_needs": val.get("needs"),
                "mechanical_dimensions_mm": mech.get("dimensions_mm"),
                "datasheet_rev": (assets.get("datasheet") or {}).get("rev"),
                "datasheet_sha256": (assets.get("datasheet") or {}).get("sha256"),
                "source_record": rec["_file"],
            }
        )

    pending = [e["sensor_type"] for e in entries if e["electrical_status"] == "pending"]
    return {
        "generated_by": "contract/scripts/ingest.py",
        "contract_pin": pin.get("pinned_commit"),
        "schema_version": SUPPORTED_SCHEMA,
        "sensor_count": len(entries),
        "electrical_pending": pending,
        "sensors": entries,
    }


def render_md(io_map: dict) -> str:
    lines = [
        "# IO map — generated from the pinned USR snapshot",
        "",
        f"Contract pin: `{io_map['contract_pin']}` · sensors: {io_map['sensor_count']} · "
        f"electrical facets still pending sign-off (USR-3): **{len(io_map['electrical_pending'])}**",
        "",
        "> Generated file — do not edit. Regenerate with `python3 contract/scripts/ingest.py`.",
        "",
        "| sensor_type | part | vendor | wire_token | class | bus | i2c addrs | logic V | elec status | datasheet rev |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for e in io_map["sensors"]:
        addrs = ",".join(e["i2c_addresses"]) if e["i2c_addresses"] else "—"
        flag = "⚠ pending" if e["electrical_status"] == "pending" else e["electrical_status"]
        lines.append(
            f"| {e['sensor_type']} | {e['part_number']} | {e['vendor']} | {e['wire_token']} "
            f"| {e['class']} | {e['bus']} | {addrs} | {e['logic_level_v']} | {flag} | {e['datasheet_rev'] or 'TODO'} |"
        )
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="validate only, write nothing")
    args = ap.parse_args(argv)

    try:
        pin = json.loads(PIN_FILE.read_text())
        records = load_records()
        io_map = build_io_map(records, pin)
    except IngestError as e:
        print(f"INGEST FAIL: {e}", file=sys.stderr)
        return 1

    if not args.check:
        OUT_JSON.write_text(json.dumps(io_map, indent=1) + "\n")
        OUT_MD.write_text(render_md(io_map))
        print(f"wrote {OUT_JSON.relative_to(REPO_ROOT)} and {OUT_MD.relative_to(REPO_ROOT)}")
    print(
        f"OK: {io_map['sensor_count']} sensors, "
        f"{len(io_map['electrical_pending'])} electrical facets pending (USR-3)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
