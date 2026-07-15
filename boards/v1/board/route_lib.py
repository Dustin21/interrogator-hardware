#!/usr/bin/env python3
"""Shared routing infrastructure for H3.3 (planes, fanout, track routing).

Geometry model: shapely on top of pcbnew. All coordinates in mm, KiCad
frame (y grows DOWN — the same frame as the .kicad_pcb file), so anything
read from or written to the board needs no axis flip.

Obstacle index: every pad/via/track is registered as a shapely geometry
tagged with (netcode, layer-set). Clearance queries are conservative:
pads are their real polygon outline (GetEffectivePolygon) where available,
else bbox. Through-holes additionally register a 'hole' obstacle that
applies on every copper layer regardless of net (hole-to-copper rule).

Copper layers: F.Cu + In1.Cu + In4.Cu + B.Cu are SIGNAL layers for the
router; In2.Cu is the solid GND plane, In3.Cu the power-island layer —
tracks are never created on In2/In3 (plane integrity), only vias pass
through them (POFV process, via-in-pad allowed).
"""
import json
import math
from pathlib import Path

import pcbnew
from shapely.geometry import (LineString, MultiPolygon, Point, Polygon, box)
from shapely.ops import unary_union
from shapely.strtree import STRtree

HERE = Path(__file__).resolve().parent
V1 = HERE.parent
PCB = HERE / "interrogator_v1.kicad_pcb"

F, IN1, IN2, IN3, IN4, B = (pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu,
                            pcbnew.In3_Cu, pcbnew.In4_Cu, pcbnew.B_Cu)
SIGNAL_LAYERS = (F, IN1, IN4, B)
ALL_CU = (F, IN1, IN2, IN3, IN4, B)

# rule set (JLCPCB 6L through-via + POFV capabilities; netclasses in .kicad_pro)
CLEARANCE = 0.10          # default copper-copper
CLEARANCE_BGA = 0.09      # inside the VFBGA142 courtyard (kicad_dru rule)
TRACK_W = 0.10
TRACK_W_PWR = 0.25
VIA_D, VIA_DRILL = 0.40, 0.20
HOLE_TO_COPPER = 0.22     # 0.2 rule + 0.02 polygon-approx margin
EDGE_CLEARANCE = 0.20


def mm(v):
    return pcbnew.FromMM(float(v))


def tomm(v):
    return pcbnew.ToMM(int(v))


def load():
    return pcbnew.LoadBoard(str(PCB))


def board_poly(board):
    """Edge.Cuts bean outline as a shapely Polygon (KiCad frame)."""
    pts = []
    segs = []
    for d in board.GetDrawings():
        if d.GetLayer() == pcbnew.Edge_Cuts and d.GetShape() == pcbnew.SHAPE_T_SEGMENT:
            segs.append(((tomm(d.GetStart().x), tomm(d.GetStart().y)),
                         (tomm(d.GetEnd().x), tomm(d.GetEnd().y))))
    # chain the segments
    seg_map = {}
    for a, b_ in segs:
        seg_map.setdefault(a, []).append(b_)
        seg_map.setdefault(b_, []).append(a)
    start = segs[0][0]
    pts = [start]
    prev, cur = None, start
    while True:
        nxts = [p for p in seg_map[cur] if p != prev]
        if not nxts:
            break
        prev, cur = cur, nxts[0]
        if cur == start:
            break
        pts.append(cur)
    return Polygon(pts)


def pad_shape(pad):
    """Conservative shapely shape of a pad's copper (KiCad frame, mm)."""
    try:
        poly = pad.GetEffectivePolygon()
        outs = []
        for i in range(poly.OutlineCount()):
            o = poly.Outline(i)
            outs.append(Polygon([(tomm(o.CPoint(k).x), tomm(o.CPoint(k).y))
                                 for k in range(o.PointCount())]))
        if outs:
            return unary_union(outs)
    except Exception:
        pass
    bb = pad.GetBoundingBox()
    return box(tomm(bb.GetLeft()), tomm(bb.GetTop()),
               tomm(bb.GetRight()), tomm(bb.GetBottom()))


def pad_layers(pad):
    """Set of copper layers this pad's copper exists on."""
    if pad.GetAttribute() in (pcbnew.PAD_ATTRIB_PTH,):
        return set(ALL_CU)
    lay = set()
    for l in ALL_CU:
        if pad.IsOnLayer(l):
            lay.add(l)
    return lay


class Obstacles:
    """Copper-obstacle index per layer + global hole index.

    Static items (harvested once) live in an STRtree; items added during
    routing go to per-layer 'recent' lists that are scanned linearly with a
    bbox pre-test (cheap for the few hundred routing-time additions).
    """

    def __init__(self):
        self.items = {l: [] for l in ALL_CU}   # static (geom, netcode)
        self.recent = {l: [] for l in ALL_CU}  # dynamic (geom, netcode)
        self.holes = []                        # static (x, y, r)
        self.recent_holes = []
        self._trees = None
        self._holetree = None

    def add(self, geom, netcode, layers):
        target = self.recent if self._trees is not None else self.items
        for l in layers:
            target[l].append((geom, netcode))

    def add_hole(self, x, y, dia):
        if self._trees is not None:
            self.recent_holes.append((x, y, dia / 2.0))
        else:
            self.holes.append((x, y, dia / 2.0))

    def freeze(self):
        self._trees = {}
        for l in ALL_CU:
            geoms = [g for g, _ in self.items[l]]
            self._trees[l] = STRtree(geoms) if geoms else None
        self._holegeoms = [Point(x, y).buffer(r) for x, y, r in self.holes]
        self._holetree = STRtree(self._holegeoms) if self._holegeoms else None

    def _conflict(self, probe, netcode, layer):
        t = self._trees.get(layer)
        if t is not None:
            for idx in t.query(probe):
                g, net = self.items[layer][idx]
                if net != netcode and probe.intersects(g):
                    return True
        pb = probe.bounds
        for g, net in self.recent[layer]:
            if net == netcode:
                continue
            gb = g.bounds
            if gb[0] > pb[2] or gb[2] < pb[0] or gb[1] > pb[3] or gb[3] < pb[1]:
                continue
            if probe.intersects(g):
                return True
        return False

    def clear_of(self, geom, netcode, layers, clearance, check_holes=True,
                 hole_margin=None):
        """True if geom (final size) keeps `clearance` from all other-net
        copper on the given layers, and hole_margin (default HOLE_TO_COPPER)
        from every hole."""
        if self._trees is None:
            self.freeze()
        probe = geom.buffer(clearance)
        for l in layers:
            if self._conflict(probe, netcode, l):
                return False
        if check_holes:
            hp = geom.buffer(HOLE_TO_COPPER if hole_margin is None else hole_margin)
            hb = hp.bounds
            if self._holetree is not None:
                for idx in self._holetree.query(hp):
                    if hp.intersects(self._holegeoms[idx]):
                        return False
            for x, y, r in self.recent_holes:
                if (hb[0] - r <= x <= hb[2] + r and hb[1] - r <= y <= hb[3] + r
                        and hp.distance(Point(x, y)) < r):
                    return False
        return True

    def query_net(self, geom, layer):
        """Netcodes of copper intersecting geom on layer."""
        if self._trees is None:
            self.freeze()
        out = set()
        t = self._trees.get(layer)
        if t is not None:
            for idx in t.query(geom):
                g, net = self.items[layer][idx]
                if geom.intersects(g):
                    out.add(net)
        for g, net in self.recent[layer]:
            if geom.intersects(g):
                out.add(net)
        return out


def harvest_board(board, include_tracks=True):
    """Build the obstacle index + pad tables from the live board."""
    obs = Obstacles()
    pads = []            # dicts: ref, num, net, netname, pos(x,y), shape, layers, th
    for fp in board.GetFootprints():
        ref = fp.GetReference()
        for pad in fp.Pads():
            sh = pad_shape(pad)
            lay = pad_layers(pad)
            net = pad.GetNetCode()
            th = pad.GetAttribute() in (pcbnew.PAD_ATTRIB_PTH, pcbnew.PAD_ATTRIB_NPTH)
            if th and pad.GetDrillSize().x > 0:
                obs.add_hole(tomm(pad.GetPosition().x), tomm(pad.GetPosition().y),
                             tomm(pad.GetDrillSize().x))
            if not lay:
                continue    # paste-only aperture (EP subdivision) — no copper
            obs.add(sh, net if pad.GetNumber() else -1, lay)
            pads.append(dict(ref=ref, num=pad.GetNumber(), net=net,
                             netname=pad.GetNetname(),
                             x=tomm(pad.GetPosition().x), y=tomm(pad.GetPosition().y),
                             shape=sh, layers=lay, th=th, pad=pad))
    if include_tracks:
        for t in board.GetTracks():
            if t.GetClass() == "PCB_VIA":
                x, y = tomm(t.GetPosition().x), tomm(t.GetPosition().y)
                obs.add(Point(x, y).buffer(tomm(t.GetWidth()) / 2), t.GetNetCode(),
                        set(ALL_CU))
                obs.add_hole(x, y, tomm(t.GetDrill()))
            else:
                ls = LineString([(tomm(t.GetStart().x), tomm(t.GetStart().y)),
                                 (tomm(t.GetEnd().x), tomm(t.GetEnd().y))])
                obs.add(ls.buffer(tomm(t.GetWidth()) / 2), t.GetNetCode(),
                        {t.GetLayer()})
    return obs, pads


def keepout_polys(board):
    """All no-copper regions: rule areas (board + footprint) as shapely."""
    polys = []
    zones = list(board.Zones())
    for fp in board.GetFootprints():
        zones += list(fp.Zones())
    for z in zones:
        if not z.GetIsRuleArea():
            continue
        o = z.Outline()
        for i in range(o.OutlineCount()):
            ol = o.Outline(i)
            polys.append(Polygon([(tomm(ol.CPoint(k).x), tomm(ol.CPoint(k).y))
                                  for k in range(ol.PointCount())]))
    return polys


def add_via(board, x, y, netcode, dia=VIA_D, drill=VIA_DRILL):
    v = pcbnew.PCB_VIA(board)
    v.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y)))
    v.SetViaType(pcbnew.VIATYPE_THROUGH)
    v.SetDrill(mm(drill))
    v.SetWidth(mm(dia))
    v.SetLayerPair(F, B)
    v.SetNetCode(netcode)
    board.Add(v)
    return v


def add_track(board, x1, y1, x2, y2, layer, netcode, width=TRACK_W):
    t = pcbnew.PCB_TRACK(board)
    t.SetStart(pcbnew.VECTOR2I(mm(x1), mm(y1)))
    t.SetEnd(pcbnew.VECTOR2I(mm(x2), mm(y2)))
    t.SetLayer(layer)
    t.SetWidth(mm(width))
    t.SetNetCode(netcode)
    board.Add(t)
    return t


def add_zone(board, layer, netcode, poly, name="", priority=0,
             min_thick=0.15, clearance=0.15, thermal=True):
    z = pcbnew.ZONE(board)
    z.SetLayer(layer)
    z.SetNetCode(netcode)
    z.SetZoneName(name)
    z.SetAssignedPriority(priority) if hasattr(z, "SetAssignedPriority") else z.SetPriority(priority)
    z.SetMinThickness(mm(min_thick))
    z.SetLocalClearance(mm(clearance))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL if thermal
                       else pcbnew.ZONE_CONNECTION_FULL)
    z.SetThermalReliefGap(mm(0.25))
    z.SetThermalReliefSpokeWidth(mm(0.3))
    ext = list(poly.exterior.coords)
    z.AddPolygon(pcbnew.VECTOR_VECTOR2I([pcbnew.VECTOR2I(mm(px), mm(py))
                                         for px, py in ext[:-1]]))
    board.Add(z)
    return z


def add_rule_area(board, poly, name, layers=ALL_CU):
    z = pcbnew.ZONE(board)
    z.SetIsRuleArea(True)
    z.SetDoNotAllowCopperPour(True)
    z.SetDoNotAllowTracks(True)
    z.SetDoNotAllowVias(True)
    z.SetDoNotAllowPads(False)
    z.SetDoNotAllowFootprints(False)
    ls = pcbnew.LSET()
    for l in layers:
        ls.addLayer(l)
    z.SetLayerSet(ls)
    z.SetZoneName(name)
    ext = list(poly.exterior.coords)
    z.AddPolygon(pcbnew.VECTOR_VECTOR2I([pcbnew.VECTOR2I(mm(px), mm(py))
                                         for px, py in ext[:-1]]))
    board.Add(z)
    return z


def fill_zones(board):
    filler = pcbnew.ZONE_FILLER(board)
    filler.Fill(board.Zones())


def save(board):
    board.Save(str(PCB))
    prl = PCB.with_suffix(".kicad_prl")
    if prl.exists():
        prl.unlink()
