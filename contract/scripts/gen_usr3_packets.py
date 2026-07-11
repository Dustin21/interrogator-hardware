#!/usr/bin/env python3
"""Generate USR-3 electrical-resolution packet drafts (H0 deliverable).

One markdown packet per sensor under ``contract/usr3_packets/``. Each packet
is a PR-ready *proposal* for the upstream `electrical` facet: candidate facts
from the pinned record, the datasheet AssetPin to cite against, and the fixed
verification checklist an embedded-SME (or the H1 bench spike) completes.

These packets are how the ratified change flow ships electrical truth
downstream: drafted here -> owner lands upstream -> facet pending->approved.

Regenerate with:  python3 contract/scripts/gen_usr3_packets.py
"""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
IO_MAP = REPO_ROOT / "contract" / "io_map.json"
OUT_DIR = REPO_ROOT / "contract" / "usr3_packets"

CHECKLIST = """\
## Verification checklist (embedded-SME / H1 bench)

- [ ] Bus + interface options confirmed against datasheet pinout (I2C/I3C/SPI/UART modes, max clock per mode)
- [ ] All selectable I2C addresses enumerated (straps/jumpers), default address confirmed
- [ ] Interface-select / address straps documented (tie level, silent-failure modes)
- [ ] Supply range + logic-level domain confirmed (core vs IO rails if split)
- [ ] INT / data-ready line(s): polarity, drive type (push-pull/OD), timing
- [ ] FIFO / watermark batch-read support: yes/no, depth
- [ ] Power states + typical/max currents per state (feeds W-PWR model)
- [ ] Land pattern / package confirmed vs mechanical drawing (feeds mechanical facet)
- [ ] Keepout / placement constraints (RF, optical window, thermal, magnetic)

**Sign-off:** pending → approved by: ______ · date: ______ · evidence tier: E1
"""


def main() -> int:
    io_map = json.loads(IO_MAP.read_text())
    OUT_DIR.mkdir(exist_ok=True)
    for e in io_map["sensors"]:
        addrs = ", ".join(e["i2c_addresses"]) if e["i2c_addresses"] else "*none recorded upstream — enumerate from datasheet*"
        body = f"""# USR-3 electrical resolution packet — {e['sensor_type']}

> DRAFT proposal for `facets.electrical` of `shared/schemas/sensors/{e['source_record']}`
> (upstream single source of truth; this packet is the ingest-package input, never applied directly).
> Contract pin: `{io_map['contract_pin']}` · current upstream status: **{e['electrical_status']}** ({e['electrical_tier']})

| field | candidate value (pinned record) | to confirm against |
|---|---|---|
| part_number | {e['part_number']} | vendor ordering info |
| vendor | {e['vendor']} | — |
| wire_token | {e['wire_token']} | upstream command contract |
| bus (as recorded) | {e['bus']} | datasheet interface section — **the new design may reassign (SPI/I3C per PLAN §5.2); record ALL supported interfaces** |
| i2c_addresses | {addrs} | datasheet address table + strap pins |
| logic_level_v | {e['logic_level_v']} | datasheet supply/IO spec |
| datasheet (AssetPin) | {e['datasheet_rev'] or 'TODO — pin rev + sha256 from registry_assets'} | `registry_assets/{e['sensor_type'].replace('_','-') if e['sensor_type'] != 'NEO_M9N' else 'NEO-M9N'}/datasheet/` |

Upstream `needs`: {e['electrical_needs'] or '—'}

{CHECKLIST}"""
        (OUT_DIR / f"{e['sensor_type']}.md").write_text(body)
    print(f"wrote {io_map['sensor_count']} packets to {OUT_DIR.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
