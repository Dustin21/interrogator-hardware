#!/usr/bin/env python3
"""H3.3 grid router engine (deterministic A*, 0.1mm grid, 4 signal layers).

Model
-----
* Grid: 0.1 mm, KiCad frame (y down). Signal layers F.Cu, In1.Cu, In4.Cu,
  B.Cu (In2 = GND plane, In3 = power islands — vias only).
* owner[l][ix,iy] int16: -1 free, net >= 0 exclusively that net's copper
  (inflated by clearance + half track width), -2 conflict/foreign-multi.
  A cell is enterable for net N iff owner in (-1, N).
* via_owner[l]: same but inflated for the via barrel (r0.2 + clearance).
  A via fits at a cell iff every copper layer allows it AND the cell is
  outside the hole-spacing mask and inside the via-legal board region.
* Connectivity: geometric union-find over pads/tracks/vias/zone fills of
  each net (zone fill polys merge everything they touch). The router works
  cluster-pair by cluster-pair (MST, nearest first).
* Paths: 8-neighbour A*, via moves between any two signal layers, cost =
  distance + via penalty; emitted as simplified PCB_TRACK/PCB_VIA sets and
  immediately rasterized back into the grids.

Instantiate Router once per session; stages call route_net()/route_pair().
"""
import heapq
import math
from collections import defaultdict

import numpy as np
import pcbnew
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union
from shapely import contains_xy

import route_lib as RL
from route_lib import (ALL_CU, B, F, IN1, IN2, IN3, IN4, SIGNAL_LAYERS,
                       mm, tomm)

RES = 0.1
NX, NY = int(68.2 / RES), int(40.2 / RES)
FREE, MULTI = -1, -2
LIDX = {F: 0, IN1: 1, IN4: 2, B: 3}
LAYERS = [F, IN1, IN4, B]
VIA_COST = 8           # grid units (0.8mm equivalent) — cheap vias
                       # beat the long single-layer wanderers that
                       # were walling off corridors (H3.3b finding)
LAYER_COST = {0: 0.0, 1: 0.02, 2: 0.02, 3: 0.0}   # mild inner-layer bias


def ix(v):
    return int(round(v / RES))


class Grids:
    def __init__(self):
        self.owner = [np.full((NX, NY), FREE, np.int32) for _ in LAYERS]
        # fine grids: dru rules inside the via-in-pad BGA courtyards
        # (0.09 clearance + 0.09 track -> inflation 0.135) — open the
        # diagonal ball-gap escape channels invisible at default inflation
        self.owner_fine = [np.full((NX, NY), FREE, np.int32) for _ in LAYERS]
        self.via_owner = [np.full((NX, NY), FREE, np.int32) for _ in LAYERS]
        self.via_extra = np.zeros((NX, NY), bool)   # hole spacing / region bans

    def _paint(self, arr, geom, net):
        b_ = geom.bounds
        i0, i1 = max(0, int(b_[0] / RES) - 1), min(NX - 1, int(b_[2] / RES) + 2)
        j0, j1 = max(0, int(b_[1] / RES) - 1), min(NY - 1, int(b_[3] / RES) + 2)
        if i1 <= i0 or j1 <= j0:
            return
        xs = np.arange(i0, i1) * RES
        ys = np.arange(j0, j1) * RES
        XX, YY = np.meshgrid(xs, ys, indexing="ij")
        m = contains_xy(geom, XX.ravel(), YY.ravel()).reshape(XX.shape)
        sub = arr[i0:i1, j0:j1]
        upd = m & (sub != net)
        sub[upd & (sub == FREE)] = net
        sub[upd & (sub != FREE) & (sub != net)] = MULTI
        arr[i0:i1, j0:j1] = sub

    def paint_copper(self, geom, net, layers, infl_track, infl_via):
        g1 = geom.buffer(infl_track, resolution=8)
        gf = geom.buffer(0.137, resolution=8)     # fine: 0.09+0.045 (+eps)
        g2 = geom.buffer(infl_via, resolution=8)
        for l in layers:
            li = LIDX.get(l)
            if li is None:
                continue
            self._paint(self.owner[li], g1, net)
            self._paint(self.owner_fine[li], gf, net)
            self._paint(self.via_owner[li], g2, net)

    def ban_via_region(self, geom):
        b_ = geom.bounds
        i0, i1 = max(0, int(b_[0] / RES) - 1), min(NX - 1, int(b_[2] / RES) + 2)
        j0, j1 = max(0, int(b_[1] / RES) - 1), min(NY - 1, int(b_[3] / RES) + 2)
        if i1 <= i0 or j1 <= j0:
            return
        xs = np.arange(i0, i1) * RES
        ys = np.arange(j0, j1) * RES
        XX, YY = np.meshgrid(xs, ys, indexing="ij")
        m = contains_xy(geom, XX.ravel(), YY.ravel()).reshape(XX.shape)
        self.via_extra[i0:i1, j0:j1] |= m


class Router:
    def __init__(self, board, track_w=0.10, clearance=0.11):
        self.board = board
        self.track_w = track_w
        self.clearance = clearance
        self.bean = RL.board_poly(board)
        self.g = Grids()
        self.uf = {}          # union-find over item ids
        self.items = defaultdict(list)   # net -> [(id, geom, layers)]
        self.pad_of = {}      # (ref,num) -> item id (first pad geom)
        self.netname = {}
        self._harvest()

    # ---------------- union-find ------------------------------------------
    def _find(self, a):
        while self.uf[a] != a:
            self.uf[a] = self.uf[self.uf[a]]
            a = self.uf[a]
        return a

    def _union(self, a, b_):
        ra, rb = self._find(a), self._find(b_)
        if ra != rb:
            self.uf[rb] = ra

    # ---------------- harvest ----------------------------------------------
    def _add_item(self, net, geom, layers, key=None):
        iid = len(self.uf)
        self.uf[iid] = iid
        self.items[net].append((iid, geom, frozenset(layers)))
        if key:
            self.pad_of[key] = iid
        return iid

    def _harvest(self):
        brd = self.board
        infl_t = self.clearance + self.track_w / 2
        infl_v = self.clearance + 0.2 + 0.02          # via barrel r + margin
        hole_pts = []
        # pads
        for fp in brd.GetFootprints():
            ref = fp.GetReference()
            for pad in fp.Pads():
                net = pad.GetNetCode()
                sh = RL.pad_shape(pad)
                lay = RL.pad_layers(pad)
                th = pad.GetAttribute() in (pcbnew.PAD_ATTRIB_PTH,
                                            pcbnew.PAD_ATTRIB_NPTH)
                if th and pad.GetDrillSize().x > 0:
                    hole_pts.append((tomm(pad.GetPosition().x),
                                     tomm(pad.GetPosition().y),
                                     tomm(pad.GetDrillSize().x) / 2))
                if not lay:
                    continue
                paint_net = net if (net > 0 and pad.GetNumber()) else MULTI
                self.g.paint_copper(sh, paint_net, lay, infl_t, infl_v)
                if net > 0:
                    iid = self._add_item(net, sh, lay, key=(ref, pad.GetNumber()))
                    self.item_ref = getattr(self, "item_ref", {})
                    self.item_ref[iid] = ref
                    self.netname[net] = pad.GetNetname()
        # tracks + vias
        for t in brd.GetTracks():
            net = t.GetNetCode()
            if t.GetClass() == "PCB_VIA":
                x, y = tomm(t.GetPosition().x), tomm(t.GetPosition().y)
                sh = Point(x, y).buffer(tomm(t.GetWidth()) / 2)
                self.g.paint_copper(sh, net if net > 0 else MULTI,
                                    LAYERS, infl_t, infl_v)
                hole_pts.append((x, y, tomm(t.GetDrill()) / 2))
                if net > 0:
                    self._add_item(net, sh, ALL_CU)
            else:
                sh = LineString([(tomm(t.GetStart().x), tomm(t.GetStart().y)),
                                 (tomm(t.GetEnd().x), tomm(t.GetEnd().y))]
                                ).buffer(tomm(t.GetWidth()) / 2)
                self.g.paint_copper(sh, net if net > 0 else MULTI,
                                    [t.GetLayer()], infl_t, infl_v)
                if net > 0:
                    self._add_item(net, sh, [t.GetLayer()])
        # zone fills (In2/In3) — connectivity + via-owner obstacles for
        # foreign nets are NOT painted (zones refill around new copper), but
        # fills DO merge same-net items and vias must not land on foreign
        # island fills -> paint via_owner only.
        self.zone_polys = []
        for z in brd.Zones():
            if z.GetIsRuleArea():
                o = z.Outline()
                for i in range(o.OutlineCount()):
                    ol = o.Outline(i)
                    poly = Polygon([(tomm(ol.CPoint(k).x), tomm(ol.CPoint(k).y))
                                    for k in range(ol.PointCount())])
                    # no tracks/vias in rule areas: ban across all layers
                    for li in range(4):
                        self.g._paint(self.owner_layer(li), poly.buffer(
                            self.track_w / 2), MULTI)
                    self.g.ban_via_region(poly.buffer(0.25))
                continue
            net = z.GetNetCode()
            sp = z.GetFilledPolysList(z.GetLayer())
            polys = []
            for i in range(sp.OutlineCount()):
                ol = sp.Outline(i)
                polys.append(Polygon([(tomm(ol.CPoint(k).x), tomm(ol.CPoint(k).y))
                                      for k in range(ol.PointCount())]))
            fill = unary_union(polys) if polys else None
            if fill is not None and not fill.is_empty:
                self.zone_polys.append((net, z.GetLayer(), fill))
                if z.GetLayer() == IN3 and net > 0:
                    # a through-via pierces In3: foreign vias must clear the
                    # island fill (own-net vias may land in it)
                    g2 = fill.buffer(0.30, resolution=8)
                    for li in range(4):
                        self.g._paint(self.g.via_owner[li], g2, net)
        # merge same-net contacts
        for net, lst in self.items.items():
            n = len(lst)
            for a in range(n):
                ida, ga, la = lst[a]
                for b2 in range(a + 1, n):
                    idb, gb, lb = lst[b2]
                    if (la & lb) and ga.distance(gb) < 0.02:
                        self._union(ida, idb)
            # zone fills merge items they touch
            for zi, (znet, zlayer, fill) in enumerate(self.zone_polys):
                if znet != net:
                    continue
                touched = [iid for iid, gm, la in lst
                           if (zlayer in la or len(la) == 6) and fill.intersects(gm)]
                for iid in touched[1:]:
                    self._union(touched[0], iid)
                if touched:
                    self.zone_anchor = getattr(self, "zone_anchor", {})
                    self.zone_anchor[zi] = touched[0]
        # hole spacing mask (0.5mm center ban around every existing hole)
        for x, y, r in hole_pts:
            self.g.ban_via_region(Point(x, y).buffer(r + 0.42))
        # vias only well inside the bean and away from rule areas
        outside = box(-1, -1, 69, 41).difference(self.bean.buffer(-0.5))
        self.g.ban_via_region(outside)
        for li in range(4):
            self.g._paint(self.g.owner[li],
                          box(-1, -1, 69, 41).difference(self.bean.buffer(-0.35)),
                          MULTI)

    def owner_layer(self, li):
        return self.g.owner[li]

    def build_fine_mask(self, refs=("U_N657", "U_A121", "U_GAUGE")):
        """Cells inside the via-in-pad courtyards, where dru 0.09/0.09
        applies and fine-mode routing is legal."""
        self.fine_mask = np.zeros((NX, NY), bool)
        for fp in self.board.GetFootprints():
            if fp.GetReference() not in refs:
                continue
            xs = [tomm(p.GetPosition().x) for p in fp.Pads()]
            ys = [tomm(p.GetPosition().y) for p in fp.Pads()]
            i0, i1 = max(0, ix(min(xs) - 0.45)), min(NX - 1, ix(max(xs) + 0.45))
            j0, j1 = max(0, ix(min(ys) - 0.45)), min(NY - 1, ix(max(ys) + 0.45))
            self.fine_mask[i0:i1 + 1, j0:j1 + 1] = True

    # ---------------- clusters --------------------------------------------
    def clusters(self, net):
        cl = defaultdict(list)
        for iid, geom, lay in self.items[net]:
            cl[self._find(iid)].append((iid, geom, lay))
        out = list(cl.values())
        excl = getattr(self, "exclude_refs", ())
        if excl:
            iref = getattr(self, "item_ref", {})
            out = [c for c in out
                   if not all(iref.get(iid, "") in excl for iid, _g, _l in c)]
        return out

    def unconnected_count(self):
        return sum(max(0, len(self.clusters(n)) - 1) for n in self.items)

    # ---------------- A* ---------------------------------------------------
    def _seed_cells(self, cluster, net):
        """Cells inside the cluster's copper, per layer (entry points)."""
        cells = []
        for iid, geom, lay in cluster:
            ll = [LIDX[l] for l in lay if l in LIDX]
            if len(lay) == 6:
                ll = [0, 1, 2, 3]
            b_ = geom.bounds
            i0, i1 = max(0, ix(b_[0])), min(NX - 1, ix(b_[2]))
            j0, j1 = max(0, ix(b_[1])), min(NY - 1, ix(b_[3]))
            for i in range(i0, i1 + 1):
                for j in range(j0, j1 + 1):
                    if geom.contains(Point(i * RES, j * RES)) or \
                       geom.distance(Point(i * RES, j * RES)) < 0.03:
                        for li in ll:
                            ow = self.g.owner[li][i, j]
                            if ow == FREE or ow == net or ow == MULTI:
                                cells.append((li, i, j))
        return cells

    def route_cluster_pair(self, net, ca, cb, width=None, layers=None,
                           window=6.0, max_nodes=900000, via_ok=True,
                           region=None, attract=None, fine=False):
        """A* from cluster ca to cluster cb. Returns (path, reason)."""
        width = width or self.track_w
        wl = [LIDX[l] for l in (layers or LAYERS)]
        src = [c for c in self._seed_cells(ca, net) if c[0] in wl]
        dst = [c for c in self._seed_cells(cb, net) if c[0] in wl]
        if not src or not dst:
            return None, ("no-src" if not src else "no-dst")
        # cells inside the endpoint copper are always enterable for this
        # route (fine-pitch pads get swallowed by neighbour inflation —
        # physically the outward escape is legal, see H3_REPORT)
        allow = set(src) | set(dst)
        for cl in (ca, cb):
            for iid, geom, lay in cl:
                ll = [LIDX[l] for l in lay if l in LIDX] or [0, 1, 2, 3]
                b_ = geom.bounds
                for i in range(max(0, ix(b_[0])), min(NX - 1, ix(b_[2])) + 1):
                    for j in range(max(0, ix(b_[1])), min(NY - 1, ix(b_[3])) + 1):
                        if geom.distance(Point(i * RES, j * RES)) < 0.03:
                            for li in ll:
                                if li in wl:
                                    allow.add((li, i, j))
        dstset = set(dst)
        # window box
        allc = src + dst
        i0 = max(1, min(c[1] for c in allc) - int(window / RES))
        i1 = min(NX - 2, max(c[1] for c in allc) + int(window / RES))
        j0 = max(1, min(c[2] for c in allc) - int(window / RES))
        j1 = min(NY - 2, max(c[2] for c in allc) + int(window / RES))
        # width penalty: for wider tracks, also require neighbours free
        extra = int(math.ceil(max(0.0, (width - self.track_w) / 2) / RES))
        gx = np.array([c[1] for c in dst], dtype=float)
        gy = np.array([c[2] for c in dst], dtype=float)

        def h(i, j):
            dx = np.abs(gx - i)
            dy = np.abs(gy - j)
            return float((np.maximum(dx, dy) + 0.42 * np.minimum(dx, dy)).min()) * 0.98

        fine_mask = getattr(self, "fine_mask", None)

        def passable(li, i, j):
            if region is not None and not region[i, j]:
                return False
            if fine and fine_mask is not None and fine_mask[i, j]:
                o = self.g.owner_fine[li]
            else:
                o = self.g.owner[li]
            if extra == 0:
                v = o[i, j]
                return v == FREE or v == net or (li, i, j) in allow
            if (li, i, j) in allow:
                return True
            sub = o[i - extra:i + extra + 1, j - extra:j + extra + 1]
            return bool(np.all((sub == FREE) | (sub == net)))

        def via_free(i, j):
            if self.g.via_extra[i, j]:
                return False
            for li in range(4):
                v = self.g.via_owner[li][i, j]
                if v != FREE and v != net:
                    return False
            return True

        DIRS = [(1, 0, 1.0), (-1, 0, 1.0), (0, 1, 1.0), (0, -1, 1.0),
                (1, 1, 1.42), (1, -1, 1.42), (-1, 1, 1.42), (-1, -1, 1.42)]
        openq = []
        gcost = {}
        came = {}
        for s in src:
            gcost[s] = 0.0
            heapq.heappush(openq, (h(s[1], s[2]), 0.0, s))
        nodes = 0
        found = None
        while openq and nodes < max_nodes:
            _, gc, cur = heapq.heappop(openq)
            if gcost.get(cur, 1e18) < gc - 1e-9:
                continue
            if cur in dstset:
                found = cur
                break
            nodes += 1
            li, i, j = cur
            for dx, dy, w in DIRS:
                ni, nj = i + dx, j + dy
                if not (i0 <= ni <= i1 and j0 <= nj <= j1):
                    continue
                if not passable(li, ni, nj):
                    continue
                nc = gc + w + LAYER_COST[li]
                if attract is not None:
                    nc += attract(ni * RES, nj * RES)
                nxt = (li, ni, nj)
                if nc < gcost.get(nxt, 1e18) - 1e-9:
                    gcost[nxt] = nc
                    came[nxt] = cur
                    heapq.heappush(openq, (nc + h(ni, nj), nc, nxt))
            if via_ok and via_free(i, j):
                for li2 in wl:
                    if li2 == li:
                        continue
                    if not passable(li2, i, j):
                        continue
                    nc = gc + VIA_COST
                    nxt = (li2, i, j)
                    if nc < gcost.get(nxt, 1e18) - 1e-9:
                        gcost[nxt] = nc
                        came[nxt] = cur
                        heapq.heappush(openq, (nc + h(i, j), nc, nxt))
        if found is None:
            return None, ("budget" if nodes >= max_nodes else "exhausted")
        path = [found]
        while path[-1] in came:
            path.append(came[path[-1]])
        path.reverse()
        return path, "ok"

    # ---------------- emit --------------------------------------------------
    def emit(self, net, path, width=None):
        """Write tracks/vias for a path; rasterize; merge clusters."""
        width = width or self.track_w
        segs = []           # (layer, (x1,y1), (x2,y2))
        vias = []
        # simplify: group consecutive same-layer, collinear runs
        run = [path[0]]
        for a, b_ in zip(path, path[1:]):
            if a[0] != b_[0]:
                vias.append((a[1] * RES, a[2] * RES))
                self._flush_run(run, segs)
                run = [b_]
            else:
                run.append(b_)
        self._flush_run(run, segs)
        length = 0.0
        new_items = []
        infl_t = self.clearance + self.track_w / 2
        infl_v = self.clearance + 0.22
        for layer_i, (x1, y1), (x2, y2) in segs:
            if (x1, y1) == (x2, y2):
                continue
            RL.add_track(self.board, x1, y1, x2, y2, LAYERS[layer_i], net, width)
            geom = LineString([(x1, y1), (x2, y2)]).buffer(width / 2)
            self.g.paint_copper(geom, net, [LAYERS[layer_i]],
                                infl_t + (width - self.track_w) / 2, infl_v)
            new_items.append((geom, [LAYERS[layer_i]]))
            length += math.hypot(x2 - x1, y2 - y1)
        for x, y in vias:
            RL.add_via(self.board, x, y, net)
            geom = Point(x, y).buffer(0.2)
            self.g.paint_copper(geom, net, LAYERS, infl_t, infl_v)
            self.g.ban_via_region(Point(x, y).buffer(0.52))
            new_items.append((geom, ALL_CU))
        # connectivity: add items, union with everything touching
        first = None
        for geom, lay in new_items:
            iid = self._add_item(net, geom, lay)
            if first is None:
                first = iid
            else:
                self._union(first, iid)
        if first is not None:
            for iid, gm, la in self.items[net]:
                if iid == first:
                    continue
                for geom, lay in new_items:
                    if (set(lay) & set(la) or len(la) == 6) and gm.distance(geom) < 0.02:
                        self._union(first, iid)
                        break
            # zone fills: a new via landing in a same-net island/plane fill
            # joins that fill's cluster
            anchors = getattr(self, "zone_anchor", {})
            for zi, (znet, zlayer, fill) in enumerate(self.zone_polys):
                if znet != net or zi not in anchors:
                    continue
                for geom, lay in new_items:
                    if len(lay) == 6 and fill.intersects(geom):
                        self._union(first, anchors[zi])
                        break
        return length, len(vias)

    def _flush_run(self, run, segs):
        if len(run) < 1:
            return
        li = run[0][0]
        pts = [(c[1], c[2]) for c in run]
        # collinear compression
        out = [pts[0]]
        for k in range(1, len(pts) - 1):
            dx1 = pts[k][0] - out[-1][0]
            dy1 = pts[k][1] - out[-1][1]
            dx2 = pts[k + 1][0] - pts[k][0]
            dy2 = pts[k + 1][1] - pts[k][1]
            if dx1 * dy2 != dy1 * dx2:
                out.append(pts[k])
        out.append(pts[-1])
        for a, b_ in zip(out, out[1:]):
            segs.append((li, (a[0] * RES, a[1] * RES), (b_[0] * RES, b_[1] * RES)))

    # ---------------- net driver -------------------------------------------
    def route_net(self, net, width=None, layers=None, window=6.0,
                  max_grow=3, via_ok=True, region=None, attract=None,
                  fine=False, max_nodes=900000):
        """Connect all clusters of a net (nearest-pair first). Returns
        (n_connected, n_failed, total_len, n_vias)."""
        done = fail = 0
        tot_len = 0.0
        tot_via = 0
        failed_pairs = set()
        while True:
            cls = self.clusters(net)
            if len(cls) <= 1:
                break
            # nearest pair not yet failed
            roots = [self._find(c[0][0]) for c in cls]
            best = None
            for a in range(len(cls)):
                for b_ in range(a + 1, len(cls)):
                    key = frozenset((roots[a], roots[b_]))
                    if key in failed_pairs:
                        continue
                    d = min(g1.distance(g2) for _, g1, _ in cls[a]
                            for _, g2, _ in cls[b_])
                    if best is None or d < best[0]:
                        best = (d, a, b_)
            if best is None:
                fail += len(cls) - 1
                for c in cls[1:]:
                    self.failed_edges = getattr(self, "failed_edges", [])
                    self.failed_edges.append(
                        (net, f"{self.netname.get(net, '?')}:unroutable"))
                break
            _, a, b_ = best
            # trim giant clusters (GND/rails) to the items near the meeting
            # point — seeding the whole plane cluster would be quadratic
            ga = min(((g1, g2) for _, g1, _ in cls[a] for _, g2, _ in cls[b_]),
                     key=lambda p: p[0].distance(p[1]))
            cx = (ga[0].centroid.x + ga[1].centroid.x) / 2
            cy = (ga[0].centroid.y + ga[1].centroid.y) / 2

            def near(cl, rad):
                out = [it for it in cl
                       if it[1].distance(Point(cx, cy)) <= rad]
                return out or cl[:20]
            path = None
            win = window
            reasons = []
            for _try in range(max_grow):
                path, why = self.route_cluster_pair(
                    net, near(cls[a], win + 4), near(cls[b_], win + 4),
                    width=width, layers=layers,
                    window=win, via_ok=via_ok, max_nodes=max_nodes,
                    region=region, attract=attract, fine=fine)
                reasons.append(why)
                if path:
                    break
                win *= 2.2
            if not path:
                failed_pairs.add(frozenset((roots[a], roots[b_])))
                self.failed_edges = getattr(self, "failed_edges", [])
                self.failed_edges.append(
                    (net, f"{self.netname.get(net, '?')}:{'/'.join(reasons)}"))
                continue
            ln, nv = self.emit(net, path, width=width)
            tot_len += ln
            tot_via += nv
            done += 1
        return done, fail, tot_len, tot_via
