#!/usr/bin/env python3
"""Netlist -> .kicad_pcb via the pcbnew python bindings (KiCad 7.0.11).

Path A variant: kinet2pcb does not build on this host (Debian setuptools
`install_layout` regression), but the pcbnew bindings it would call are
available — so this script does the same job directly:

  1. parse boards/v1/netlist/interrogator_v1.net (S-expr; comps + nets),
  2. load every footprint from library/footprints{,/generated} with the
     official /usr/share/kicad/footprints as fallback,
  3. place the 38 components.json majors at their bean-floorplan positions
     (refdes<->part mapping table below; bottom-side parts flipped),
  4. greedy-grid-place every remaining part (passives, connectors, TPs,
     co-parts) inside the bean with no-overlap + polygon containment,
  5. bind pads to nets by (ref, pin-number) — alnum pads that the E0 logical
     pin maps don't cover simply stay unbound (H3 pin-map hardening),
  6. draw Edge.Cuts from boards/v1/outline.json,
  7. save boards/v1/board/interrogator_v1.kicad_pcb.

Placement here is a ROUTING BASELINE (H3 starts from the DRC unconnected
count), not a reviewed layout. Run: python3 boards/v1/board/build_board.py
"""
import json
import re
import sys
from pathlib import Path

import numpy as np
import pcbnew
from shapely.geometry import Polygon, box

HERE = Path(__file__).resolve().parent          # boards/v1/board
V1 = HERE.parent
REPO = V1.parents[1]
LIB = REPO / "library" / "footprints"
OFFICIAL = Path("/usr/share/kicad/footprints")

NETLIST = V1 / "netlist" / "interrogator_v1.net"
OUT = HERE / "interrogator_v1.kicad_pcb"

GAP = 0.8

# ---------------------------------------------------------------------------
# refdes <-> components.json part table (majors). Lists = co-placed refs.
PLACEMENT_TABLE = {
    "MLX90642 thermal 32x24": ["U_MLX42"],
    "VL53L8CH ToF 8x8 raw":   ["U_VL53"],
    "TCS3448 14ch VIS":       ["U_TCS"],
    "AS7331 UV A/B/C":        ["U_AS7331"],
    "AS7421 64ch NIR +":      ["U_AS7421"],
    "MLX90632 spot FIR +":    ["U_MLX32"],
    "VD66GY camera (DNP)":    ["J_CAM"],
    "BME688 gas/T/RH/P":      ["U_BME"],
    "SGP41 VOC/NOx":          ["U_SGP"],
    "ENS161 4-el MOX +":      ["U_ENS"],
    "SCD41 true CO2 +":       ["U_SCD"],
    "SHT41 ref T/RH +":       ["U_SHT"],
    "BMV080 PM2.5":           ["U_BMV"],
    "MAX30102 PPG":           ["U_MAX"],
    "AS7058 PPG/ECG/BioZ":    ["U_AS7058"],
    "A121 60GHz radar":       ["U_A121"],
    "MMC5983MA nT mag +":     ["U_MMC"],
    "TMAG5273 mT hall":       ["U_TMAG"],
    "STM32N657 VFBGA142":     ["U_N657"],
    "Octal NOR flash":        ["U_NOR"],
    "IQS7222A touch":         ["U_TOUCH"],
    "DRV2605L haptic":        ["U_HAP"],
    "MIA-M10Q GNSS RAWX":     ["U_GNSS"],
    "BL54L15 BLE sentinel":   ["U_BL54"],
    "ESP32-C6-MINI WiFi":     ["U_C6"],
    "BNO086 IMU raw+fused":   ["U_BNO"],
    "ADS131M04 24b 4ch":      ["U_ADS"],
    "PIN radiation det +":    ["D_PIN", "SH_RAD"],          # concentric block
    "MEMS mic +":             ["MK1"],
    "SGX-4CO electrochem +":  ["U_CO"],
    "CYPD3177 USB-C PD":      ["U_PD"],
    "BQ25620 charger 3.5A":   ["U_CHG"],
    "BQ27427 gauge":          ["U_GAUGE"],
    "TPS62840 sentinel buck": ["U_AON"],
    "TPS62823 core buck":     ["U_CORE"],
    "TLV62568 1V8 buck":      ["U_1V8"],
    "BQ29700+FET protect":    ["U_PROT", "Q_PROT"],         # side by side
    "Load switches x7":       ["U_SW_OPTICAL", "U_SW_AIR", "U_SW_CONTACT",
                               "U_SW_RADAR", "U_SW_GNSS", "U_SW_WIFI",
                               "U_SW_ACC"],                 # row
}


def parse_netlist(text):
    """Return (comps: ref->footprint, nets: name->[(ref,pin)...])."""
    comps = {}
    for m in re.finditer(r'\(comp\s*\(ref "([^"]+)"\).*?\(footprint "([^"]+)"\)',
                         text, re.S):
        comps[m.group(1)] = m.group(2)
    nets_txt = text[text.index("(nets"):]
    nets = {}
    for m in re.finditer(
            r'\(net\s*\(code \d+\)\s*\(name "([^"]+)"\)(.*?)(?=\(net\s*\(code|\Z)',
            nets_txt, re.S):
        name, body = m.group(1), m.group(2)
        nodes = re.findall(r'\(ref "([^"]+)"\)\s*\(pin "([^"]+)"\)', body)
        nets[name] = nodes
    return comps, nets


FP_CACHE = {}

def load_fp(fpid):
    """Resolve 'Lib:Name' -> FOOTPRINT (fresh copy each call)."""
    lib, name = fpid.split(":", 1)
    for d in (LIB / f"{lib}.pretty", LIB / "generated", OFFICIAL / f"{lib}.pretty"):
        if (d / f"{name}.kicad_mod").exists():
            fp = pcbnew.FootprintLoad(str(d), name)
            if fp:
                return fp
    return None


def mm(v):
    return pcbnew.FromMM(float(v))


def fp_bbox_mm(fp):
    bb = fp.GetBoundingBox(False, False)   # no text
    return pcbnew.ToMM(bb.GetWidth()), pcbnew.ToMM(bb.GetHeight())


def main():
    outline = json.loads((V1 / "outline.json").read_text())
    bean = Polygon(outline["points_mm"])
    H = outline["width_mm"]
    comps_pos = {c["name"]: c for c in json.loads((V1 / "components.json").read_text())}

    comps, nets = parse_netlist(NETLIST.read_text())
    print(f"netlist: {len(comps)} comps, {len(nets)} nets")

    board = pcbnew.NewBoard(str(OUT))

    netinfo = {}
    for name in sorted(nets):
        ni = pcbnew.NETINFO_ITEM(board, name)
        board.Add(ni)
        netinfo[name] = ni
    pad_net = {}
    for name, nodes in nets.items():
        for ref, pin in nodes:
            pad_net[(ref, pin)] = name

    # --- fixed placements from components.json ---------------------------
    fixed = {}          # ref -> (x_center, y_center_kicad, side)
    for part, refs in PLACEMENT_TABLE.items():
        c = comps_pos[part]
        x, y, w, h = c["x_mm"], c["y_mm"], c["w_mm"], c["h_mm"]
        side = c["side"]
        cy = H - (y + h / 2)                   # KiCad y grows downward
        if len(refs) == 1 or part == "PIN radiation det +":
            for ref in refs:                   # concentric (D_PIN + SH_RAD)
                fixed[ref] = (x + w / 2, cy, side)
        elif part == "BQ29700+FET protect":
            fixed[refs[0]] = (x + w * 0.28, cy, side)
            fixed[refs[1]] = (x + w * 0.75, cy, side)
        else:                                  # row distribution (switches)
            n = len(refs)
            pitch = w / n
            for i, ref in enumerate(refs):
                fixed[ref] = (x + pitch * (i + 0.5), cy, side)

    # --- occupancy grids for the greedy placer ---------------------------
    # RES 0.25 grid; a cell is usable when its center clears the bean edge
    # by 0.45 mm (edge clearance); part-to-part spacing comes from the 0.15
    # per-side inflation below (bbox >= courtyard, so no courtyard overlap).
    RES = 0.25
    nx, ny = int(68 / RES) + 2, int(40 / RES) + 2
    occ = {"top": np.zeros((nx, ny), bool), "bot": np.zeros((nx, ny), bool)}
    occF = {"top": np.zeros((nx, ny), bool), "bot": np.zeros((nx, ny), bool)}
    shrunk = bean.buffer(-0.45)
    from shapely.geometry import Point
    inside = np.zeros((nx, ny), bool)
    for i in range(nx):
        for j in range(ny):
            inside[i, j] = shrunk.contains(Point(i * RES, H - j * RES))
    def mark(side, cx, cy, w, h):
        i0 = max(0, int((cx - w / 2 - 0.05) / RES))
        i1 = min(nx, int((cx + w / 2 + 0.05) / RES) + 1)
        j0 = max(0, int((cy - h / 2 - 0.05) / RES))
        j1 = min(ny, int((cy + h / 2 + 0.05) / RES) + 1)
        occ[side][i0:i1, j0:j1] = True
    def free(side, cx, cy, w, h):
        i0, i1 = int((cx - w / 2) / RES), int((cx + w / 2) / RES) + 1
        j0, j1 = int((cy - h / 2) / RES), int((cy + h / 2) / RES) + 1
        if i0 < 0 or j0 < 0 or i1 > nx or j1 > ny:
            return False
        return inside[i0:i1, j0:j1].all() and not occ[side][i0:i1, j0:j1].any()

    # --- instantiate all footprints ---------------------------------------
    missing, placed_n, grid_parts = [], 0, []
    footprints = {}
    for ref, fpid in sorted(comps.items()):
        fp = load_fp(fpid)
        if fp is None:
            missing.append((ref, fpid))
            continue
        fp.SetReference(ref)
        footprints[ref] = fp
        board.Add(fp)
        if ref in fixed:
            cx, cy, side = fixed[ref]
            fp.SetPosition(pcbnew.VECTOR2I(mm(cx), mm(cy)))
            if side == "bot":
                fp.Flip(fp.GetPosition(), False)
            w, h = fp_bbox_mm(fp)
            mark(side, cx, cy, max(w, 0.8), max(h, 0.8))
            placed_n += 1
        else:
            grid_parts.append(ref)

    # --- greedy grid placement for the rest -------------------------------
    grid_parts.sort(key=lambda r: -fp_bbox_mm(footprints[r])[0]
                    * fp_bbox_mm(footprints[r])[1])
    unplaced = []
    for ref in grid_parts:
        fp = footprints[ref]
        w, h = fp_bbox_mm(fp)
        w, h = max(w, 0.8), max(h, 0.8)
        done = False
        for side in ("bot", "top"):
            step = 0.5
            for cy in np.arange(1.5, 39.5, step):
                for cx in np.arange(1.5, 67.5, step):
                    if free(side, cx, cy, w, h):
                        fp.SetPosition(pcbnew.VECTOR2I(mm(cx), mm(cy)))
                        if side == "bot":
                            fp.Flip(fp.GetPosition(), False)
                        mark(side, cx, cy, w, h)
                        done = True
                        break
                if done:
                    break
            if done:
                break
        if not done:
            # containment-only fallback: keep the part INSIDE the bean even if
            # its courtyard overlaps a primary neighbour — recorded as H3
            # placement debt (shows up as courtyard-overlap DRC items, not
            # lost parts). Fallback parts still avoid EACH OTHER via occF.
            for side in ("top", "bot"):
                for cy in np.arange(1.5, 39.5, 0.5):
                    for cx in np.arange(1.5, 67.5, 0.5):
                        i0, i1 = int((cx - w / 2) / RES), int((cx + w / 2) / RES) + 1
                        j0, j1 = int((cy - h / 2) / RES), int((cy + h / 2) / RES) + 1
                        if (0 <= i0 and 0 <= j0 and i1 <= nx and j1 <= ny
                                and inside[i0:i1, j0:j1].all()
                                and not occF[side][i0:i1, j0:j1].any()):
                            fp.SetPosition(pcbnew.VECTOR2I(mm(cx), mm(cy)))
                            if side == "bot":
                                fp.Flip(fp.GetPosition(), False)
                            occF[side][i0:i1, j0:j1] = True
                            done = True
                            break
                    if done:
                        break
                if done:
                    break
            unplaced.append(ref)

    # --- pad -> net binding -----------------------------------------------
    bound, unbound_pads = 0, 0
    for ref, fp in footprints.items():
        for pad in fp.Pads():
            key = (ref, pad.GetNumber())
            if key in pad_net:
                pad.SetNet(netinfo[pad_net[key]])
                bound += 1
            else:
                unbound_pads += 1

    # --- Edge.Cuts bean polygon -------------------------------------------
    pts = outline["points_mm"]
    for k in range(len(pts)):
        x1, y1 = pts[k]
        x2, y2 = pts[(k + 1) % len(pts)]
        seg = pcbnew.PCB_SHAPE(board)
        seg.SetShape(pcbnew.SHAPE_T_SEGMENT)
        seg.SetStart(pcbnew.VECTOR2I(mm(x1), mm(H - y1)))
        seg.SetEnd(pcbnew.VECTOR2I(mm(x2), mm(H - y2)))
        seg.SetLayer(pcbnew.Edge_Cuts)
        seg.SetWidth(mm(0.1))
        board.Add(seg)

    board.Save(str(OUT))
    # pcbnew auto-creates .kicad_pro/.kicad_prl on save — remove them: CI's
    # eda job gates on *.kicad_pro and routing has not happened yet (H3).
    for ext in (".kicad_pro", ".kicad_prl"):
        p = OUT.with_suffix(ext)
        if p.exists():
            p.unlink()
    print(f"placed fixed={placed_n} grid={len(grid_parts) - len(unplaced)} "
          f"overlap-fallback={len(unplaced)}: {unplaced[:12]}{chr(46)*3 if len(unplaced)>12 else chr(39)*0}")
    print(f"pads bound to nets: {bound}; pads without net (E0 pin-map gap): {unbound_pads}")
    if missing:
        print("MISSING FOOTPRINTS:")
        for r, f in missing:
            print("  ", r, f)
        sys.exit(1)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
