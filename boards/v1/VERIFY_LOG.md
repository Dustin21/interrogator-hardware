# VERIFY closure log — H2 stage-2

**Date:** 2026-07-12 · Method: `pdftotext` over the STAGED datasheet PDFs in
`registry_assets/<PART>/datasheet/` (the only vendor documents reachable in
this environment). Every closure below is annotated in the circuit source as
`VERIFIED-DS <doc> p<page>`. Items that need a missing PDF are listed at the
bottom with the exact file the owner should drop in.

## Closed (datasheet-verified)

| # | Item | Verdict | Evidence | Circuit action |
|---|------|---------|----------|----------------|
| 1 | BMV080 I2C address + interface straps | **0x57 confirmed**; protocol select is a dedicated **PS pin: to VDDIO = I2C, to GND = SPI**; in I2C mode CSB + MISO become address straps and must not float — CSB=1, MISO=1 → 0x57 | bst-bmv080-ds000.pdf p26 (Fig. 25 + pin table), p32 (Table 14) | **Bug fixed**: old model strapped `AB_SEL → GND`, which per DS selects SPI. Replaced with `PS/CSB/MISO_ADDR` pins all strapped to VDDIO (sensors_misc.py) |
| 2 | MAX30102 1.8 V core on 3.3 V-pulled I2C bus | **Safe** — abs-max "All Other Pins to GND −0.3 V to +6.0 V"; DS states tolerance of any supply order | MAX30102.pdf p2 (Abs Max), p28 | Comment closed (lib_parts.py, sensors_i2c.py) |
| 3 | A121 supply rails | **VRX/VTX/VDIG are 1.8 V-only** (abs-max 2.0 V; VRX/VTX must never exceed VDIG); **VIO may be 1.8 or 3.3 V** (abs-max 3.63 V) | A121-Datasheet.pdf (v1.8) p10 Table 2, p6 | **ECO-H3 flagged**: current wiring feeds the whole part from 3V3_RADAR — VDIG/VRX/VTX bundle must move to the 1V8 rail (comment in lib_parts.py + sensors_misc.py) |
| 4 | A121 SPI max clock | **50 MHz**, SPI mode 0 (CPOL=CPHA=0), SS released between transactions | A121-Datasheet.pdf p16-17 (Table 12) | Comment closed; shared SPI1 at N657 speeds is legal |
| 5 | TMAG5273 variant addresses | **A1 (and A2) default = 0x35**; B=0x22, C=0x78, D=0x44 (Table 6-2) → order **TMAG5273A1** | tmag5273.pdf p16 | Comment closed (lib_parts.py, sensors_i2c.py) |
| 6 | BNO085/BNO086 PS straps + addresses | **PS1=1, PS0=1 → SPI**; both must be high at reset, then PS0 repurposes as active-low WAKE; pins 5/6; I2C fallback addr 0x4A/0x4B via SA0 | BNO085 DS p9 (Fig 1-5), p10, p18, p19, p14 | Matches existing 10k-pullup + host-GPIO topology; comment closed |
| 7 | VL53L8CX comm-mode strap | **C1 = SPI_I2C_N: 47 k to IOVDD → SPI; 47 k to GND → I2C.** There is **no separate I2C_RST pin** (C1 doubles as I2C-reset by toggling). Full pad-name map extracted (A1..C7) | vl53l8cx.pdf (DS14161) p6-7 Table 3 | Comment closed; **second finding: IOVDD is 1.2/1.8 V only** — ECO-H3 to move IOVDD+CORE_1V8 off 3V3_OPTICAL |
| 8 | AS7331 address straps | **addr[6:0] = 1110_1,A1,A0** → A1A0=00 gives **0x74**; A1=pin 7, A0=pin 14 | AS7331-AQFT DS p43, p9 | Comment closed |
| 9 | BME688 address | **SDO=VDDIO → 0x77** (SDO=GND → 0x76; must not float); CSB high = I2C | bst-bme688-ds000.pdf p45 | Confirmed as wired |
| 10 | SGP41 address + package | **0x59 fixed**; DFN-6 2.44×2.44×0.85, pitch 0.8, GND die pad → footprint generated from these numbers | SGP41 DS p12, p1/p18 | Confirmed; footprint `generated/SGP41_DFN6_2.44x2.44` |
| 11 | TCS3448 address (partial) | TCS3448 DS unavailable; **family anchor: AS7343 ordering table lists 0x39** (TCS3448 is the ams-named AS7343 successor, same 3.1×2.0 OLGA) | AS7343-DLGM DS p5, p3 | Stays `# VERIFY` with the anchor noted |

Bonus extractions used for footprints: A121 full 50-ball named map (DS p8-9)
→ `generated/A121_fcCSP50`; VL53L8 pad-name grid → `generated/ST_VL53L8_LGA16`.

## Still open — exact PDFs needed in `registry_assets/<PART>/datasheet/`

| Item | Needed file |
|------|-------------|
| AS7058 addr 0x30 + WLCSP42 ball map | `AS7058/datasheet/AS7058_DS001573*.pdf` (ams-osram) |
| AS7421 addr 0x64 + OLGA10 land pattern | `AS7421/datasheet/AS7421_DS000913*.pdf` (ams-osram) |
| TCS3448 addr + package (close the 0x39 anchor) | `TCS3448/datasheet/TCS3448_DS*.pdf` (ams-osram) |
| MLX90632 pinout + SFN land pattern | `MLX90632/datasheet/MLX90632-Datasheet-Melexis.pdf` |
| MLX90642 TO-39 pin circle orientation | `MLX90642/datasheet/MLX90642-Datasheet-Melexis.pdf` |
| ESP32-C6 SDIO GPIO map | `ESP32-C6/datasheet/esp32-c6_datasheet_en.pdf` + `esp32-c6-mini-1_datasheet_en.pdf` |
| BQ27427 sense topology + DSBGA ball map | `BQ27427/datasheet/bq27427.pdf` (TI) |
| CYPD3177 strap resistor values | `CYPD3177/datasheet/Infineon-CYPD3177*.pdf` |
| STM32N657 VFBGA142 ball map (blocks routing!) | `STM32N657/datasheet/DS14791 stm32n657x0.pdf` (ST) |
| BL54L15 pad map + antenna keepout | `BL54L15/datasheet/BL54L15 module datasheet.pdf` (Ezurio) |
| MIA-M10Q pad map + RF keepout | `MIA-M10Q/datasheet/MIA-M10Q_IntegrationManual_UBX*.pdf` |
| ENS161 LGA-9 pinout/land pattern | `ENS161/datasheet/SC-001224-DS-*-ENS16x.pdf` (ScioSense) |
| SGX-4CO cell drawing (pin circle) | `SGX-4CO/datasheet/SGX-4CO*.pdf` (SGX Sensortech / Amphenol) |
| IQS7222A QFN-20 pad map | `IQS7222A/datasheet/IQS7222A_Datasheet.pdf` (Azoteq) |
| TPS22916 WCSP ball order | `TPS22916/datasheet/tps22916.pdf` (TI) |
| LMP91000 pin map (footprint already official WSON-14) | `LMP91000/datasheet/lmp91000.pdf` (TI) |
