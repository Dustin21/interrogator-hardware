#!/usr/bin/env python3
"""Milestone DRC runner for H3.3 (pcbnew.WriteDRCReport; kicad-cli 7 has no
`pcb drc`). Usage: python3 drc_check.py <prefix> [note ...]
Writes <prefix>.rpt + <prefix>.json next to the board. Zones are refilled
before the check so the report always reflects fresh fills.
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

import pcbnew

HERE = Path(__file__).resolve().parent
PCB = HERE / "interrogator_v1.kicad_pcb"
prefix = sys.argv[1] if len(sys.argv) > 1 else "drc_check"
notes = sys.argv[2:]
RPT = HERE / f"{prefix}.rpt"
OUT = HERE / f"{prefix}.json"

board = pcbnew.LoadBoard(str(PCB))
zones = board.Zones()
if len(list(zones)):
    pcbnew.ZONE_FILLER(board).Fill(zones)
tracks = list(board.GetTracks())
nvia = sum(1 for t in tracks if t.GetClass() == "PCB_VIA")
print(f"loaded: {len(board.GetFootprints())} fps, {board.GetNetCount()} nets, "
      f"{nvia} vias, {len(tracks) - nvia} tracks, {len(list(zones))} zones")
pcbnew.WriteDRCReport(board, str(RPT), pcbnew.EDA_UNITS_MILLIMETRES, False)

txt = RPT.read_text()
sections = re.split(r"\*\* (.+?) \*\*", txt)
counts, bodies = {}, {}
for i in range(1, len(sections) - 1, 2):
    m = re.match(r"Found (\d+) (.+)", sections[i])
    if m:
        counts[m.group(2)] = int(m.group(1))
        bodies[m.group(2)] = sections[i + 1]
viol = Counter(re.findall(r"\[(\w+)\]:", bodies.get("DRC violations", "")))

result = {
    "tool": "pcbnew 7.0.11 WriteDRCReport",
    "board": PCB.name,
    "vias": nvia,
    "tracks": len(tracks) - nvia,
    "zones": len(list(zones)),
    "counts": counts,
    "violations_by_type": dict(viol),
    "notes": notes,
}
OUT.write_text(json.dumps(result, indent=1))
print(json.dumps({"counts": counts, "violations_by_type": dict(viol)}, indent=1))

p = PCB.with_suffix(".kicad_prl")
if p.exists():
    p.unlink()
