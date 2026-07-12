#!/usr/bin/env python3
"""Bean board outline for the Product Stone enclosure (ADR-0003 rev C).

The stone plan is defined by enclosure/product_stone.py: half-widths
w_smooth(x) (+y edge) and w_notch(x) (-y edge) along the 75 mm long axis.
The PCB must clear wall 1.6 mm + assembly clearance 1.9 mm => the board
outline is the stone plan inset by 3.5 mm (shapely negative buffer, round
joins, so tip curvature is handled properly — not a naive y-shrink).

Output: boards/v1/outline.json —
  { points_mm: [[x,y]...] closed CCW polygon (first!=last), area_mm2,
    length_mm, width_mm, inset_mm, source }
Board frame: translated so bbox min = (0,0); fat lobe at x=0 end, taper at
x=length. Run: python3 boards/v1/outline.py
"""
import json
from pathlib import Path

import numpy as np
from shapely.geometry import Polygon

HERE = Path(__file__).resolve().parent

# --- stone plan (must match enclosure/product_stone.py) ---------------------
A = 37.5                      # half-length (75 mm long axis)
INSET = 3.5                   # wall 1.6 + clearance 1.9


def w_smooth(x):
    u = np.clip(x / A, -1, 1)
    return 24.0 * np.power(np.clip(1 - u * u, 0, 1), 0.55) * (1 - 0.10 * u)


def w_notch(x):
    w = w_smooth(x)
    return w * (1 - 0.16 * np.exp(-((x + 9.0) / 10.5) ** 2))


def stone_plan(n=240):
    xs = np.linspace(-A + 0.05, A - 0.05, n)
    top = [(float(x), float(w_smooth(x))) for x in xs]
    bot = [(float(x), float(-w_notch(x))) for x in xs[::-1]]
    return Polygon(top + bot)


def bean_outline(n_out=96):
    plan = stone_plan()
    inner = plan.buffer(-INSET, join_style=1, quad_segs=16)
    inner = inner.simplify(0.02)
    xy = np.asarray(inner.exterior.coords)[:-1]          # drop closing dup
    # resample to n_out points by arc length for a clean even polygon
    seg = np.linalg.norm(np.diff(np.vstack([xy, xy[:1]]), axis=0), axis=1)
    s = np.concatenate([[0], np.cumsum(seg)])
    total = s[-1]
    tgt = np.linspace(0, total, n_out, endpoint=False)
    pts = []
    closed = np.vstack([xy, xy[:1]])
    j = 0
    for t in tgt:
        while s[j + 1] < t:
            j += 1
        f = (t - s[j]) / max(s[j + 1] - s[j], 1e-9)
        pts.append(closed[j] * (1 - f) + closed[j + 1] * f)
    pts = np.array(pts)
    # translate: bbox min -> (0,0); fat lobe (stone -x) lands at board x=0
    pts -= pts.min(axis=0)
    poly = Polygon(pts)
    if not poly.exterior.is_ccw:
        pts = pts[::-1]
        poly = Polygon(pts)
    return pts, poly


def main():
    pts, poly = bean_outline()
    w, h = pts[:, 0].max(), pts[:, 1].max()
    out = {
        "source": "enclosure/product_stone.py plan inset by 3.5mm "
                  "(wall 1.6 + clearance 1.9), shapely round-join buffer",
        "inset_mm": INSET,
        "length_mm": round(float(w), 2),
        "width_mm": round(float(h), 2),
        "area_mm2": round(float(poly.area), 1),
        "n_points": len(pts),
        "points_mm": [[round(float(x), 3), round(float(y), 3)] for x, y in pts],
    }
    (HERE / "outline.json").write_text(json.dumps(out, indent=1))
    print(f"bean outline: {w:.1f} x {h:.1f} mm, area {poly.area:.0f} mm^2, "
          f"{len(pts)} pts (old rect 60x46 = 2760 mm^2)")


if __name__ == "__main__":
    main()
