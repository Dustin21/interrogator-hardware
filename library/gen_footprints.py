#!/usr/bin/env python3
"""Parametric KiCad footprint (.kicad_mod) generators — H2 stage-2.

Generates the TO-GENERATE footprints into library/footprints/generated/.
Every file is tier E0: header comment records the dimension source and the
rule 'E0 — overlay-verify against the vendor land-pattern drawing before fab'.

Pad-size policy: IPC-7351 nominal derived from body/pitch class —
  * QFN/DFN/SON perimeter: pad width = 0.55*pitch (>=0.20), length = 0.80 with
    0.05 outward toe past body edge (0.30 in / 0.05 out of nominal lead).
  * CSP/BGA balls: NSMD pad = 0.55*pitch (0.5 mm pitch -> 0.275 -> rounded).
  * Castellated modules: 0.8 x 1.4 pads, 0.6 inward from edge.
Sources: staged datasheet PDFs in registry_assets (marked DS pNN) or
docs/research/bom-v1.md (marked RS/E0-unverified).

Run: python3 library/gen_footprints.py
"""
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "footprints" / "generated"
OUT.mkdir(parents=True, exist_ok=True)

F = lambda v: f"{v:.6g}"


class FP:
    """Minimal .kicad_mod S-expression builder (KiCad 7 syntax)."""

    def __init__(self, name, descr, source, smd=True):
        self.name, self.descr, self.source, self.smd = name, descr, source, smd
        self.items = []

    def pad(self, num, x, y, w, h, shape="roundrect", kind="smd",
            layers='"F.Cu" "F.Paste" "F.Mask"', drill=None, rratio=0.25):
        d = f" (drill {F(drill)})" if drill else ""
        rr = f" (roundrect_rratio {F(rratio)})" if shape == "roundrect" else ""
        self.items.append(
            f'  (pad "{num}" {kind} {shape} (at {F(x)} {F(y)}) '
            f'(size {F(w)} {F(h)}){d} (layers {layers}){rr})')

    def circle_pad(self, num, x, y, dia, kind="smd",
                   layers='"F.Cu" "F.Paste" "F.Mask"', drill=None):
        d = f" (drill {F(drill)})" if drill else ""
        self.items.append(
            f'  (pad "{num}" {kind} circle (at {F(x)} {F(y)}) '
            f'(size {F(dia)} {F(dia)}){d} (layers {layers}))')

    def rect_lines(self, w, h, layer, width):
        x, y = w / 2, h / 2
        for a, b in [((-x, -y), (x, -y)), ((x, -y), (x, y)),
                     ((x, y), (-x, y)), ((-x, y), (-x, -y))]:
            self.items.append(
                f'  (fp_line (start {F(a[0])} {F(a[1])}) (end {F(b[0])} {F(b[1])}) '
                f'(stroke (width {F(width)}) (type solid)) (layer "{layer}"))')

    def fp_circle(self, cx, cy, r, layer, width):
        self.items.append(
            f'  (fp_circle (center {F(cx)} {F(cy)}) (end {F(cx + r)} {F(cy)}) '
            f'(stroke (width {F(width)}) (type solid)) (fill none) (layer "{layer}"))')

    def pin1_dot(self, x, y):
        self.fp_circle(x, y, 0.15, "F.SilkS", 0.25)

    def body(self, w, h, courtyard_margin=0.25):
        self.rect_lines(w, h, "F.Fab", 0.1)
        self.rect_lines(w + 2 * courtyard_margin, h + 2 * courtyard_margin,
                        "F.CrtYd", 0.05)

    def write(self):
        attr = "smd" if self.smd else "through_hole"
        hdr = (f'(footprint "{self.name}" (version 20221018) (generator gen_footprints)\n'
               f'  (layer "F.Cu")\n'
               f'  (descr "{self.descr} | dims: {self.source} | '
               f'E0 -- overlay-verify against vendor land-pattern drawing before fab")\n'
               f'  (attr {attr})\n'
               f'  (fp_text reference "REF**" (at 0 -1) (layer "F.SilkS") '
               f'(effects (font (size 0.5 0.5) (thickness 0.1))))\n'
               f'  (fp_text value "{self.name}" (at 0 1) (layer "F.Fab") '
               f'(effects (font (size 0.5 0.5) (thickness 0.1))))\n')
        (OUT / f"{self.name}.kicad_mod").write_text(
            hdr + "\n".join(self.items) + "\n)\n")
        return self.name


def ball_grid(name, descr, source, body_w, body_h, pitch, balls, pad_dia):
    """balls = list of (num, col_idx, row_idx) with idx 0-based from top-left."""
    fp = FP(name, descr, source)
    cols = max(b[1] for b in balls) + 1
    rows = max(b[2] for b in balls) + 1
    x0, y0 = -(cols - 1) * pitch / 2, -(rows - 1) * pitch / 2
    for num, c, r in balls:
        fp.circle_pad(num, x0 + c * pitch, y0 + r * pitch, pad_dia)
    fp.body(body_w, body_h)
    fp.pin1_dot(-body_w / 2 - 0.3, -body_h / 2)
    return fp.write()


def dual_row(name, descr, source, body_w, body_h, pitch, n_per_row, row_span,
             pad_w, pad_h, ep=None):
    """DFN/OLGA dual-row: pins 1..n down the left column (top->bottom),
    n+1..2n up the right column (bottom->top), counterclockwise."""
    fp = FP(name, descr, source)
    y0 = -(n_per_row - 1) * pitch / 2
    for i in range(n_per_row):
        fp.pad(i + 1, -row_span / 2, y0 + i * pitch, pad_w, pad_h)
    for i in range(n_per_row):
        fp.pad(n_per_row + i + 1, row_span / 2, y0 + (n_per_row - 1 - i) * pitch,
               pad_w, pad_h)
    if ep:
        fp.pad(2 * n_per_row + 1, 0, 0, ep[0], ep[1])
    fp.body(body_w, body_h)
    fp.pin1_dot(-body_w / 2 - 0.3, y0)
    return fp.write()


def quad_qfn(name, descr, source, body, pitch, n_side, pad_w, pad_l, ep=None):
    """QFN/SON quad, pins 1..4*n counterclockwise from top of left side."""
    fp = FP(name, descr, source)
    span = body + 0.1  # pad center line: body edge + slight toe
    off = -(n_side - 1) * pitch / 2
    n = 0
    for i in range(n_side):        # left, top->bottom
        n += 1; fp.pad(n, -span / 2, off + i * pitch, pad_l, pad_w)
    for i in range(n_side):        # bottom, left->right
        n += 1; fp.pad(n, off + i * pitch, span / 2, pad_w, pad_l)
    for i in range(n_side):        # right, bottom->top
        n += 1; fp.pad(n, span / 2, -off - i * pitch, pad_l, pad_w)
    for i in range(n_side):        # top, right->left
        n += 1; fp.pad(n, -off - i * pitch, -span / 2, pad_w, pad_l)
    if ep:
        n += 1; fp.pad(n, 0, 0, ep, ep)
    fp.body(body, body)
    fp.pin1_dot(-body / 2 - 0.3, off)
    return fp.write()


def castellated(name, descr, source, body_w, body_h, n_left, n_bottom, n_right,
                n_top, pitch, pad_w=0.8, pad_l=1.4):
    """Castellated module, pins 1.. counterclockwise from top of left edge."""
    fp = FP(name, descr, source)
    n = 0
    yoff = -(n_left - 1) * pitch / 2
    for i in range(n_left):
        n += 1; fp.pad(n, -body_w / 2 + pad_l / 2 - 0.2, yoff + i * pitch, pad_l, pad_w)
    xoff = -(n_bottom - 1) * pitch / 2
    for i in range(n_bottom):
        n += 1; fp.pad(n, xoff + i * pitch, body_h / 2 - pad_l / 2 + 0.2, pad_w, pad_l)
    for i in range(n_right):
        n += 1; fp.pad(n, body_w / 2 - pad_l / 2 + 0.2, -yoff - i * pitch, pad_l, pad_w)
    xoff2 = -(n_top - 1) * pitch / 2
    for i in range(n_top):
        n += 1; fp.pad(n, -xoff2 - i * pitch, -body_h / 2 + pad_l / 2 - 0.2, pad_w, pad_l)
    fp.body(body_w, body_h)
    fp.pin1_dot(-body_w / 2 - 0.5, yoff)
    return fp.write()


generated = []

# ---------------------------------------------------------------------------
# 1. A121 fcCSP50 — REAL ball map from Acconeer A121 DS v1.8 p8-9 (staged PDF).
#    Body 5.5 x 5.2 x 0.88 mm, 0.5 mm pitch, rows A..K (no I) x cols 1..10.
A121_BALLS = (
    "A2 A3 A4 A5 A6 A7 A8 A9 B1 B2 B9 B10 C1 C2 C9 C10 D1 D2 D9 D10 "
    "E1 E2 E9 E10 F1 F2 F9 F10 G1 G10 H1 H2 H9 H10 J1 J2 J3 J5 J6 J8 J9 J10 "
    "K2 K3 K4 K5 K6 K7 K8 K9").split()
ROWS = "ABCDEFGHJK"
balls = [(b, int(b[1:]) - 1, ROWS.index(b[0])) for b in A121_BALLS]
generated.append(ball_grid(
    "A121_fcCSP50", "Acconeer A121 60GHz radar, fcCSP50 AiP",
    "DS v1.8 p5/p8-9 (body 5.5x5.2x0.88, 0.5mm pitch, 50 named balls)",
    5.5, 5.2, 0.5, balls, 0.27))
# antenna keepout note lives in descr of the board doc; AiP -> no copper above.

# 2. VL53L8CH optical LGA16+thermal — pad NAMES from VL53L8CX DS14161 Table 3
#    p6-7 (staged): rows A(1-7), B(1,4,7), C(1-7); body 6.4x3.0x1.75.
#    Col/row pitch E0-estimate from body (drawing figure is an image).
fp = FP("ST_VL53L8_LGA16",
        "ST VL53L8CH/CX ToF module, optical LGA16 + thermal pad",
        "DS14161 Table 3 p6-7 pad names; body 6.4x3.0 p4; pitch E0-est 0.85/1.0")
cp, rp = 0.85, 1.0
for r, row in enumerate("ABC"):
    for c in range(7):
        num = f"{row}{c + 1}"
        if row == "B" and c + 1 not in (1, 4, 7):
            continue
        w, h = (0.5, 0.5) if num == "B4" else (0.4, 0.6)
        fp.pad(num, -3 * cp + c * cp, -rp + r * rp, w, h)
fp.body(6.4, 3.0)
fp.pin1_dot(-3.5, -1.5)
generated.append(fp.write())

# 3. AS7331 OLGA16 — body 3.65x2.61 (DS p65 drawing is image); dual-row E0.
generated.append(dual_row(
    "AS7331_OLGA16", "ams AS7331 UV A/B/C spectral, OLGA16",
    "AS7331 DS p7/p65: body 3.65x2.61x1.0; 16 pads dual-row E0-est pitch 0.4",
    3.65, 2.61, 0.4, 8, 2.4, 0.6, 0.22))

# 4. TCS3448 — AS7343 successor, same OLGA-8 class 3.1x2.0x1.0
#    (AS7343 DS p3/p5 staged; TCS3448 DS unavailable -> reuse family pattern).
generated.append(dual_row(
    "TCS3448_OLGA8", "ams TCS3448 14ch VIS spectral (AS7343-family OLGA-8)",
    "AS7343 DS p3 body 3.1x2.0x1.0, OLGA-8 p5; pitch 0.65 E0; TCS3448 DS unavailable",
    3.1, 2.0, 0.65, 4, 1.9, 0.7, 0.3))

# 5. AS7421 OLGA-10 3.5x3.5 (RS/bom-v1.md E0-unverified; no DS available).
generated.append(dual_row(
    "AS7421_OLGA10", "ams AS7421 64ch NIR spectral, OLGA-10 class",
    "RS bom-v1.md E0-unverified: 3.5x3.5x1.8 OLGA10; pitch 0.6 E0",
    3.5, 3.5, 0.6, 5, 2.8, 0.6, 0.28))

# 6. MLX90632 SFN 3x3 (RS E0-unverified; no DS). Pad-count placeholder DFN-8.
generated.append(dual_row(
    "MLX90632_SFN8_3x3", "Melexis MLX90632 spot FIR, SFN/QFN 3x3 class",
    "RS bom-v1.md E0-unverified: 3x3x1.0 SFN; DFN-8 P0.65 PLACEHOLDER pad count",
    3.0, 3.0, 0.65, 4, 2.9, 0.75, 0.3))

# 7. SGP41 DFN-6 — Sensirion SGP41 DS p18 (staged): 2.44x2.44x0.85, pitch 0.8,
#    central die pad (GND).  6 perimeter pads dual-row + EP.
generated.append(dual_row(
    "SGP41_DFN6_2.44x2.44", "Sensirion SGP41 VOC/NOx, DFN-6 + die pad",
    "SGP41 DS p1/p18: body 2.44x2.44x0.85, terminal pitch 0.8 (die pad GND)",
    2.44, 2.44, 0.8, 3, 2.2, 0.7, 0.35, ep=(1.0, 1.6)))

# 8. ENS161 LGA-9 3x3 (RS E0-unverified). 3+3+3 U-perimeter placeholder.
fp = FP("ENS161_LGA9", "ScioSense ENS161 4-el MOX, LGA-9 3x3",
        "RS bom-v1.md E0-unverified: LGA-9 3x3x0.9; U-perimeter 3/3/3 pitch 0.85 E0")
for i in range(3):
    fp.pad(i + 1, -1.35, -0.85 + i * 0.85, 0.7, 0.4)          # left 1-3
for i in range(3):
    fp.pad(4 + i, -0.85 + i * 0.85, 1.35, 0.4, 0.7)           # bottom 4-6
for i in range(3):
    fp.pad(7 + i, 1.35, 0.85 - i * 0.85, 0.7, 0.4)            # right 7-9
fp.body(3.0, 3.0)
fp.pin1_dot(-1.9, -0.85)
generated.append(fp.write())

# 9. BMV080 host interface = Molex 503566-1302 ZIF (13 ckt, 0.30 mm pitch) —
#    Bosch BMV080 DS p16 (staged) lists this connector as the mating part.
fp = FP("BMV080_Molex_503566-1302_ZIF13",
        "BMV080 PM2.5 flex-to-host: Molex 503566-1302 Easy-On ZIF, 13ckt 0.3mm",
        "BMV080 DS p16 (connector P/N + 13ckt/0.3mm); Molex pattern E0-est")
for i in range(13):
    fp.pad(i + 1, -1.8 + i * 0.3, -1.4, 0.18, 0.8)
fp.pad("MP1", -2.65, 0.9, 0.7, 0.9)
fp.pad("MP2", 2.65, 0.9, 0.7, 0.9)
fp.body(6.0, 3.4)
fp.pin1_dot(-1.8, -2.3)
generated.append(fp.write())

# 10. AS7058 WLCSP42 2.82x2.55 (RS E0-unverified). 7x6 grid, 0.4 pitch,
#     NUMERIC ball numbering 1..42 (real A1..G6 map needs ams DS).
balls = [(str(r * 7 + c + 1), c, r) for r in range(6) for c in range(7)]
generated.append(ball_grid(
    "AS7058_WLCSP42", "ams AS7058 PPG/ECG/BioZ AFE, WLCSP42",
    "RS bom-v1.md E0-unverified: 2.82x2.55 WLCSP42; 7x6@0.4 NUMERIC-PLACEHOLDER map",
    2.82, 2.55, 0.4, balls, 0.23))

# 11. STM32N657 VFBGA142 (DS14791 unavailable here). 0.5 mm pitch;
#     PLACEHOLDER 12x12 serpentine fill of 142 numeric balls — REPLACE with
#     real ball map before any routing (E0 hard gate).
balls = [(str(i + 1), i % 12, i // 12) for i in range(142)]
generated.append(ball_grid(
    "ST_VFBGA142_PLACEHOLDER", "STM32N657X0 VFBGA142 0.5mm",
    "RS bom-v1.md: body 8x8 E0-unverified; BALL MAP PLACEHOLDER (numeric 12x12 fill)",
    8.0, 8.0, 0.5, balls, 0.27))

# 12. Octal NOR BGA24 (MX25UW6445G-class; no DS here). 6x4 @ 1.0 mm numeric.
balls = [(str(i + 1), i % 6, i // 6) for i in range(24)]
generated.append(ball_grid(
    "NOR_BGA24_6x8", "Octal xSPI NOR flash, BGA-24 1.0mm (xccela class)",
    "EST components.json 8x6 body; 6x4 balls @1.0 NUMERIC-PLACEHOLDER (E0)",
    8.0, 6.0, 1.0, balls, 0.4))

# 13. BL54L15 castellated module 10x14 (Ezurio DS unavailable). 32 pads used
#     by the circuit model; 12/4/12/4 perimeter, NUMERIC E0 placeholder.
generated.append(castellated(
    "BL54L15_MODULE", "Ezurio BL54L15 (nRF54L15) BLE module, castellated",
    "RS bom-v1.md E0-unverified: 10x14 module; 32 castellations NUMERIC-PLACEHOLDER; "
    "antenna keepout at top edge per module manual (get Ezurio DS)",
    10.0, 14.0, 12, 4, 12, 4, 1.1))

# 14. MIA-M10Q 4.5x4.5 SiP LGA (u-blox integration manual unavailable).
generated.append(castellated(
    "UBLOX_MIA_M10Q", "u-blox MIA-M10Q GNSS SiP, LGA 4.5x4.5",
    "RS bom-v1.md E0-unverified: 4.5x4.5x1.0 SiP; 20-pad perimeter 5/5/5/5 "
    "NUMERIC-PLACEHOLDER pitch 0.8; RF corner keepout (get u-blox manual)",
    4.5, 4.5, 5, 5, 5, 5, 0.8, pad_w=0.4, pad_l=0.5))

# 15. TPS22916 CSP-4 (TI YFP 0.76x0.76, 0.4 pitch — RS E0). Numeric 2x2.
balls = [("1", 0, 0), ("2", 0, 1), ("3", 1, 1), ("4", 1, 0)]  # A1,B1,B2,A2 order E0
generated.append(ball_grid(
    "TPS22916_CSP4", "TI TPS22916 load switch, 4-ball WCSP",
    "RS bom-v1.md E0-unverified: 0.76x0.76 YFP, 0.4mm pitch; ball order E0",
    0.76, 0.76, 0.4, balls, 0.23))

# 16. AD8317 LFCSP-8 2x3 (ADI CP-8-13 class; DS unavailable here). E0.
generated.append(dual_row(
    "AD8317_LFCSP8_2x3", "ADI AD8317 RF log detector, LFCSP-8 2x3mm",
    "ADI CP-8-13 class E0: body 2x3, pitch 0.5, EP 0.9x1.6 (verify vs ADI DS)",
    2.0, 3.0, 0.5, 4, 1.8, 0.6, 0.25, ep=(0.9, 1.6)))

# 17. SGX-4CO electrochemical cell, 4-series TH (SGX DS unavailable). 3 radial
#     pins (WE/RE/CE); board envelope held to the ratified 14x14 floorplan
#     rect (components.json) — the cell body may overhang inside the chassis
#     air pocket, but copper/courtyard stays in the 14 mm square. E0.
fp = FP("SGX_4CO_4SERIES_TH", "SGX 4-CO electrochemical CO cell, TH radial",
        "RS bom-v1.md E0-unverified: 4-series can, courtyard held to the "
        "ratified 14x14 envelope; 3 pins on 4.5mm-radius circle E0 (WE/RE/CE) "
        "-- get SGX 4-CO DS before fab", smd=False)
for num, ang in ((1, 90), (2, 210), (3, 330)):     # WE, RE, CE
    x = 4.5 * math.cos(math.radians(ang))
    y = -4.5 * math.sin(math.radians(ang))
    fp.circle_pad(num, x, y, 1.8, kind="thru_hole",
                  layers='"*.Cu" "*.Mask"', drill=0.9)
fp.fp_circle(0, 0, 6.7, "F.SilkS", 0.15)
fp.fp_circle(0, 0, 6.9, "F.CrtYd", 0.05)
fp.body(0.1, 0.1, courtyard_margin=0)  # fab cross at center
generated.append(fp.write())

# 18. Pogo accessory ring — 6 pads on a 9 mm circle (ADR-0002 custom, E0).
fp = FP("POGO6_MAGRING", "Magnetic 6-pogo accessory landing ring (ADR-0002)",
        "Custom mech E0: 6x 1.8mm gold pads on 9mm-dia circle, center magnet zone")
for i in range(6):
    ang = math.radians(60 * i - 90)
    fp.circle_pad(i + 1, 4.5 * math.cos(ang), 4.5 * math.sin(ang), 1.8)
fp.fp_circle(0, 0, 5.7, "F.SilkS", 0.15)
fp.fp_circle(0, 0, 5.9, "F.CrtYd", 0.05)
fp.pin1_dot(0, -6.4)
generated.append(fp.write())

# 19-22. Mechanical-custom simple footprints (E0).
fp = FP("ELECTRODE_PAD_8MM", "Exposed ECG/touch electrode pad, 8mm",
        "Custom mech E0: 8mm bare-copper/gold disc, mask-defined")
fp.circle_pad(1, 0, 0, 8.0)
fp.fp_circle(0, 0, 4.25, "F.CrtYd", 0.05)
generated.append(fp.write())

fp = FP("ELECTRODE_RING_12MM", "ECG reference ring electrode, 12mm OD",
        "Custom mech E0: annular exposed ring (drawn as 12mm disc pad, "
        "mask ring defined at layout)")
fp.circle_pad(1, 0, 0, 12.0)
fp.fp_circle(0, 0, 6.25, "F.CrtYd", 0.05)
generated.append(fp.write())

fp = FP("PIEZO_DISC_PADS", "Piezo disc contact pads (12mm disc above)",
        "Custom mech E0: 2 SMD pads 2x3mm at 6mm spacing")
fp.pad(1, -3.0, 0, 2.0, 3.0)
fp.pad(2, 3.0, 0, 2.0, 3.0)
fp.rect_lines(9.0, 4.0, "F.CrtYd", 0.05)
generated.append(fp.write())

fp = FP("LRA_PADS", "LRA haptic actuator solder pads",
        "Custom mech E0: 2 SMD pads 1.5x2mm at 4mm spacing")
fp.pad(1, -2.0, 0, 1.5, 2.0)
fp.pad(2, 2.0, 0, 1.5, 2.0)
fp.rect_lines(6.5, 3.0, "F.CrtYd", 0.05)
generated.append(fp.write())

# 23. Radiation-cavity shield can, 10x10 frame, 4 corner tabs (E0 custom).
fp = FP("SHIELD_CAN_RAD_10x10", "Radiation charge-amp shield can 10x10 (light-tight)",
        "Custom mech E0: 10x10 frame, 4x corner tabs 1.5x1.5; pick drawn can at DFM")
for num, (sx, sy) in enumerate([(-1, -1), (-1, 1), (1, 1), (1, -1)], 1):
    fp.pad(num, sx * 4.6, sy * 4.6, 1.5, 1.5)
fp.rect_lines(10.0, 10.0, "F.Fab", 0.1)
fp.rect_lines(11.0, 11.0, "F.CrtYd", 0.05)
generated.append(fp.write())

# 24. GNSS chip antenna fallback pads (Antenova SR4G013 harvested official is
#     preferred; this 2-pad generic stays for the netlist AE_GNSS binding if
#     a different P/N is chosen). 3216-class.
fp = FP("GNSS_CHIP_ANT_3216", "GNSS L1 chip antenna, 3216-class 2-pad",
        "Generic 3.2x1.6 chip antenna E0; final P/N (Antenova SR4G013 official "
        "footprint harvested) at stage-3")
fp.pad(1, -1.4, 0, 0.9, 1.8)
fp.pad(2, 1.4, 0, 0.9, 1.8)
fp.body(3.2, 1.6)
generated.append(fp.write())

if __name__ == "__main__":
    print(f"generated {len(generated)} footprints into {OUT}:")
    for g in generated:
        print(" ", g)
