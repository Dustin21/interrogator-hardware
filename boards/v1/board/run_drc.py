#!/usr/bin/env python3
"""H3 routing baseline DRC.

kicad-cli 7.0.11 has no `pcb drc` subcommand (that arrived in KiCad 8), so
the DRC is run through the same engine via the pcbnew python bindings
(pcbnew.WriteDRCReport). The .rpt is parsed into drc_baseline.json with the
schema {tool, violations_by_type, violation_total, unconnected_items, notes}.
`kicad-cli pcb export svg` is run afterwards as the load-proof that the
board file parses in kicad-cli. Run: python3 boards/v1/board/run_drc.py
"""
import json
import re
import subprocess
from collections import Counter
from pathlib import Path

import pcbnew

HERE = Path(__file__).resolve().parent
PCB = HERE / "interrogator_v1.kicad_pcb"
RPT = HERE / "drc_baseline.rpt"
OUT = HERE / "drc_baseline.json"

board = pcbnew.LoadBoard(str(PCB))
print(f"loaded: {len(board.GetFootprints())} footprints, "
      f"{board.GetNetCount()} nets")
pcbnew.WriteDRCReport(board, str(RPT), pcbnew.EDA_UNITS_MILLIMETRES, False)

txt = RPT.read_text()
sections = re.split(r"\*\* (.+?) \*\*", txt)
# sections: ['', 'Found N DRC violations', body, 'Found N unconnected pads', body, ...]
counts = {}
bodies = {}
for i in range(1, len(sections) - 1, 2):
    m = re.match(r"Found (\d+) (.+)", sections[i])
    if m:
        counts[m.group(2)] = int(m.group(1))
        bodies[m.group(2)] = sections[i + 1]

viol_types = Counter(re.findall(r"\[(\w+)\]:", bodies.get("DRC violations", "")))

result = {
    "tool": "pcbnew 7.0.11 WriteDRCReport (kicad-cli 7.x has no `pcb drc`; "
            "same DRC engine)",
    "board": PCB.name,
    "footprints": len(board.GetFootprints()),
    "nets": board.GetNetCount(),
    "counts": counts,
    "violations_by_type": dict(viol_types),
    "notes": [
        "H3 ROUTING BASELINE — no tracks routed yet: the unconnected-pads "
        "count is the routing todo, not a failure.",
        "courtyard/silk overlaps come from the greedy baseline placement "
        "(77 overlap-fallback parts) — H3 placement refinement debt.",
        "pads with no net (E0 logical pin maps vs real package pads) are "
        "not counted here — see build_board.py output (392).",
    ],
}
OUT.write_text(json.dumps(result, indent=1))
print(json.dumps({k: v for k, v in result.items() if k in ("counts", "violations_by_type")}, indent=1))

# load-proof through kicad-cli itself (scratch output, not committed)
r = subprocess.run(["kicad-cli", "pcb", "export", "svg", "--layers",
                    "F.Cu,B.Cu,Edge.Cuts", "-o", "/tmp/board_loadproof.svg",
                    str(PCB)], capture_output=True, text=True)
print("kicad-cli load-proof:", "OK" if r.returncode == 0 else r.stderr[:400])
# keep the board dir free of auto-created project files (CI gates on *.kicad_pro)
for ext in (".kicad_pro", ".kicad_prl"):
    p = PCB.with_suffix(ext)
    if p.exists():
        p.unlink()
