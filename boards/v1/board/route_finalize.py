#!/usr/bin/env python3
"""H3.3d — final DRC + audits + artifacts.

* refills zones, runs the DRC engine -> drc_final.{rpt,json}
* honest unconnected census (geometric connectivity, no report cap),
  split into: do-not-route (AS7058/MMC5983MA), testpoint-only edges,
  signal edges, power edges
* CO_AFE_OUT guard audit (foreign copper within 0.30mm on its layers)
* radiation-confinement audit (RAD_* copper outside the shield-can bbox)
* XSPI / diff-pair length tables
* copper utilization per layer, track/via counts
* per-layer SVG exports via kicad-cli

Run: python3 boards/v1/board/route_finalize.py
"""
import json
import subprocess
import time

import pcbnew
from shapely.geometry import LineString, Point

import route_lib as RL
from route_router import Router

HERE = RL.HERE


def track_len(board, netcode):
    tot, nvia = 0.0, 0
    for t in board.GetTracks():
        if t.GetNetCode() != netcode:
            continue
        if t.GetClass() == "PCB_VIA":
            nvia += 1
        else:
            tot += RL.tomm(int(t.GetLength()))
    return round(tot, 2), nvia


def main():
    t0 = time.time()
    board = RL.load()
    r = Router(board)
    r.exclude_refs = ()
    out = {}

    # ---- unconnected census -------------------------------------------------
    dnr_refs = ("U_AS7058", "U_MMC")
    census = {"do_not_route": 0, "testpoint": 0, "signal": 0, "power": 0}
    per_net = {}
    iref = getattr(r, "item_ref", {})
    for net in r.items:
        cls = r.clusters(net)
        if len(cls) <= 1:
            continue
        name = r.netname.get(net, "?")
        edges = len(cls) - 1
        # classify each surplus cluster
        for c in cls[1:]:
            refs = {iref.get(iid, "") for iid, _g, _l in c}
            refs.discard("")
            if refs and refs <= set(dnr_refs):
                census["do_not_route"] += 1
            elif refs and all(x.startswith("TP") for x in refs):
                census["testpoint"] += 1
            elif name == "GND" or name.startswith(("3V3", "1V8", "V")):
                census["power"] += 1
            else:
                census["signal"] += 1
        per_net[name] = edges
    out["unconnected_census"] = census
    out["unconnected_total"] = sum(census.values())
    out["unconnected_by_net"] = dict(sorted(per_net.items(),
                                            key=lambda kv: -kv[1]))

    # ---- length tables --------------------------------------------------------
    xspi = ["XSPI_CS_N", "XSPI_DQS", "XSPI_CLK"] + [f"XSPI_D{i}" for i in range(8)]
    out["xspi_mm"] = {}
    for name in xspi:
        n = board.FindNet(name)
        if n:
            out["xspi_mm"][name] = track_len(board, n.GetNetCode())
    pairs = {}
    for p, q in (("USB_DP", "USB_DM"), ("CSI_CKP", "CSI_CKN"),
                 ("CSI_D0P", "CSI_D0N"), ("CSI_D1P", "CSI_D1N")):
        lp = track_len(board, board.FindNet(p).GetNetCode())
        lq = track_len(board, board.FindNet(q).GetNetCode())
        pairs[f"{p}/{q}"] = {"p": lp, "n": lq,
                             "delta_mm": round(lp[0] - lq[0], 3)}
    out["pairs"] = pairs

    # ---- CO_AFE_OUT guard audit ----------------------------------------------
    co = board.FindNet("CO_AFE_OUT").GetNetCode()
    viol = []
    for t in board.GetTracks():
        if t.GetNetCode() != co or t.GetClass() == "PCB_VIA":
            continue
        seg = LineString([(RL.tomm(t.GetStart().x), RL.tomm(t.GetStart().y)),
                          (RL.tomm(t.GetEnd().x), RL.tomm(t.GetEnd().y))])
        probe = seg.buffer(0.30 + RL.tomm(int(t.GetWidth())) / 2)
        hits = r.g and None
        near = set()
        for t2 in board.GetTracks():
            if t2.GetNetCode() in (co, 0) or t2.GetClass() == "PCB_VIA":
                continue
            if t2.GetLayer() != t.GetLayer():
                continue
            seg2 = LineString([(RL.tomm(t2.GetStart().x), RL.tomm(t2.GetStart().y)),
                               (RL.tomm(t2.GetEnd().x), RL.tomm(t2.GetEnd().y))])
            if probe.intersects(seg2):
                near.add(t2.GetNetname())
        viol.extend(sorted(near))
    out["co_afe_guard_intrusions"] = sorted(set(viol))

    # ---- radiation confinement audit -------------------------------------------
    sh = next(fp for fp in board.GetFootprints() if fp.GetReference() == "SH_RAD")
    c = sh.GetPosition()
    cx, cy = RL.tomm(c.x), RL.tomm(c.y)
    outside = []
    for name in ("RAD_IN", "RAD_VREF", "RAD_VTH", "PIN_BIAS"):
        n = board.FindNet(name).GetNetCode()
        for t in board.GetTracks():
            if t.GetNetCode() != n:
                continue
            for px, py in ((RL.tomm(t.GetStart().x), RL.tomm(t.GetStart().y)),
                           (RL.tomm(t.GetEnd().x), RL.tomm(t.GetEnd().y))):
                if abs(px - cx) > 5.3 or abs(py - cy) > 5.3:
                    outside.append(name)
                    break
    out["rad_nets_outside_can"] = sorted(set(outside))

    # ---- copper stats ------------------------------------------------------------
    layers = {RL.F: "F.Cu", RL.IN1: "In1.Cu", RL.IN2: "In2.Cu",
              RL.IN3: "In3.Cu", RL.IN4: "In4.Cu", RL.B: "B.Cu"}
    area = {v: 0.0 for v in layers.values()}
    ntr = nvia = 0
    tlen = 0.0
    for t in board.GetTracks():
        if t.GetClass() == "PCB_VIA":
            nvia += 1
        else:
            ntr += 1
            L = RL.tomm(int(t.GetLength()))
            tlen += L
            area[layers.get(t.GetLayer(), "?")] = area.get(
                layers.get(t.GetLayer(), "?"), 0) + L * RL.tomm(int(t.GetWidth()))
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    for z in board.Zones():
        if z.GetIsRuleArea():
            continue
        try:
            sp = z.GetFilledPolysList(z.GetLayer())
            area[layers[z.GetLayer()]] += sp.Area() / 1e12
        except Exception:
            pass
    bean_area = RL.board_poly(board).area
    out["copper_util_pct"] = {k: round(100 * v / bean_area, 1)
                              for k, v in area.items()}
    out["tracks"] = ntr
    out["vias"] = nvia
    out["track_len_mm"] = round(tlen, 0)

    (HERE / "route_final_audit.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1)[:3000])

    # ---- DRC + renders ---------------------------------------------------------
    board.Save(str(RL.PCB))
    subprocess.run(["python3", str(HERE / "drc_check.py"), "drc_final",
                    "H3.3d final: routed board"], cwd=HERE)
    for name, lay in (("board_final_top", "F.Cu,F.SilkS,Edge.Cuts"),
                      ("board_final_bottom", "B.Cu,B.SilkS,Edge.Cuts"),
                      ("board_final_in1", "In1.Cu,Edge.Cuts"),
                      ("board_final_in2_gnd", "In2.Cu,Edge.Cuts"),
                      ("board_final_in3_pwr", "In3.Cu,Edge.Cuts"),
                      ("board_final_in4", "In4.Cu,Edge.Cuts")):
        subprocess.run(["kicad-cli", "pcb", "export", "svg", "--layers", lay,
                        "-o", str(HERE / f"{name}.svg"), str(RL.PCB)],
                       capture_output=True)
    p = RL.PCB.with_suffix(".kicad_prl")
    if p.exists():
        p.unlink()
    print(f"done ({time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main()
