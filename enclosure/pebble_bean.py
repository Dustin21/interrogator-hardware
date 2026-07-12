#!/usr/bin/env python3
"""Pebble-Bean — the chosen form (ADR-0003 rev B): ergonomic bean/palm stone.

Bean plan-form (curved spine, concave inner edge for thumb/finger wrap), domed
top with thumb scoop, flatter underside with a stable desk landing patch (dock
ring/pogo/air live there). Flip it over = other-hand version (ambidextrous via
the flip). ~72 x 50 x 20 mm. Renders 4 views + STL.
Run: python3 enclosure/pebble_bean.py
"""
import numpy as np, trimesh
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from pathlib import Path
HERE = Path(__file__).resolve().parent

A = 36.0            # half-length (x)
BEND = 9.0          # bean curvature of the spine
H_TOP, H_BOT = 13.5, 6.5
BASEC = np.array([0.14,0.145,0.16]); GLOW = np.array([0.10,0.55,0.48])
GLASS = np.array([0.06,0.07,0.09]);  TIP = np.array([0.75,0.78,0.82])

def width(x):                      # half-width profile (egg: fat end -x, taper +x)
    u = np.clip(x/A, -1, 1)
    return 25.0*np.sqrt(np.clip(1-u*u, 0, 1))*(1 - 0.12*u)

def spine_y(x):                    # bean bend (concave side = +y inner edge)
    return BEND*(1 - (x/A)**2) - BEND*0.55

def z_top(x, t):                   # t in [-1,1] across width; superellipse dome
    w = width(x)
    dome = H_TOP*np.power(np.clip(1-np.abs(t)**2.3, 0, 1), 0.62)
    taper = np.power(np.clip(1-(np.abs(x)/A)**2.6, 0, 1), 0.5)
    z = dome*taper
    # thumb scoop: midline, biased toward the inner (concave, +t) edge
    z -= 2.6*np.exp(-(((x-2)/10.0)**2 + ((t-0.35)/0.42)**2))
    return np.clip(z, 0, None)

def z_bot(x, t):                   # flatter dome, clipped to a landing flat
    w = width(x)
    dome = H_BOT*np.power(np.clip(1-np.abs(t)**2.1, 0, 1), 0.66)
    taper = np.power(np.clip(1-(np.abs(x)/A)**2.4, 0, 1), 0.55)
    return -np.minimum(dome*taper, 5.2)   # flat patch at -5.2 (desk landing)

NXG, NTG = 240, 130
xs = np.linspace(-A+0.2, A-0.2, NXG)
def build_face(zfun, flip):
    verts, cols = [], []
    for x in xs:
        w = max(width(x), 0.3); yc = spine_y(x)
        ts = np.linspace(-1, 1, NTG)
        zz = zfun(np.full_like(ts, x), ts)
        for t, z in zip(ts, zz):
            y = yc + t*w
            col = BASEC.copy()
            if abs(z) < 0.5: col = GLOW                       # parting-line glow seam
            if not flip and z > 0.5 and ((x-2)/11.0)**2 + ((t-0.35)/0.5)**2 < 1.0: col = GLASS  # scoop glass (elliptical)
            if x > A-4 and abs(z) < 4 and abs(t) < 0.3: col = TIP  # liquid tip (taper end)
            verts.append((x, y, z)); cols.append(col)
    return np.array(verts), np.array(cols)

Vt, Ct = build_face(z_top, False)
Vb, Cb = build_face(z_bot, True)
def faces(n_rows, n_cols, off=0, rev=False):
    f = []
    for r in range(n_rows-1):
        for c in range(n_cols-1):
            a,b2,c2,d = r*n_cols+c, (r+1)*n_cols+c, (r+1)*n_cols+c+1, r*n_cols+c+1
            t1, t2 = (a,b2,c2), (a,c2,d)
            if rev: t1, t2 = t1[::-1], t2[::-1]
            f += [tuple(i+off for i in t1), tuple(i+off for i in t2)]
    return f
F = np.array(faces(NXG, NTG) + faces(NXG, NTG, off=len(Vt), rev=True))
V = np.vstack([Vt, Vb]); C = np.vstack([Ct, Cb])
trimesh.Trimesh(V, F, process=True).export(HERE/"pebble_bean.stl")
print("bean:", np.round(trimesh.Trimesh(V,F).extents,1), "mm")

def vdir(e,a):
    e,a=np.radians(e),np.radians(a); return np.array([np.cos(e)*np.cos(a),np.cos(e)*np.sin(a),np.sin(e)])
def render(name, elev, azim, zoom=0.55):
    tri = V[F]
    n = np.cross(tri[:,1]-tri[:,0], tri[:,2]-tri[:,0]); n/=(np.linalg.norm(n,axis=1,keepdims=True)+1e-12)
    czm = tri.mean(axis=1)[:,2]
    n[(czm>0)&(n[:,2]<0)] *= -1; n[(czm<=0)&(n[:,2]>0)] *= -1
    fc = C[F].mean(axis=1)*2.1
    vd = vdir(elev,azim)
    L1 = np.array([0.25,-0.3,0.92]); L1/=np.linalg.norm(L1)
    H2=(L1+vd); H2/=np.linalg.norm(H2)
    fill=np.array([-0.6,0.6,0.4]); fill/=np.linalg.norm(fill)
    lam = 0.46+0.34*np.clip(n@L1,0,1)+0.14*np.clip(n@fill,0,1)
    spec = 0.30*np.clip(n@H2,0,1)**70; fres = 0.16*np.clip(1-np.abs(n@vd),0,1)**3
    cols = np.clip(fc*lam[:,None]+(spec+fres)[:,None]*np.array([0.9,0.92,0.96]),0,0.92)
    order = np.argsort(tri.mean(axis=1)@vd)
    fig = plt.figure(figsize=(7.8,5.6), dpi=150); ax = fig.add_subplot(111, projection="3d")
    ax.add_collection3d(Poly3DCollection(tri[order], facecolors=cols[order], edgecolor="none"))
    r = max(V.max(0)-V.min(0))*zoom; c=(V.max(0)+V.min(0))/2
    ax.set_xlim(c[0]-r,c[0]+r); ax.set_ylim(c[1]-r,c[1]+r); ax.set_zlim(-r*0.55, r*0.61)
    ax.view_init(elev=elev, azim=azim); ax.set_axis_off()
    ax.set_proj_type('persp', focal_length=0.55); ax.set_box_aspect((1,1,0.58))
    fig.patch.set_facecolor("white"); plt.tight_layout(pad=0)
    fig.savefig(HERE/f"bean_{name}.png", bbox_inches="tight", facecolor="white"); plt.close(fig)
    print("rendered", name)

for nm, el, az in [("iso",30,-58),("thumb",42,-95),("side",4,-92),("top",89,-90)]:
    render(nm, el, az)
