"""Compute + radios — STM32N657, octal NOR, BL54L15 sentinel, ESP32-C6 WiFi."""

from pathlib import Path

from skidl import Net, Part, TEMPLATE  # NC is a skidl builtin

from lib_parts import STM32N657, NOR_OCTAL, BL54L15, XTAL_3225
from util import join, C, R, decouple, gnd, tp, pullup

ESPRESSIF_SYM = str(Path(__file__).resolve().parents[3]
                    / "library" / "symbols" / "Espressif.kicad_sym")


def build_compute():
    GND = gnd()
    v3sys = Net.fetch("3V3_SYS")
    v18 = Net.fetch("1V8")
    vcore = Net.fetch("VDD_CORE_N6")
    aon = Net.fetch("3V3_AON")

    # ================= STM32N657 application MCU ==========================
    # Real VFBGA142 ball map — VERIFIED-DS DS14791 Rev 9 Table 18 p88-112
    # (see lib_parts.py). Supply plan (Table 24 p139 + §3.4 p25-27):
    #   VDDCORE (M5-M9)  <- VDD_CORE_N6 buck: 0.81V at boot (VOS low), raised
    #                       to 0.89V by VCORE_SEL for 800MHz overdrive.
    #   VDD (F12/G12/H12), VDDIO4 (D8, SDMMC->ESP32), VDD33USB <- 3V3_SYS.
    #   VDDIO3 (K12/L12) <- 1V8 (XSPI NOR runs at 1.8V).
    #   VDDA18* group + VDDSMPS (bypass, Fig 2 p26) + PDR_ON <- 1V8.
    #   VDDCSI <- VDD_CORE_N6 (range = VDDCORE, Table 24).
    #   VBAT <- 3V3_AON (backup domain alive in ambient mode).
    # Cap counts/values per-rail: AN5967 not staged — E0, verify at H3.
    n6 = STM32N657(ref="U_N657", footprint="generated:ST_VFBGA142")
    n6["VDDCORE1 VDDCORE2 VDDCORE3 VDDCORE4 VDDCORE5"] += vcore
    n6["VDDCSI"] += vcore
    n6["VDD1 VDD2 VDD3"] += v3sys
    n6["VDDIO4 VDD33USB"] += v3sys
    n6["VDDIO3_1 VDDIO3_2"] += v18
    n6["VDDA18CSI VDDA18PLL VDDA18USB VDDA18ADC VDDA18AON VDDA18PMU"] += v18
    n6["VDDSMPS1 VDDSMPS2 VDDSMPS3"] += v18   # bypass config, Fig 2 p26
    n6["VSSSMPS1 VSSSMPS2 VSSSMPS3"] += GND
    n6["VLXSMPS1 VLXSMPS2 VLXSMPS3"] += NC    # SMPS off/bypass — no coil
    n6["VFBSMPS"] += NC
    n6["VSS1 VSS2 VSS3 VSS4 VSS5 VSS6 VSS7 VSS8"] += GND
    n6["VSSA VSSAON VSSAPMU"] += GND
    n6["PDR_ON"] += v18                       # PDR enabled (1.62-1.98V, Table 24)
    # V08CAP: backup-regulator output — external cap only (value per AN5967, E0)
    v08 = Net.fetch("N6_V08CAP")
    v08 += n6["V08CAP"]
    c08 = C("1uF")
    v08 += c08[1]
    GND += c08[2]
    # VBAT backup domain from the always-on rail (RTC keeps time with EN_N6 off)
    n6["VBAT"] += aon
    decouple(aon, n=1)
    # ADC reference pair: VREF+ <- 1V8 (<= VDD18ADC, Table 24), VREF- <- GND
    n6["VREF_P"] += v18
    n6["VREF_N"] += GND
    decouple(v18, n=1)
    # PWR_ON handshake: N6 requests the external VCORE buck (§3.4.7 Fig 3
    # p27 — device startup with VCORE from an external SMPS). Net consumed
    # by U_CORE EN in power.py; 100k pulldown keeps the buck off during VDD
    # ramp. VCORE_SEL switches the buck divider 0.81V -> 0.89V (VOS high).
    rpo = R("100k")
    join("N6_PWR_ON", n6["PWR_ON"], rpo[1])
    GND += rpo[2]
    join("N6_VCORE_SEL", n6["VCORE_SEL"])
    decouple(vcore, n=4, bulk_uF=10)          # 5 VDDCORE balls (AN5967 E0)
    decouple(v18, n=4)                        # VDDA18 group + VDDIO3
    decouple(v3sys, n=4)
    # USB PHY / CSI PHY reference resistors — 200R 1% to GND
    # VERIFIED-DS DS14791 Table 123 p219 (RTXRTUNE) + Table 122 p218 (REXT)
    rtx = R("200R 1%")
    n6["OTG1_TXRTUNE"] += rtx[1]
    GND += rtx[2]
    rcsi = R("200R 1%")
    n6["CSI_REXT"] += rcsi[1]
    GND += rcsi[2]
    # HSE crystal: 48 MHz (HSE range 16-48 MHz, DS p13) — required reference
    # for the USB HS PHY PLL + CSI PLL; there was NO crystal in the stage-1
    # model (HSI RC is not a legal USB-HS reference). Load caps E0.
    xt = XTAL_3225(ref="X_HSE", footprint="Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm")
    xt.value = "48MHz"
    join("N6_OSC_IN", n6["OSC_IN"], xt["X1"])
    join("N6_OSC_OUT", n6["OSC_OUT"], xt["X2"])
    xt["GND1"] += GND
    xt["GND2"] += GND
    cx1, cx2 = C("10pF"), C("10pF")
    join("N6_OSC_IN", cx1[1])
    join("N6_OSC_OUT", cx2[1])
    GND += cx1[2], cx2[2]
    # LSE not fitted — PC14/PC15 stay NC (input-only, DS Table 18)
    n6["PC14_OSC32_IN"] += NC
    n6["PC15_OSC32_OUT"] += NC
    # unused second USB PHY, CC (external CYPD3177), reserved + spare GPIO
    n6["OTG1_ID UCPD1_CC1 UCPD1_CC2"] += NC
    n6["OTG2_HSDM OTG2_HSDP OTG2_ID OTG2_TXRTUNE"] += NC
    n6["RSVD_C3 RSVD_A4"] += NC               # keep floating (Table 18 fn4)
    # PN7/PN12 (ex XSPI_NCLK/NCS2) are now INT_VL53/LPN_VL53 — the two spare
    # VDDIO3-domain (1.8V) balls serve the VL53L8CH sidebands natively (H3.0)
    n6["PA0_NC PA2_NC PA15_NC PB0_NC PD1_NC PE7_NC PG14_NC"] += NC
    n6["PE8_NC PG10_NC"] += NC                # freed by the PN7/PN12 ECO

    # SPI1 sensor bus
    join("SPI1_SCK", n6["SPI1_SCK"])
    join("SPI1_MISO", n6["SPI1_MISO"])
    join("SPI1_MOSI", n6["SPI1_MOSI"])
    join("CS_VL53_N", n6["CS_VL53_N"])
    join("CS_BNO_N", n6["CS_BNO_N"])
    join("CS_ADS_N", n6["CS_ADS_N"])
    join("CS_A121_N", n6["CS_A121_N"])

    # I2C-A (1MHz-capable) + I2C-B (400k) — pull-ups to 3V3_SYS, the N657 IO
    # rail (present whenever the N657 is powered; sensors on gated domain rails
    # see idle-high bus only when their domain is also on — level note: all
    # bus devices are 3.3V-IO parts except MAX30102 (+6V abs-max, closed) and
    # ENS161/A121 (VDDIO pins fed from 3.3V domains); the 1.8V-only TCS3448
    # sits behind a PCA9306 segment of I2C-A (sensors_i2c.py, H3.0).
    # Bus A = I2C2 (PB10/PB11), bus B = I2C4 (PE13/PE14) — I2C1 is not bonded
    # on VFBGA142 (VERIFIED-DS DS14791 Table 18: only I2C1_SMBA on PB4).
    # Note: no ball in the Table 18 dump carries the "_f" (Fm+ 20mA drive)
    # I/O flag — 1MHz on bus A relies on the 2.2k pullups; confirm rise
    # times at H3 bring-up (peripheral timing supports Fm+ regardless).
    i2ca_sda, i2ca_scl = Net.fetch("I2CA_SDA"), Net.fetch("I2CA_SCL")
    i2cb_sda, i2cb_scl = Net.fetch("I2CB_SDA"), Net.fetch("I2CB_SCL")
    n6["I2CA_SDA"] += i2ca_sda
    n6["I2CA_SCL"] += i2ca_scl
    n6["I2CB_SDA"] += i2cb_sda
    n6["I2CB_SCL"] += i2cb_scl
    pullup(i2ca_sda, v3sys, "2.2k")   # 2.2k for 1MHz Fm+ on I2C-A
    pullup(i2ca_scl, v3sys, "2.2k")
    pullup(i2cb_sda, v3sys, "4.7k")   # 400kHz on I2C-B
    pullup(i2cb_scl, v3sys, "4.7k")

    # SDIO to ESP32-C6
    for s in ("SDIO_CLK", "SDIO_CMD", "SDIO_D0", "SDIO_D1", "SDIO_D2", "SDIO_D3"):
        join(s, n6[s])

    # UART1 + PPS (GNSS), UART2 (sentinel link)
    join("GNSS_RX", n6["UART1_TX"])   # N6 TX -> GNSS RXD
    join("GNSS_TX", n6["UART1_RX"])   # GNSS TXD -> N6 RX
    join("GNSS_PPS", n6["PPS_IN"])   # TIMEPULSE -> input capture
    join("IMCU_N6_TX", n6["UART2_TX"])
    join("IMCU_N6_RX", n6["UART2_RX"])

    # USB HS
    join("USB_DP", n6["USB_DP"])
    join("USB_DM", n6["USB_DM"])

    # Camera (MIPI CSI-2, J_CAM DNP) — nets exist, connector in sensors_misc
    for s in ("CSI_CKP", "CSI_CKN", "CSI_D0P", "CSI_D0N", "CSI_D1P", "CSI_D1N",
              "CAM_XCLK", "CAM_RSTN"):
        join(s, n6[s])

    # PDM mic
    join("PDM_CLK", n6["PDM_CLK"])
    join("PDM_DATA", n6["PDM_DATA"])

    # Analog + clocks
    join("RF_DET_OUT", n6["ADC_IN0"])   # AD8317 output
    join("CLK_ADS", n6["MCO_OUT"])   # 8.192MHz to ADS131M04 CLKIN

    # SWD #1 + boot straps
    join("N6_SWDIO", n6["SWDIO"])
    join("N6_SWCLK", n6["SWCLK"])
    nrst = Net.fetch("N6_NRST")
    nrst += n6["NRST"]
    pullup(nrst, v3sys, "10k")
    boot = Net.fetch("N6_BOOT0")
    boot += n6["BOOT0"]
    rboot = R("10k")
    boot += rboot[1]
    GND += rboot[2]
    tp(boot)
    # BOOT1 (= PA6 default boot pin, VERIFIED-DS DS14791 §3.6 p14): strap
    # low -> external-flash boot from XSPI NOR; testpoint allows forcing
    # serial/dev boot. PA6 is reserved as strap-only (not reused for SPI —
    # it is sampled at reset release).
    boot1 = Net.fetch("N6_BOOT1")
    boot1 += n6["BOOT1"]
    rboot1 = R("10k")
    boot1 += rboot1[1]
    GND += rboot1[2]
    tp(boot1)

    # Interrupt fan-in
    for s in ("INT_VL53", "INT_BNO", "DRDY_ADS", "INT_MAX", "INT_AS7058",
              "IRQ_A121", "DRDY_MMC", "INT_TMAG", "INT_TCS", "RDY_AS7331",
              "INT_AS7421", "INT_BMV", "INT_ENS"):
        join(s, n6[s])

    # Wake pair with the sentinel
    join("WAKE_N6", n6["WAKE_IN"])
    join("ATTN_N6", n6["WAKE_OUT"])

    # Emitter controls
    join("EN_UV_REQ", n6["EN_UV_REQ"])
    join("EN_WHITE", n6["EN_WHITE"])
    join("RSTN_BNO", n6["RSTN_BNO"])
    join("LPN_VL53", n6["LPN_VL53"])

    # ================= Octal NOR on XSPI ==================================
    nor = NOR_OCTAL(ref="U_NOR", footprint="generated:NOR_BGA24_6x8")
    nor["VCC"] += v18
    nor["VSS"] += GND
    for i in range(8):
        net = Net.fetch(f"XSPI_D{i}")
        net += n6[f"XSPI_D{i}"], nor[f"DQ{i}"]
    join("XSPI_CLK", n6["XSPI_CLK"], nor["CLK"])
    join("XSPI_CS_N", n6["XSPI_CS_N"], nor["CS_N"])
    join("XSPI_DQS", n6["XSPI_DQS"], nor["DQS"])
    nor_rst = Net.fetch("NOR_RST_N")
    nor_rst += nor["RESET_N"]
    pullup(nor_rst, v18, "10k")
    decouple(v18, n=2)
    # placeholder BGA24 pads 15-24: NC-pending until the Macronix DS lands
    for p in nor.pins:
        if p.name.startswith("PEND_"):
            p += NC

    # ================= BL54L15 BLE sentinel ================================
    bl = BL54L15(ref="U_BL54", footprint="generated:BL54L15_MODULE")
    bl["VCC"] += aon                 # pad 26 VDD_nRF  VERIFIED-DS EZ-DS v1.9 Table 1
    for g in ("GND", "GND2", "GND3", "GND4"):   # pads 1/16/27/39 — all must
        bl[g] += GND                 # tie to the GND plane (Table 1 Note 1)
    decouple(aon, n=2, bulk_uF=10)

    bl["SENT_SDA"] += Net.fetch("SENT_SDA")
    bl["SENT_SCL"] += Net.fetch("SENT_SCL")
    pullup(Net.fetch("SENT_SDA"), aon, "4.7k")   # always-on bus -> AON rail
    pullup(Net.fetch("SENT_SCL"), aon, "4.7k")

    bl["GEIGER_PULSE_IN"] += Net.fetch("GEIGER_PULSE")

    for name in ("OPTICAL", "AIR", "CONTACT", "RADAR", "GNSS", "WIFI"):
        bl[f"EN_{name}"] += Net.fetch(f"EN_{name}")
    bl["EN_N6"] += Net.fetch("EN_N6")
    bl["EN_FAN"] += Net.fetch("EN_FAN")
    bl["EN_ACC"] += Net.fetch("EN_ACC")
    bl["EN_HAPTIC"] += Net.fetch("EN_HAPTIC")
    bl["INTERLOCK_OK"] += Net.fetch("INTERLOCK_OK")

    # inter-MCU UART (cross-over) + wake lines
    bl["UART_TX"] += Net.fetch("IMCU_N6_RX")
    bl["UART_RX"] += Net.fetch("IMCU_N6_TX")
    bl["WAKE_N6"] += Net.fetch("WAKE_N6")
    bl["ATTN_FROM_N6"] += Net.fetch("ATTN_N6")

    bl["TOUCH_RDY_IN"] += Net.fetch("TOUCH_RDY_N")
    bl["GAUGE_INT_IN"] += Net.fetch("GAUGE_INT_N")
    pullup(Net.fetch("GAUGE_INT_N"), aon, "100k")
    bl["CHG_INT_IN"] += Net.fetch("CHG_INT_N")
    pullup(Net.fetch("CHG_INT_N"), aon, "100k")
    # PD_FAULT: CYPD3177 FAULT is actively driven high on fault (VERIFIED-DS
    # 002-25383 p6) — the old open-drain pullup was removed; testpoint only.

    for i in range(1, 7):
        bl[f"GLOW{i}"] += Net.fetch(f"GLOW{i}")

    bl["NFC1"] += NC   # NFC antenna not fitted in v1 (pads 15/14, P1.02/P1.03)
    bl["NFC2"] += NC
    bl["XL1"] += NC    # pads 25/24 — reserved for optional 32.768 kHz
    bl["XL2"] += NC    # crystal (VERIFIED-DS EZ-DS v1.9 Table 1 p12)

    # SWD #2
    join("BL_SWDIO", bl["SWDIO"])
    join("BL_SWCLK", bl["SWCLK"])
    bl_rst = Net.fetch("BL_RESET_N")
    bl_rst += bl["RESET_N"]
    pullup(bl_rst, aon, "10k")

    # ================= ESP32-C6-MINI-1 (WiFi, SDIO) ========================
    # Symbol source: espressif/kicad-libraries (harvested copy in library/symbols).
    c6t = Part(ESPRESSIF_SYM, "ESP32-C6-MINI-1/U", dest=TEMPLATE)
    c6 = c6t(ref="U_C6", footprint="Espressif:ESP32-C6-MINI-1")
    v_wifi = Net.fetch("3V3_WIFI")
    c6["3V3"] += v_wifi
    decouple(v_wifi, n=1, bulk_uF=22)
    for p in c6.pins:
        if p.name == "GND":
            p += GND
    # EN via RC from the gated rail: module boots when 3V3_WIFI comes up
    ren = R("10k")
    cen = C("1uF")
    en_net = Net.fetch("C6_EN")
    v_wifi += ren[1]
    en_net += ren[2], cen[1], c6["EN/CHIP_PU"]
    GND += cen[2]
    # SDIO slave mapping — VERIFIED-DS esp32-c6-mini-1 DS v1.5 p10-11
    # Table 3-1: pad 24 IO18=SDIO_CMD, 25 IO19=SDIO_CLK, 26 IO20=SDIO_DATA0,
    # 27 IO21=SDIO_DATA1, 28 IO22=SDIO_DATA2, 29 IO23=SDIO_DATA3. CLOSED.
    c6["GPIO18"] += Net.fetch("SDIO_CMD")
    c6["GPIO19"] += Net.fetch("SDIO_CLK")
    c6["GPIO20"] += Net.fetch("SDIO_D0")
    c6["GPIO21"] += Net.fetch("SDIO_D1")
    c6["GPIO22"] += Net.fetch("SDIO_D2")
    c6["GPIO23"] += Net.fetch("SDIO_D3")
    # boot-mode service UART to testpoints
    tx = Net.fetch("C6_TXD0")
    rx = Net.fetch("C6_RXD0")
    tx += c6[31]   # U0TXD/GPIO16  VERIFIED-DS p11 (pad 31 = TXD0)
    rx += c6[30]   # U0RXD/GPIO17  VERIFIED-DS p11 (pad 30 = RXD0)
    tp(tx)
    tp(rx)
    boot9 = Net.fetch("C6_BOOT")
    boot9 += c6["GPIO9"]
    pullup(boot9, v_wifi, "10k")
    tp(boot9)
    # all remaining module pins unused in v1
    for p in c6.pins:
        if not p.nets and p.name != "NC":
            p += NC
    for p in c6.pins:
        if p.name == "NC":
            p += NC

    # bus testpoints
    for n in ("SPI1_SCK", "SPI1_MISO", "SPI1_MOSI", "I2CA_SDA", "I2CA_SCL",
              "I2CB_SDA", "I2CB_SCL", "SENT_SDA", "SENT_SCL", "SDIO_CLK",
              "SDIO_CMD", "IMCU_N6_TX", "IMCU_N6_RX", "GNSS_PPS",
              "N6_SWDIO", "N6_SWCLK", "BL_SWDIO", "BL_SWCLK"):
        tp(Net.fetch(n))
