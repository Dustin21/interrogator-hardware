#!/usr/bin/env python3
"""Product Stone — ADR-0003 rev C: exact match to the owner's product-design image.

Definitive geometry from the 10-view turnaround: smooth standing stone, subtle
bean waist on one long edge (offset toward the fat end), thin lens profile,
flowing engraved S-curve strata on both faces (the interface marking — no scoop,
no visible ports; touch/PPG live under the engraved field). ~75 x 48 x 19 mm.
Run: python3 enclosure/product_stone.py  -> product_stone.stl + stone_*.png
"""
import numpy as np, trimesh
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from pathlib import Path
HERE = Path(__file__).resolve().parent

A = 37.5                      # half-length (75 mm long axis, x)
H_F, H_B = 10.0, 9.0          # front/back face depths (19 mm lens)
BASEC = np.array([0.155,0.155,0.16])
LINEC = BASEC*0.72            # engraved strata (darker etch)

def w_smooth(x):              # convex edge half-width (egg: fat -x, taper +x)
    u = np.clip(x/A, -1, 1)
    return 24.0*np.power(np.clip(1-u*u,0,1), 0.55)*(1-0.10*u)

def w_notch(x):               # waisted edge: concavity offset toward fat end
    w = w_smooth(x)
    return w*(1 - 0.16*np.exp(-((x+9.0)/10.5)**2))

def face_z(x, t, h):          # lens dome per face; t in [-1(waist),1(smooth)]
    taper = np.power(np.clip(1-(np.abs(x)/A)**2.5, 0, 1), 0.52)
    return h*np.power(np.clip(1-np.abs(t)**2.15, 0, 1), 0.60)*taper

def strata(x, t):             # engraved flowing S-curves (3 nested)
    for k, (a0, ph, amp) in enumerate([(-0.28,0.6,0.42),(0.02,0.2,0.5),(0.32,-0.3,0.44)]):
        tl = a0 + amp*np.sin(np.pi*0.9*(x/A) + ph)
        if abs(t - tl) < 0.022: return True
    return False

NXG, NTG = 260, 140
xs = np.linspace(-A+0.15, A-0.15, NXG)
def build(h, sign):
    verts, cols = [], []
    for x in xs:
        wU, wL = w_smooth(x), w_notch(x)
        ts = np.linspace(-1, 1, NTG)
        for t in ts:
            w = wU if t >= 0 else wL
            y = t*max(w, 0.3)
            z = sign*face_z(x, t, h)
            # flatten the back face center for the desk landing (back = sign<0)
            if sign < 0: z = max(z, -h*0.82) if abs(t) < 0.55 and abs(x) < 22 else z
            col = LINEC if (strata(x, t) and abs(z) > 0.8) else BASEC
            verts.append((x, y, z)); cols.append(col)
    return np.array(verts), np.array(cols)

Vf, Cf = build(H_F, +1)
Vb, Cb = build(H_B, -1)
def faces(nr, nc, off=0, rev=False):
    f=[]
    for r in range(nr-1):
        for c in range(nc-1):
            a,b2,c2,d = r*nc+c,(r+1)*nc+c,(r+1)*nc+c+1,r*nc+c+1
            t1,t2 = (a,b2,c2),(a,c2,d)
            if rev: t1,t2 = t1[::-1],t2[::-1]
            f += [tuple(i+off for i in t1), tuple(i+off for i in t2)]
    return f
F = np.array(faces(NXG,NTG) + faces(NXG,NTG,off=len(Vf),rev=True))
V = np.vstack([Vf,Vb]); C = np.vstack([Cf,Cb])
trimesh.Trimesh(V,F,process=True).export(HERE/"product_stone.stl")
print("stone:", np.round(trimesh.Trimesh(V,F).extents,1), "mm")

def vdir(e,a):
    e,a=np.radians(e),np.radians(a); return np.array([np.cos(e)*np.cos(a),np.cos(e)*np.sin(a),np.sin(e)])
def render(name, elev, azim, zoom=0.56):
    tri = V[F]
    n = np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]); n/=(np.linalg.norm(n,axis=1,keepdims=True)+1e-12)
    czm = tri.mean(axis=1)[:,2]
    n[(czm>0)&(n[:,2]<0)]*=-1; n[(czm<=0)&(n[:,2]>0)]*=-1
    fc = C[F].mean(axis=1)*2.3
    vd = vdir(elev,azim)
    L1 = np.array([0.45,-0.25,0.86]); L1/=np.linalg.norm(L1)
    H2 = (L1+vd); H2/=np.linalg.norm(H2)
    lam = 0.42+0.40*np.clip(n@L1,0,1)+0.14*np.clip(n@np.array([-0.7,0.5,0.2]),0,1)
    spec = 0.28*np.clip(n@H2,0,1)**50
    fres = 0.18*np.clip(1-np.abs(n@vd),0,1)**2.5
    cols = np.clip(fc*lam[:,None]+(spec+fres)[:,None]*np.array([0.85,0.86,0.88]),0,0.88)
    order = np.argsort(tri.mean(axis=1)@vd)
    BG = "#17181b"
    fig = plt.figure(figsize=(7.6,5.6), dpi=150); ax = fig.add_subplot(111, projection="3d")
    ax.add_collection3d(Poly3DCollection(tri[order], facecolors=cols[order], edgecolor="none"))
    r = max(V.max(0)-V.min(0))*zoom; c=(V.max(0)+V.min(0))/2
    ax.set_xlim(c[0]-r,c[0]+r); ax.set_ylim(c[1]-r,c[1]+r); ax.set_zlim(-r*0.6,r*0.6)
    ax.view_init(elev=elev, azim=azim); ax.set_axis_off()
    ax.set_proj_type('persp', focal_length=0.6); ax.set_box_aspect((1,1,0.62))
    fig.patch.set_facecolor(BG); ax.set_facecolor(BG); plt.tight_layout(pad=0)
    fig.savefig(HERE/f"stone_{name}.png", bbox_inches="tight", facecolor=BG); plt.close(fig)
    print("rendered", name)

# views matching the turnaround: front face, top(plan), edge profile, iso 45
for nm, el, az in [("front",0,-90),("top",89,-90),("edge",0,2),("iso45",28,-135)]:
    render(nm, el, az)
