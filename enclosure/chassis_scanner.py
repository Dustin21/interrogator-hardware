#!/usr/bin/env python3
"""Chassis v1 "Scanner" — Magic-Mouse-inspired ergonomic hand-scanner (ADR-0003).

A low, palm-cupping arched form: bilaterally symmetric (ambidextrous), a thin
forward SENSING PROW you point + sweep, a comfortable rear hump for the palm,
touch/PPG on the crown, liquid-sample port at the prow tip, and the magnetic
dock + pogo accessory ring on the underside. No buttons. Sweep = scanning
aperture (motion super-resolution). Pockets, sticks (magnetic), hangs, sits.

Loft sections are sampled by angle from each profile's centroid so wire
correspondence is clean (no loft twist). Feature cuts are guarded.
Outputs: chassis_scanner.step + .stl. Run: python3 enclosure/chassis_scanner.py
"""
from pathlib import Path
import numpy as np
import cadquery as cq
from cadquery import exporters

HERE = Path(__file__).resolve().parent
H_PEAK = 24.0
WALL = 1.6

# teardrop control polygon (CCW): wide rounded rear (+Y palm) -> narrow prow (-Y)
FOOT = [(0,-41),(17,-31),(25,-9),(27,15),(20,34),(0,41),(-20,34),(-27,15),(-25,-9),(-17,-31)]

def sample_poly(poly, n=96):
    """n points on the convex polygon, ordered by angle from its centroid."""
    P = np.array(poly, float); c = P.mean(0)
    out = []
    for a in np.linspace(0, 2*np.pi, n, endpoint=False):
        d = np.array([np.cos(a), np.sin(a)]); best = None
        for i in range(len(P)):
            p1 = P[i]-c; e = P[(i+1) % len(P)]-P[i]
            M = np.array([[d[0], -e[0]], [d[1], -e[1]]])
            if abs(np.linalg.det(M)) < 1e-9: continue
            t, s = np.linalg.solve(M, p1)
            if t > 0 and -1e-6 <= s <= 1+1e-6 and (best is None or t < best): best = t
        out.append((c[0]+best*d[0], c[1]+best*d[1]))
    return out

def ellipse_pts(rx, ry, cx, cy, n=96):
    return [(cx+rx*np.cos(a), cy+ry*np.sin(a)) for a in np.linspace(0, 2*np.pi, n, endpoint=False)]

def build():
    sec0 = sample_poly(FOOT)
    sec1 = sample_poly([(x*0.74, y*0.74+7) for (x, y) in FOOT])
    sec2 = ellipse_pts(12, 8, 0, 12)          # rear-biased crown
    body = (cq.Workplane("XY").polyline(sec0).close()
            .workplane(offset=13.0).polyline(sec1).close()
            .workplane(offset=H_PEAK-13.0).polyline(sec2).close()
            .loft(ruled=False))

    def try_cut(name, fn):
        nonlocal body
        try:
            body = fn(body); print(f"  + {name}")
        except Exception as ex:
            print(f"  ! skipped {name}: {type(ex).__name__}")

    # SENSING PROW window (flat lens recessed into the front slope near the tip)
    try_cut("prow window", lambda b: b.cut(
        cq.Workplane("XZ", origin=(0, -29.0, 8.0)).rect(22, 6).extrude(-2.0)))
    # CROWN touch/PPG dish (shallow spherical scoop where fingertips rest)
    try_cut("crown dish", lambda b: b.cut(
        cq.Workplane("XY", origin=(0, 3.0, H_PEAK+8.0)).sphere(9.0)))
    # GLOW light-pipe groove around the base skirt
    def glow(b):
        outer = cq.Workplane("XY").workplane(offset=2.2).polyline(sample_poly(FOOT)).close().extrude(0.9)
        inner = cq.Workplane("XY").workplane(offset=2.0).polyline(
            sample_poly([(x*0.93, y*0.93) for (x, y) in FOOT])).close().extrude(1.4)
        return b.cut(outer.cut(inner))
    try_cut("glow groove", glow)
    # UNDERSIDE dock/ferrous-target ring + 6 pogo accessory pads
    try_cut("dock ring", lambda b: b.cut(
        cq.Workplane("XY", origin=(0, 8.0, 0)).circle(11.0).extrude(0.6)))
    try_cut("pogo pads", lambda b: b.faces("<Z").workplane(centerOption="CenterOfMass")
            .center(0, 8.0).polarArray(7.0, 0, 360, 6).circle(0.9).cutBlind(-0.6))
    # air intake grid + mic port on the underside
    try_cut("air intake", lambda b: b.faces("<Z").workplane(centerOption="CenterOfMass")
            .center(14, -13).rarray(2.3, 2.3, 3, 3).circle(0.45).cutBlind(1.2))
    try_cut("mic port", lambda b: b.faces("<Z").workplane(centerOption="CenterOfMass")
            .center(-14, -13).circle(0.5).cutBlind(1.2))
    # LIQUID sample port at the prow tip
    try_cut("liquid port", lambda b: b.cut(
        cq.Workplane("XZ", origin=(0, -40.0, 5.0)).circle(1.1).extrude(4.0)))
    # USB-C on the rear skirt
    try_cut("usb-c", lambda b: b.cut(
        cq.Workplane("XZ", origin=(0, 40.0, 4.0)).slot2D(9.2, 3.4, 0).extrude(4.0)))
    return body

def main():
    b = build()
    exporters.export(b, str(HERE/"chassis_scanner.step"))
    exporters.export(b, str(HERE/"chassis_scanner.stl"), tolerance=0.08, angularTolerance=0.15)
    bb = b.val().BoundingBox()
    print(f"scanner chassis OK: {bb.xlen:.0f} x {bb.ylen:.0f} x {bb.zlen:.0f} mm; STEP+STL exported")

if __name__ == "__main__":
    main()
