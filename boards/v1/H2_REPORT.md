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
