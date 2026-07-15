#!/usr/bin/env python3
"""v1 board definition — BOARD-FIRST minimal floorplan (ADR-0004).

H3.1R (2026-07-15): the bean-polygon containment is REMOVED. Rationale
(ADR-0004): forcing the PCB into the 67.9x39.9 Product-Stone bean was the
root cause of every placement/routing crisis (courtyard overflow, USB
back-tunnel, and the H3.3 routing stall at XSPI 9/11 + partial diff pairs) —
the curved bean has no straight routing channels and wastes its corners. The
Product Stone stays the industrial-design north star but is NO LONGER a hard
board boundary. The v1 PCB outline is now an OUTPUT of minimum-area packing:
parts pack to a tight two-face rectangle, then a rounded-rectangle outline is
wrapped around the packed courtyards + a passive/route ring. Chassis is
derived downstream from the real board and co-optimized in a later pass.

Algorithm:
  1. FFDH (first-fit decreasing-height) shelf-pack the real footprint
     courtyard rectangles per face; sweep the interior width for minimum
     shared board area (aspect <= 1.55).
  2. Board interior = max(top,bottom face bbox) + a PASSIVE/ROUTE RING that
     restores bean-class part density (~62% courtyard fill) so the ~360
     supporting passives/TPs interleave in the shelf gaps + ring and the
     router gets straight channels.
  3. MECH connectors/electrodes/antenna auto-slot into the gaps (unchanged
     placer, now against the rectangle; opposite-face through-hole halos
     still honored).  Edge-critical parts (USB-C, BL54 antenna, ESP32,
     MIA-M10Q, SGX inlet, SMA/pogo) are anchored to the derived board edges;
     build_board.py does the final flush-to-edge so RF keep-outs extend
     OFF-board.
  4. Outline = rounded rect (R=2) written to outline.json (derived, replaces
     the bean).  collide + rectangle-containment checks still gate.

Outputs: outline.json (DERIVED), components.json, floorplan_top/bottom.svg,
envelope.json, ../../docs/power-budget.md. Run: python3 boards/v1/design_v1.py
"""
import json
import math
from pathlib import Path

from shapely.geometry import Polygon, box

HERE = Path(__file__).resolve().parent
DOCS = HERE.parents[1] / "docs"

BOARD_T = 1.6
GAP = 0.5          # major courtyard-to-courtyard gap (true courtyard extents)
MECH_GAP = 0.4     # mech envelopes already include IPC courtyard margin
RING = 2.6         # passive/route ring restoring bean-class density + edge lane
CORNER_R = 2.0     # rounded-rect corner radius

# ---------------------------------------------------------------------------
# Zone table retained ONLY as a face + grouping label (the x/y bean positions
# are no longer used for placement — FFDH derives positions).  side + zone
# name flow into components.json and the SVG coloring; aperture-cluster
# coherence (optical/optical2/fir2/air on TOP) is preserved because those
# parts share the top face and FFDH keeps a face's parts contiguous.
ZONE_FACE = {
    "contact": "top", "ppg": "top", "optical": "top", "optical2": "top",
    "fir2": "top", "rad_top": "top", "air": "top", "air_scd": "top",
    "air_bmv": "top", "magnet": "top", "radar": "top",
    "gas_b": "bot", "io": "bot", "gnss": "bot", "haptic_t": "top",
    "sense_b": "bot", "radio_ble": "bot", "compute": "bot", "power": "bot",
    "power2": "bot", "radio_wifi": "bot",
}

# name, w, h, z(height), zone, provenance, note   (w,h = real fp courtyard extent)
PARTS = [
    # ---------- TOP (sensing face) ----------
    ("MAX30102 PPG",            6.2, 3.9, 1.55,"ppg",     "DS", "contact window, fat lobe"),
    ("AS7058 PPG/ECG/BioZ",     3.2, 3.5,0.7, "contact", "RS WLCSP42", "ECG return on back ring"),
    ("MLX90642 thermal 32x24",  9.9, 9.9, 5.1, "optical", "DS TO-39 O5.84 pin circle (E1)", "TO-39+lens; tallest top part"),
    ("VD66GY camera (DNP)",    18.4, 8.2, 3.5, "optical", "FH12-24 fp extent (H3.2)", "slot = J_CAM 24p FPC connector (18.2x8 courtyard) + module window above; DNP"),
    ("TXU0304 SPI shifter +",   7.8, 5.6, 1.2, "optical", "EST TSSOP-14 (pinout E0)", "H3.0: VL53L8CH 3.3<->1.8V SPI branch"),
    ("VL53L8CH ToF 8x8 raw",    7.0, 3.6, 1.75,"optical", "DS DS14310 (E1)", "SPI via TXU0304; IOVDD/CORE on 1V8_OPTICAL; APERTURE cluster"),
    ("TCS3448 14ch VIS",        3.7, 2.6, 1.0, "optical2","DS DS001121 (E1)", "1.8V-only; behind PCA9306 segment; APERTURE cluster"),
    ("AS7331 UV A/B/C",         4.3, 3.2, 1.0, "optical2","DS OLGA16", "UV-clear/quartz aperture; APERTURE cluster"),
    ("AS7421 64ch NIR +",       7.2, 6.6, 2.3, "optical2","DS DS000667 p45 (E1)", "OLGA10 6.6x6.0; 4 integrated NIR LEDs; APERTURE cluster"),
    ("PCA9306 I2C xlate +",     4.5, 2.7, 1.1, "optical2","EST VSSOP-8 (pinout E0)", "H3.0: TCS3448 1.8V I2C-A segment"),
    ("MLX90632 spot FIR +",     3.6, 3.6, 1.0, "fir2",    "DS SFN5 (E1)", "medical-grade spot temp; APERTURE cluster"),
    ("PIN radiation det +",    11.4, 11.4, 2.0, "rad_top", "RS large-area PIN", "light-tight shield can (11.4 = shield-can courtyard extent)"),
    ("SCD41 true CO2 +",       10.8, 10.8, 6.5, "air_scd",     "RS", "photoacoustic NDIR; top mid anchor"),
    ("BME688 gas/T/RH/P",       3.6, 3.6, 0.93,"air",     "DS", "air pocket, thermal moat"),
    ("SGP41 VOC/NOx",           3.0, 3.0,0.85,"air",     "DS", "air pocket"),
    ("ENS161 4-el MOX +",       3.6, 3.6, 0.9, "air",     "RS LGA9", "scent granularity"),
    ("SHT41 ref T/RH +",        2.5, 2.1, 0.5, "air",     "RS DFN4", "reference anchor for MOX comp"),
    ("BMV080 PM2.5",            6.6, 4.0, 3.0, "air_bmv",     "DS ZIF13", "Molex 503566 ZIF host conn; intake window (edge-access, soft)"),
    ("MMC5983MA nT mag +",      3.6, 3.6, 1.0, "magnet",  "RS LGA16", ">15mm from power currents"),
    ("TMAG5273 mT hall",        4.2, 3.5, 1.1, "magnet",  "DS SOT23-6", "dock-magnet detect"),
    ("A121 60GHz radar",        6.1, 5.8, 0.88,"radar",   "DS fcCSP50", "AiP at liquid tip (edge-access); radome above"),
    # ---------- BOTTOM (compute face) ----------
    ("SGX-4CO electrochem +",  17.0, 17.0,18.0, "gas_b",   "DS DS-0138 p1 (E1)", "13.5 PCD socket ring + O20 can; gas inlet EDGE; can overhang; enclosure pocket FLAG (H3_REPORT)"),
    ("IQS7222A touch",          4.4, 4.4, 0.6, "io",      "DS QFN20 (E1)", "9 self-cap electrodes (H3.0 ratified)"),
    ("DRV2605L haptic",         6.5, 3.6, 0.9, "haptic_t","RS VSSOP", "LRA driver"),
    ("MIA-M10Q GNSS RAWX",      5.1, 5.1, 1.0, "gnss",    "DS M-LGA53 (E1)", "SR4G013 antenna keepout — RF EDGE (IM UBX-21028173)"),
    ("BNO086 IMU raw+fused",    4.6, 6.1, 1.1, "sense_b", "DS LGA28", "vibration-aware mount"),
    ("MEMS mic +",              4.1, 3.3,1.0, "sense_b", "RS", "heart/lung + acoustic; bottom port"),
    ("BL54L15 BLE sentinel",   10.6, 14.6, 2.0, "radio_ble","DS EZ-DS v1.9 (E1)", "antenna END (5.0x8.5 keepout) at board EDGE; keepout extends OFF-board >=15mm; flush at H3.2R"),
    ("STM32N657 VFBGA142",      8.6, 8.6, 1.2, "compute", "DS VFBGA142 (E1)", "app MCU + NPU + I3C/SPI/CSI; away from IR/thermopile + gauge NTC (thermal)"),
    ("48MHz HSE crystal +",     4.3, 3.5, 0.8, "compute", "DS DS14791 p13; 3225", "PH0/PH1 (A7/B7 balls); USB-HS/CSI PLL ref"),
    ("Octal NOR flash",         6.6, 8.6, 1.2, "compute", "EST BGA24", "N6 flashless"),
    ("CYPD3177 USB-C PD",       5.4, 5.4, 0.6, "power",   "RS QFN24", "near USB-C edge"),
    ("ADS131M04 24b 4ch",       4.4, 4.4, 0.8, "power",   "RS WQFN", "piezo + radiation-PIN charge amp"),
    ("BQ27427 gauge",           3.7, 3.7, 0.6, "power",   "RS DSBGA", "NTC sense — away from N657/MLX heat (thermal)"),
    ("TLV62568 1V8 buck",       3.5, 4.2, 0.6, "power",   "RS SOT23-5", ""),
    ("BQ29700+FET protect",     5.6, 3.0, 0.6, "power",   "RS SON6", ""),
    ("BQ25620 charger 3.5A",    3.1, 3.6, 0.6, "power",   "DS WQFN-18 RYK 2.5x3.0 (E1)", "~1C fast charge"),
    ("TPS62840 sentinel buck",  2.8, 2.8, 0.6, "power",   "RS SOT583", "60nA IQ rail"),
    ("TPS62823 core buck",      2.8, 2.8, 0.6, "power",   "RS SOT583", ""),
    ("Load switches x10",      15.0, 1.5, 0.5, "power2",  "DS WCSP-4 (E1)", "6 domains + accessory + 3x gated 1V8 sub-rails (H3.0)"),
    ("ESP32-C6-MINI WiFi",     13.8, 17.2, 2.4, "radio_wifi","RS", "SDIO; gated; module keepout at board EDGE, antenna off-board"),
]

# ---------------------------------------------------------------------------
# MECH: connectors / electrodes / debug / antenna get packed slots too.
# name, w, h, allowed sides (pref order), edge tag (None|'S'|'N'|'W'|'E'|'SW'..)
MECH = [
    ("USB-C receptacle",      10.7, 9.0, ("bot", "top"), "S"),   # short-edge (hard)
    ("RF survey U.FL +",       4.5, 5.2, ("top", "bot"), "E"),   # edge SMA/U.FL
    ("GNSS chip antenna",     16.8, 4.0, ("top",),       "N"),   # antenna at edge
    ("Pogo landing field +",   7.6, 5.1, ("bot",),       "E"),   # dock edge
    ("Touch flex ZIF +",       6.6, 4.0, ("bot", "top"), "W"),   # touch flex edge
    ("Piezo disc pads",        5.3, 2.8, ("top", "bot"), None),
    ("SWD N6 tag-connect",     8.4, 2.2, ("bot", "top"), None),
    ("SWD BL54 tag-connect",   8.4, 2.2, ("bot", "top"), None),
    ("Battery connector",      6.6, 5.8, ("bot", "top"), "S"),   # cell lead edge
    ("ECG land L +",           4.6, 4.6, ("top",),       "W"),
    ("ECG land R +",           4.6, 4.6, ("top",),       "W"),
    ("ECG land REF +",         4.6, 4.6, ("bot", "top"), None),
    ("LRA pads",               3.1, 6.6, ("bot", "top"), None),
    ("Fan connector",          3.1, 4.6, ("bot", "top"), "E"),
]
MECH_NAMES = {m[0] for m in MECH}
# TH/NPTH features that pierce the board — those SPOTS must be clear on the
# other face too (halo radius). Offsets from courtyard center (pcbnew-measured).
MECH_THRU = {
    "USB-C receptacle": [(2.89, 2.31, 0.6), (4.32, 2.81, 0.65), (4.32, 1.36, 0.65)],
}


def gap_of(name):
    return MECH_GAP if name in MECH_NAMES else GAP


# ---------------------------------------------------------------------------
def ffdh(items, width, gapfn):
    """First-fit decreasing-height shelf pack. items=(name,w,h). Returns
    {name:(x,y,w,h)}, packed_w, packed_h.  Lower-left origin."""
    order = sorted(items, key=lambda t: -t[2])
    x = 0.0
    y = 0.0
    row_h = 0.0
    maxx = 0.0
    pos = {}
    for name, w, h in order:
        g = gapfn(name)
        if x + w > width and x > 0:
            x = 0.0
            y += row_h
            row_h = 0.0
        pos[name] = (x, y, w, h)
        x += w + g
        row_h = max(row_h, h + g)
        maxx = max(maxx, x - g)
    return pos, maxx, y + row_h - (gapfn(order[-1][0]) if order else 0)


def pack_parts():
    """FFDH-pack PARTS + MECH per face; sweep interior width for min shared
    area. Per-face FFDH => zero same-face courtyard overlap by construction.
    Edge-critical parts get an EDGE tag flowed to build_board for flush-to-
    edge (RF keep-outs off-board); design just sizes the minimal rectangle."""
    facelist = {"top": [], "bot": []}
    meta = {}
    for name, w, h, z, zone, prov, note in PARTS:
        facelist[ZONE_FACE[zone]].append((name, w, h))
        meta[name] = (z, zone, prov, note, None)
    for name, w, h, sides, tag in MECH:
        facelist[sides[0]].append((name, w, h))
        meta[name] = (0.5, "mech", "fp-extent envelope", f"mech edge={tag}", tag)

    best = None
    for iw10 in range(440, 1200, 5):
        IW = iw10 / 10.0
        pt, Wt, Lt = ffdh(facelist["top"], IW, gap_of)
        pb, Wb, Lb = ffdh(facelist["bot"], IW, gap_of)
        W, L = max(Wt, Wb), max(Lt, Lb)
        asp = max(W, L) / min(W, L)
        if asp > 1.55:
            continue
        area = W * L
        if best is None or area < best[0]:
            best = (area, IW, pt, pb, W, L)
    _, IW, pt, pb, coreW, coreL = best

    boardW = coreW + 2 * RING
    boardL = coreL + 2 * RING
    placed = {}
    edges = {}
    for face, pos in (("top", pt), ("bot", pb)):
        for name, (x, y, w, h) in pos.items():
            z, zone, prov, note, tag = meta[name]
            placed[name] = (face, x + RING, y + RING, w, h, z, zone, prov, note)
            if tag:
                edges[name] = tag
    return placed, boardW, boardL, edges


# ---------------------------------------------------------------------------
def make_outline(W, L, r=CORNER_R, per_corner=17):
    """Rounded-rectangle polygon, CCW, lower-left origin. >=64 points."""
    pts = []
    # corners: (cx, cy, start_angle) going CCW from bottom-right arc
    corners = [
        (W - r, r, -math.pi / 2),      # bottom-right
        (W - r, L - r, 0.0),           # top-right
        (r, L - r, math.pi / 2),       # top-left
        (r, r, math.pi),               # bottom-left
    ]
    for cx, cy, a0 in corners:
        for k in range(per_corner):
            a = a0 + (math.pi / 2) * k / (per_corner - 1)
            pts.append((round(cx + r * math.cos(a), 3),
                        round(cy + r * math.sin(a), 3)))
    # dedupe consecutive
    out = []
    for p in pts:
        if not out or (abs(p[0] - out[-1][0]) > 1e-4 or abs(p[1] - out[-1][1]) > 1e-4):
            out.append(list(p))
    return out


def shoelace(pts):
    a = 0.0
    for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]):
        a += x1 * y2 - x2 * y1
    return abs(a) / 2


# ---------------------------------------------------------------------------
def place_mech(placed, W, L, board):
    """Auto-slot the MECH parts around the packed majors (deterministic).
    Edge-tagged parts are anchored to the derived board edges."""
    import numpy as np
    from shapely.geometry import Point
    RES = 0.1
    nx, ny = int((W + 2) / RES), int((L + 2) / RES)
    occ = {"top": np.zeros((nx, ny), bool), "bot": np.zeros((nx, ny), bool)}
    edge = {g: board.buffer(-(0.15 + g)) for g in (GAP, MECH_GAP)}
    inside = {g: np.zeros((nx, ny), bool) for g in edge}
    for g, poly in edge.items():
        for i in range(nx):
            for j in range(ny):
                inside[g][i, j] = poly.contains(Point(i * RES, j * RES))
    EPS = 1e-6

    def mark(side, x, y, w, h, g):
        i0 = max(0, int((x - g) / RES + EPS))
        i1 = min(nx, int((x + w + g) / RES + EPS) + 1)
        j0 = max(0, int((y - g) / RES + EPS))
        j1 = min(ny, int((y + h + g) / RES + EPS) + 1)
        occ[side][i0:i1, j0:j1] = True

    for n, (side, x, y, w, h, *_r) in placed.items():
        if n == "SGX-4CO electrochem +":
            cx, cy = x + w / 2, y + h / 2
            mark(side, cx - 10.45, cy - 10.45, 20.9, 20.9, MECH_GAP)
        else:
            mark(side, x, y, w, h, MECH_GAP)
            if n in ("STM32N657 VFBGA142", "A121 60GHz radar"):
                mark("top" if side == "bot" else "bot", x, y, w, h, MECH_GAP)

    # edge anchors from the derived board rectangle
    def anchor(tag):
        cx, cy = W / 2, L / 2
        return {
            "S": (cx, 1.5), "N": (cx, L - 1.5), "W": (1.5, cy), "E": (W - 1.5, cy),
            None: (cx, cy),
        }[tag]

    offsets = sorted(((dx * RES, dy * RES)
                      for dx in range(-int(W / RES), int(W / RES) + 1)
                      for dy in range(-int(L / RES), int(L / RES) + 1)),
                     key=lambda o: o[0] * o[0] + o[1] * o[1])

    def thru_spots(name, cx, cy, rotated):
        for dx, dy, halo in MECH_THRU.get(name, ()):
            if rotated:
                dx, dy = dy, dx
            for sx in (-1, 1):
                for sy in (-1, 1):
                    yield cx + sx * dx, cy + sy * dy, halo

    def free(side, cx, cy, w, h, name=None, rotated=False):
        i0, i1 = int((cx - w / 2) / RES + EPS), int((cx + w / 2) / RES + EPS) + 1
        j0, j1 = int((cy - h / 2) / RES + EPS), int((cy + h / 2) / RES + EPS) + 1
        if i0 < 0 or j0 < 0 or i1 > nx or j1 > ny:
            return False
        if not inside[MECH_GAP][i0:i1, j0:j1].all():
            return False
        if occ[side][i0:i1, j0:j1].any():
            return False
        other = "top" if side == "bot" else "bot"
        for px, py, halo in thru_spots(name, cx, cy, rotated):
            a0, a1 = int((px - halo) / RES + EPS), int((px + halo) / RES + EPS) + 1
            b0, b1 = int((py - halo) / RES + EPS), int((py + halo) / RES + EPS) + 1
            if occ[other][a0:a1, b0:b1].any():
                return False
        return True

    out = {}
    for name, w, h, sides, tag in sorted(
            MECH, key=lambda m: (len(m[3]), -m[1] * m[2])):
        ax, ay = anchor(tag)
        got = None
        for side in sides:
            for dx, dy in offsets:
                cx, cy = ax + dx, ay + dy
                for Wp, Hp in ((w, h), (h, w)):
                    if free(side, cx, cy, Wp, Hp, name=name,
                            rotated=(Wp, Hp) != (w, h)):
                        got = (side, cx - Wp / 2, cy - Hp / 2, Wp, Hp)
                        break
                if got:
                    break
            if got:
                break
        if got is None:
            raise SystemExit(f"MECH NO-SLOT: {name} — grow RING/board (§5.8)")
        side, x, y, Wp, Hp = got
        mark(side, x, y, Wp, Hp, MECH_GAP)
        other = "top" if side == "bot" else "bot"
        for px, py, halo in thru_spots(name, x + Wp / 2, y + Hp / 2,
                                       (Wp, Hp) != (w, h)):
            mark(other, px - halo, py - halo, 2 * halo, 2 * halo, 0.0)
        rot = 90 if (Wp, Hp) != (w, h) else 0
        out[name] = (side, x, y, Wp, Hp, 0.5, "mech",
                     "fp-extent envelope (H3.2)",
                     f"auto-slotted mech edge={tag}, rot={rot}")
    return out


def collide_check(placed):
    from itertools import combinations
    for side in ("top", "bot"):
        ps = [(n,) + v for n, v in placed.items() if v[0] == side]
        for a, b in combinations(ps, 2):
            an, ax, ay, aw, ah = a[0], a[2], a[3], a[4], a[5]
            bn, bx, by, bw, bh = b[0], b[2], b[3], b[4], b[5]
            g = min(gap_of(an), gap_of(bn))
            eps = 0.02
            if not (ax + aw + g <= bx + eps or bx + bw + g <= ax + eps
                    or ay + ah + g <= by + eps or by + bh + g <= ay + eps):
                raise SystemExit(f"COLLISION {an} vs {bn}")


def containment_check(placed, board):
    for n, (side, x, y, w, h, *_rest) in placed.items():
        g = gap_of(n)
        r = box(x - g, y - g, x + w + g, y + h + g)
        if not board.contains(r):
            raise SystemExit(f"OUTSIDE BOARD: {n} at ({x:.1f},{y:.1f}) {w}x{h}")


ZCOL = {"optical":"#dbe7f6","optical2":"#dbe7f6","air":"#e3f3ef","contact":"#fbeee6",
        "radar":"#f3e8fb","magnet":"#f2f2ea","rad_top":"#f7f2e2",
        "compute":"#dbe7f6","radio_ble":"#f3e8fb","radio_wifi":"#efe3fb","sense_b":"#f2f2ea",
        "gas_b":"#e3f3ef","power":"#fdecec","power2":"#fdecec","io":"#e7eefb",
        "gnss":"#e7eefb","haptic_t":"#e7eefb","ppg":"#fbeee6","air_scd":"#e3f3ef",
        "air_bmv":"#e3f3ef","fir2":"#dbe7f6","mech":"#efeadf"}


def svg(side, placed, fname, W, L, outline_pts):
    S = 11
    Wpx, Hpx = W * S + 170, L * S + 120
    op = " ".join(f"{x*S:.1f},{(L-y)*S:.1f}" for x, y in outline_pts)
    e = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{Wpx:.0f}" height="{Hpx:.0f}" font-family="Helvetica,Arial" font-size="10">',
         f'<rect width="{Wpx:.0f}" height="{Hpx:.0f}" fill="white"/><g transform="translate(60,44)">',
         f'<polygon points="{op}" fill="#134E4A" opacity="0.06" stroke="#134E4A" stroke-width="2"/>']
    for n, v in placed.items():
        s2, x, y, w, h, z, zn, prov, note = v
        if s2 != side:
            continue
        fill = ZCOL.get(zn, "#1E3A8A")
        e.append(f'<rect x="{x*S}" y="{(L-y-h)*S}" width="{w*S}" height="{h*S}" fill="{fill}" opacity="0.9" stroke="#334" stroke-width="0.5" rx="2"/>')
        lbl = n.replace(" +", "").split(" (")[0]
        e.append(f'<text x="{(x+w/2)*S}" y="{(L-y-h/2)*S+2}" text-anchor="middle" fill="#1E293B" font-size="7">{lbl}</text>')
    e.append(f'<line x1="0" y1="{L*S+20}" x2="{W*S}" y2="{L*S+20}" stroke="#333"/>')
    e.append(f'<text x="{W*S/2}" y="{L*S+35}" text-anchor="middle" font-size="11">{W:.1f} mm</text>')
    e.append(f'<line x1="{W*S+20}" y1="0" x2="{W*S+20}" y2="{L*S}" stroke="#333"/>')
    e.append(f'<text x="{W*S+28}" y="{L*S/2}" font-size="11">{L:.1f} mm</text>')
    title = "TOP · sensing face" if side == "top" else "BOTTOM · compute face"
    e.append(f'<text x="0" y="-20" font-size="14" font-weight="bold">interrogator v1 · MINIMAL board (ADR-0004) · {title} · 6L {BOARD_T}mm</text>')
    e.append('</g></svg>')
    (HERE / fname).write_text("\n".join(e))


# ---- two-mode power (mA); adds are gated/duty-cycled ----
AMBIENT={"BL54L15 sentinel":0.6,"STM32N657 avg (batch+stop)":12.0,"BME688 ULP":0.09,"SGP41 duty":0.3,
 "ENS161 duty":0.2,"BMV080 1-min duty":2.6,"MLX90642 1fps":1.5,"MLX90632 spot":0.05,"SHT41 duty":0.01,
 "BNO086 low-rate":1.5,"MMC+TMAG":0.3,"mic (VAD)":0.3,"A121 hibernate":0.011,"GNSS duty":0.4,
 "PIN+ADC leak":0.3,"SCD41 gated OFF":0.0,"SGX-CO bias":0.1,"misc/regs":1.35}
INTERROGATE={"STM32N657 full+NPU":150.0,"WiFi C6 stream":120.0,"VL53L8CH 15Hz":45.0,"A121 duty":20.0,
 "MLX90642 8fps":25.0,"spectral+UV+NIR+PPGx2+LEDs":34.0,"SCD41 active":18.0,"GNSS cont":9.0,
 "blower 50%":19.0,"env sensors":9.0,"sentinel+haptic+glow":8.0}
CELL_MAH,CELL=1200,"LP503450-class 1200 mAh (50x34x5.2mm) 1S LiPo + protection"


def power_md():
    a = sum(AMBIENT.values()); i = sum(INTERROGATE.values())
    L = ["# Two-mode power budget (v1.1 — model; measured at H4)", "",
         f"Cell: **{CELL}**; USB-C PD ~1C fast charge (BQ25620).", "",
         "## Ambient (R3: target 8h, floor 5h)", "",
         "| load | mA |", "|---|---|"] + [f"| {k} | {v:.2f} |" for k, v in AMBIENT.items()]
    L += [f"| **total** | **{a:.1f}** |", "", f"**Ambient runtime ≈ {CELL_MAH/a:.0f} h** — clears 8h target ~{CELL_MAH/a/8:.0f}×.", "",
          "## Interrogation (deep dive)", "", "| load | mA |", "|---|---|"] + [f"| {k} | {v:.1f} |" for k, v in INTERROGATE.items()]
    L += [f"| **total** | **{i:.0f}** |", "", f"**Continuous interrogation ≈ {CELL_MAH/i:.1f} h** (bursty → mixed 8–20h).", "",
          "Adds (MLX90632/AS7421/mic/ENS161/SCD41/SGX-CO/SHT41) are gated/duty-cycled; SCD41 + electrochem bias",
          "hard-gated in ambient. PIN radiation replaces BG51 on the ADS131M04 analog domain.", "",
          "H3.0 adders (3x TPS22916 1V8 sub-rail switches ~2 uA IQ each, PCA9306 ~0, TXU0304 ~1 uA):",
          "<7 uA total — below the model's resolution, absorbed in `misc/regs` (no line-item change)."]
    (DOCS / "power-budget.md").write_text("\n".join(L)); return a, i


def main():
    placed, W, L, edges = pack_parts()
    outline_pts = make_outline(W, L)
    board = Polygon(outline_pts)
    collide_check(placed)
    containment_check(placed, board)
    # edge-flush hints for build_board (RF keep-outs off-board): written into
    # each edge part's note so the placer knows which rim to push it to.
    for name, tag in edges.items():
        v = list(placed[name])
        v[8] = v[8] + f" | EDGE:{tag}"
        placed[name] = tuple(v)

    area = shoelace(outline_pts)
    o = {"source": "DERIVED (ADR-0004): min-area FFDH pack of real footprint "
                   "courtyards + passive/route ring, wrapped in a rounded rect. "
                   "Bean containment removed — Product Stone is no longer a hard "
                   "board boundary.",
         "shape": "rounded-rectangle", "corner_r_mm": CORNER_R,
         "length_mm": round(W, 3), "width_mm": round(L, 3),
         "area_mm2": round(area, 1), "n_points": len(outline_pts),
         "points_mm": outline_pts}
    (HERE / "outline.json").write_text(json.dumps(o, indent=1))

    svg("top", placed, "floorplan_top.svg", W, L, outline_pts)
    svg("bot", placed, "floorplan_bottom.svg", W, L, outline_pts)
    comps = [{"name": n, "side": v[0], "x_mm": round(v[1], 2), "y_mm": round(v[2], 2),
              "w_mm": v[3], "h_mm": v[4], "z_mm": v[5], "zone": v[6],
              "provenance": v[7], "note": v[8], "new": ("+" in n)}
             for n, v in placed.items()]
    (HERE / "components.json").write_text(json.dumps(comps, indent=1))

    th = max(v[5] for v in placed.values() if v[0] == "top")
    bh = max(v[5] for v in placed.values() if v[0] == "bot")
    env = {"board_shape": "DERIVED rounded-rectangle (ADR-0004: min-area pack, "
                          "bean containment removed)",
           "board_bbox_w_mm": round(W, 2), "board_bbox_h_mm": round(L, 2),
           "board_t_mm": BOARD_T, "board_area_mm2": round(area, 1),
           "prev_bean_area_mm2": 2064.9,
           "area_vs_bean": f"{area/2064.9:.0%} of the 2065mm2 bean (but fully "
                           f"rectangular — zero wasted corners, straight route channels)",
           "max_comp_top_mm": th, "max_comp_bot_mm": bh,
           "stack_mm": round(BOARD_T + th + bh, 1),
           "note_battery": "cell is a MATING part (LP503450-class 50x34x5.2mm) via "
                           "J_BATT — excluded from board area; stacks behind the "
                           "compute face in the enclosure.",
           "layers": 6, "process": "JLCPCB 6L through-via + POFV",
           "sensor_count": len(PARTS)}
    (HERE / "envelope.json").write_text(json.dumps(env, indent=1))
    a, i = power_md()
    ntop = sum(1 for v in placed.values() if v[0] == "top")
    print(f"OK MINIMAL board {W:.1f} x {L:.1f} = {area:.0f}mm2 "
          f"({area/2064.9:.0%} of bean, RECTANGULAR); "
          f"{len(placed)} placed (top {ntop} / bot {len(placed)-ntop}); "
          f"stack {BOARD_T+th+bh:.1f}mm; ambient {a:.1f}mA→{CELL_MAH/a:.0f}h; "
          f"interrogate {i:.0f}mA→{CELL_MAH/i:.1f}h")


if __name__ == "__main__":
    main()
