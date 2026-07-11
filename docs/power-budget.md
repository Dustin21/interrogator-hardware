# Two-mode power budget (v1, model — measured at H4 via per-domain shunts)

Cell: **LP503450-class 1200 mAh, 50x34x5.2 mm, ~21 g (1S LiPo + protection)** — fast charge ≥1.2 A (~1C) via BQ25620 + USB-C PD.

## Ambient mode (R3)

| load | mA avg |
|---|---|
| BL54L15 sentinel (BLE+touch+rad+gauge) | 0.60 |
| STM32N657 avg (50ms/s batch @~120mA + stop ~6mA) | 12.00 |
| BME688 ULP | 0.09 |
| SGP41 duty 1/10 | 0.30 |
| BMV080 1-min duty | 2.60 |
| MLX90642 1fps duty | 1.50 |
| BNO086 low-rate | 1.50 |
| MMC+TMAG | 0.30 |
| VL53L8CH gated off | 0.00 |
| A121 hibernate | 0.01 |
| GNSS duty 1/30 | 0.40 |
| ADC+touch+misc | 0.50 |
| **total** | **19.8** |

**Runtime ambient ≈ 61 h** (target 8 h, floor 5 h → met with ~8x margin).

## Interrogation mode (deep dive, everything hot)

| load | mA avg |
|---|---|
| STM32N657 full run + NPU | 150.0 |
| Wi-Fi C6 stream avg | 120.0 |
| VL53L8CH 15Hz | 45.0 |
| A121 duty | 20.0 |
| MLX90642 8fps | 25.0 |
| spectral+UV+PPG x2 + LEDs | 30.0 |
| GNSS cont | 9.0 |
| blower 50% duty | 19.0 |
| sensors env cont | 8.0 |
| sentinel+haptics+glow | 8.0 |
| **total** | **434** |

**Runtime continuous interrogation ≈ 2.8 h** (deep dives are minutes-long bursts; mixed use lands 8–20 h).

Provenance: currents from datasheets/vendor pages cited in docs/research/bom-v1.md; N6 run current is the
flagged community figure (DS14791 table pull pending) — the sentinel split makes the ambient number robust to it.