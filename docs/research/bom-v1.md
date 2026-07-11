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
