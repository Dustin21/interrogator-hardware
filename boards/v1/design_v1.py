#!/usr/bin/env python3
"""v1 board definition — bean-shaped board (Product Stone interior), zone-packer.

Stage-2 (H2): the board is no longer a 60x46 rectangle. The outline is the
Product Stone plan (enclosure/product_stone.py) inset 3.5 mm (1.6 wall +
1.9 clearance) — see boards/v1/outline.py -> outline.json. Zones are mapped
onto the bean: optical + contact toward the fat lobe face, air pocket mid
(SCD41 top mid), taper end = radar tip + edge sensors (magnet), compute +
power bottom mid/fat, SGX-CO cell bottom fat lobe, ESP32-C6 bottom taper
(antenna toward the tip edge). The radiation PIN block moved to the TOP face
mid-fat (gamma does not care which face; light-tight can either way) because
the bottom fat lobe is consumed by the 14x14 SGX cell.

Packer: shelf-pack per zone + global collision check + NEW polygon-containment
check — every part rect, grown by the 0.8 mm margin, must sit fully inside the
bean outline; any violation raises (the respin promise still holds: edit PARTS,
rerun, get a fresh legal floorplan or a loud failure).

Outputs: components.json, floorplan_top.svg, floorplan_bottom.svg,
envelope.json, ../../docs/power-budget.md. Run: python3 boards/v1/design_v1.py
"""
import json
from pathlib import Path

from shapely.geometry import Polygon, box

HERE = Path(__file__).resolve().parent
DOCS = HERE.parents[1] / "docs"

BOARD_T = 1.6
GAP = 0.8                                      # min courtyard gap (mm)


def load_outline():
    f = HERE / "outline.json"
    if not f.exists():
        import outline as outline_mod
        outline_mod.main()
    o = json.loads(f.read_text())
    return o, Polygon(o["points_mm"])


OUTLINE, BEAN = load_outline()
BOARD_W, BOARD_H = OUTLINE["length_mm"], OUTLINE["width_mm"]  # bbox of the bean

# Zones: name -> (side, x0, y0, w, h)  [bottom-left origin, mm, board frame:
# fat lobe at x=0, taper tip at x~68; +y = smooth edge, -y notched edge]
ZONES = {
    # TOP = sensing face
    "contact":   ("top", 3.5, 19.0,  8.0,  7.0),   # fat-lobe face: PPG window + ECG AFE
    "optical":   ("top", 11.0, 15.0, 28.0, 10.6),  # fat/mid face: FIR array, cam, ToF
    "optical2":  ("top", 11.0, 27.0, 17.0,  4.3),  # spectral row above the big optics
    "rad_top":   ("top", 26.0,  4.0, 12.0, 11.0),  # PIN radiation block (moved top)
    "air":       ("top", 40.0, 10.0, 16.0, 20.0),  # mid air pocket, SCD41 anchor
    "magnet":    ("top", 53.0,  8.0,  9.0,  5.5),  # taper edge, quiet currents
    "radar":     ("top", 58.5, 16.2,  6.5,  6.0),  # taper tip: A121 AiP + radome
    # BOTTOM = compute face
    "gas_b":     ("bot",  6.5, 10.5, 16.0, 15.5),  # SGX-CO cell, fat lobe, vent
    "io":        ("bot",  7.0,  4.5, 14.0,  6.0),  # touch/haptic/GNSS fat-notch edge
    "sense_b":   ("bot", 12.0, 27.5, 10.0,  6.5),  # IMU + mic (quiet, near CG)
    "radio_ble": ("bot", 24.0, 27.3, 15.5, 10.5),  # BL54L15 rotated 90deg, ant at edge
    "compute":   ("bot", 24.5, 17.0, 20.0,  9.3),  # N657 + NOR, mid
    "power":     ("bot", 24.0,  4.5, 20.5, 10.0),  # notch-edge power row
    "radio_wifi":("bot", 46.7, 10.8, 14.0, 17.4),  # C6 at taper, antenna to tip
}

# name, w, h, z(height), zone, provenance, note
PARTS = [
    # ---------- TOP (sensing face) ----------
    ("MAX30102 PPG",            5.6, 3.3, 1.55,"contact", "DS", "contact window, fat lobe"),
    ("AS7058 PPG/ECG/BioZ",     2.82,2.55,0.7, "contact", "RS WLCSP42", "ECG return on back ring"),
    ("MLX90642 thermal 32x24",  9.6, 9.6, 5.1, "optical", "RS", "TO-39+lens; tallest top part"),
    ("VD66GY camera (DNP)",     8.0, 8.0, 3.5, "optical", "EST", "global shutter, N6 CSI; DNP"),
    ("VL53L8CH ToF 8x8 raw",    6.4, 3.0, 1.75,"optical", "DS vl53l8cx", "SPI strap in copper"),
    ("TCS3448 14ch VIS",        3.1, 2.0, 1.0, "optical2","RS", "AS7343-family; diffuser"),
    ("AS7331 UV A/B/C",         3.65,2.6, 1.0, "optical2","DS OLGA16", "UV-clear/quartz aperture"),
    ("AS7421 64ch NIR +",       3.5, 3.5, 1.8, "optical2","RS OLGA10", "hydration 970nm; +LED"),
    ("MLX90632 spot FIR +",     3.0, 3.0, 1.0, "optical2","RS QFN", "medical-grade spot temp"),
    ("PIN radiation det +",    10.0,10.0, 2.0, "rad_top", "RS large-area PIN", "moved TOP (SGX owns bottom fat lobe); light-tight can"),
    ("SCD41 true CO2 +",       10.1,10.1, 6.5, "air",     "RS", "photoacoustic NDIR; top mid anchor"),
    ("BME688 gas/T/RH/P",       3.0, 3.0, 0.93,"air",     "DS", "air pocket, thermal moat"),
    ("SGP41 VOC/NOx",           2.44,2.44,0.85,"air",     "DS", "air pocket"),
    ("ENS161 4-el MOX +",       3.0, 3.0, 0.9, "air",     "RS LGA9", "scent granularity"),
    ("SHT41 ref T/RH +",        1.5, 1.5, 0.5, "air",     "RS DFN4", "reference anchor for MOX comp"),
    ("BMV080 PM2.5",            6.0, 3.5, 3.0, "air",     "DS ZIF13", "Molex 503566 ZIF host conn; element on flex at window"),
    ("MMC5983MA nT mag +",      3.0, 3.0, 1.0, "magnet",  "RS LGA16", ">15mm from power currents"),
    ("TMAG5273 mT hall",        2.9, 2.8, 1.1, "magnet",  "DS SOT23-6", "dock-magnet detect"),
    ("A121 60GHz radar",        5.5, 5.2, 0.88,"radar",   "DS fcCSP50", "AiP at liquid tip; radome above"),
    # ---------- BOTTOM (compute face) ----------
    ("SGX-4CO electrochem +",  14.0,14.0, 4.0, "gas_b",   "RS 4-series", "CO safety/breath; fat-lobe vent; ~2-5yr life FLAG"),
    ("IQS7222A touch",          3.0, 3.0, 0.6, "io",      "RS QFN20", "12ch shell electrodes"),
    ("DRV2605L haptic",         3.0, 3.0, 0.9, "io",      "RS VSSOP", "LRA driver"),
    ("MIA-M10Q GNSS RAWX",      4.5, 4.5, 1.0, "io",      "RS", "antenna keepout at fat notch edge"),
    ("BNO086 IMU raw+fused",    3.8, 5.2, 1.1, "sense_b", "DS LGA28", "vibration-aware mount"),
    ("MEMS mic +",              3.5, 2.65,1.0, "sense_b", "RS", "heart/lung + acoustic; bottom port"),
    ("BL54L15 BLE sentinel",   14.0,10.0, 2.0, "radio_ble","RS Ezurio", "ROTATED 90; antenna long-edge at smooth rim"),
    ("STM32N657 VFBGA142",      8.0, 8.0, 1.2, "compute", "RS", "app MCU + NPU + I3C/SPI/CSI"),
    ("Octal NOR flash",         8.0, 6.0, 1.2, "compute", "EST BGA24", "N6 flashless"),
    ("CYPD3177 USB-C PD",       4.0, 4.0, 0.6, "power",   "RS QFN24", ""),
    ("BQ29700+FET protect",     4.0, 3.0, 0.6, "power",   "RS SON6", ""),
    ("BQ25620 charger 3.5A",    2.5, 3.0, 0.6, "power",   "RS WQFN", "~1C fast charge"),
    ("BQ27427 gauge",           1.6, 1.6, 0.6, "power",   "RS DSBGA", ""),
    ("ADS131M04 24b 4ch",       3.0, 3.0, 0.8, "power",   "RS WQFN", "piezo + radiation-PIN charge amp; moved to power row"),
    ("TPS62840 sentinel buck",  1.6, 2.1, 0.6, "power",   "RS SOT583", "60nA IQ rail"),
    ("TPS62823 core buck",      1.6, 2.1, 0.6, "power",   "RS SOT583", ""),
    ("TLV62568 1V8 buck",       1.6, 2.9, 0.6, "power",   "RS SOT23-5", ""),
    ("Load switches x7",        9.5, 2.0, 0.5, "power",   "RS WCSP", "6 domains + accessory port (H2 ratified)"),
    ("ESP32-C6-MINI WiFi",     13.2,16.6, 2.4, "radio_wifi","RS", "SDIO; gated; antenna toward tip"),
]

def pack():
    """Shelf-pack each zone; return name->(side,x,y,w,h,z,zone,prov,note). Raise on overflow."""
    placed = {}
    for zname, (side, zx, zy, zw, zh) in ZONES.items():
        items = [p for p in PARTS if p[4] == zname]
        cx, cy, row_h = zx + GAP, zy + zh, 0.0  # pack top-down within zone
        for name, w, h, z, _zone, prov, note in items:
            if cx + w > zx + zw:                  # wrap row
                cx = zx + GAP
                cy -= row_h + GAP
                row_h = 0.0
            x, y = cx, cy - h
            if x + w > zx + zw + 0.01 or y < zy - 0.01:
                raise SystemExit(f"OVERFLOW zone '{zname}': {name} — grow zone or move part (§5.8)")
            placed[name] = (side, x, y, w, h, z, zname, prov, note)
            cx += w + GAP
            row_h = max(row_h, h)
    return placed

def collide_check(placed):
    from itertools import combinations
    for side in ("top", "bot"):
        ps = [(n,)+v for n, v in placed.items() if v[0] == side]
        for a, b in combinations(ps, 2):
            _, _, ax, ay, aw, ah = a[0], a[1], a[2], a[3], a[4], a[5]
            _, _, bx, by, bw, bh = b[0], b[1], b[2], b[3], b[4], b[5]
            eps = 0.02  # tolerance for exact-gap float boundaries
            if not (ax+aw+GAP <= bx+eps or bx+bw+GAP <= ax+eps or ay+ah+GAP <= by+eps or by+bh+GAP <= ay+eps):
                raise SystemExit(f"COLLISION {a[0]} vs {b[0]}")

def containment_check(placed):
    """Every part rect grown by the GAP margin must sit inside the bean."""
    for n, (side, x, y, w, h, *_rest) in placed.items():
        r = box(x - GAP, y - GAP, x + w + GAP, y + h + GAP)
        if not BEAN.contains(r):
            raise SystemExit(f"OUTSIDE BEAN: {n} at ({x:.1f},{y:.1f}) {w}x{h} "
                             f"(+{GAP} margin) — move its zone inboard")

ZCOL = {"optical":"#dbe7f6","optical2":"#dbe7f6","air":"#e3f3ef","contact":"#fbeee6",
        "radar":"#f3e8fb","magnet":"#f2f2ea","rad_top":"#f7f2e2",
        "compute":"#dbe7f6","radio_ble":"#f3e8fb","radio_wifi":"#efe3fb","sense_b":"#f2f2ea",
        "gas_b":"#e3f3ef","power":"#fdecec","io":"#e7eefb"}

def svg(side, placed, fname):
    S = 11
    W, Hh = BOARD_W*S+170, BOARD_H*S+120
    bean_pts = " ".join(f"{x*S:.1f},{(BOARD_H-y)*S:.1f}" for x, y in OUTLINE["points_mm"])
    e=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.0f}" height="{Hh:.0f}" font-family="Helvetica,Arial" font-size="10">',
       f'<rect width="{W:.0f}" height="{Hh:.0f}" fill="white"/><g transform="translate(60,44)">',
       f'<polygon points="{bean_pts}" fill="#134E4A" opacity="0.07" stroke="#134E4A" stroke-width="2"/>']
    for zn,(zs,zx,zy,zw,zh) in ZONES.items():
        if zs!=side: continue
        e.append(f'<rect x="{zx*S}" y="{(BOARD_H-zy-zh)*S}" width="{zw*S}" height="{zh*S}" fill="{ZCOL[zn]}" opacity="0.6" rx="5"/>')
        e.append(f'<text x="{(zx+0.4)*S}" y="{(BOARD_H-zy-zh)*S+12}" fill="#889" font-size="9">{zn.upper()}</text>')
    for n,v in placed.items():
        s2,x,y,w,h,z,zn,prov,note = v
        if s2!=side: continue
        newp = "+" in n
        fill = "#0F766E" if newp else "#1E3A8A"
        e.append(f'<rect x="{x*S}" y="{(BOARD_H-y-h)*S}" width="{w*S}" height="{h*S}" fill="{fill}" opacity="0.85" rx="2"/>')
        lbl=n.replace(" +","").split(" (")[0]
        e.append(f'<text x="{(x+w/2)*S}" y="{(BOARD_H-y-h)*S-2}" text-anchor="middle" fill="#1E293B" font-size="8">{lbl}</text>')
    e.append(f'<line x1="0" y1="{BOARD_H*S+20}" x2="{BOARD_W*S}" y2="{BOARD_H*S+20}" stroke="#333"/>')
    e.append(f'<text x="{BOARD_W*S/2}" y="{BOARD_H*S+35}" text-anchor="middle" font-size="11">{BOARD_W:.1f} mm (bean bbox)</text>')
    e.append(f'<line x1="{BOARD_W*S+20}" y1="0" x2="{BOARD_W*S+20}" y2="{BOARD_H*S}" stroke="#333"/>')
    e.append(f'<text x="{BOARD_W*S+28}" y="{BOARD_H*S/2}" font-size="11">{BOARD_H:.1f} mm</text>')
    title = "TOP · sensing face" if side=="top" else "BOTTOM · compute face"
    e.append(f'<text x="0" y="-20" font-size="14" font-weight="bold">interrogator v1 · bean board · {title} · 6-layer {BOARD_T}mm · green=new</text>')
    e.append('</g></svg>')
    (HERE/fname).write_text("\n".join(e))

# ---- two-mode power (mA); adds are gated/duty-cycled ----
AMBIENT={"BL54L15 sentinel":0.6,"STM32N657 avg (batch+stop)":12.0,"BME688 ULP":0.09,"SGP41 duty":0.3,
 "ENS161 duty":0.2,"BMV080 1-min duty":2.6,"MLX90642 1fps":1.5,"MLX90632 spot":0.05,"SHT41 duty":0.01,
 "BNO086 low-rate":1.5,"MMC+TMAG":0.3,"mic (VAD)":0.3,"A121 hibernate":0.011,"GNSS duty":0.4,
 "PIN+ADC leak":0.3,"SCD41 gated OFF":0.0,"SGX-CO bias":0.1,"misc/regs":1.35}  # incl. 3V3_SYS buck IQ
INTERROGATE={"STM32N657 full+NPU":150.0,"WiFi C6 stream":120.0,"VL53L8CH 15Hz":45.0,"A121 duty":20.0,
 "MLX90642 8fps":25.0,"spectral+UV+NIR+PPGx2+LEDs":34.0,"SCD41 active":18.0,"GNSS cont":9.0,
 "blower 50%":19.0,"env sensors":9.0,"sentinel+haptic+glow":8.0}
CELL_MAH,CELL=1200,"LP503450-class 1200 mAh (50x34x5.2mm) 1S LiPo + protection"

def power_md():
    a=sum(AMBIENT.values()); i=sum(INTERROGATE.values())
    L=["# Two-mode power budget (v1.1 — model; measured at H4)","",
       f"Cell: **{CELL}**; USB-C PD ~1C fast charge (BQ25620).","","## Ambient (R3: target 8h, floor 5h)","",
       "| load | mA |","|---|---|"]+[f"| {k} | {v:.2f} |" for k,v in AMBIENT.items()]
    L+=[f"| **total** | **{a:.1f}** |","",f"**Ambient runtime ≈ {CELL_MAH/a:.0f} h** — clears 8h target ~{CELL_MAH/a/8:.0f}×.","",
        "## Interrogation (deep dive)","","| load | mA |","|---|---|"]+[f"| {k} | {v:.1f} |" for k,v in INTERROGATE.items()]
    L+=[f"| **total** | **{i:.0f}** |","",f"**Continuous interrogation ≈ {CELL_MAH/i:.1f} h** (bursty in practice → mixed 8–20h).","",
        "Adds (MLX90632/AS7421/mic/ENS161/SCD41/SGX-CO/SHT41) are gated/duty-cycled; SCD41 + electrochem bias",
        "hard-gated in ambient. PIN radiation replaces BG51 on the ADS131M04 analog domain."]
    (DOCS/"power-budget.md").write_text("\n".join(L)); return a,i

def main():
    placed=pack(); collide_check(placed); containment_check(placed)
    svg("top",placed,"floorplan_top.svg"); svg("bot",placed,"floorplan_bottom.svg")
    comps=[{"name":n,"side":v[0],"x_mm":round(v[1],2),"y_mm":round(v[2],2),"w_mm":v[3],"h_mm":v[4],
            "z_mm":v[5],"zone":v[6],"provenance":v[7],"note":v[8],"new":("+" in n)} for n,v in placed.items()]
    (HERE/"components.json").write_text(json.dumps(comps,indent=1))
    th=max(v[5] for v in placed.values() if v[0]=="top"); bh=max(v[5] for v in placed.values() if v[0]=="bot")
    env={"board_shape":"bean (Product Stone plan inset 3.5mm — boards/v1/outline.json)",
         "board_bbox_w_mm":BOARD_W,"board_bbox_h_mm":BOARD_H,"board_t_mm":BOARD_T,
         "board_area_mm2":OUTLINE["area_mm2"],
         "prev_rect_mm":[60,46],"prev_rect_area_mm2":2760.0,
         "area_vs_old_rect":f"{OUTLINE['area_mm2']/2760.0:.0%} of the old 60x46 rectangle",
         "max_comp_top_mm":th,"max_comp_bot_mm":bh,
         "stack_mm":round(BOARD_T+th+bh,1),"device_target_mm":[75,48,19],"chassis_buffer_mm":{"wall":1.6,"clearance":1.9},
         "layers":6,"process":"JLCPCB 6L through-via + POFV","sensor_count":sum(1 for _ in PARTS)}
    (HERE/"envelope.json").write_text(json.dumps(env,indent=1))
    a,i=power_md()
    print(f"OK bean {BOARD_W}x{BOARD_H} bbox, area {OUTLINE['area_mm2']:.0f}mm2 "
          f"({OUTLINE['area_mm2']/2760:.0%} of old 60x46); parts {len(PARTS)}; "
          f"stack {BOARD_T+th+bh:.1f}mm; ambient {a:.1f}mA→{CELL_MAH/a:.0f}h; "
          f"interrogate {i:.0f}mA→{CELL_MAH/i:.1f}h")

if __name__=="__main__":
    main()
