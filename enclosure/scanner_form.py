#!/usr/bin/env python3
"""Smooth parametric 'Scanner' form (ADR-0003) — Magic-Mouse-class curvature.

Generates a dense watertight-ish mesh (visual + STL) of the ergonomic hand-scanner:
teardrop footprint, rear palm arch, low sensing prow, crown touch dish, prow
window band, glow skirt, liquid tip. Renders 5 shaded views (PNG).
Run: python3 enclosure/scanner_form.py
"""
import numpy as np, trimesh
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from pathlib import Path

HERE = Path(__file__).resolve().parent

# ---------- parametric body ----------
L_R, L_F = 36.0, 46.0        # rear/front half-lengths from y0
Y0, A_MAX, H_PK = 5.0, 27.0, 24.0
PX, PZ = 2.6, 1.75           # superellipse exponents (full shoulders)

def halfwidth(y):
    y = np.asarray(y, float)
    a = np.zeros_like(y)
    r = y >= Y0
    u = np.clip((y[r]-Y0)/L_R, 0, 1);  a[r] = A_MAX*np.power(np.clip(1-u**2.2,0,1), 0.55)
    u = np.clip((Y0-y[~r])/L_F, 0, 1); a[~r] = A_MAX*np.power(np.clip(1-u**2.0,0,1), 0.62)
    return np.maximum(a, 0.0)

def spine(y):
    knots_y = np.array([-46,-40,-30,-18,-4, 10, 22, 32, 41])
    knots_h = np.array([  0,  6,  9, 13, 20, 24, 21, 13,  0])
    h = np.interp(y, knots_y, knots_h)
    k = np.hanning(31); k /= k.sum()
    yy = np.linspace(-46, 41, 600); hh = np.convolve(np.interp(yy, knots_y, knots_h), k, "same")
    return np.interp(y, yy, hh)

def top_z(x, y):
    a = halfwidth(y); h = spine(y)
    with np.errstate(divide="ignore", invalid="ignore"):
        t = np.clip(1 - np.abs(np.where(a>0, x/np.maximum(a,1e-6), 2))**PX, 0, 1)
    z = h * np.power(t, 1/PZ)
    # crown touch dish (fingertip scoop)
    z -= 3.2*np.exp(-(((x)/7.5)**2 + ((y-6)/8.5)**2))
    return np.clip(z, 0, None)

NY, NX = 260, 180
ys = np.linspace(-45.9, 40.9, NY)
verts, faces, vcol = [], [], []
BASE  = np.array([0.115,0.12,0.135])   # near-black shell
GLASS = np.array([0.05,0.06,0.075])    # prow window band
GLOW  = np.array([0.10,0.55,0.48])     # teal light ring
TIP   = np.array([0.75,0.78,0.82])     # liquid port ring

rows = []
for y in ys:
    a = max(halfwidth(np.array([y]))[0], 0.4)
    xs = np.linspace(-a, a, NX)
    z = top_z(xs, np.full_like(xs, y))
    # prow window: flatten a glass band into the front slope
    if -34 <= y <= -23:
        m = np.abs(xs) < 12.0
        z[m] = np.minimum(z[m], np.maximum(z[m]*0.92, 0.0))
    rows.append((xs, np.full_like(xs, y), z))

idx = lambda r, c: r*NX + c
for r,(xs,yy,zz) in enumerate(rows):
    for c in range(NX):
        x,y,z = xs[c], yy[c], zz[c]
        col = BASE.copy()
        if -34 <= y <= -23 and abs(x) < 12: col = GLASS.copy()
        if 1.2 < z < 2.1: col = GLOW.copy()                     # glow skirt
        if y < -39 and z < 6.5 and abs(x) < 3: col = TIP.copy() # liquid tip accent
        verts.append((x,y,z)); vcol.append(col)
for r in range(NY-1):
    for c in range(NX-1):
        faces.append((idx(r,c), idx(r+1,c), idx(r+1,c+1)))
        faces.append((idx(r,c), idx(r+1,c+1), idx(r,c+1)))
# base plate (fan)
verts.append((0, float(ys.mean()), 0.0)); vcol.append(BASE*0.8); ctr = len(verts)-1
for r in range(NY-1):
    faces.append((ctr, idx(r,0), idx(r+1,0)))
    faces.append((ctr, idx(r+1,NX-1), idx(r,NX-1)))
faces.append((ctr, idx(0,NX-1), idx(0,0)))
faces.append((ctr, idx(NY-1,0), idx(NY-1,NX-1)))

V = np.array(verts); F = np.array(faces); C = np.array(vcol)
mesh = trimesh.Trimesh(V, F, process=True)
mesh.export(HERE/"chassis_scanner_smooth.stl")
print("mesh:", len(V), "verts", len(F), "faces; extents", np.round(mesh.extents,1))

# ---------- render ----------
def render(name, elev, azim, zoom=0.56):
    tri = V[F]; fc = C[F].mean(axis=1)
    n = np.cross(tri[:,1]-tri[:,0], tri[:,2]-tri[:,0])
    n /= (np.linalg.norm(n, axis=1, keepdims=True)+1e-12)
    L1 = np.array([0.4,-0.45,0.8]); L1/=np.linalg.norm(L1)
    L2 = np.array([-0.6,0.3,0.45]); L2/=np.linalg.norm(L2)
    lam = 0.62*np.clip(n@L1,0,1) + 0.30*np.clip(n@L2,0,1)
    spec = 0.5*np.clip(n@L1,0,1)**24
    cols = np.clip(fc*(0.30+0.85*lam[:,None]) + spec[:,None]*np.array([0.9,0.92,0.95]), 0, 1)
    order = np.argsort((tri.mean(axis=1) @ view_dir(elev, azim)))
    fig = plt.figure(figsize=(7.4,5.2), dpi=160); ax = fig.add_subplot(111, projection="3d")
    ax.add_collection3d(Poly3DCollection(tri[order], facecolors=cols[order], edgecolor="none"))
    r = max(V.max(0)-V.min(0))*zoom; c = (V.max(0)+V.min(0))/2
    ax.set_xlim(c[0]-r,c[0]+r); ax.set_ylim(c[1]-r,c[1]+r); ax.set_zlim(0, 2*r*0.62)
    ax.view_init(elev=elev, azim=azim); ax.set_axis_off()
    ax.set_proj_type('persp', focal_length=0.32)
    fig.patch.set_facecolor("white"); plt.tight_layout(pad=0)
    fig.savefig(HERE/f"scanner_{name}.png", bbox_inches="tight", facecolor="white"); plt.close(fig)
    print("rendered", name)

def view_dir(elev, azim):
    e, a = np.radians(elev), np.radians(azim)
    return np.array([np.cos(e)*np.cos(a), np.cos(e)*np.sin(a), np.sin(e)])

for nm, el, az in [("iso_front",26,-128),("iso_rear",28,52),("side",6,-90),("top",89,-90),("front",10,180)]:
    render(nm, el, az)
