# Interface requirements -> interrogator firmware project (v1 hardware)

The board this repo is building; firmware adapts to this (owner-ratified flow).

1. **Compute**: STM32N657 (app, ESP-class port replaced by STM32 port; Neural-ART available) + nRF54L15 module (sentinel, Zephyr/nRF Connect). Inter-MCU: UART (CRC8 framing may carry over) + shared GPIO wake lines.
2. **Buses**: VL53L8CH + BNO086 on SPI+DMA w/ INT; I2C-A (MLX90642, MAX30102, AS7058, ADS131M04-SPI actually -> ADS on SPI2); I2C-B (BME688, SGP41, BMV080, TCS3448, AS7331, MMC5983MA, TMAG5273, IQS7222A); I3C capable pins reserved. GNSS on UART+PPS to input-capture. Wi-Fi via SDIO (ESP-Hosted-MCU).
3. **INT/data-ready wired for every sensor that has one**; FIFO watermark reads; GPS-PPS disciplined timestamps (utc = monotonic + gps_offset contract preserved).
4. **Power domains** (firmware-controlled load switches): OPTICAL, AIR(+fan), CONTACT, RF-WIFI, GNSS, RADAR. Ambient = sentinel + duty-cycled N657. Command surface should map SET_*_RATE + domain on/off.
5. **Wire contract**: binary IDL (ADR-0004) target; text debug mode; ~25-100 KB/s budget unchanged; BLE control plane + Wi-Fi bulk (WebRTC-class transport terminated app-side).
6. **Sensor set deltas** (ingest package to registry): MLX90642, VL53L8CH, TCS3448, BNO086, MMC5983MA, MIA_M10Q, IQS7222A, ADS131M04, AS7058 new records; AMG8833/AS7263/MPR121/NEO_M9N/ADS1115/VL53L8CX/AS7343/BNO085 deprecated-by-successor.
7. **OTA**: A/B slots, signed images, sentinel-rooted identity; feature-gate hooks.
