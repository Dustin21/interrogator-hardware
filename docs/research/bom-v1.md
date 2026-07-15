# v1 BOM — market-scan verdicts (web-verified 2026-07-11)

Full agent research in session transcript; per-claim URLs verified at Digi-Key/Mouser/LCSC/vendor pages.

## Sensor deltas vs baseline (ratified for v1 unless owner objects)
| Ch | v1 part | Action | Why | $@1k |
|---|---|---|---|---|
| Gas | BME688 | keep | only raw programmable-heater MOX + T/RH/P | 7.50 |
| VOC/NOx | SGP41 | keep | only cheap raw NOx; no successor (SGP43 doesn't exist) | 5.70 |
| PM | BMV080 | keep | nothing smaller emerged; fanless mW-class | 31.00 |
| Thermal | **MLX90642** (was AMG8833) | replace | 32x24 raw px, 2uA sleep, ~$21 | 21.00 |
| PPG | MAX30102 + **AS7058** | add | AS7058: 20-bit PPG/ECG/BioZ, <20uA, $2.51 | 8.71 |
| ToF | **VL53L8CH** (was CX) | replace | +$0.18 buys raw CNH histograms | 5.58 |
| Spectral | **TCS3448** + AS7331, drop AS7263 | replace | ams-named AS7343 successor; AS7263 legacy | 10.09 |
| IMU | **BNO086** (was 085) | replace | drop-in, 3x stock, lower idle; raw+fused | 9.06 |
| Mag | TMAG5273 + **MMC5983MA** | add | nT regime (heading/ferrous) for $1.36 | 1.67 |
| Radar | A121 | keep | raw Sparse-IQ, deep stock | 7.62 |
| GNSS | **MIA-M10Q-01B** (was NEO-M9N) | replace | 4.5mm SiP, 1/4 power, only RAWX variant | 8.08 |
| Radiation | BG51 | keep | 25uA pulse-to-GPIO, no analog chain | ~50 est |
| Touch | **IQS7222A** (was MPR121, EOL) | replace | $0.42, raw counts, 6.7uA | 0.42 |
| ADC | **ADS131M04** (was ADS1115) | replace | 4ch simultaneous 24-bit 64kSPS; AD8317 absorbed into N6 ADC | 3.59 |
| Camera | VD66GY (DNP opt) | add-opt | global shutter, N6 first-party, longevity 2036 | ~18 |

**Sensor subtotal ~ $183 @1k** (+camera). Compute+radio+power: STM32N657 ($12.5-14.9) + XSPI NOR + BL54L15 ($3.99) + ESP32-C6-MINI-1 ($2.50, SDIO 53Mbps) + power tree ($7.80) ~ **$31**. Actuator: Sunon UB3F3-500 blower ~$13 (L10 report requested).

## Hard findings that changed the architecture
1. u-blox NORA-W36 EOL + UART-limited -> **Wi-Fi = ESP32-C6-MINI-1, ESP-Hosted over SDIO** (53 Mbps TCP verified).
2. nRF54L15 has **no cap-touch peripheral** -> IQS7222A handles touch (needed anyway, MPR121 EOL).
3. i.MX RT1170 NRND + zero franchise stock; ESP32-P4 mid-EOL rev transition -> **strengthens N657 choice**.
4. AS7343 EOL trajectory (TCS3448 successor; resolve 10k-MOQ flag with ams before H2 freeze).
5. MPR121 discontinued; AS7038RB discontinued (avoid).

## Open verifications (H2 gates)
STM32N6 DS14791 power tables · TCS3448 lifecycle/MOQ · MIA-M10Q-01B orderability · BG51 quote+dims · BNO08x current tables · Sunon L10 · C6 module cert grant list.

## Replacement trade-off ledger (owner review 2026-07-11)
| Swap | LOSE | GAIN |
|---|---|---|
| AMG8833→MLX90642 | 6x active draw (28 vs 4.5mA); tallest part on face (TO-39+lens 5.1mm); young silicon, no 1k break; AMG field history | 12x raw px; raw-or-cal selectable; 2uA sleep => lower AVERAGE power duty-cycled; FOV options; MLX90641 fallback |
| VL53L8CX→CH | +$0.18; heavier frames on bus (budgeted, SPI+DMA); less community mileage on CNH | raw per-zone photon histograms (material/translucency/multi-target; permanent substrate) |
| AS7343→TCS3448 | AS7343 lib ecosystem; 10k-MOQ/lifecycle ambiguity (OPEN); driver work | channel survives (AS7343 EOL); same 14ch/pkg/power; half price; raw FIFO |
| BNO085→BNO086 | ~nothing (+$0.25) | 3x stock; lower idle; 14-bit accel fusion; firmware carries over |
| NEO-M9N→MIA-M10Q-01B | nav rate ~25->~10Hz class; no SPI/USB; less forgiving RF layout; -01B orderability UNCONFIRMED (most likely swap to revert; MAX-M10S fallback) | only RAWX (raw pseudorange/carrier phase); 1/4 power; 4.5mm SiP; -$4; SAW+LNA integrated |
| MPR121→IQS7222A | prototype touch firmware + hobbyist lore; Azoteq GUI tooling | part is ALIVE (MPR121 EOL); 3.5x cheaper; 6.7uA ULP; raw counts; wake features enabling gesture language |
| ADS1115→ADS131M04 | I2C simplicity (SPI-only, DMA lane); 10x active power (duty-cycled); wide direct FSR (M04 +/-1.2V needs attenuators) | 4ch simultaneous 24-bit/64kSPS (~300x raw bits/$); true waveform capture; spare precision channels; AD8317 absorbed by N657 ADC |

Pattern: losses are OPERATIONAL (mA, drivers, supply risk — all fenced: sleep/duty architecture, H2
one-time driver work, named fallbacks + DNP pads). Gains are INFORMATIONAL (histograms, carrier phase,
resolution, simultaneity) — permanent, compounding through every future model. Forced swaps: MPR121,
AS7343. Watch-item: MIA-M10Q-01B orderability.

## Candidate ADDS from owner review (pending owner call)
- SHT41 (~$1.50, 1.5mm DFN): unheated reference-grade T/RH anchor away from self-heating; improves MOX
  humidity compensation. Recommend ADD.
- SCD41 (~$8-12, 10x10x6.5): TRUE CO2 (photoacoustic NDIR) — the one real hole in the air stack
  (BME688 eCO2 is a VOC proxy). Strong for buildings/facilities vertical. Recommend ADD if envelope allows.
- ENS161: REJECTED (black-box DSP outputs vs ADR-0014 raw-first; same MOX class = no orthogonal info;
  1.8V rail; patchy supply). SGP41 was never replaced — BME688+SGP41 are complements (different MOX
  platforms; SGP41 has the NOx pixel).

## RATIFIED 2026-07-11 (ADR-0002)
All 7 adds ACCEPTED (MLX90632, AS7421, MEMS mic, ENS161, SCD41, SGX-4CO, SHT41). BG51→bare-PIN ACCEPTED.
Magnetic pogo accessory port ACCEPTED. Board 60×46, chassis 66×50×18. See docs/decisions/0002.

## H2.5 datasheet note (2026-07-12) — SGX-4CO (DS-0138 Issue 3)
- MOUNTING: pins must NOT be glued or soldered (DS p3 note 1, warranty) — **BOM add: 3× PSB
  socket receptacles for Ø1.55 pins** (Mill-Max 0326/0305 class, drill Ø1.7); cell plugs in →
  field-replaceable, which is exactly the R2 serviceability flag ("~2-5yr life") answered.
- Pin circle: 3× Ø1.55 pins on 13.5 mm PCD, can Ø20 × 16.5 (+3.9 pins) — footprint E1;
  13.5 PCD pad ring slightly exceeds the ratified 14×14 envelope → ECO-H3 gas_b repack
  (EXECUTED at H3.1: envelope 17×17, gas_b zone grown; can Ø20 stays on-board).
- Electricals (p1): output 70±20 nA/ppm, recommended load 10 Ω, range 0-2000 ppm (overload
  5000), t90 <30 s, baseline ±2 ppm, filter capacity >20 000 ppm·h, life >24 months in air,
  −30..+50 °C, 15-90 %RH; intrinsic-safety max o/c 1.3 V / 0.3 mA @2000 ppm — comfortably
  inside LMP91000 potentiostat range (TIA gains cover 70 nA/ppm × 2000 ppm = 140 µA FS).
