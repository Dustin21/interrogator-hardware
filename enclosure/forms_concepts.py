#!/usr/bin/env python3
"""Form-language concepts: Compass Puck + River Pebble (parametric, rendered).
Run: python3 enclosure/forms_concepts.py  ->  enclosure/concept_{puck,pebble}_{view}.png + STLs
"""
import numpy as np, trimesh
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from pathlib import Path
HERE = Path(__file__).resolve().parent

BASEC = np.array([0.14,0.145,0.16]); GLOW = np.array([0.10,0.55,0.48])
GLASS = np.array([0.05,0.06,0.075]); TIP = np.array([0.75,0.78,0.82])

def build_grid(top_z, half_w, ys, nx, color_fn, mirror=False):
    verts, cols = [], []
    for y in ys:
        a = max(half_w(y), 0.3)
        xs = np.linspace(-a, a, nx)
        zz = top_z(xs, np.full_like(xs, y))
        for x, z in zip(xs, zz):
            verts.append((x, y, z)); cols.append(color_fn(x, y, z))
    NY, NX = len(ys), nx
    idx = lambda r, c: r*NX + c
    faces = []
    for r in range(NY-1):
        for c in range(NX-1):
            faces.append((idx(r,c), idx(r+1,c), idx(r+1,c+1)))
            faces.append((idx(r,c), idx(r+1,c+1), idx(r,c+1)))
    V = np.array(verts); C = np.array(cols); F = np.array(faces)
    if mirror:  # mirror z for double-sided pebble
        Vm = V.copy(); Vm[:,2] *= -1
        Fm = F[:, ::-1] + len(V)
        V = np.vstack([V, Vm]); C = np.vstack([C, C*0.96]); F = np.vstack([F, Fm])
    else:       # flat base
        Vb = V.copy(); Vb[:,2] = 0.0
        Fb = F[:, ::-1] + len(V)
        V = np.vstack([V, Vb]); C = np.vstack([C, np.tile(BASEC, (len(V)//2,1))]); F = np.vstack([F, Fb])
    return V, C, F

# ---------- Compass Puck: R=29, H=16, flat crown, rounded edge, bezel glow ----------
R_P, H_P = 29.0, 16.0
def puck_z(x, y):
    rho = np.sqrt(x*x + y*y)/R_P
    z = H_P*np.power(np.clip(1-rho**4.2, 0, 1), 1/2.4)
    z -= 2.6*np.exp(-((x*x+y*y)/(9.5**2)))          # crown dish
    return np.clip(z, 0, None)
def puck_col(x, y, z):
    rho = np.sqrt(x*x+y*y)/R_P
    if 0.965 < rho and 5.5 < z < 9.5: return GLOW   # bezel ring (pointing segment story)
    if rho > 0.999 and abs(y) < 3 and z < 5: return TIP  # liquid port at south rim
    return BASEC
def puck_hw(y):
    return np.sqrt(max(R_P*R_P - y*y, 0.0)) if abs(y) < R_P else 0.0

# ---------- River Pebble: 76x52x20 egg, symmetric both faces, equator glow seam ----------
A_E, B_E, H_E = 38.0, 26.0, 10.0
def peb_hw(y):  # egg outline: narrow toward +y (the "nose")
    if abs(y) >= A_E: return 0.0
    u = y/A_E
    return B_E*np.sqrt(max(1-u*u, 0))*(1 - 0.16*u)
def peb_z(x, y):
    a = np.array([peb_hw(v) for v in np.atleast_1d(y)])
    a = np.maximum(a, 1e-6)
    t = np.clip(1 - (np.abs(x)/a)**2.35, 0, 1)
    u = np.clip(np.abs(np.atleast_1d(y))/A_E, 0, 1)
    hy = H_E*np.power(np.clip(1-u**2.6, 0, 1), 0.55)
    z = hy*np.power(t, 0.62)
    z -= 1.9*np.exp(-((x*x + (np.atleast_1d(y)-0)**2)/(8.0**2)))   # thumb dish
    return np.clip(z, 0.0, None)
def peb_col(x, y, z):
    if z < 0.55: return GLOW                        # equator light seam
    if y > A_E*0.86 and z < 4: return TIP           # liquid dimple at nose
    if -6 < y < 14 and abs(x) < 10 and z > H_E*0.55: return GLASS*1.6  # dish glass
    return BASEC

def vdir(e,a):
    e,a=np.radians(e),np.radians(a); return np.array([np.cos(e)*np.cos(a),np.cos(e)*np.sin(a),np.sin(e)])

def render(V, C, F, name, elev, azim, zoom=0.55, zfloor=None):
    tri = V[F]
    n = np.cross(tri[:,1]-tri[:,0], tri[:,2]-tri[:,0]); n /= (np.linalg.norm(n,axis=1,keepdims=True)+1e-12)
    cz = tri.mean(axis=1)[:,2]
    n[(cz>0.05)&(n[:,2]<0)] *= -1; n[(cz<=0.05)&(n[:,2]>0)] *= -1
    fc = C[F].mean(axis=1)*2.1
    vd = vdir(elev, azim)
    L1 = np.array([0.25,-0.3,0.92]); L1/=np.linalg.norm(L1)
    H2 = (L1+vd); H2/=np.linalg.norm(H2)
    fill = np.array([-0.6,0.6,0.4]); fill/=np.linalg.norm(fill)
    lam = 0.46+0.34*np.clip(n@L1,0,1)+0.14*np.clip(n@fill,0,1)
    spec = 0.30*np.clip(n@H2,0,1)**70; fres = 0.16*np.clip(1-np.abs(n@vd),0,1)**3
    cols = np.clip(fc*lam[:,None]+(spec+fres)[:,None]*np.array([0.9,0.92,0.96]),0,0.92)
    order = np.argsort(tri.mean(axis=1)@vd)
    fig = plt.figure(figsize=(7.6,5.4), dpi=150); ax = fig.add_subplot(111, projection="3d")
    ax.add_collection3d(Poly3DCollection(tri[order], facecolors=cols[order], edgecolor="none"))
    r = max(V.max(0)-V.min(0))*zoom; c=(V.max(0)+V.min(0))/2
    ax.set_xlim(c[0]-r,c[0]+r); ax.set_ylim(c[1]-r,c[1]+r)
    z0 = (V[:,2].min() if zfloor is None else zfloor)
    ax.set_zlim(z0, z0+2*r*0.58)
    ax.view_init(elev=elev, azim=azim); ax.set_axis_off()
    ax.set_proj_type('persp', focal_length=0.55); ax.set_box_aspect((1,1,0.58))
    fig.patch.set_facecolor("white"); plt.tight_layout(pad=0)
    fig.savefig(HERE/f"concept_{name}.png", bbox_inches="tight", facecolor="white"); plt.close(fig)
    print("rendered", name)

# build + render puck
ysP = np.linspace(-R_P+0.15, R_P-0.15, 200)
Vp, Cp, Fp = build_grid(puck_z, puck_hw, ysP, 160, puck_col, mirror=False)
trimesh.Trimesh(Vp, Fp, process=True).export(HERE/"concept_puck.stl")
for nm, el, az in [("puck_iso",26,-55),("puck_side",6,2),("puck_top",89,-90)]:
    render(Vp, Cp, Fp, nm, el, az)

# build + render pebble (double-sided)
ysE = np.linspace(-A_E+0.2, A_E-0.2, 220)
Ve, Ce, Fe = build_grid(lambda x,y: peb_z(x,y), peb_hw, ysE, 150, peb_col, mirror=True)
trimesh.Trimesh(Ve, Fe, process=True).export(HERE/"concept_pebble.stl")
for nm, el, az in [("pebble_iso",26,-125),("pebble_side",4,2),("pebble_top",89,-90)]:
    render(Ve, Ce, Fe, nm, el, az, zfloor=-H_E)
print("concepts done")
