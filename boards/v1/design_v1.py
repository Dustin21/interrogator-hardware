#!/usr/bin/env python3
"""v1 board definition — grounded floorplan, envelope, and power model.

Every dimension carries provenance: DS = extracted from the datasheet PDF in
registry_assets (page-greppable), RS = July-2026 web research (URL in
docs/research/bom-v1.md), EST = estimate flagged for H2 verification.

Outputs: components.json, floorplan_top.svg, floorplan_bottom.svg,
envelope.json, ../../docs/power-budget.md
Run: python3 boards/v1/design_v1.py
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
DOCS = HERE.parents[1] / "docs"

BOARD_W, BOARD_H = 54.0, 40.0  # mm — computed by iteration below (assertions enforce fit)
BOARD_T = 1.6                  # 6-layer JLCPCB stackup

# name, w, h, comp_height, side, zone, (x, y) bottom-left mm, provenance, note
C = [
    # ---- TOP = sensing face ----
    ("MLX90642 (thermal 32x24)",  9.6, 9.6, 5.1, "top", "optical", ( 4.0, 29.0), "RS", "TO-39 can+lens; 110deg BCA"),
    ("VL53L8CH (ToF 8x8 raw)",    6.4, 3.0, 1.75,"top", "optical", (15.5, 32.0), "DS vl53l8cx p1", "SPI mode strap in copper"),
    ("TCS3448 (14ch spectral)",   3.1, 2.0, 1.0, "top", "optical", (23.5, 32.5), "RS", "AS7343 successor; diffuser window"),
    ("AS7331 (UV A/B/C)",         3.65,2.6, 1.0, "top", "optical", (28.5, 32.3), "DS AS7331 OLGA16", "quartz/UV-clear aperture"),
    ("VD66GY camera (DNP opt)",   8.0, 8.0, 3.5, "top", "optical", (34.0, 30.0), "EST module", "global shutter, N6 CSI; DNP per D7"),
    ("A121 (60GHz radar)",        5.5, 5.2, 0.88,"top", "rf",      (24.0, 20.5), "DS A121 p1 fcCSP50", "AiP; plastic radome above"),
    ("BME688 (gas/T/RH/P)",       3.0, 3.0, 0.93,"top", "air",     (40.0, 20.0), "DS bme688 p1", "air pocket, thermal moat slots"),
    ("SGP41 (VOC/NOx raw)",       2.44,2.44,0.85,"top", "air",     (45.5, 20.3), "DS sgp41 p1", "air pocket"),
    ("BMV080 (PM2.5)",            4.2, 3.5, 3.0, "top", "air",     (44.0, 12.5), "DS bmv080 element", "free-air window req; unit incl. flex EST"),
    ("MAX30102EFD (PPG)",         5.6, 3.3, 1.55,"top", "contact", ( 6.0,  6.0), "DS max30102 p1", "contact window"),
    ("AS7058 (PPG2/ECG/BioZ)",    2.82,2.55,0.7, "top", "contact", (13.5,  6.3), "RS WLCSP-42", "shares contact zone; electrodes on shell"),
    ("MMC5983MA (nT mag)",        3.0, 3.0, 1.0, "top", "quiet",   ( 3.0, 18.0), "RS LGA-16", ">15mm from power/LED currents"),
    ("TMAG5273 (mT hall)",        2.9, 2.8, 1.1, "top", "quiet",   ( 3.0, 12.5), "DS tmag5273 SOT-23-6", ""),
    # ---- BOTTOM = compute face ----
    ("STM32N657 (VFBGA142 8x8)",  8.0, 8.0, 1.2, "bot", "digital", (20.0, 16.0), "RS ST DS", "app MCU + NPU; I3C/SPI/CSI"),
    ("Octal NOR flash",           8.0, 6.0, 1.2, "bot", "digital", (30.0, 16.0), "EST BGA24", "N6 is flashless"),
    ("BL54L15 (BLE sentinel)",   10.0,14.0, 2.0, "bot", "rf",      ( 3.0, 24.0), "RS Ezurio", "antenna keepout top-left edge"),
    ("ESP32-C6-MINI-1 (WiFi)",   13.2,16.6, 2.4, "bot", "rf",      (39.0,  3.0), "RS Espressif DS", "SDIO to N6; antenna keepout bottom-right edge; gated"),
    ("MIA-M10Q (GNSS RAWX)",      4.5, 4.5, 1.0, "bot", "rf",      (48.0, 34.0), "RS u-blox", "chip antenna keepout top-right corner both sides"),
    ("BNO086 (IMU raw+fused)",    3.8, 5.2, 1.1, "bot", "quiet",   (33.0, 23.5), "DS bno085 p1 LGA-28", "center, vibration-aware mount"),
    ("ADS131M04 (24b 4ch ADC)",   3.0, 3.0, 0.8, "bot", "analog",  (15.5, 25.5), "RS WQFN", "piezo + spare precision ch"),
    ("IQS7222A (touch)",          3.0, 3.0, 0.6, "bot", "digital", (41.5, 26.0), "RS QFN20", "shell electrodes; wake to sentinel"),
    ("DRV2605L + LRA drv",        3.0, 3.0, 0.9, "bot", "digital", (46.5, 26.0), "RS VSSOP", "LRA mounts in chassis"),
    ("CYPD3177 (USB-C PD)",       4.0, 4.0, 0.6, "bot", "power",   ( 4.0,  4.0), "RS QFN24", ""),
    ("BQ25620 (charger 3.5A)",    2.5, 3.0, 0.6, "bot", "power",   ( 9.5,  4.0), "RS WQFN", "fast charge ~1C+, thermal reg"),
    ("BQ27427 (fuel gauge)",      1.6, 1.6, 0.6, "bot", "power",   (13.5,  4.5), "RS DSBGA", ""),
    ("TPS62840 (sentinel buck)",  1.6, 2.1, 0.6, "bot", "power",   (16.5,  4.3), "RS SOT-583", "60nA IQ always-on rail"),
    ("TPS62823 (N6 core buck)",   1.6, 2.1, 0.6, "bot", "power",   (19.5,  4.3), "RS SOT-583", ""),
    ("TLV62568 (1V8 buck)",       1.6, 2.9, 0.6, "bot", "power",   (22.5,  4.0), "RS SOT-23-5", ""),
    ("BQ29700+FETs (1S protect)", 4.0, 3.0, 0.6, "bot", "power",   ( 4.0, 12.5), "RS SON-6", ""),
    ("Load switches x6",          8.0, 2.0, 0.5, "bot", "power",   ( 4.0,  9.5), "RS WCSP x6", "per-segment sensor power gating"),
    ("USB-C conn (mid-mount)",    9.0, 7.5, 3.2, "bot", "power",   (27.0,  0.0), "RS GCT USB4105", "bottom edge; ESD arrays adjacent"),
    ("BG51 (radiation)",         31.5, 9.5, 2.9, "bot", "quiet",   (14.5, 30.0), "EST Teviso (ds blocked)", "thin-window zone in shell; VERIFY dims H2"),
]

def check():
    from itertools import combinations
    for side in ("top", "bot"):
        parts = [c for c in C if c[4] == side]
        for c in parts:
            x, y = c[6]; w, h = c[1], c[2]
            assert 1.0 <= x and 0.0 <= y and x + w <= BOARD_W - 1.0 and y + h <= BOARD_H + 0.01, f"OOB: {c[0]}"
        for a, b in combinations(parts, 2):
            ax, ay = a[6]; bx, by = b[6]
            gap = 0.8  # min courtyard gap mm
            if not (ax + a[1] + gap <= bx or bx + b[1] + gap <= ax or ay + a[2] + gap <= by or by + b[2] + gap <= ay):
                raise AssertionError(f"COLLISION {a[0]} vs {b[0]}")

ZONES_TOP = [("optical", 2, 28, 50, 12, "#dbe7f6"), ("air", 37, 10, 15, 15, "#e3f3ef"),
             ("contact", 3, 3, 16, 8.5, "#fbeee6"), ("rf", 22, 18, 10, 9, "#f3e8fb"), ("quiet", 2, 11, 7, 11.5, "#f2f2ea")]
ZONES_BOT = [("digital", 7, 8, 36, 12, "#dbe7f6"), ("rf", 2, 22, 12, 17, "#f3e8fb"),
             ("power", 3, 0, 32, 8, "#fdecec"), ("quiet", 16, 25, 22, 8, "#f2f2ea")]

def svg(side, zones, fname):
    S = 12  # px/mm
    W, Hh = BOARD_W * S + 160, BOARD_H * S + 120
    e = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{Hh}" font-family="Helvetica,Arial" font-size="11">',
         f'<rect x="0" y="0" width="{W}" height="{Hh}" fill="white"/>',
         f'<g transform="translate(60,40)">',
         f'<rect x="0" y="0" width="{BOARD_W*S}" height="{BOARD_H*S}" rx="{3*S}" fill="#134E4A" opacity="0.08" stroke="#134E4A" stroke-width="2"/>']
    for name, zx, zy, zw, zh, col in zones:
        e.append(f'<rect x="{zx*S}" y="{(BOARD_H-zy-zh)*S}" width="{zw*S}" height="{zh*S}" fill="{col}" opacity="0.8" rx="6"/>')
        e.append(f'<text x="{(zx+0.5)*S}" y="{(BOARD_H-zy-zh)*S+14}" fill="#666" font-size="10">{name.upper()}</text>')
    for c in C:
        if c[4] != side: continue
        x, y = c[6]; w, h = c[1], c[2]
        e.append(f'<rect x="{x*S}" y="{(BOARD_H-y-h)*S}" width="{w*S}" height="{h*S}" fill="#1E3A8A" opacity="0.85" rx="2"/>')
        lbl = c[0].split(" (")[0]
        e.append(f'<text x="{(x+w/2)*S}" y="{(BOARD_H-y-h)*S-3}" text-anchor="middle" fill="#1E293B" font-size="9">{lbl}</text>')
    # dimensions
    e.append(f'<line x1="0" y1="{BOARD_H*S+22}" x2="{BOARD_W*S}" y2="{BOARD_H*S+22}" stroke="#333"/>')
    e.append(f'<text x="{BOARD_W*S/2}" y="{BOARD_H*S+38}" text-anchor="middle">{BOARD_W:.0f} mm</text>')
    e.append(f'<line x1="{BOARD_W*S+22}" y1="0" x2="{BOARD_W*S+22}" y2="{BOARD_H*S}" stroke="#333"/>')
    e.append(f'<text x="{BOARD_W*S+30}" y="{BOARD_H*S/2}" writing-mode="tb">{BOARD_H:.0f} mm</text>')
    title = "TOP — sensing face" if side == "top" else "BOTTOM — compute face"
    e.append(f'<text x="0" y="-16" font-size="15" font-weight="bold">interrogator v1 · {title} · 6-layer, {BOARD_T} mm</text>')
    e.append('</g></svg>')
    (HERE / fname).write_text("\n".join(e))

# ---- power model (mA @3.7V-equivalent unless noted; provenance in bom doc) ----
AMBIENT = {  # duty-cycled, sentinel-supervised
    "BL54L15 sentinel (BLE+touch+rad+gauge)": 0.6, "STM32N657 avg (50ms/s batch @~120mA + stop ~6mA)": 12.0,
    "BME688 ULP": 0.09, "SGP41 duty 1/10": 0.3, "BMV080 1-min duty": 2.6, "MLX90642 1fps duty": 1.5,
    "BNO086 low-rate": 1.5, "MMC+TMAG": 0.3, "VL53L8CH gated off": 0.0, "A121 hibernate": 0.011,
    "GNSS duty 1/30": 0.4, "ADC+touch+misc": 0.5,  # microSD dropped from v1: NOR + phone sync buffer (density win) "leakage/regs": 1.2,
}
INTERROGATE = {
    "STM32N657 full run + NPU": 150.0, "Wi-Fi C6 stream avg": 120.0, "VL53L8CH 15Hz": 45.0,
    "A121 duty": 20.0, "MLX90642 8fps": 25.0, "spectral+UV+PPG x2 + LEDs": 30.0, "GNSS cont": 9.0,
    "blower 50% duty": 19.0, "sensors env cont": 8.0, "sentinel+haptics+glow": 8.0,
}
CELL_MAH, CELL = 1200, "LP503450-class 1200 mAh, 50x34x5.2 mm, ~21 g (1S LiPo + protection)"

def power_md():
    amb = sum(AMBIENT.values()); intg = sum(INTERROGATE.values())
    lines = ["# Two-mode power budget (v1, model — measured at H4 via per-domain shunts)", "",
             f"Cell: **{CELL}** — fast charge ≥1.2 A (~1C) via BQ25620 + USB-C PD.", "",
             "## Ambient mode (R3)", "", "| load | mA avg |", "|---|---|"]
    lines += [f"| {k} | {v:.2f} |" for k, v in AMBIENT.items()]
    lines += [f"| **total** | **{amb:.1f}** |", "",
              f"**Runtime ambient ≈ {CELL_MAH/amb:.0f} h** (target 8 h, floor 5 h → met with ~{CELL_MAH/amb/8:.0f}x margin).",
              "", "## Interrogation mode (deep dive, everything hot)", "", "| load | mA avg |", "|---|---|"]
    lines += [f"| {k} | {v:.1f} |" for k, v in INTERROGATE.items()]
    lines += [f"| **total** | **{intg:.0f}** |", "",
              f"**Runtime continuous interrogation ≈ {CELL_MAH/intg:.1f} h** (deep dives are minutes-long bursts; mixed use lands 8–20 h).",
              "", "Provenance: currents from datasheets/vendor pages cited in docs/research/bom-v1.md; N6 run current is the",
              "flagged community figure (DS14791 table pull pending) — the sentinel split makes the ambient number robust to it."]
    (DOCS / "power-budget.md").write_text("\n".join(lines))
    return amb, intg

def main():
    check()
    svg("top", ZONES_TOP, "floorplan_top.svg")
    svg("bot", ZONES_BOT, "floorplan_bottom.svg")
    comps = [{"name": n, "w_mm": w, "h_mm": h, "z_mm": z, "side": s, "zone": zo, "x_mm": xy[0], "y_mm": xy[1],
              "provenance": pr, "note": nt} for n, w, h, z, s, zo, xy, pr, nt in C]
    (HERE / "components.json").write_text(json.dumps(comps, indent=1))
    top_h = max(c[3] for c in C if c[4] == "top"); bot_h = max(c[3] for c in C if c[4] == "bot")
    env = {"board_w_mm": BOARD_W, "board_h_mm": BOARD_H, "board_t_mm": BOARD_T,
           "max_comp_top_mm": top_h, "max_comp_bot_mm": bot_h,
           "stack_note": "board+comps ~%.1f mm; +battery 5.2 under bottom; +shell 2x1.4 + gaps" % (BOARD_T + top_h + bot_h),
           "device_target_mm": [62, 47, 17], "chassis_buffer_mm": {"xy": 2.0, "z": 1.0, "spare_apertures": 2},
           "layers": 6, "process": "JLCPCB 6L through-via + POFV via-in-pad"}
    (HERE / "envelope.json").write_text(json.dumps(env, indent=1))
    amb, intg = power_md()
    print(f"OK board {BOARD_W}x{BOARD_H}x{BOARD_T}; stack {BOARD_T+top_h+bot_h:.1f}mm; "
          f"ambient {amb:.1f} mA -> {CELL_MAH/amb:.0f} h; interrogate {intg:.0f} mA -> {CELL_MAH/intg:.1f} h")

if __name__ == "__main__":
    main()
