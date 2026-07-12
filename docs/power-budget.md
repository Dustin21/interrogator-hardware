# Two-mode power budget (v1.1 — model; measured at H4)

Cell: **LP503450-class 1200 mAh (50x34x5.2mm) 1S LiPo + protection**; USB-C PD ~1C fast charge (BQ25620).

## Ambient (R3: target 8h, floor 5h)

| load | mA |
|---|---|
| BL54L15 sentinel | 0.60 |
| STM32N657 avg (batch+stop) | 12.00 |
| BME688 ULP | 0.09 |
| SGP41 duty | 0.30 |
| ENS161 duty | 0.20 |
| BMV080 1-min duty | 2.60 |
| MLX90642 1fps | 1.50 |
| MLX90632 spot | 0.05 |
| SHT41 duty | 0.01 |
| BNO086 low-rate | 1.50 |
| MMC+TMAG | 0.30 |
| mic (VAD) | 0.30 |
| A121 hibernate | 0.01 |
| GNSS duty | 0.40 |
| PIN+ADC leak | 0.30 |
| SCD41 gated OFF | 0.00 |
| SGX-CO bias | 0.10 |
| misc/regs | 1.20 |
| **total** | **21.5** |

**Ambient runtime ≈ 56 h** — clears 8h target ~7×.

## Interrogation (deep dive)

| load | mA |
|---|---|
| STM32N657 full+NPU | 150.0 |
| WiFi C6 stream | 120.0 |
| VL53L8CH 15Hz | 45.0 |
| A121 duty | 20.0 |
| MLX90642 8fps | 25.0 |
| spectral+UV+NIR+PPGx2+LEDs | 34.0 |
| SCD41 active | 18.0 |
| GNSS cont | 9.0 |
| blower 50% | 19.0 |
| env sensors | 9.0 |
| sentinel+haptic+glow | 8.0 |
| **total** | **457** |

**Continuous interrogation ≈ 2.6 h** (bursty in practice → mixed 8–20h).

Adds (MLX90632/AS7421/mic/ENS161/SCD41/SGX-CO/SHT41) are gated/duty-cycled; SCD41 + electrochem bias
hard-gated in ambient. PIN radiation replaces BG51 on the ADS131M04 analog domain.