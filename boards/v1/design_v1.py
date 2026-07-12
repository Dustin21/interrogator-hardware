#!/usr/bin/env python3
"""v1 board definition — grounded floorplan (zone-packer), envelope, power model.

Provenance per dimension: DS = datasheet PDF in registry_assets, RS = July-2026
web research (docs/research/bom-v1.md), EST = estimate flagged for H2.

Zone-packer: each part is assigned to a (side, zone); the packer shelf-packs parts
inside the zone rectangle (row-major, min-gap). Adding/removing a sensor = edit the
PARTS list; placement + collision-freedom regenerate automatically (the R6/R12 respin
promise). If a zone overflows, the packer raises — the signal to grow the board (§5.8).

Outputs: components.json, floorplan_top.svg, floorplan_bottom.svg, envelope.json,
../../docs/power-budget.md.  Run: python3 boards/v1/design_v1.py
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
DOCS = HERE.parents[1] / "docs"

BOARD_W, BOARD_H, BOARD_T = 60.0, 46.0, 1.6   # grew from 54x40 to absorb the 7 adds + big gas cells (§5.8 XY lever)
GAP = 0.8                                      # min courtyard gap (mm)

# Zones: name -> (side, x0, y0, w, h)  [bottom-left origin, mm]
ZONES = {
    # TOP = sensing face
    "optical":   ("top", 2.0, 29.5, 56.0, 15.0),
    "air":       ("top", 34.0, 9.0, 24.0, 18.0),
    "contact":   ("top", 2.0, 2.0, 19.0, 9.0),
    "radar":     ("top", 23.0, 19.0, 9.0, 8.0),
    "magnet":    ("top", 2.0, 13.0, 8.0, 14.0),
    # BOTTOM = compute face
    "compute":   ("bot", 20.0, 27.0, 24.0, 18.0),
    "radio_ble": ("bot", 2.0, 30.0, 12.0, 15.0),
    "radio_wifi":("bot", 45.0, 2.0, 14.0, 18.0),
    "sense_b":   ("bot", 18.0, 14.0, 26.0, 11.0),   # IMU, radiation-PIN, mic, ADC (quiet)
    "gas_b":     ("bot", 2.0, 13.0, 15.0, 16.0),    # SGX-CO electrochemical (vent) — big cell
    "power":     ("bot", 2.0, 2.0, 26.0, 10.0),
    "io":        ("bot", 46.0, 22.0, 13.0, 22.0),   # touch, haptic, GNSS corner
}

# name, w, h, z(height), zone, provenance, note
PARTS = [
    # ---------- TOP (sensing face) ----------
    ("MLX90642 thermal 32x24",  9.6, 9.6, 5.1, "optical", "RS", "TO-39+lens; tallest top part"),
    ("VL53L8CH ToF 8x8 raw",    6.4, 3.0, 1.75,"optical", "DS vl53l8cx", "SPI strap in copper"),
    ("TCS3448 14ch VIS",        3.1, 2.0, 1.0, "optical", "RS", "AS7343 successor; diffuser"),
    ("AS7331 UV A/B/C",         3.65,2.6, 1.0, "optical", "DS OLGA16", "UV-clear/quartz aperture"),
    ("AS7421 64ch NIR +",       3.5, 3.5, 1.8, "optical", "RS OLGA10", "hydration 970nm; +LED"),
    ("MLX90632 spot FIR +",     3.0, 3.0, 1.0, "optical", "RS QFN", "medical-grade spot temp"),
    ("VD66GY camera (DNP)",     8.0, 8.0, 3.5, "optical", "EST", "global shutter, N6 CSI; DNP"),
    ("A121 60GHz radar",        5.5, 5.2, 0.88,"radar",   "DS fcCSP50", "AiP; radome above"),
    ("BME688 gas/T/RH/P",       3.0, 3.0, 0.93,"air",     "DS", "air pocket, thermal moat"),
    ("SGP41 VOC/NOx",           2.44,2.44,0.85,"air",     "DS", "air pocket"),
    ("ENS161 4-el MOX +",       3.0, 3.0, 0.9, "air",     "RS LGA9", "scent granularity"),
    ("SCD41 true CO2 +",       10.1,10.1, 6.5, "air",     "RS", "photoacoustic NDIR; tall; gated"),
    ("SHT41 ref T/RH +",        1.5, 1.5, 0.5, "air",     "RS DFN4", "reference anchor for MOX comp"),
    ("BMV080 PM2.5",            4.2, 3.5, 3.0, "air",     "DS element", "free-air window"),
    ("MAX30102 PPG",            5.6, 3.3, 1.55,"contact", "DS", "contact window"),
    ("AS7058 PPG/ECG/BioZ",     2.82,2.55,0.7, "contact", "RS WLCSP42", "ECG needs return electrode (back)"),
    ("MMC5983MA nT mag +",      3.0, 3.0, 1.0, "magnet",  "RS LGA16", ">15mm from currents"),
    ("TMAG5273 mT hall",        2.9, 2.8, 1.1, "magnet",  "DS SOT23-6", "dock-magnet detect"),
    # ---------- BOTTOM (compute face) ----------
    ("STM32N657 VFBGA142",      8.0, 8.0, 1.2, "compute", "RS", "app MCU + NPU + I3C/SPI/CSI"),
    ("Octal NOR flash",         8.0, 6.0, 1.2, "compute", "EST BGA24", "N6 flashless"),
    ("IQS7222A touch",          3.0, 3.0, 0.6, "io",      "RS QFN20", "12ch shell electrodes"),
    ("DRV2605L haptic",         3.0, 3.0, 0.9, "io",      "RS VSSOP", "LRA driver"),
    ("MIA-M10Q GNSS RAWX",      4.5, 4.5, 1.0, "io",      "RS", "antenna keepout corner"),
    ("BL54L15 BLE sentinel",   10.0,14.0, 2.0, "radio_ble", "RS Ezurio", "pre-certified; antenna edge"),
    ("ESP32-C6-MINI WiFi",     13.2,16.6, 2.4, "radio_wifi", "RS", "SDIO; gated; antenna edge"),
    ("BNO086 IMU raw+fused",    3.8, 5.2, 1.1, "sense_b", "DS LGA28", "vibration-aware mount"),
    ("ADS131M04 24b 4ch",       3.0, 3.0, 0.8, "sense_b", "RS WQFN", "piezo + radiation-PIN charge amp"),
    ("PIN radiation det +",    10.0,10.0, 2.0, "sense_b", "RS large-area PIN", "replaces BG51; dose; light-tight; scales to SiPM"),
    ("MEMS mic +",              3.5, 2.65,1.0, "sense_b", "RS", "heart/lung + acoustic; bottom port"),
    ("SGX-4CO electrochem +",  14.0,14.0, 4.0, "gas_b",   "RS 4-series", "CO safety/breath; vent; ~2-5yr life FLAG"),
    ("CYPD3177 USB-C PD",       4.0, 4.0, 0.6, "power",   "RS QFN24", ""),
    ("BQ25620 charger 3.5A",    2.5, 3.0, 0.6, "power",   "RS WQFN", "~1C fast charge"),
    ("BQ27427 gauge",           1.6, 1.6, 0.6, "power",   "RS DSBGA", ""),
    ("TPS62840 sentinel buck",  1.6, 2.1, 0.6, "power",   "RS SOT583", "60nA IQ rail"),
    ("TPS62823 core buck",      1.6, 2.1, 0.6, "power",   "RS SOT583", ""),
    ("TLV62568 1V8 buck",       1.6, 2.9, 0.6, "power",   "RS SOT23-5", ""),
    ("BQ29700+FET protect",     4.0, 3.0, 0.6, "power",   "RS SON6", ""),
    ("Load switches x7",        9.5, 2.0, 0.5, "power",   "RS WCSP", "6 domains + accessory port (H2 ratified)"),
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
                raise SystemExit(f"OVERFLOW zone '{zname}': {name} — grow board or zone (§5.8)")
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

ZCOL = {"optical":"#dbe7f6","air":"#e3f3ef","contact":"#fbeee6","radar":"#f3e8fb","magnet":"#f2f2ea",
        "compute":"#dbe7f6","radio_ble":"#f3e8fb","radio_wifi":"#efe3fb","sense_b":"#f2f2ea",
        "gas_b":"#e3f3ef","power":"#fdecec","io":"#e7eefb"}

def svg(side, placed, fname):
    S = 11
    W, Hh = BOARD_W*S+170, BOARD_H*S+120
    e=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{Hh}" font-family="Helvetica,Arial" font-size="10">',
       f'<rect width="{W}" height="{Hh}" fill="white"/><g transform="translate(60,44)">',
       f'<rect x="0" y="0" width="{BOARD_W*S}" height="{BOARD_H*S}" rx="{3*S}" fill="#134E4A" opacity="0.07" stroke="#134E4A" stroke-width="2"/>']
    for zn,(zs,zx,zy,zw,zh) in ZONES.items():
        if zs!=side: continue
        e.append(f'<rect x="{zx*S}" y="{(BOARD_H-zy-zh)*S}" width="{zw*S}" height="{zh*S}" fill="{ZCOL[zn]}" opacity="0.7" rx="5"/>')
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
    e.append(f'<text x="{BOARD_W*S/2}" y="{BOARD_H*S+35}" text-anchor="middle" font-size="11">{BOARD_W:.0f} mm</text>')
    e.append(f'<line x1="{BOARD_W*S+20}" y1="0" x2="{BOARD_W*S+20}" y2="{BOARD_H*S}" stroke="#333"/>')
    e.append(f'<text x="{BOARD_W*S+28}" y="{BOARD_H*S/2}" font-size="11">{BOARD_H:.0f} mm</text>')
    title = "TOP · sensing face" if side=="top" else "BOTTOM · compute face"
    e.append(f'<text x="0" y="-20" font-size="14" font-weight="bold">interrogator v1 · {title} · 6-layer {BOARD_T}mm · green=new</text>')
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
    placed=pack(); collide_check(placed)
    svg("top",placed,"floorplan_top.svg"); svg("bot",placed,"floorplan_bottom.svg")
    comps=[{"name":n,"side":v[0],"x_mm":round(v[1],2),"y_mm":round(v[2],2),"w_mm":v[3],"h_mm":v[4],
            "z_mm":v[5],"zone":v[6],"provenance":v[7],"note":v[8],"new":("+" in n)} for n,v in placed.items()]
    (HERE/"components.json").write_text(json.dumps(comps,indent=1))
    th=max(v[5] for v in placed.values() if v[0]=="top"); bh=max(v[5] for v in placed.values() if v[0]=="bot")
    env={"board_w_mm":BOARD_W,"board_h_mm":BOARD_H,"board_t_mm":BOARD_T,"max_comp_top_mm":th,"max_comp_bot_mm":bh,
         "stack_mm":round(BOARD_T+th+bh,1),"device_target_mm":[66,50,18],"chassis_buffer_mm":{"xy":2.0,"z":1.0},
         "layers":6,"process":"JLCPCB 6L through-via + POFV","sensor_count":sum(1 for _ in PARTS)}
    (HERE/"envelope.json").write_text(json.dumps(env,indent=1))
    a,i=power_md()
    print(f"OK {BOARD_W}x{BOARD_H}x{BOARD_T}; parts {len(PARTS)}; stack {BOARD_T+th+bh:.1f}mm; "
          f"ambient {a:.1f}mA→{CELL_MAH/a:.0f}h; interrogate {i:.0f}mA→{CELL_MAH/i:.1f}h")

if __name__=="__main__":
    main()
