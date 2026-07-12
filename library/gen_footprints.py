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

    def __init__(self, name, descr, source, smd=True, tier="E0"):
        self.name, self.descr, self.source, self.smd = name, descr, source, smd
        self.tier = tier
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
               f'{self.tier} -- overlay-verify against vendor land-pattern drawing before fab")\n'
               f'  (attr {attr})\n'
               f'  (fp_text reference "REF**" (at 0 -1) (layer "F.SilkS") '
               f'(effects (font (size 0.5 0.5) (thickness 0.1))))\n'
               f'  (fp_text value "{self.name}" (at 0 1) (layer "F.Fab") '
               f'(effects (font (size 0.5 0.5) (thickness 0.1))))\n')
        (OUT / f"{self.name}.kicad_mod").write_text(
            hdr + "\n".join(self.items) + "\n)\n")
        return self.name


def ball_grid(name, descr, source, body_w, body_h, pitch, balls, pad_dia,
              tier="E0"):
    """balls = list of (num, col_idx, row_idx) with idx 0-based from top-left."""
    fp = FP(name, descr, source, tier=tier)
    cols = max(b[1] for b in balls) + 1
    rows = max(b[2] for b in balls) + 1
    x0, y0 = -(cols - 1) * pitch / 2, -(rows - 1) * pitch / 2
    for num, c, r in balls:
        fp.circle_pad(num, x0 + c * pitch, y0 + r * pitch, pad_dia)
    fp.body(body_w, body_h)
    fp.pin1_dot(-body_w / 2 - 0.3, -body_h / 2)
    return fp.write()


def dual_row(name, descr, source, body_w, body_h, pitch, n_per_row, row_span,
             pad_w, pad_h, ep=None, tier="E0"):
    """DFN/OLGA dual-row: pins 1..n down the left column (top->bottom),
    n+1..2n up the right column (bottom->top), counterclockwise."""
    fp = FP(name, descr, source, tier=tier)
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

# 4. TCS3448 OLGA-8 — REAL land pattern from TCS3448 DS001121 v2-00 p51
#    Fig 11: 2 rows of 4, pitch 0.8 (centers ±0.4/±1.2), row c-c 1.276
#    (2x 0.638), pads 0.488 x 0.575, pin-1 chamfered. Body 3.1x2.0x1.0 (p5).
#    Drawn as dual COLUMNS (pins 1-4 down the left = VDD,SCL,GND,LDR per
#    p8 Fig 2; 5-8 up the right), i.e. the p51 drawing rotated 90°.
generated.append(dual_row(
    "TCS3448_OLGA8", "ams TCS3448 14ch VIS spectral, OLGA-8",
    "TCS3448 DS001121 p51 Fig 11: pitch 0.8, row c-c 1.276, pads 0.488x0.575; body 3.1x2.0 p5",
    2.0, 3.1, 0.8, 4, 1.276, 0.575, 0.488, tier="E1"))

# 5. AS7421 OLGA-10 — REAL outline from AS7421 DS000667 p45-46 Fig 60/61:
#    body 6.60 x 6.0 x 2.21 (NOT 3.5x3.5 as the old E0 guess); two rows of
#    5 pads (0.6x0.5, pitch 1.25, rows at ±2.6), two large center pads
#    (GND=11 left, LEDA=12 right, ~2.8x3.0 at ±1.65 c-c 3.30). Top view:
#    pins 1-5 along the BOTTOM edge left->right (p6 Fig 3), 6-10 along the
#    top edge right->left, matching the bottom-view drawing mirrored.
fp = FP("AS7421_OLGA10", "ams AS7421 64ch NIR spectral + 4 NIR LEDs, OLGA-10",
        "AS7421 DS000667 p45-46: body 6.6x6.0; pads 0.6x0.5 pitch 1.25 rows +/-2.6; "
        "EPs ~2.8x3.0 at +/-1.65 (window c-c 3.30 p45)", tier="E1")
for i in range(5):                       # pins 1-5, bottom edge, left->right
    fp.pad(i + 1, -2.5 + i * 1.25, 2.6, 0.65, 0.55)
for i in range(5):                       # pins 6-10, top edge, right->left
    fp.pad(6 + i, 2.5 - i * 1.25, -2.6, 0.65, 0.55)
fp.pad(11, -1.65, 0, 2.8, 3.0)           # exposed pad GND
fp.pad(12, 1.65, 0, 2.8, 3.0)            # exposed pad LEDA
fp.body(6.6, 6.0)
fp.pin1_dot(-3.6, 2.6)
generated.append(fp.write())

# 6. MLX90632 SFN 3x3 — REAL footprint from MLX90632 DS rev13 p47 Fig 26:
#    5 pads 0.30x0.25 in one column at left edge (pitch 0.5, e1 p46 Table 17),
#    pin 1 top; central thermal copper 2.10 x 2.55 (8x 0.2mm PTH, tented) ->
#    pad 6. Body 3.0x3.0 (DD=EE, p46).
fp = FP("MLX90632_SFN5_3x3", "Melexis MLX90632 spot FIR, SFN 3x3 (5 pads + thermal)",
        "MLX90632 DS rev13 p47 Fig 26: 5x 0.30x0.25 @0.5 left column; "
        "thermal 2.10x2.55; body 3.0 p46", tier="E1")
for i in range(5):                       # pins 1-5 top->bottom (p8 Table 5)
    fp.pad(i + 1, -1.25, -1.0 + i * 0.5, 0.30, 0.25)
fp.pad(6, 0.1, 0, 2.10, 2.55)            # thermal pad (vias at layout stage)
fp.body(3.0, 3.0)
fp.pin1_dot(-1.8, -1.0)
generated.append(fp.write())

# 7. SGP41 DFN-6 — Sensirion SGP41 DS p18 (staged): 2.44x2.44x0.85, pitch 0.8,
#    central die pad (GND).  6 perimeter pads dual-row + EP.
generated.append(dual_row(
    "SGP41_DFN6_2.44x2.44", "Sensirion SGP41 VOC/NOx, DFN-6 + die pad",
    "SGP41 DS p1/p18: body 2.44x2.44x0.85, terminal pitch 0.8 (die pad GND)",
    2.44, 2.44, 0.8, 3, 2.2, 0.7, 0.35, ep=(1.0, 1.6)))

# 8. ENS161 LGA-9 — REAL pattern from ENS161 DS v1.1 p41-42: 3x3 pad GRID
#    (not U-perimeter!), pitch 1.05, leads 0.7 sq, land +0.05/side -> 0.8 sq;
#    body 3.0x3.0x0.9. Numbering (top view, p5 Fig 2): row1: 1 8 7 /
#    row2: 2 9 6 / row3: 3 4 5; pin 1 top-left.
fp = FP("ENS161_LGA9", "ScioSense ENS161 4-el MOX, LGA-9 3x3 grid",
        "ENS161 DS v1.1 p41 Table 40 (pitch 1.05, lead 0.7+0.05 land) + p5 pin grid",
        tier="E1")
ENS_GRID = [(1, 0, 0), (8, 1, 0), (7, 2, 0),
            (2, 0, 1), (9, 1, 1), (6, 2, 1),
            (3, 0, 2), (4, 1, 2), (5, 2, 2)]
for num, c, r in ENS_GRID:
    fp.pad(num, -1.05 + c * 1.05, -1.05 + r * 1.05, 0.8, 0.8)
fp.body(3.0, 3.0)
fp.pin1_dot(-1.7, -1.05)
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

# 10. AS7058 WLCSP42 — GRID GEOMETRY verified from AS7058_DS001085_short p9
#     Fig 2: rows A-G x cols 1-6 (42 balls), 0.4 pitch, die 2.545 x 2.815
#     ±0.02, A1 top-left (top through view). Ball NAMES are real; the
#     ball->SIGNAL map is still pending the NDA-gated full DS (DS001573).
balls = [(f"{r}{c + 1}", c, ri)
         for ri, r in enumerate("ABCDEFG") for c in range(6)]
generated.append(ball_grid(
    "AS7058_WLCSP42", "ams AS7058 PPG/ECG/BioZ AFE, WLCSP42",
    "AS7058 short DS DS001085 p9: A1..G6 grid @0.4, die 2.545x2.815; "
    "ball-signal map pending full DS (NDA)",
    2.545, 2.815, 0.4, balls, 0.23, tier="E1"))

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

# 14. MIA-M10Q — REAL M-LGA53 map from MIA-M10Q DS UBX-22015849 p9 Fig 2 +
#     p19 Fig 4: body 4.5x4.5x1.0, 53 pads Ø0.27 on a sparse 9x9 grid,
#     pitch 0.5, A1 top-left (top view). Land = 1:1 copper, NSMD, mask
#     opening Ø0.37, paste = copper (IM UBX-21028173 p83). Keep the RF_IN
#     corner (B9/A8-A9) clear of noisy routing; GND stitch under the SiP.
fp = FP("UBLOX_MIA_M10Q", "u-blox MIA-M10Q GNSS SiP, M-LGA53 4.5x4.5",
        "MIA-M10Q DS p9/p19 (53 pads O0.27 @0.5, sparse 9x9); IM p83 land 1:1, mask 0.37",
        tier="E1")
MIA_ROWS = {  # row letter -> populated columns (from DS p9 Fig 2)
    "A": (1, 2, 3, 4, 5, 6, 7, 8, 9), "B": (1, 2, 8, 9),
    "C": (1, 3, 4, 5, 6, 7, 9), "D": (1, 2, 9), "E": (1, 2, 3, 4, 7, 9),
    "F": (1, 3, 4, 7, 9), "G": (1, 3, 4, 5, 6, 7, 9), "H": (1, 8, 9),
    "J": (1, 2, 3, 4, 5, 6, 7, 8, 9)}
for ri, (row, cols) in enumerate(MIA_ROWS.items()):
    for cnum in cols:
        fp.circle_pad(f"{row}{cnum}", -2.0 + (cnum - 1) * 0.5,
                      -2.0 + ri * 0.5, 0.27)
fp.body(4.5, 4.5)
fp.pin1_dot(-2.6, -2.0)
generated.append(fp.write())

# 15. TPS22916 YFP WCSP-4 — REAL ball map from TPS22916 DS SLVSDO5F p3
#     Fig 5-1/Table 5-1: A1 VOUT, A2 VIN, B1 GND, B2 ON; 0.78x0.78 body,
#     0.4 pitch. Top (marking) view: col 2 left / col 1 right, row B top.
balls = [("B2", 0, 0), ("B1", 1, 0), ("A2", 0, 1), ("A1", 1, 1)]
generated.append(ball_grid(
    "TPS22916_CSP4", "TI TPS22916 load switch, 4-ball WCSP (YFP)",
    "TPS22916 DS p3: A1 VOUT/A2 VIN/B1 GND/B2 ON; 0.78x0.78, 0.4 pitch",
    0.78, 0.78, 0.4, balls, 0.23, tier="E1"))

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

# 25. MLX90642 TO-39 — REAL pin circle from MLX90642 DS rev003 p31 Fig 34:
#     can Ø9.14 (cap Ø9.3), pins Ø0.45 (glass seal Ø1.12) on a Ø5.84 circle
#     in two 45°-spaced pairs; index tab between the SDA/SCL pair. Pin map
#     p4 Fig 1 (bottom view, tab up): SCL left / SDA right near tab, GND /
#     VDD opposite -> TOP view (tab up, -Y here): 1 SDA upper-left,
#     4 SCL upper-right, 2 VDD lower-left, 3 GND lower-right.
fp = FP("MLX90642_TO39", "Melexis MLX90642 32x24 FIR, TO-39 4-lead (45deg pairs)",
        "MLX90642 DS p31 Fig 34: pin circle O5.84, pins O0.45 in 45deg pairs, "
        "can O9.14/9.3; pin map p4 Fig 1", smd=False, tier="E1")
_r = 2.92
for num, ang in ((1, 112.5), (4, 67.5), (2, 247.5), (3, 292.5)):
    fp.circle_pad(num, _r * math.cos(math.radians(ang)),
                  -_r * math.sin(math.radians(ang)), 1.5,
                  kind="thru_hole", layers='"*.Cu" "*.Mask"', drill=0.8)
fp.fp_circle(0, 0, 4.65, "F.SilkS", 0.15)     # cap Ø9.3
fp.fp_circle(0, 0, 4.9, "F.CrtYd", 0.05)
# index tab marker (silk triangle-ish tick at tab position, -Y)
fp.items.append('  (fp_line (start -0.4 -4.65) (end 0.4 -4.65) '
                '(stroke (width 0.25) (type solid)) (layer "F.SilkS"))')
fp.pin1_dot(-1.6, -3.2)
generated.append(fp.write())

# 26. BQ25620 WQFN-18 "RYK" 2.5x3.0 — pins from SLUSEG2D p5 Fig 6-1; land
#     pattern approximated from the RYK0018A LAND PATTERN EXAMPLE (DS p86,
#     4226526/A): 22X 0.2-wide package pads -> 0.25-wide lands; left/right
#     signal rows at y = +0.85/+0.393/-0.007/-0.407/-0.85 (pins 1-5 left
#     top->bottom, 10-14 right bottom->top); bottom pads 6,7 (TS/QON) short,
#     8,9 (BAT/SYS) long power pads; top pads 18..15 (VBUS/PMID/SW/GND)
#     long power pads. HR pad shapes simplified to rectangles —
#     OVERLAY-VERIFY against TI drawing 4226526/A before fab.
fp = FP("BQ25620_WQFN18_RYK", "TI BQ25620 charger, WQFN-HR 18 (RYK) 2.5x3.0",
        "SLUSEG2D p85-86 RYK0018A land pattern example (HR pads approximated "
        "to rectangles)", tier="E1")
_ys = (0.85, 0.393, -0.007, -0.407, -0.85)
for i, y in enumerate(_ys):                    # pins 1-5, left, top->bottom
    fp.pad(i + 1, -1.2, -y, 0.4, 0.25)
for i, y in enumerate(_ys):                    # pins 10-14, right, bottom->top
    fp.pad(10 + i, 1.2, -_ys[len(_ys) - 1 - i], 0.4, 0.25)
fp.pad(6, -0.625, 0.8, 0.25, 0.7)              # TS
fp.pad(7, -0.225, 0.8, 0.25, 0.7)              # QON
fp.pad(8, 0.175, 0.625, 0.25, 1.05)            # BAT (long HR pad)
fp.pad(9, 0.575, 0.625, 0.25, 1.05)            # SYS (long HR pad)
fp.pad(15, 0.575, -0.57, 0.25, 1.14)           # GND (long)
fp.pad(16, 0.175, -0.57, 0.25, 1.14)           # SW (long)
fp.pad(17, -0.225, -0.57, 0.25, 1.14)          # PMID (long)
fp.pad(18, -0.625, -0.57, 0.25, 1.14)          # VBUS (long)
fp.body(2.5, 3.0)
fp.pin1_dot(-1.7, -0.85)
generated.append(fp.write())

if __name__ == "__main__":
    print(f"generated {len(generated)} footprints into {OUT}:")
    for g in generated:
        print(" ", g)
