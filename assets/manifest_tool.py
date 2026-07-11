#!/usr/bin/env python3
"""AssetPin manifest tool — local now, S3 later (owner decision D10, no Git LFS).

The manifest (``assets/manifest.json``) is the single ledger of every heavy
design asset (footprints, 3D models, vendor docs, gerbers, renders). Each entry:

    {"asset_id": "step-as7343", "part": "AS7343", "kind": "model_3d",
     "location": "device:registry_assets/AS7343/3d/AS7343_OLGA8.step",
     "object_key": null, "sha256": "...", "bytes": 16384,
     "source_url": "...", "evidence_tier": "E0", "retrieved": "2026-07-11"}

``location`` prefixes: ``repo:`` (in-tree), ``device:`` (owner's machine,
relative to the folder root), ``s3:`` (future — bucket/key in object_key).
``verify`` checks sha256 for every entry it can reach (repo: always; others
are reported as unreachable-here, not failures).

Usage:
    python3 assets/manifest_tool.py add --file <path> --part X --kind Y \
        [--asset-id ID] [--location LOC] [--source-url URL] [--tier E0]
    python3 assets/manifest_tool.py verify
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST = REPO_ROOT / "assets" / "manifest.json"


def _load() -> list[dict]:
    if MANIFEST.exists():
        return json.loads(MANIFEST.read_text())
    return []


def _save(entries: list[dict]) -> None:
    entries.sort(key=lambda e: e["asset_id"])
    MANIFEST.write_text(json.dumps(entries, indent=1) + "\n")


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def cmd_add(args: argparse.Namespace) -> int:
    p = Path(args.file)
    if not p.exists():
        print(f"no such file: {p}", file=sys.stderr)
        return 1
    entries = _load()
    asset_id = args.asset_id or f"{args.kind}-{args.part.lower()}-{p.name.lower()}"
    if any(e["asset_id"] == asset_id for e in entries):
        print(f"asset_id already present: {asset_id}", file=sys.stderr)
        return 1
    entries.append(
        {
            "asset_id": asset_id,
            "part": args.part,
            "kind": args.kind,
            "location": args.location or f"repo:{p.relative_to(REPO_ROOT)}",
            "object_key": None,
            "sha256": sha256_of(p),
            "bytes": p.stat().st_size,
            "source_url": args.source_url,
            "evidence_tier": args.tier,
            "retrieved": dt.date.today().isoformat(),
        }
    )
    _save(entries)
    print(f"added {asset_id}")
    return 0


def cmd_verify(_args: argparse.Namespace) -> int:
    entries = _load()
    bad, unreachable = [], []
    for e in entries:
        loc = e["location"]
        if loc.startswith("repo:"):
            p = REPO_ROOT / loc[len("repo:"):]
            if not p.exists():
                bad.append((e["asset_id"], "missing file"))
            elif sha256_of(p) != e["sha256"]:
                bad.append((e["asset_id"], "sha256 mismatch"))
        else:
            unreachable.append(e["asset_id"])
    print(f"manifest: {len(entries)} entries, {len(bad)} bad, {len(unreachable)} not verifiable here (device:/s3:)")
    for aid, why in bad:
        print(f"  FAIL {aid}: {why}", file=sys.stderr)
    return 1 if bad else 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("add")
    a.add_argument("--file", required=True)
    a.add_argument("--part", required=True)
    a.add_argument("--kind", required=True, choices=["datasheet", "schematic", "model_3d", "footprint", "symbol", "gerber", "render", "doc"])
    a.add_argument("--asset-id")
    a.add_argument("--location")
    a.add_argument("--source-url")
    a.add_argument("--tier", default="E0", choices=["E0", "E1", "E2"])
    a.set_defaults(fn=cmd_add)
    v = sub.add_parser("verify")
    v.set_defaults(fn=cmd_verify)
    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
