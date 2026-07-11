"""Tests for contract ingest + asset manifest (H0 verification gate)."""

import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "contract" / "scripts"))
import ingest  # noqa: E402


def test_pin_recorded():
    pin = json.loads((REPO / "contract" / "upstream" / "PIN.json").read_text())
    assert pin["pinned_commit"] and len(pin["pinned_commit"]) == 40
    assert "interrogator" in pin["source_repo"]


def test_loads_all_records():
    records = ingest.load_records()
    assert len(records) == 16, "expected the 16 vendored USR records"
    types = {r["sensor_type"] for r in records}
    assert {"BME688", "VL53L8CX", "NEO_M9N", "MPR121", "MIKROE_4036", "BNO085"} <= types


def test_io_map_shape_and_aliases():
    pin = json.loads((REPO / "contract" / "upstream" / "PIN.json").read_text())
    io_map = ingest.build_io_map(ingest.load_records(), pin)
    assert io_map["sensor_count"] == 16
    by_type = {e["sensor_type"]: e for e in io_map["sensors"]}
    # wire_token alias survives (GPS -> NEO_M9N per upstream record)
    assert by_type["NEO_M9N"]["wire_token"] == "GPS"
    # every entry carries a bus and a validation status
    for e in io_map["sensors"]:
        assert e["bus"], f"{e['sensor_type']} missing bus"
        assert e["electrical_status"] in {"pending", "approved", "verified"}


def test_pending_facets_are_flagged_not_hidden():
    pin = json.loads((REPO / "contract" / "upstream" / "PIN.json").read_text())
    io_map = ingest.build_io_map(ingest.load_records(), pin)
    # upstream ships these pending (USR-3 unresolved) — ingest must surface, not mask
    assert io_map["electrical_pending"], "expected pending electrical facets to be flagged"
    assert set(io_map["electrical_pending"]) <= {e["sensor_type"] for e in io_map["sensors"]}


def test_duplicate_sensor_type_rejected(tmp_path):
    src = REPO / "contract" / "upstream" / "sensors"
    for f in src.glob("*.yaml"):
        (tmp_path / f.name).write_text(f.read_text())
    rec = yaml.safe_load((src / "BME688.yaml").read_text())
    (tmp_path / "BME688_copy.yaml").write_text(yaml.safe_dump(rec))
    with pytest.raises(ingest.IngestError, match="duplicate"):
        ingest.build_io_map(
            ingest.load_records(tmp_path),
            {"pinned_commit": "x" * 40},
        )


def test_bad_schema_version_rejected(tmp_path):
    rec = yaml.safe_load((REPO / "contract" / "upstream" / "sensors" / "BME688.yaml").read_text())
    rec["schema_version"] = "sensor-registry-999"
    (tmp_path / "BME688.yaml").write_text(yaml.safe_dump(rec))
    with pytest.raises(ingest.IngestError, match="schema_version"):
        ingest.load_records(tmp_path)


def test_cli_check_mode_green():
    r = subprocess.run(
        [sys.executable, str(REPO / "contract" / "scripts" / "ingest.py"), "--check"],
        capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stderr


def test_generated_io_map_is_current():
    """CI tripwire: committed io_map.json must match a fresh ingest (no drift)."""
    pin = json.loads((REPO / "contract" / "upstream" / "PIN.json").read_text())
    fresh = ingest.build_io_map(ingest.load_records(), pin)
    committed = json.loads((REPO / "contract" / "io_map.json").read_text())
    assert fresh == committed, "io_map.json is stale — rerun contract/scripts/ingest.py"


def test_manifest_verify_green():
    r = subprocess.run(
        [sys.executable, str(REPO / "assets" / "manifest_tool.py"), "verify"],
        capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stdout + r.stderr


def test_manifest_catches_corruption(tmp_path, monkeypatch):
    import importlib
    sys.path.insert(0, str(REPO / "assets"))
    mt = importlib.import_module("manifest_tool")
    victim = tmp_path / "x.step"
    victim.write_text("ISO-10303-21; original")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps([{
        "asset_id": "t", "part": "X", "kind": "model_3d",
        "location": "repo:x.step", "object_key": None,
        "sha256": mt.sha256_of(victim), "bytes": victim.stat().st_size,
        "source_url": None, "evidence_tier": "E0", "retrieved": "2026-07-11",
    }]))
    monkeypatch.setattr(mt, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(mt, "MANIFEST", manifest)
    assert mt.cmd_verify(None) == 0
    victim.write_text("ISO-10303-21; TAMPERED")
    assert mt.cmd_verify(None) == 1
