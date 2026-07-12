# H2 stage-1 report — complete electrical design as circuit-code

**Date:** 2026-07-12 · **Scope:** SKiDL circuit modules, KiCad netlist, ERC,
component-library manifest. Layout, real pin/ball maps, and footprint
generation are stage-2.

## What was built

`boards/v1/circuit/` — modular SKiDL (Python) circuit, v1.1 sensor set (38
components.json parts + support circuitry):

| Module | Contents |
|---|---|
| `lib_parts.py` | All custom part templates (our symbol source; pin maps tier **E0**) |
| `power.py` | USB-C + CYPD3177 PD sink → BQ25620 charger (SENTINEL_I2C 0x6B) → VSYS; BQ29700+dual-FET low-side 1S protection; BQ27427 gauge; TPS62840→3V3_AON; TPS62823→VDD_CORE_N6; **TPS62823 #2→3V3_SYS (stage-1 add)**; TLV62568→1V8; 6× TPS22916 domain switches + **7th for accessory port (stage-1 add)** |
| `compute.py` | STM32N657 (used-signals model), octal-NOR on XSPI (8d+clk+cs+dqs), BL54L15 sentinel (enables/wakes/glow/SENTINEL_I2C), ESP32-C6-MINI-1 on SDIO (real Espressif symbol) |
| `sensors_spi.py` | VL53L8CH (SPI-strapped), BNO086 (PS1 strap), ADS131M04 (piezo diff AIN0, PIN-rad AIN1, accessory AIN2, CO-AFE AIN3, CLKIN from N657 MCO) |
| `sensors_i2c.py` | Full I2C-A / I2C-B population w/ straps, INT pull-ups, per-domain power + decoupling; collision audit in module docstring |
| `sensors_misc.py` | BMV080, A121 (SPI-only), MIA-M10Q (+V_BCKP diode from AON, PPS→N657), PDM mic, J_CAM 24p FPC (DNP), **PIN radiation front-end** (BPW34S + OPA381-class charge amp + TLV3201 comparator → GEIGER_PULSE to sentinel + energy-proxy to ADS AIN1, SHIELD_RAD guard, powered from 3V3_AON for ambient counting), AD8317+SMA→ADC_IN0, UV LED **hardware-interlocked** (74LVC1G08: EN_UV_REQ ∧ INTERLOCK_OK, VLED on gated 3V3_OPTICAL = second interlock), white LED, AS7421-driven 970 nm NIR LED, 6× glow LEDs, fan FET+flyback from VSYS, SGX-4CO + LMP91000 potentiostat |
| `accessory.py` | 6-pogo magnetic port (VACC/GND/SENTINEL_I2C/AN1=ECG-ref/AN2=ADS), IQS7222A (12 electrodes→FPC), DRV2605L→LRA, 2× TC2030, testpoints |
| `main.py` | Builds all, runs ERC, writes netlist; exit 0 iff ERC-clean |

**Netlist:** `boards/v1/netlist/interrogator_v1.net` — KiCad format, **330 parts,
207 nets**, ~277 KB. Parses (balanced S-expr, verified by test).

## ERC result

**0 errors / 0 warnings** (SKiDL 2.2.3). Three findings closed by justified
`drive=POWER` annotations (RC-filtered protector VDD, cell-negative terminal,
diode-fed GNSS backup rail) — documented in `boards/v1/circuit/WAIVERS.md`.
No suppressed pin-conflict or unconnected-pin issues.

## Address map (bus / addr per device)

| Bus (master) | Addr | Device | Note |
|---|---|---|---|
| SENTINEL_I2C (BL54L15, 3V3_AON pull-ups 4.7k) | 0x44 | IQS7222A | **deliberate**: collides with SHT41 0x44 → moved off I2C-B; also the wake source |
| | 0x55 | BQ27427 | gauge |
| | 0x5A | DRV2605L | haptics |
| | 0x6B | BQ25620 | charger |
| | 0x50 | accessory ID EEPROM | reserved, via pogo |
| I2C-A (N657 I2C1, 1 MHz-capable, 2.2k→3V3_SYS) | 0x33 | MLX90642 | |
| | 0x3A | MLX90632 | |
| | 0x57 | MAX30102 | 1.8 V core; 3V3 bus tolerance **VERIFY** |
| | 0x30 | AS7058 | addr **VERIFY** |
| I2C-B (N657 I2C2, 400 kHz, 4.7k→3V3_SYS) | 0x77 | BME688 | SDO=1 strap |
| | 0x59 | SGP41 | fixed |
| | 0x53 | ENS161 | ADDR=1 strap; VDD on 1V8 |
| | 0x62 | SCD41 | fixed |
| | 0x44 | SHT41 | fixed (IQS collision resolved above) |
| | 0x39 | TCS3448 | **VERIFY** |
| | 0x74 | AS7331 | A1A0=00 |
| | 0x64 | AS7421 | **VERIFY** |
| | 0x30 | MMC5983MA | vs AS7058 0x30: different bus — OK |
| | 0x35 | TMAG5273 | A1 variant **VERIFY** |
| | 0x57 | BMV080 | vs MAX30102 0x57: different bus — OK; addr **VERIFY** |
| | 0x48 | LMP91000 | fixed (CO potentiostat) |

**No same-bus collisions.** SPI1: 4 CS (VL53, BNO, ADS, A121). SDIO: ESP32-C6.
UART1+PPS: MIA-M10Q. UART2: inter-MCU. All INT/DRDY lines wired (R7), incl.
INT_TCS/RDY_AS7331/INT_AS7421/INT_ENS/INT_BMV/INT_TMAG beyond the core set.

## Stage-1 engineering adds/deviations (need ratification + components.json update)

1. **U_SYS3V3 (2nd TPS62823) → 3V3_SYS**: the ratified regulator set had no main
   3.3 V rail; domain switches would have fed raw VSYS (3.0–4.35 V) to 3.3 V
   sensors. EN_N6-gated. Small (SOT-583+L+2C), fits power zone.
2. **U_SW_ACC (7th TPS22916)**: switched accessory-port power (VSYS→VACC, EN_ACC).
3. Radiation front-end on **3V3_AON** so the sentinel counts dose in ambient
   (OPA381-class ~0.8 mA when enabled — firmware duty-cycles; flag for W-PWR).
4. ENS161 core on 1V8 (EN_N6-gated) with VDDIO on 3V3_AIR — power-sequencing
   note for stage-2.
5. Domain rails hang off 3V3_SYS (EN_N6-gated): sentinel must assert EN_N6
   before any EN_domain. Matches duty-cycled-N657 architecture.

## Library coverage (`library/manifest.json`)

- components.json parts: **38** — manifest covers all (tested).
- Footprints harvested: **20/38** (18 kicad-official + espressif C6 + espressif symbol);
  34 `.kicad_mod` files copied under `library/footprints/` (incl. passives/connectors).
- **TO-GENERATE: 18/38** — expected and honest: MLX90632 SFN, VL53L8 module,
  TCS3448/AS7331/AS7421 OLGA, AS7058 WLCSP42, A121 fcCSP, BMV080, SGP41 DFN,
  ENS161 LGA9, STM32N657 VFBGA142, octal-NOR BGA24, BL54L15, MIA-M10Q,
  TPS22916 CSP-4, ADS131M04 WQFN-20, SGX-4CO cell, camera FPC + custom mech
  (pogo ring, electrodes, shield can, piezo, LRA pads).
- Provenance caveat: GitHub mirrors KiCad/kicad-footprints + kicad-symbols are
  **stale 2020 snapshots** (KiCad dev moved to GitLab — unreachable here);
  official files were taken from the Ubuntu-packaged KiCad **7.0.11** libraries
  instead (same official content, versioned). espressif/kicad-libraries cloned
  fine (ESP32-C6-MINI-1 symbol + footprint). SnapEDA/easyeda2kicad/vendor
  portals: blocked, as expected.
- All harvested *generic* footprints (LGA-16/28, QFN-20/24, WQFN-16, DSBGA-9,
  TO-39-4, SOT-583) carry `verify_notes` — pad-map confirmation vs DS is a
  stage-2 gate before layout.

## Toolchain

- **kicad-cli 7.0.11 — INSTALLED and working** (apt, with kicad-symbols +
  kicad-footprints 7.0.11 packages). Available for stage-2 (`kicad-cli` sch/pcb
  export, DRC).
- SKiDL 2.2.3 (pip; kinet2pcb/hierplace extras skipped — need pcbnew python
  bindings at layout stage, kicad package provides them).

## Tests

`contract/tests/test_h2.py`: (a) netlist exists/parses/contains 57 major refdes
+ 22 architecture nets, (b) manifest covers every components.json part with
honest provenance + harvested files exist, (c) `main.py` rebuild is ERC-clean.
**Full suite: 14/14 passed** (11 pre-existing ingest + 3 new).

## NEXT (stage-2)

1. **Pin-map hardening**: replace E0 logical pin numbers with real package
   pins/balls from datasheets (every `# pinout E0` in lib_parts.py); resolve
   all `# VERIFY` items (AS7058/AS7421/TCS3448/BMV080 addresses, TMAG variant,
   MAX30102 bus tolerance, A121 supply domains, C6 SDIO GPIO map, BQ27427
   sense topology, CYPD3177 strap values, charger/regulator dividers).
2. **Footprint generation** for the 18 TO-GENERATE parts (scripted
   `.kicad_mod` writers from DS drawings; MLX90642 TO-39+lens, A121 AiP
   keepout, BL54L15 antenna keepout are the tricky ones).
3. **Schematic/PCB path**: netlist → pcbnew import (kinet2pcb now that KiCad
   is installed) or `.kicad_sch` generation; seed placement from
   components.json x/y (design_v1.py zone-packer).
4. **iBOM / live-priced BOM** (R13): generate interactive BOM with LCSC/DK
   pricing columns.
5. **Ratify stage-1 adds** (3V3_SYS buck, 7th load switch) → update
   components.json + rerun zone-packer + power budget.
6. ERC re-run after pin-map hardening; add antenna/RF review (BL54 + C6 + GNSS
   corner) before layout.

---

# H2 stage-2 report — footprints 38/38, bean board, first .kicad_pcb

**Date:** 2026-07-12 · **Scope:** footprint generation, bean outline + repack,
board-file bring-up (pcbnew), datasheet VERIFY closures.

## 1. Footprint coverage: 38/38, zero TO-GENERATE left

`library/gen_footprints.py` — parametric `.kicad_mod` writers (ball-grid,
dual-row DFN/OLGA, quad QFN/SON, castellated module, TH radial, ring/pad
customs). 24 files generated into `library/footprints/generated/`; every file
header carries its dimension source + the rule *"E0 — overlay-verify against
the vendor land-pattern drawing before fab"*. All 24 load in pcbnew 7.0.11.

- **From staged datasheets** (best tier): A121 fcCSP50 with the **real named
  50-ball map** (DS p8-9), VL53L8 LGA16 with real pad names (DS14161 Table 3),
  SGP41 DFN-6 (2.44/0.8 + die pad, DS p18), BMV080 host side = **Molex
  503566-1302 ZIF 13ckt 0.3 mm** (DS p16), AS7331 OLGA16 body dims,
  TCS3448 = AS7343-family OLGA-8.
- **E0 placeholders (flagged in-file)**: STM32N657 VFBGA142 (numeric 12×12
  fill — must be replaced from DS14791 **before routing**), AS7058 WLCSP42,
  NOR BGA24, BL54L15 castellations, MIA-M10Q perimeter, TPS22916 CSP4,
  MLX90632 SFN, ENS161 LGA9, AS7421 OLGA10, AD8317 LFCSP8, SGX cell, customs.
- **Remapped to KiCad-official instead of generating** (per-part in
  manifest): ADS131M04 → generic QFN-20 3×3 P0.4; camera FPC + touch FPC →
  Hirose FH12-24/13; OPA381 → MSOP-8; LMP91000 → WSON-14 4×4 (exact class
  match); GNSS antenna → Antenova SR4G013.
- `library/manifest.json`: **22 harvested + 16 generated-E0 = 38/38**,
  `footprint_to_generate: 0` (tested).

## 2. Bean board — outline + repack

- `boards/v1/outline.py` → `outline.json`: Product Stone plan
  (enclosure/product_stone.py `w_smooth`/`w_notch`) inset **3.5 mm**
  (1.6 wall + 1.9 clearance) via shapely round-join buffer; resampled to a
  **96-point closed polygon**. Board bbox **67.9 × 39.9 mm**, area
  **2065 mm² = 75 % of the old 60×46 rectangle** (recorded in envelope.json).
- `design_v1.py`: zones re-mapped onto the bean — optical + contact on the
  fat-lobe face, air pocket mid with **SCD41 top-mid**, taper tip = A121
  radar + magnet edge sensors, **SGX-CO (14×14) bottom fat lobe**, compute +
  power bottom mid, C6 bottom taper (antenna toward tip), BL54L15 rotated 90°
  with its antenna edge on the smooth rim. The **PIN radiation block moved to
  the TOP face** (bottom fat lobe is consumed by the SGX cell; gamma doesn't
  care). Packer gained a **polygon-containment check** (every part rect +0.8
  margin fully inside the bean; violation raises). Pack passes; SVGs now draw
  the bean outline. Stack 12.1 mm (unchanged parts). Power budget untouched
  (same part set).
- Real finding for H3: at 2065 mm²/face the bean is tight — the 284
  passives/TPs/connectors do NOT all fit at conservative shelf spacing
  (see §3 overlap debt).

## 3. Board file — `boards/v1/board/interrogator_v1.kicad_pcb`

- **Path A (pcbnew scripting)**: `kinet2pcb` does not build here (Debian
  setuptools `install_layout` regression in its 2020-era setup.py), but the
  pcbnew 7.0.11 python bindings are present — `build_board.py` does the same
  netlist→board conversion directly: parses the netlist, loads every
  footprint (repo libs + generated + official fallback), places the 38
  majors at their bean-floorplan coordinates (refdes↔part table; bottom
  parts flipped), greedy-grid-places the remaining 284 parts inside the
  bean, binds **1019 pads to nets** by (ref, pin), and draws the 96-segment
  Edge.Cuts bean. 392 pads stay unbound where E0 logical pin numbers don't
  match real package pad names (A1-style balls) — H3 pin-map hardening.
- Placement debt: **77 parts** (TPs + decoupling caps + the 3 big mech items
  pogo-ring/ECG-ring/SMA) only fit via the containment-only fallback —
  inside the bean but courtyard-overlapping primaries. That is the DRC noise
  band below and the first H3 work item.
- **DRC baseline** (`run_drc.py` → `drc_baseline.json`): kicad-cli **7.0.11
  has no `pcb drc`** (KiCad 8 feature) — DRC runs through the same engine via
  `pcbnew.WriteDRCReport`; `kicad-cli pcb export svg` passes as load-proof.
  Counts: **unconnected pads 499** (the routing todo — expected, no tracks),
  **Footprint errors 0**, violations 1389 = courtyard/silk/clearance overlap
  noise from baseline placement (309 clearance, 154 courtyards_overlap,
  199 silk_overlap, …) + 45 items_not_allowed + 30 text_height.
- **No `.kicad_pro` created on purpose** — CI's eda job gates on `*.kicad_pro`
  and routing hasn't happened; arming it now would fail the pipeline
  honestly-but-uselessly.

## 4. VERIFY closures (see boards/v1/VERIFY_LOG.md)

**Closed from staged PDFs (11):** BMV080 addr 0x57 + PS/CSB/MISO straps
(**bug fixed** — old model's GND strap selected SPI); MAX30102 6 V-tolerant
pins → 3V3 bus OK; **A121 rails: VRX/VTX/VDIG 1.8 V-only → ECO-H3** (+ SPI
50 MHz mode 0); TMAG5273A1 = 0x35 (full variant table); BNO085 PS1/PS0
straps + 0x4A/0x4B; VL53L8CX SPI strap = C1 to IOVDD (no I2C_RST pin exists;
**IOVDD 1.2/1.8 V-only → ECO-H3**); AS7331 0x74 strap math; BME688 0x77;
SGP41 0x59; TCS3448 0x39 anchored to AS7343 DS (partial).

**Still open (16)** — each listed in VERIFY_LOG.md with the exact PDF to drop
into `registry_assets/<PART>/datasheet/`; the routing-blocking one is
**DS14791 (STM32N657 ball map)**.

## 5. Tests

`contract/tests/test_h2.py` extended: manifest 38/38 + no TO-GENERATE, every
manifest footprint file exists, generated files carry the E0 header, bean
outline valid closed polygon with 1500–2600 mm² sanity, board file loads with
Edge.Cuts + ≥30 footprints + DRC baseline captured. **Full suite: 19/19
passed** (11 ingest + 8 H2).

## H2.6 update (2026-07-12) — N657 ball map landed, board file now STALE

DS14791 Rev 9 arrived: the STM32N657 model was rebuilt on the **real 142-ball
VFBGA142 map** (Table 18) and `ST_VFBGA142_PLACEHOLDER` (numeric 12×12 grid —
wrong ball count layout AND wrong refs) was **deleted**, replaced by
`generated/ST_VFBGA142` (E1, 15×15 A-R×1-15 sparse grid). Consequence:
**`board/interrogator_v1.kicad_pcb` is stale** — it still embeds the
placeholder footprint and pre-H2.6 netlist. Do NOT trust it; rebuilding via
`build_board.py` is H3's first act (per plan). Netlist + ERC + tests are the
source of truth in the meantime. Also landed in H2.6: real VDDCORE plan
(0.81 V boot / 0.89 V VOS-high via `N6_VCORE_SEL`), `PWR_ON`-gated core buck,
VDD-first rail sequencing, HSE crystal add, three buck FB-divider value bugs
fixed (core would have received **1.145 V** — over the 0.921 V max),
VL53L8CH closed on its own DS (DS14310), VD66GY captured (DNP notes).
AN5967 (N6 hardware getting-started) and AN5897 (VL53L8 integration) are the
two remaining app notes worth staging before H3 fanout (cap counts,
via-in-pad, land fine print).

## NEXT (H3 routing)

1. ~~Drop in DS14791 → replace `ST_VFBGA142_PLACEHOLDER`~~ **DONE at H2.6**
   (real ball map, E1 footprint). First H3 act: re-run `build_board.py`
   against the new netlist/footprints (board file stale, see above).
2. Execute the two ECOs: A121 VDIG/VRX/VTX → 1V8; VL53L8CH IOVDD/CORE_1V8 →
   1V8 (level-shift or run SPI1 domain at 1.8 V).
3. Placement refinement: absorb the 77 overlap-fallback parts (decouplers to
   their owners' back side, TP field consolidation, pogo/ECG rings to their
   ADR positions), then route: 499 unconnected → 0.
4. Antenna/RF review at the bean edges (BL54 rim, C6 tip, GNSS notch corner).
5. Create the `.kicad_pro` only when routing starts (arms CI eda job).
