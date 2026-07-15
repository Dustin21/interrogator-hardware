#!/usr/bin/env python3
"""H3.3a — planes + fanout.

1. Board rule areas (no copper, all layers): BL54L15 antenna keep-out
   (EZ-DS v1.9 §7.3.1 — the on-board 5.0x8.5 region under the module's
   antenna end; taken from the footprint's Dwgs.User dashed rect) and the
   SR4G013 GNSS antenna region (IM UBX-21028173 ground-clearance under the
   antenna, minus a feed corridor at the feed pad). The ESP32-C6 keep-out
   ships inside the Espressif footprint already (ECO-H3.2-E).
2. In2.Cu solid GND plane over the whole bean.
3. In3.Cu power islands: VDD_CORE_N6, gated 1V8_*/3V3_* islands, 3V3_AON,
   VSYS, 1V8, 3V3_SYS (subtract-in-order, single piece per rail, 0.3
   island-island clearance). Rails whose pads fall outside their island
   are left to the H3.3c router as PWR-class tracks (star feed from the
   load switch is the intended topology for the gated rails anyway).
4. VFBGA142 / fcCSP50 / DSBGA-9 / BGA24 via-in-pad POFV fanout: 0.2/0.4
   through via at every netted ball center, no dogbones (0.5mm pitch).
5. Plane-drop vias: every other SMD pad on GND or an island-covered rail
   gets a 0.2/0.4 via + surface stub (shared with a nearby same-net via
   when one is already in reach). AS7058 + MMC5983MA are NOT fanned out
   (PROVISIONAL-E0 ball maps — do-not-route stands).
6. interrogator_v1.kicad_dru written: clearance/hole relaxation inside the
   via-in-pad BGA courtyards (0.09 copper / 0.15 hole-to-copper).
7. Zones filled, board saved. Run DRC via run_drc.py afterwards.

Run: python3 boards/v1/board/route_planes.py
"""
import json
import math
import sys
from pathlib import Path

import pcbnew
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union

import route_lib as RL
from route_lib import (ALL_CU, B, F, IN1, IN2, IN3, IN4, CLEARANCE,
                       HOLE_TO_COPPER, TRACK_W, VIA_D, VIA_DRILL, mm, tomm)

HERE = Path(__file__).resolve().parent

# forced via-in-pad fanout: only the 0.5mm-pitch parts whose INNER balls
# cannot escape laterally (VFBGA142 15x15, fcCSP50) + the DSBGA-9 center
# ball (U_GAUGE B2 = VSS; its 8 edge balls escape laterally on B.Cu).
# The NOR BGA24 is 1.0mm pitch — lateral + checked drops like everything
# else. Forced balls that fail the opposite-face check fall through to the
# searched-drop path (edge balls) or the H3.3c router.
BGA_FANOUT_REFS = ("U_N657", "U_A121")
FORCED_BALLS = {("U_GAUGE", "B2")}
DO_NOT_ROUTE_REFS = ("U_AS7058", "U_MMC")   # PROVISIONAL-E0 pin maps

# island rails, most-local first (subtract-in-order)
ISLAND_RAILS = [
    "VDD_CORE_N6",
    "1V8_RADAR", "3V3_RADAR", "3V3_GNSS", "1V8_OPTICAL", "3V3_OPTICAL",
    "1V8_AIR", "3V3_AIR", "3V3_CONTACT", "3V3_WIFI",
    "3V3_AON", "VSYS", "1V8", "3V3_SYS",
]


def main():
    board = RL.load()
    bds = board.GetDesignSettings()
    bds.m_HoleClearance = mm(0.20)   # JLC 6L hole-to-copper capability
    bean = RL.board_poly(board)
    print(f"bean area {bean.area:.0f} mm2")

    obs, pads = RL.harvest_board(board)
    netbyname = {}
    for p in pads:
        netbyname.setdefault(p["netname"], p["net"])

    # ---- 1. antenna rule areas --------------------------------------------
    bl54 = next(fp for fp in board.GetFootprints()
                if fp.GetReference() == "U_BL54")
    xs, ys = [], []
    for g in bl54.GraphicalItems():
        if g.GetLayer() == pcbnew.Dwgs_User:
            bb = g.GetBoundingBox()
            xs += [tomm(bb.GetLeft()), tomm(bb.GetRight())]
            ys += [tomm(bb.GetTop()), tomm(bb.GetBottom())]
    bl_keep = Polygon([(min(xs), min(ys)), (max(xs), min(ys)),
                       (max(xs), max(ys)), (min(xs), max(ys))])
    bl_keep_on = bl_keep.intersection(bean.buffer(1.0))  # on-board part
    RL.add_rule_area(board, bl_keep_on, "BL54L15 antenna keepout (EZ-DS v1.9 7.3.1)")

    ant = next(fp for fp in board.GetFootprints()
               if fp.GetReference() == "AE_GNSS")
    abb = ant.GetBoundingBox(False, False)
    ant_poly = Polygon([(tomm(abb.GetLeft()) - 0.3, tomm(abb.GetTop()) - 0.3),
                        (tomm(abb.GetRight()) + 0.3, tomm(abb.GetTop()) - 0.3),
                        (tomm(abb.GetRight()) + 0.3, tomm(abb.GetBottom()) + 0.3),
                        (tomm(abb.GetLeft()) - 0.3, tomm(abb.GetBottom()) + 0.3)])
    feed = [p for p in pads if p["ref"] == "AE_GNSS"]
    corridors = unary_union([Point(p["x"], p["y"]).buffer(
        2.3 if p["netname"] == "GND" else 1.6) for p in feed])
    ant_keep = ant_poly.difference(corridors)
    if ant_keep.geom_type == "MultiPolygon":
        ant_keep = max(ant_keep.geoms, key=lambda g: g.area)
    RL.add_rule_area(board, ant_keep,
                     "SR4G013 GNSS antenna clearance (IM UBX-21028173)")
    keeps = [bl_keep, ant_keep] + RL.keepout_polys(board)
    keep_union = unary_union(keeps)

    # ---- 2. In2 GND plane ---------------------------------------------------
    gnd = board.FindNet("GND").GetNetCode()
    RL.add_zone(board, IN2, gnd, bean, "GND plane (In2)", min_thick=0.15)

    # ---- 3. In3 power islands ----------------------------------------------
    # Nearest-pad Voronoi partition of the whole In3 face: every raster cell
    # goes to the rail whose nearest pad is closest (no greedy ordering, no
    # starvation, full-coverage locality). Masks are polygonized, eroded
    # 0.16 (=> >=0.32 island-to-island gap), and every piece keeping >=2
    # pads survives. Pieces of one rail are bridged by PWR-class tracks at
    # H3.3c — for the gated rails that IS the intended star-feed-from-the-
    # switch topology.
    import numpy as np
    from scipy.spatial import cKDTree
    from shapely.geometry import box as sbox

    usable = bean.buffer(-0.4).difference(keep_union.buffer(0.15))
    rail_pts = {}
    seeds, labels = [], []
    for ri, rail in enumerate(ISLAND_RAILS):
        pts = [(p["x"], p["y"]) for p in pads if p["netname"] == rail
               and p["ref"] not in DO_NOT_ROUTE_REFS]
        rail_pts[rail] = pts
        seeds += pts
        labels += [ri] * len(pts)
    tree = cKDTree(seeds)
    labels = np.array(labels)

    GRES = 0.2
    minx, miny, maxx, maxy = bean.bounds
    gx = np.arange(minx, maxx + GRES, GRES)
    gy = np.arange(miny, maxy + GRES, GRES)
    XX, YY = np.meshgrid(gx, gy, indexing="ij")
    cells = np.column_stack([XX.ravel(), YY.ravel()])
    _, nearest = tree.query(cells, k=1)
    cell_rail = labels[nearest].reshape(XX.shape)
    # usable mask
    from shapely import contains_xy
    umask = contains_xy(usable, XX.ravel(), YY.ravel()).reshape(XX.shape)

    islands = {}
    island_cover = {}
    for ri, rail in enumerate(ISLAND_RAILS):
        mask = (cell_rail == ri) & umask
        idx = np.argwhere(mask)
        if idx.size == 0:
            print(f"island {rail}: no cells — all pads to router")
            continue
        boxes = [sbox(gx[i] - GRES / 2, gy[j] - GRES / 2,
                      gx[i] + GRES / 2, gy[j] + GRES / 2) for i, j in idx]
        region = unary_union(boxes).buffer(0.001)
        region = region.buffer(-0.16).intersection(usable)
        region = region.simplify(0.06)
        pts = rail_pts[rail]
        pieces = ([region] if region.geom_type == "Polygon"
                  else list(getattr(region, "geoms", [])))
        kept = []
        for g in pieces:
            cov = g.buffer(-0.26)
            n = sum(1 for x, y in pts if cov.contains(Point(x, y)))
            if n >= 2 and g.area >= 2.0:
                kept.append(g)
        if not kept:
            print(f"island {rail}: no viable piece — all pads to router")
            continue
        region = unary_union(kept)
        islands[rail] = region
        cover = region.buffer(-0.30)      # via annulus fully inside the fill
        island_cover[rail] = cover
        covered = sum(1 for x, y in pts if cover.contains(Point(x, y)))
        print(f"island {rail}: {region.area:.0f} mm2, {len(kept)} piece(s), "
              f"covers {covered}/{len(pts)} pads")
        for k, poly in enumerate(kept):
            RL.add_zone(board, IN3, netbyname[rail], poly.simplify(0.05),
                        f"{rail} island (In3) #{k}", min_thick=0.15)

    # ---- 4+5. fanout + plane-drop vias --------------------------------------
    via_count = {"bga": 0, "drop": 0, "shared": 0, "fail": 0}
    via_registry = {}           # netcode -> [(x, y)]
    board_via_ok = bean.buffer(-0.45).difference(keep_union.buffer(0.1))
    # searched drops must stay OUT of the via-in-pad fields (+0.7 halo):
    # the channels between the forced ball vias are the ONLY inner-layer
    # escape paths for interior-ball signals (H3.3b finding)
    for ref in BGA_FANOUT_REFS:
        fp2 = next(f for f in board.GetFootprints() if f.GetReference() == ref)
        pxs = [tomm(pp.GetPosition().x) for pp in fp2.Pads()]
        pys = [tomm(pp.GetPosition().y) for pp in fp2.Pads()]
        field = Polygon([(min(pxs) - 0.7, min(pys) - 0.7),
                         (max(pxs) + 0.7, min(pys) - 0.7),
                         (max(pxs) + 0.7, max(pys) + 0.7),
                         (min(pxs) - 0.7, max(pys) + 0.7)])
        board_via_ok = board_via_ok.difference(field)

    def register_via(x, y, net):
        RL.add_via(board, x, y, net)
        obs.add(Point(x, y).buffer(VIA_D / 2), net, set(ALL_CU))
        obs.add_hole(x, y, VIA_DRILL)
        via_registry.setdefault(net, []).append((x, y))

    # 4. via-in-pad BGA fanout — position is FORCED (ball center), but a
    # through-via must still be verified against the OPPOSITE face + all
    # inner copper; a conflict here is a placement bug, so it is logged
    # loudly and the via is SKIPPED (visible as unconnected, never a short).
    bga_skips = []
    blocked_fanout = []
    for p in pads:
        forced = ((p["ref"] in BGA_FANOUT_REFS or (p["ref"], p["num"]) in FORCED_BALLS)
                  and p["net"] > 0 and not p["th"])
        if forced:
            vgeom = Point(p["x"], p["y"]).buffer(VIA_D / 2)
            others = [l for l in ALL_CU if l not in p["layers"]]
            # in-field 0.5mm-pitch neighbours: dru hole rule is 0.15 there
            if not obs.clear_of(vgeom, p["net"], others, 0.10, hole_margin=0.16):
                bga_skips.append(f'{p["ref"]}.{p["num"]} {p["netname"]}')
                blocked_fanout.append(p)      # edge balls: searched drop below
                continue
            register_via(p["x"], p["y"], p["net"])
            via_count["bga"] += 1
    if bga_skips:
        print(f"  fanout blocked by opposite-face copper (fall through to "
              f"searched drops / router): {bga_skips}")
    print(f"via-in-pad fanout: {via_count['bga']} vias "
          f"({', '.join(BGA_FANOUT_REFS)})")

    # 5. plane-drop vias for GND + covered rail pads
    DIRS = [(math.cos(a * math.pi / 8), math.sin(a * math.pi / 8))
            for a in range(16)]
    RADII = (0.55, 0.7, 0.85, 1.0, 1.2, 1.45, 1.7, 2.0, 2.4, 2.8, 3.2)

    rf_pads = [q["shape"] for q in pads
               if q["netname"] in ("GNSS_RF", "RF_IN")]

    def rf_clear(geom):
        return all(geom.distance(s) >= 0.21 for s in rf_pads)

    def stub_ok(p, vx, vy, width):
        line = LineString([(p["x"], p["y"]), (vx, vy)])
        corr = line.buffer(width / 2)
        if corr.intersects(keep_union):
            return False                      # rule areas allow no tracks
        if p["netname"] not in ("GNSS_RF", "RF_IN") and not rf_clear(corr):
            return False                      # RF netclass clearance 0.2
        return obs.clear_of(corr, p["net"], [next(iter(p["layers"]))],
                            CLEARANCE + 0.02, check_holes=False)

    def drop_via(p, region=None):
        """region: shapely area the via must land in (rail islands); None=GND."""
        width = min(0.25, max(0.12, min(p["shape"].bounds[2] - p["shape"].bounds[0],
                                        p["shape"].bounds[3] - p["shape"].bounds[1]) * 0.8))
        # big pads (EPs, lands): via-in-pad at center, POFV
        cpt = Point(p["x"], p["y"])
        if (p["shape"].buffer(-(VIA_D / 2 + 0.05)).contains(cpt)
                and board_via_ok.contains(cpt)
                and (region is None or region.contains(cpt))
                and obs.clear_of(cpt.buffer(VIA_D / 2),
                                 p["net"], list(ALL_CU), CLEARANCE + 0.02)):
            register_via(p["x"], p["y"], p["net"])
            via_count["drop"] += 1
            return True
        # reuse a nearby same-net via if a straight stub reaches it (any
        # same-net via is a verified connection — no region test needed)
        for vx, vy in via_registry.get(p["net"], []):
            d = math.hypot(vx - p["x"], vy - p["y"])
            if d < 1.6 and stub_ok(p, vx, vy, width):
                RL.add_track(board, p["x"], p["y"], vx, vy,
                             next(iter(p["layers"])), p["net"], width)
                obs.add(LineString([(p["x"], p["y"]), (vx, vy)]).buffer(width / 2),
                        p["net"], {next(iter(p["layers"]))})
                via_count["shared"] += 1
                return True
        for r in RADII:
            for dx, dy in DIRS:
                vx, vy = p["x"] + dx * r, p["y"] + dy * r
                vpt = Point(vx, vy)
                if not board_via_ok.contains(vpt):
                    continue
                if region is not None and not region.contains(vpt):
                    continue
                vgeom = vpt.buffer(VIA_D / 2)
                if not obs.clear_of(vgeom, p["net"], list(ALL_CU), CLEARANCE + 0.02):
                    continue
                if p["netname"] not in ("GNSS_RF", "RF_IN") and not rf_clear(vgeom):
                    continue
                if not stub_ok(p, vx, vy, width):
                    continue
                register_via(vx, vy, p["net"])
                RL.add_track(board, p["x"], p["y"], vx, vy,
                             next(iter(p["layers"])), p["net"], width)
                obs.add(LineString([(p["x"], p["y"]), (vx, vy)]).buffer(width / 2),
                        p["net"], {next(iter(p["layers"]))})
                via_count["drop"] += 1
                return True
        via_count["fail"] += 1
        return False

    rail_nets = {netbyname[r]: r for r in islands if r in netbyname}
    fails = []
    router_pads = 0
    blocked_ids = {id(p) for p in blocked_fanout}
    for p in sorted(pads, key=lambda q: (q["ref"], q["num"])):
        if ((p["ref"] in BGA_FANOUT_REFS and id(p) not in blocked_ids)
                or p["ref"] in DO_NOT_ROUTE_REFS):
            continue
        if p["th"] or p["net"] <= 0 or not p["layers"]:
            continue
        if len(p["layers"]) > 1:
            continue                      # already through-connected
        if p["net"] == gnd:
            region = None                 # In2 is everywhere
        elif p["net"] in rail_nets:
            rail = rail_nets[p["net"]]
            region = island_cover[rail]
            if not region.contains(Point(p["x"], p["y"])):
                router_pads += 1
                continue                  # outside island -> router track
        else:
            continue                      # signal net -> router
        if not drop_via(p, region):
            fails.append((p["ref"], p["num"], p["netname"]))
    print(f"rail pads outside islands (router feeds): {router_pads}")

    print(f"plane drops: {via_count['drop']} new vias, "
          f"{via_count['shared']} shared-stub, {via_count['fail']} FAILED")
    if fails:
        print("  failed drops (left to router):",
              [f"{r}.{n} {nn}" for r, n, nn in fails[:20]])

    # ---- 5b. cleanup: drop In3 island pieces that got NO via (dead copper) --
    removed = 0
    for z in list(board.Zones()):
        if z.GetIsRuleArea() or z.GetLayer() != IN3:
            continue
        o = z.Outline().Outline(0)
        zpoly = Polygon([(tomm(o.CPoint(k).x), tomm(o.CPoint(k).y))
                         for k in range(o.PointCount())])
        vias_in = [1 for x, y in via_registry.get(z.GetNetCode(), [])
                   if zpoly.contains(Point(x, y))]
        if not vias_in:
            board.Remove(z)
            removed += 1
    print(f"removed {removed} via-less In3 island pieces (dead copper)")

    # ---- 6. kicad_dru: BGA via-in-pad relaxations ---------------------------
    cond = " || ".join(f"A.insideCourtyard('{r}')" for r in BGA_FANOUT_REFS)
    dru = HERE / "interrogator_v1.kicad_dru"
    dru.write_text(f"""(version 1)
# H3.3a — via-in-pad POFV fanout regions (0.5 mm pitch, 0.2/0.4 vias):
# JLCPCB 6L via-in-pad process; clearance/hole relaxations apply ONLY
# inside the fanout parts' courtyards.
(rule bga_viainpad_clearance
  (condition "{cond}")
  (constraint clearance (min 0.09mm)))
(rule bga_viainpad_hole
  (condition "{cond}")
  (constraint hole_clearance (min 0.15mm)))
(rule bga_viainpad_track
  (condition "{cond}")
  (constraint track_width (min 0.09mm)))
""")
    print(f"wrote {dru.name}")

    # ---- 7. fill + save ------------------------------------------------------
    RL.fill_zones(board)
    RL.save(board)
    tracks = [t for t in board.GetTracks()]
    print(f"saved: {sum(1 for t in tracks if t.GetClass() == 'PCB_VIA')} vias, "
          f"{sum(1 for t in tracks if t.GetClass() != 'PCB_VIA')} tracks, "
          f"{len(list(board.Zones()))} zones")


if __name__ == "__main__":
    main()
