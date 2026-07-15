# H3 report — rail ECOs, floorplan repack, board rebuild, routing

**Date started:** 2026-07-12 · Grows stage by stage (H3.0 rail ECOs →
H3.1 repack → H3.2 board rebuild → H3.3 routing).

## H3.0 — rail ECOs (1.8V IO architecture + flagged ECO-H3 items)

### H3.0-1 · 1.8V IO architecture decision

**Question:** can the shared sensor SPI bus (SPI1: VL53L8CH, A121, BNO086,
ADS131M04) run entirely at 1.8V from a 1.8V N657 VDDIO domain, eliminating
SPI level shifters?

**Answer: no — and the minimum-shifter architecture needs exactly one 4-bit
shifter.** The device-side voltages would allow an all-1.8V bus (VL53L8CH
IOVDD 1.2/1.8V-only; A121 VIO 1.8-or-3.3V; BNO086 VDDIO 1.7-3.6V; ADS131M04
DVDD accepts 1.8V), but the host side does not: on the VFBGA142 the SPI1
balls (PA5/PB4/PB5) and all four CS GPIOs live in the **VDD general-GPIO
supply domain** (DS14791 Table 18 fn1 — one OPT124 bit 17 / VDDIOVRSEL
setting for the whole domain). VDD could legally run at 1.8V (DS: 1.71-3.6V),
but it also supplies the BL54L15 UART/wake pins (sentinel is hard-wired to
the 3.3V AON rail — nRF54 VIH 0.7·VDD = 2.31V), both I2C buses (BME688 etc.
VIH 0.7·3.3V), SWD, and the EN/interlock fabric. Dragging all of that to
1.8V costs far more translators than it saves. The VFBGA142 bonds only two
other IO domains: VDDIO3 (1.8V, the XSPI PN port — no SPI/I2C AFs) and
VDDIO4 (3.3V, the SDMMC group consumed by the ESP32-C6, whose module IO is
3.3V). There is no relocation target for SPI1.

**Chosen architecture** (fewest translators, gating story intact):

| Item | Decision |
|---|---|
| SPI1 bus | stays 3.3V (BNO086, ADS131M04, A121-VIO side unchanged) |
| VL53L8CH SPI branch | **1× TXU0304** fixed-direction shifter (SCLK/MOSI/NCS ↓, MISO ↑); VCCB = gated 1V8_OPTICAL → B-port Hi-Z when the domain is off (doubles as bus isolation) |
| VL53L8CH INT/LPn | **no shifter** — moved to the N657's two spare **VDDIO3 (1.8V) PN-port balls**: INT_VL53 → PN7 (F14, ex XSPIM_P2_NCLK, unused with a single-ended NOR), LPN_VL53 → PN12 (K14, ex XSPIM_P2_NCS2). PE8/PG10 returned to the spare pool. PN7 is boot-ROM-touched (Table 18 fn7) but only as an XSPI clock output against our open-drain INT + 47k pullup while OPTICAL is off at boot — benign. INT pullup → 1V8_OPTICAL; LPn gets a 100k pulldown (defined-low until PN12 is configured). |
| TCS3448 I2C (1.8V-only SCL/SDA) | **1× PCA9306** segment of I2C-A (see H3.0-3) |
| A121 | VIO stays 3.3V (3V3_RADAR) → SPI/INT/ENABLE stay direct; only VDIG/VRX/VTX move to 1V8_RADAR |
| N657 OPT124/VRSEL fw config | VDD=3.3V (bit 17), VDDIO3=1.8V (bit 15), VDDIO4=3.3V (bit 14) — recorded in lib_parts.py |

Total translator count: **2 small ICs** (TXU0304 TSSOP-14, PCA9306 VSSOP-8)
versus ≥4 for an all-1.8V SPI1 (UART + I2C-A + I2C-B + EN fabric shifting).

**Real bug found while executing:** the VL53L8CH model had **no CORE_1V8
pin** — DS14310 §3.3 p11 requires all THREE supplies (AVDD 3.3V, CORE_1V8
1.8V, IOVDD 1.2/1.8V) or the device stays in reset; and the old wiring fed
IOVDD from 3.3V, over its 1.2/1.8V-only rating. Fixed: CORE_1V8 pin added,
IOVDD+CORE_1V8 → 1V8_OPTICAL (DS explicitly allows sharing when IOVDD=1.8V;
supplies may come up in any order, so the 3.3/1.8 gated pair needs no
sequencer).

### H3.0-2 · Gated 1.8V sub-rails

Three TPS22916 load switches added off the 1V8 rail, driven by the SAME
EN_* nets as their 3.3V siblings (AI-decides-what-runs invariant holds at
both voltage levels):

| Rail | Loads | EN |
|---|---|---|
| 1V8_OPTICAL | VL53L8CH IOVDD+CORE_1V8, TCS3448 VDD+GPIO strap, PCA9306 VREF1, TXU0304 VCCB | EN_OPTICAL |
| 1V8_RADAR | A121 VDIG/VRX/VTX bundle | EN_RADAR |
| 1V8_AIR | ENS161 VDD (core) | EN_AIR |

Side benefit: ENS161 core+VDDIO now rise/fall together (closes the H2
power-sequencing note — its core used to sit on the raw EN_N6-gated 1V8
while VDDIO was AIR-gated). **MAX30102 exception (deliberate):** its VDD
stays on the raw 1V8 rail — with VLED_P hard-gated the part can neither
emit nor sense, shutdown draw is ~0.7 µA, and the DS tolerates any supply
order; a fourth switch buys nothing (documented in sensors_i2c.py).

Power budget: 3× TPS22916 ≈ 2 µA IQ each when on, ~10 nA off; PCA9306 ≈ 0,
TXU0304 static ≈ 1 µA — total adder <7 µA, below the 10 µA resolution of
the budget model (`misc/regs` line unchanged; noted in docs/power-budget.md
regen at H3.1).

### H3.0-3 · TCS3448 1.8V I2C segment

**Chosen: PCA9306 pass-FET translator on I2C-A** (not a 1.8V I2C controller
domain). Reasons: (a) the VFBGA142 bonds no I2C on any 1.8V-capable ball
group — I2C1 is absent, I2C2/I2C4 balls are in the 3.3V VDD domain, and the
only 1.8V domain (VDDIO3 = PN port) has no I2C AF; (b) the address table
forces I2C-A membership — TCS3448 is fixed 0x59, which collides with SGP41
(fixed 0x59) on I2C-B (the exact reason it moved to I2C-A at H2.5). Wiring:
VREF1 → 1V8_OPTICAL, segment pullups 2×2.2k → 1V8_OPTICAL (Fm+ capable),
EN+VREF2 node driven by **EN_OPTICAL** with 200k to 3V3_SYS (PCA9306
switched-EN application) — the dead 1.8V segment is isolated from the live
3.3V bus whenever the OPTICAL domain is gated off. TCS3448 INT stays on the
3.3V side unshifted (3.6V-tolerant per DS001121 p9; N657 PF7 needs 3.3V VIH).

### H3.0-4 · IQS7222A touch flex (ratified)

v1 flex = **9 self-cap electrodes** (QFN20 exposes only CRx0-7+CTx8):
dish ring 2, rim slider 3, side-squeeze 2 (one per wall — "squeeze both
walls" gesture unchanged), back ECG-return/grip 1, reserve 1; dropped = 2nd
reserve pair + per-wall squeeze redundancy (3 of 12 zones). Flex connector
keeps 13 positions, E9-E11 grounded as guards → a v1.1 **mutual-cap Rx/Tx
matrix flex** restores >12 zones on the same connector with artwork+firmware
only. Recorded in docs/user-experience.md + accessory.py.

### H3.0-5 · VD66GY camera module rails (ratified)

The camera **module carries local 2.8V (VANA) and 1.15V (VCORE) LDOs** on
its flex; J_CAM stays 3V3_OPTICAL + 1V8 + 2-lane CSI + CCI, and reserved
pins 19-24 stay reserved (not repurposed as rail feeds). DNP in v1.
Recorded in sensors_misc.py.

### H3.0-6 · Other ECO-H3 grep results

- gen_footprints.py BL54L15/A121 keep-out notes and the SGX-4CO gas_b
  envelope note → floorplan items, executed at **H3.1** below.
- Observed gap (flagged, NOT executed — not an ECO-H3 tag): the UX spec
  asks for BNO086 INT routed to BOTH N657 and sentinel (motion wake from
  ambient), but the BL54L15's 39 pads are fully allocated; the only
  candidates are the NFC pads (P1.02/P1.03, NC in v1). Owner call for
  H3.2 whether pad 15 (P1.02) becomes BNO_INT_IN — zero-cost on the flex
  side, costs the v1.1 NFC option.

**H3.0 gate:** ERC **0 errors / 0 warnings**, netlist regenerated
(387 parts, 229 nets), tests 19/19 (see commit).

New nets: 1V8_OPTICAL, 1V8_RADAR, 1V8_AIR, I2CA_SDA_1V8, I2CA_SCL_1V8,
VL53_{SCLK,MOSI,NCS,MISO}_1V8. New parts: U_SW1V8_{OPTICAL,RADAR,AIR}
(TPS22916), U_LS_VL53 (TXU0304, **pinout E0** — DS not staged, see
docs/MISSING_VENDOR_ASSETS.md), U_XLAT_TCS (PCA9306, **pinout E0** — DS not
staged), + pullups/pulldown/decoupling.

## H3.1 — floorplan repack with real E1 envelopes

Pack result: `python3 boards/v1/design_v1.py` → **OK, 41 parts, zero
collisions, full bean-polygon containment** (bean 67.9×39.9 bbox, 2065 mm²).
Regenerated: components.json, floorplan_top/bottom.svg, envelope.json,
docs/power-budget.md.

### Envelope updates applied (E0 guess → E1 datasheet)

| Part | was | now | consequence |
|---|---|---|---|
| SGX-4CO | 14×14, z 4.0 | **17×17** (13.5 PCD ring + Ø1.7 socket drills + courtyard), **z 18.0** (16.5 can + ~1.5 socket standoff) | gas_b zone grown to 18.5×17.2; the Ø20 can stays fully ON-board at this position (no edge overhang needed). **NEW MECHANICAL FLAG** below. |
| AS7421 | 3.5×3.5 | **6.6×6.0** (OLGA10, DS000667 p45) | optical2 row rebuilt (now 23.6 wide) |
| BL54L15 | 14×10 "antenna long-edge at rim" | **10×14, antenna END at rim** — EZ-DS v1.9 Fig 11: the 5.0×8.5 keep-out sits at the pin-1 END across the 10 mm width, so the module's long axis must be perpendicular to the board edge, antenna end outboard | radio_ble zone reshaped to 11.6×14.8 at the +y smooth rim (x 25.0-36.6, the bean's widest arc). Keep-out ≥15 mm extension = off-board air; on-board keep-out lies under the module's own antenna end — no other part in it (collision check) and **no copper pour there at H3.3** (rule recorded here + in the footprint). Module top edge packs 0.8 mm (GAP) inboard — H3.2 slides it flush onto the edge. |
| BQ25620 | 2.5×3.0 ✓ | (already WQFN-18 RYK since H2.5) | — |
| MLX90632 | 3×3 ✓ SFN5 | — | — |
| MLX90642 | 9.6×9.6 ✓ (TO-39 Ø5.84 pin circle E1 from H2.5) | — | — |
| MIA-M10Q | 4.5×4.5 ✓ | note updated: SR4G013 GNSS antenna keep-out at the fat-notch edge (IM UBX-21028173) — antenna is a supporting part placed at H3.2, corner reserved |

### New parts placed (H3.0 adds)

- **48 MHz HSE crystal** (3225) — compute zone, packed directly right of the
  N657 (0.8 mm gap; PH0/PH1 = balls A7/B7 — orient at H3.2).
- **3× TPS22916 1V8 sub-rail switches** — folded into the power-row strip:
  "Load switches x7" → **"Load switches x10"** (9.5 → 13.6 mm strip).
- **TXU0304** (TSSOP-14, 6.4×5.4 courtyard) — optical zone, row below the
  FIR/cam row, near the VL53L8CH branch it shifts.
- **PCA9306** (VSSOP-8, 3.1×2.4) — optical2 row, beside the TCS3448 segment.

components.json parts 38 → **41**; manifest 41/41 (23 harvested + 5 E0 +
13 E1 generated); contract test snapshot updated 38→41 and extended with the
H3.0 refdes (U_SW1V8_*, U_LS_VL53, U_XLAT_TCS, X_HSE) + 1V8 sub-rail nets.

### Zone deltas

gas_b 16×15.5 → 18.5×17.2 (+63 mm²); optical 28×10.6 → 28×16.2 (absorbs the
TXU row; overlaps rad_top zone RECT but not its parts); optical2 17×4.3 →
23.6×6.4 (AS7421 + PCA9306); radio_ble 15.5×10.5 → 11.6×14.8 rotated to the
rim; compute 20×9.3 → 22.5×8.8 (single row N657+crystal+NOR, dropped below
the BL54); power 20.5×10 → 22×8.2 two-row layout; io shifted to
(8.0,4.2,13.5,5.8). Top/bottom faces both still pack with 0.8 mm courtyard
gaps everywhere (collision check global, eps 0.02).

### Pack stats / power budget

- Part-envelope area: top 602 mm², bottom 921 mm² over 2×2065 mm² faces
  → **37 % gross envelope utilization** (was ~29 % pre-H3.1; the SGX ring
  +63 mm², AS7421 +27 mm² and the three new ICs drive the growth).
  Passives/TPs/routing absorb the rest — H2 stage-2 already measured the
  passive-placement debt.
- Power budget regenerated: ambient **21.6 mA → 56 h** (8 h target cleared
  ~7×), interrogation **457 mA → 2.6 h** — unchanged; the H3.0 adders
  (3× TPS22916 + PCA9306 + TXU0304, <7 µA) are below model resolution and
  noted in docs/power-budget.md.

### NEW MECHANICAL FLAG (owner + enclosure): SGX-4CO height

envelope.json stack is now honest and reads **26.1 mm** (1.6 board + 6.5
SCD41 top + **18.0 SGX bottom**) against the 19 mm interior target — the H2
value (12.1 mm) was carrying the stale 4.0 mm cell-height guess. DS-0138:
can Ø20 × **16.50** + 3.9 mm pins; with socket receptacles the body sits
~18 mm proud of the board. Even alone, 1.6 + 18.0 = 19.6 mm > 19 mm. The
cell CANNOT stand inside the pebble unless the enclosure gives it a local
pocket/dome in the bottom-fat-lobe gas cavity (the vent area already has no
top-face parts opposite: contact/optical zones sit off its x-span — local
opposing stack is board + cell only). Enclosure owner actions (pick one at
H3.2): (a) local interior pocket ≥18 mm at gas_b (bulge into the 1.6 mm
wall/1.9 mm clearance budget), (b) right-angle socket adapter laying the
can down (costs ~Ø20×17 of adjacent board area), or (c) low-profile CO cell
substitution (breaks the ratified SGX-4CO pick). Flagged, not resolved here.

## H3.2 — board rebuilt placement-true, all pads net-bound

**Gate results:** `build_board.py` → 400 footprints placed, **fixed-packed=66
(55 floorplan slots), anchor-spiral=334, overlap-fallback=0 (hard build
gate)**; pads **bound=1379 / declared-NC=192 / unnumbered mech-paste=34**,
netlist pins covered **1362/1362** (zero lost, zero undeclared-unbound —
both hard gates; ledger = `boards/v1/netlist/nc_pins.json`, generated by
`circuit/main.py`, every entry justified at the model). ERC 0/0; 19/19
tests; DRC baseline: **0 footprint errors, 0 courtyard overlaps, 0
clearance, 0 malformed pads; unconnected = 499 (honest pre-route
ratsnest)**; waived: 4× hole_clearance inside the official GCT USB4105
footprint (its own NPTH pegs vs our 0.25 rule); known-open: 47×
items_not_allowed from the Espressif C6 footprint's all-layer antenna
keep-out vs the ratified taper floorplan (ECO-H3.2-E, owner call); silk
noise 735 items counted, deferred to H4.

### What the zero-overlap gate surfaced (all fixed in design_v1.py)

1. **The mechanical set had NO floorplan slots at all** (H2 grid-placed
   them into overlaps). New MECH auto-slot stage packs 14 more parts:
   USB-C, GNSS antenna, pogo field, touch ZIF, U.FL, 3× ECG lands, piezo
   lands, battery conn, 2× SWD, LRA pads, fan conn — deterministic spiral
   placement with 0.4mm gaps (their envelopes are true courtyard extents)
   and per-through-feature other-face checks.
2. **Every H2 envelope was body-sized, not courtyard-sized** (audited via
   pcbnew): e.g. DRV2605L 3×3 body vs 6.4×3.6 courtyard-with-leads,
   IQS/ADS 3×3 vs 4.3×4.3, CYPD 4×4 vs 5.3×5.3, gauge 1.6² vs 3.7².
   All 41 envelopes replaced by audited extents; GAP 0.8 → 0.5 (now a true
   courtyard-to-courtyard margin). Zones reshaped: contact split
   (ppg/contact — the SGX through-pad annulus lands mid-lobe), air split
   (column + SCD island + BMV shelf — the USB through-features own the
   face behind the old air block), MLX90632 → own taper window (fir2),
   DRV2605L → top notch, MIA-M10Q → dedicated RF-corner zone, load
   switches → own strip, camera slot = the real 18.4mm FH12-24 connector
   (VL53 moved to the TXU row).
3. **Capacity ECOs (owner ratify, all electrically transparent):**
   ECO-H3.2-A: ECG electrodes → 4mm board LANDS + shell electrodes
   (elastomer/spring through the 3.5mm wall — direct skin contact was
   never physical); pogo → 2×3 landing field, ADR-0002 mag-ring geometry
   moves to the shell; ECO-H3.2-B: **USB-C sits mid-back** (35.9–46.6,
   25.1–34.1 bot) — the notch edge belongs to the power zone; enclosure
   needs a USB tunnel or H4 relocation; ECO-H3.2-C: J_RF SMA → U.FL +
   shell pigtail; J_TOUCH → 0.3mm Molex 503566 ZIF (same P/N as BMV080);
   ECO-H3.2-D: TC2030 ×2 → plain 1.27mm SWD pad rows (NPTH locating holes
   had no both-face-clear window); piezo disc mounts shell-side onto
   compact lands; testpoints 1.0 → 0.7mm.
4. **Cross-face honesty:** TH/NPTH pads now block BOTH occupancy grids;
   U_CO receptacle marks derive from the real (flipped) pad positions;
   footprints are placed by COURTYARD CENTER (connector origins are not
   their courtyard centers); fixed slots auto-rotate to match slot aspect
   (U_MAX OLGA-14 was 90° off in H2).
5. **Under-can/shield reclaims:** the SGX cell plugs onto ≥1.5mm PSB
   receptacles → the Ø20.9 under-can region accepts 0402/0603 dust
   (low-profile mask); the radiation shield interior accepts only
   radiation-front-end nets. NOTE: the N657's left ~1.2mm slips under the
   SGX can RIM (1.2mm part vs ≥1.5mm standoff) — flagged for the
   receptacle-height check at H4.

### Board setup

6-layer (JLCPCB 6L through-via + POFV), default netclass 0.1/0.1, edge
clearance 0.2, min track/clearance floor 0.09 (BGA fanout). Netclasses
seeded in the **committed** `interrogator_v1.kicad_pro` (checked: CI's eda
glob does not reach boards/v1/board/): PWR (0.25 track), USB_HS (90Ω diff
placeholder 0.13/0.15), CSI (100Ω placeholder 0.11/0.15), RF (50Ω
placeholder 0.3), BGA_FANOUT 0.09/0.09 + pattern assignments; the
VFBGA142 area rule lives in `interrogator_v1.kicad_dru`. Diff geometry is
a PLACEHOLDER until the H3.3 impedance calc against the ratified stack.

BL54L15 flush on the +y rim (design_v1 `flush_bl54`, containment exemption
on its rim edge; rotation auto-selected so the antenna keep-out points
off-board); MIA-M10Q at its RF corner with AE_GNSS on the top arc rim;
SGX fully on-board (H3.1 analysis stands — coordinator's "can overhang"
allowance not needed).

Renders: `board_top.svg` / `board_bottom.svg`. DRC: `drc_baseline.{json,rpt}`.

## H3.1R — board-first minimal floorplan (ADR-0004: bean containment removed)

**Pivot (2026-07-15, owner):** the Product-Stone bean is no longer a hard
board boundary. Every H2/H3 placement + routing crisis (courtyard overflow,
33-part spill, the USB-C enclosure tunnel, and the H3.3 routing stall at
XSPI 9/11 + partial diff pairs) traced to cramming the board into the
67.9x39.9 bean, whose curved edges have no straight routing channels. The
PCB outline is now an OUTPUT of minimum-area packing; chassis is derived
downstream. Recorded in **ADR-0004** (supersedes the board-containment
aspect of ADR-0003).

`design_v1.py` rewritten board-first:
- FFDH shelf-pack of the real footprint courtyards (41 majors + 14 mech)
  per face; interior width swept for the minimum shared board (aspect <=1.55).
  Per-face FFDH => **zero same-face courtyard overlap by construction**.
- Board interior = packed core + 2.6 mm passive/route ring; outline = a
  rounded rectangle (R=2, 68 pts) written to `outline.json` (DERIVED,
  replaces the bean).
- Edge-critical parts carry an `EDGE:{S,N,W,E}` tag (USB-C short edge,
  BL54/ESP32/MIA RF edges, SGX inlet, SMA/pogo/battery) flowed to
  build_board for flush-to-edge so RF keep-outs extend off-board.

**Derived board: 47.7 x 44.7 mm = 2129 mm2** (103% of the 2065 bean by
area, but fully rectangular). All 55 rectangles pack collision-free,
containment-clean, **zero spills**. Stack 26.1 mm (unchanged — SGX height
flag stands). Power budget unchanged (ambient 21.6 mA -> 56 h, interrogate
457 mA -> 2.6 h). The win is routability (straight channels every layer,
no enclosure tunnels), not raw area — the part set genuinely needs
~2000 mm2/face, which the bean also gave but un-routably.

Battery is a mating/stacked part (LP503450-class 50x34x5.2 mm via J_BATT) —
excluded from board area, noted in `envelope.json`.

## H3.2R — board rebuilt placement-true on the liberated floorplan

`build_board.py` generalized off the hardcoded 68x40 bean grid to the
derived outline bbox (occupancy grid + spiral offsets now sized from
`outline.length_mm x width_mm`), then run on the ADR-0004 rectangle.

**Placement:** 66 fixed-packed (41 majors + 14 mech + co-placed refs) at
their components.json slots; 334 anchor-driven spiral (weighted-neighbour
centroid, 0/90 rotation, dust-under-SGX + shield-interior masks honored);
**overlap-fallback = 0 (hard-gated — a spill EXITS 1)**. Faces: 191 top /
209 bot.

**Pad binding (hard gate):** bound **1362 / 1362** netlist pins (= the full
pin count); 192 declared-NC (nc_pins.json ledger, each justified at the
model); 34 unnumbered mech/paste pads (NPTH + EP apertures). Zero
undeclared unbound pads, zero netlist pins without a pad.

**Board setup:** 6-layer (JLCPCB 6L through-via + POFV), default 0.1/0.1,
edge clearance 0.2, min track/clearance floor 0.09; net classes (PWR / USB_HS
90R / CSI 100R / RF 50R / BGA_FANOUT 0.09) + patterns seeded in the committed
`.kicad_pro`; VFBGA142 area rule in `.kicad_dru` (carried from H3.3a).

**DRC baseline** (`drc_baseline.{json,rpt}`, pcbnew WriteDRCReport):

| category | count | note |
|---|---|---|
| **Footprint errors** | **0** | acceptance |
| courtyard overlaps | **0** | per-face FFDH + spiral hard-gate |
| malformed-pad errors | **0** | |
| unconnected pads (ratsnest) | **499** | honest pre-route baseline (record) |
| silk (overlap/over-copper/lib/text) | 697 | silk noise, OK to remain |
| clearance | 15 | pad-pad <0.1 in dense spiral corners (pre-route) |
| solder_mask_bridge | 10 | adjacent fine-pitch mask slivers |
| silk_edge_clearance | 22 | ref-des silk near the rim |
| hole_clearance | 6 | connector NPTH vs opposite-face dust |
| items_not_allowed | 17 | courtyard/pad near Edge.Cuts on the tight rim |

Renders: `board_top.svg` / `board_bottom.svg`.

**Follow-up before routing (H3.3R):** the 5 EDGE-tagged parts (USB-C→S,
BL54→N, ESP32→E, MIA→corner, AE_GNSS→N) are placed at their packed core
slots, not yet flushed to the rim — trivial to finalize on the rectangle
(vs the bean) so the RF keep-outs sit off-board. The ~38 non-silk geometry
violations are the dense-baseline residue the router pass will clear/relieve.
Gate: circuit ERC 0/0, contract tests 19/19 (unchanged).
