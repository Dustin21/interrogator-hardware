"""Custom SKiDL part templates for the interrogator v1.1 board.

This file IS our symbol source for parts with no KiCad-official symbol
(vendor portals / easyeda2kicad are network-blocked in this environment).
Pin numbers marked `# pinout E0` are LOGICAL (sequential) and MUST be
re-mapped to real package pins/balls at footprint-generation stage.
Where the physical pin number is believed correct from datasheet memory
it is still tier E0 until checked against the PDF (H2 stage-2 gate).

Convention: only pins we actually USE (plus straps) are modeled. That keeps
ERC meaningful — an unconnected pin on one of these parts is a real error.
"""

from skidl import Part, Pin, TEMPLATE, SKIDL

# Shorthands for electrical types
IN = Pin.types.INPUT
OUT = Pin.types.OUTPUT
BI = Pin.types.BIDIR
TRI = Pin.types.TRISTATE
PAS = Pin.types.PASSIVE
PWR = Pin.types.PWRIN
PWO = Pin.types.PWROUT
OC = Pin.types.OPENCOLL
NCP = Pin.types.NOCONNECT


def mkpart(name, ref_prefix, pins, description="", footprint=None):
    """Build a SKiDL TEMPLATE part from (num, name, func) tuples."""
    p = Part(name=name, tool=SKIDL, dest=TEMPLATE, ref_prefix=ref_prefix,
             description=description)
    for num, pname, func in pins:
        p += Pin(num=str(num), name=pname, func=func)
    if footprint:
        p.footprint = footprint
    return p


def _seq(defs):
    """Number pins sequentially 1..N.  # pinout E0 — verify at footprint stage."""
    return [(i + 1, n, f) for i, (n, f) in enumerate(defs)]


# ============================================================================
# COMPUTE
# ============================================================================

# STM32N657X0 VFBGA142 — REAL ball map.
# VERIFIED-DS DS14791 Rev 9 Table 18 p88-112 (pin/ball definition, VFBGA142
# column; 142 balls extracted, count cross-checked vs Fig 7 ballout p87 and
# Table 128 N=142 p236). Grid = 15x15 (rows A-R, no I/O/Q; cols 1-15),
# 0.5 mm pitch, body 8x8, D1/E1=7.00 (Fig 67 p235). Peripheral instance
# choices are constrained by what the 142-ball package bonds out:
#  * I2C1 is NOT available on VFBGA142 (only I2C1_SMBA on PB4) — bus A uses
#    I2C2 (PB10/PB11), bus B uses I2C4 (PE13/PE14).       VERIFIED-DS Table 18
#  * USART2_RX is not bonded (PA3/PC2/PF6 absent) — sentinel link moved to
#    UART4 (TX=PA12, RX=PA11).
#  * SDMMC1 to the ESP32-C6: CK=PC12, CMD=PH2(boot pin set), D0-3=PC8-PC11.
#  * XSPIM_P2 (boot flash port) is the dedicated PN port: DQS0=PN0, NCS1=PN1,
#    IO0-7=PN2-5/PN8-11, CLK=PN6 (NCLK PN7 + NCS2 PN12 unused).
#  * BOOT1 is a non-dedicated boot pin defaulting to PA6 (§3.6 p14 + Table 19
#    AF0) — PA6 is reserved as the BOOT1 strap, NOT reused for SPI1_MISO
#    (which moves to PB4, tri-stated by CS pullups at reset).
# IO supply domains (Table 18 footnotes 1/6/9): general GPIO -> VDD (3V3),
# PN port -> VDDIO3 (1V8, NOR domain), SDMMC group PC8-12/PH2 -> VDDIO4 (3V3).
# OPT124 bits + VDDIOxVRSEL registers must match the chosen rail voltages (fw).
STM32N657 = mkpart("STM32N657", "U", [
    # --- core / IO / analog supplies ------------------------------------
    ("M5", "VDDCORE1", PWR), ("M6", "VDDCORE2", PWR), ("M7", "VDDCORE3", PWR),
    ("M8", "VDDCORE4", PWR), ("M9", "VDDCORE5", PWR),   # 0.81V VOS-lo / 0.89V VOS-hi (Table 24 p139)
    ("F12", "VDD1", PWR), ("G12", "VDD2", PWR), ("H12", "VDD3", PWR),  # 3.3V IO
    ("K12", "VDDIO3_1", PWR), ("L12", "VDDIO3_2", PWR),  # XSPI/PN port IO (1V8)
    ("D8", "VDDIO4", PWR),                               # SDMMC IO (3V3)
    ("P8", "VDDCSI", PWR),          # = VDDCORE range (Table 24 p139)
    ("R7", "VDDA18CSI", PWR), ("K4", "VDDA18PLL", PWR),
    ("D4", "VDDA18USB", PWR), ("B6", "VDD33USB", PWR),
    ("R3", "VDDA18ADC", PWR), ("E4", "VDDA18AON", PWR), ("F1", "VDDA18PMU", PWR),
    ("P2", "VREF_P", PWR), ("R2", "VREF_N", PWR),        # ADC reference pair
    ("D1", "VBAT", PWR),
    # internal SMPS — BYPASS configuration (VCORE from external buck,
    # DS14791 §3.4.4 Fig 2 p26: VDDSMPS/VDDA18PMU stay supplied at 1.8V;
    # VLXSMPS + VFBSMPS left unconnected in bypass)
    ("J1", "VDDSMPS1", PWR), ("J2", "VDDSMPS2", PWR), ("J3", "VDDSMPS3", PWR),
    ("G1", "VSSSMPS1", PWR), ("G2", "VSSSMPS2", PWR), ("G3", "VSSSMPS3", PWR),
    ("H1", "VLXSMPS1", NCP), ("H2", "VLXSMPS2", NCP), ("H3", "VLXSMPS3", NCP),
    ("F3", "VFBSMPS", NCP),
    ("E1", "V08CAP", PWO),          # backup-regulator output — cap only (0.8V)
    # grounds
    ("A15", "VSS1", PWR), ("D9", "VSS2", PWR), ("J12", "VSS3", PWR),
    ("M4", "VSS4", PWR), ("M10", "VSS5", PWR), ("M12", "VSS6", PWR),
    ("R1", "VSS7", PWR), ("R15", "VSS8", PWR),
    ("P3", "VSSA", PWR), ("F4", "VSSAON", PWR), ("F2", "VSSAPMU", PWR),
    # --- power management / reset / boot --------------------------------
    ("A1", "PDR_ON", IN),           # power-down reset enable, 1.8V (Table 24 p140)
    ("D2", "PWR_ON", OUT),          # requests external VCORE supply (§3.4.7 Fig 3 p27)
    ("C2", "NRST", IN), ("B2", "BOOT0", IN),
    ("P13", "BOOT1", IN),           # PA6 = default BOOT1 pin (§3.6 p14) — strap only
    # --- SPI1 (sensor SPI: VL53L8CH, BNO086, ADS131M04, A121) ------------
    ("R12", "SPI1_SCK", OUT),       # PA5  AF SPI1_SCK
    ("L14", "SPI1_MISO", IN),       # PB4  AF SPI1_MISO
    ("M15", "SPI1_MOSI", OUT),      # PB5  AF SPI1_MOSI
    ("C13", "CS_VL53_N", OUT),      # PD8
    ("N13", "CS_BNO_N", OUT),       # PB12
    ("B13", "CS_ADS_N", OUT),       # PE10
    ("B11", "CS_A121_N", OUT),      # PE12
    # --- I2C: bus A = I2C2, bus B = I2C4 (I2C1 not bonded on 142) ---------
    ("N15", "I2CA_SCL", BI),        # PB10 I2C2_SCL
    ("N14", "I2CA_SDA", BI),        # PB11 I2C2_SDA
    ("A11", "I2CB_SCL", BI),        # PE13 I2C4_SCL
    ("D10", "I2CB_SDA", BI),        # PE14 I2C4_SDA
    # --- SDMMC1 to ESP32-C6 (ESP-Hosted SDIO) -----------------------------
    ("A10", "SDIO_CLK", OUT),       # PC12 SDMMC1_CK
    ("B10", "SDIO_CMD", BI),        # PH2  SDMMC1_CMD
    ("A8", "SDIO_D0", BI),          # PC8  SDMMC1_D0
    ("B8", "SDIO_D1", BI),          # PC9  SDMMC1_D1
    ("A9", "SDIO_D2", BI),          # PC10 SDMMC1_D2
    ("B9", "SDIO_D3", BI),          # PC11 SDMMC1_D3
    # --- USART1: GNSS; PPS -> TIM2_CH2 capture ----------------------------
    ("P11", "UART1_TX", OUT),       # PA9  USART1_TX
    ("R11", "UART1_RX", IN),        # PA10 USART1_RX
    ("P14", "PPS_IN", IN),          # PA1  TIM2_CH2/TIM5_CH2 input capture
    # --- UART4: inter-MCU link to BL54L15 (USART2_RX not bonded) ----------
    ("P10", "UART2_TX", OUT),       # PA12 UART4_TX
    ("R10", "UART2_RX", IN),        # PA11 UART4_RX
    # --- USB HS (OTG1) -----------------------------------------------------
    ("B5", "USB_DP", BI),           # OTG1_HSDP
    ("A5", "USB_DM", BI),           # OTG1_HSDM
    ("A6", "OTG1_TXRTUNE", PAS),    # 200R +/-1% to GND (Table 123 p219)
    ("B4", "OTG1_ID", NCP),         # device-only port — ID unused
    ("D6", "UCPD1_CC1", NCP), ("D7", "UCPD1_CC2", NCP),  # CC handled by CYPD3177
    # second USB PHY unused
    ("A3", "OTG2_HSDM", NCP), ("B3", "OTG2_HSDP", NCP),
    ("A2", "OTG2_ID", NCP), ("D5", "OTG2_TXRTUNE", NCP),
    ("C3", "RSVD_C3", NCP), ("A4", "RSVD_A4", NCP),  # "must be kept floating" (Table 18 fn4)
    # --- camera MIPI CSI-2 (J_CAM DNP) -------------------------------------
    ("R5", "CSI_CKP", BI), ("P5", "CSI_CKN", BI),
    ("R6", "CSI_D0P", BI), ("P6", "CSI_D0N", BI),
    ("R4", "CSI_D1P", BI), ("P4", "CSI_D1N", BI),
    ("P7", "CSI_REXT", PAS),        # 200R +/-1% to GND (Table 122 p218)
    ("A13", "CAM_XCLK", OUT),       # PE9 TIM1_CH1 (camera DNP)
    ("C15", "CAM_RSTN", OUT),       # PE3
    # --- PDM mic (ADF1) ----------------------------------------------------
    ("D15", "PDM_CLK", OUT),        # PB6 ADF1_CCK1
    ("E12", "PDM_DATA", IN),        # PB7 ADF1_SDI0
    # --- analog / clocks ---------------------------------------------------
    ("L4", "ADC_IN0", IN),          # PF3 ADC1_INP16 — AD8317 detector out
    ("M11", "MCO_OUT", OUT),        # PA8 MCO1 — 8.192 MHz to ADS131M04
    ("A7", "OSC_IN", IN),           # PH0 — HSE crystal (16-48 MHz, DS p13)
    ("B7", "OSC_OUT", OUT),         # PH1
    ("C1", "PC14_OSC32_IN", NCP),   # LSE unused (no 32k crystal fitted)
    ("B1", "PC15_OSC32_OUT", NCP),
    # --- debug -------------------------------------------------------------
    ("R9", "SWDIO", BI),            # PA13 JTMS/SWDIO
    ("R8", "SWCLK", IN),            # PA14 JTCK/SWCLK
    # --- XSPI (octal NOR on XSPIM_P2 = dedicated PN port, boot source) -----
    ("H15", "XSPI_D0", BI),         # PN2  XSPIM_P2_IO0
    ("K15", "XSPI_D1", BI),         # PN3  XSPIM_P2_IO1
    ("E14", "XSPI_D2", BI),         # PN4  XSPIM_P2_IO2
    ("F15", "XSPI_D3", BI),         # PN5  XSPIM_P2_IO3
    ("E15", "XSPI_D4", BI),         # PN8  XSPIM_P2_IO4
    ("G14", "XSPI_D5", BI),         # PN9  XSPIM_P2_IO5
    ("H14", "XSPI_D6", BI),         # PN10 XSPIM_P2_IO6
    ("J14", "XSPI_D7", BI),         # PN11 XSPIM_P2_IO7
    ("G15", "XSPI_CLK", OUT),       # PN6  XSPIM_P2_CLK
    ("D14", "XSPI_CS_N", OUT),      # PN1  XSPIM_P2_NCS1
    ("J15", "XSPI_DQS", BI),        # PN0  XSPIM_P2_DQS0
    ("F14", "XSPI_NCLK", NCP),      # PN7  differential clk — unused (SDR/DTR NOR)
    ("K14", "XSPI_NCS2", NCP),      # PN12 second CS — unused
    # --- interrupt / data-ready inputs (R7: INT wired for every sensor) ----
    ("D12", "INT_VL53", IN),        # PE8
    ("B14", "INT_BNO", IN),         # PE1
    ("B15", "DRDY_ADS", IN),        # PE2
    ("A14", "INT_MAX", IN),         # PE0
    ("D11", "INT_AS7058", IN),      # PE15
    ("L1", "IRQ_A121", IN),         # PF2
    ("K1", "DRDY_MMC", IN),         # PF4
    ("K3", "INT_TMAG", IN),         # PF5
    ("M2", "INT_TCS", IN),          # PF7
    ("N1", "RDY_AS7331", IN),       # PF8
    ("K2", "INT_AS7421", IN),       # PF10
    ("N2", "INT_BMV", IN),          # PF11
    ("P1", "INT_ENS", IN),          # PF12
    # --- inter-MCU wake -----------------------------------------------------
    ("E2", "WAKE_IN", IN),          # PC13 — WKUP/tamper pin, Standby-capable
    ("N3", "WAKE_OUT", OUT),        # PF13
    # --- misc GPIO ----------------------------------------------------------
    ("L2", "EN_UV_REQ", OUT),       # PF14
    ("M1", "EN_WHITE", OUT),        # PF15
    ("M14", "RSTN_BNO", OUT),       # PG2
    ("P15", "LPN_VL53", OUT),       # PG10
    ("R13", "VCORE_SEL", OUT),      # PG13 — VOS-high (0.89V) request to core buck
    # --- unused GPIO balls (kept NC; available for H3 reallocation) ---------
    ("R14", "PA0_NC", NCP), ("P12", "PA2_NC", NCP), ("L15", "PA15_NC", NCP),
    ("C14", "PB0_NC", NCP), ("B12", "PD1_NC", NCP), ("A12", "PE7_NC", NCP),
    ("P9", "PG14_NC", NCP),
], description="STM32N657X0 app MCU + NPU, VFBGA142 — real ball map (VERIFIED-DS DS14791 Rev 9 Table 18)")

# HSE crystal for the N657 (USB HS PHY PLL + CSI/PLL reference; HSE range
# 16-48 MHz per DS14791 p13 — 48 MHz matches the ST N6 reference design).
# 3225 4-pad: 1/3 = crystal, 2/4 = GND. Load caps E0 (set per crystal CL).
XTAL_3225 = mkpart("XTAL_3225", "X", [
    (1, "X1", PAS), (2, "GND1", PWR), (3, "X2", PAS), (4, "GND2", PWR),
], description="48 MHz HSE crystal, 3225 (N657 USB-HS/CSI clock reference)")

# Octal xSPI NOR flash (MX25UW6445G-class, BGA24 / SOPB) — N6 is flashless.
# pinout E0
NOR_OCTAL = mkpart("NOR_OCTAL_XSPI", "U", _seq([
    ("VCC", PWR), ("VSS", PWR),
    ("CS_N", IN), ("CLK", IN), ("DQS", OUT), ("RESET_N", IN),
    ("DQ0", BI), ("DQ1", BI), ("DQ2", BI), ("DQ3", BI),
    ("DQ4", BI), ("DQ5", BI), ("DQ6", BI), ("DQ7", BI),
]), description="Octal xSPI NOR flash for STM32N657 (MX25UW6445G-class)")

# Ezurio BL54L15 module (nRF54L15) — always-on sentinel MCU + BLE.
# VERIFIED-DS EZ-DS-BL54L15 v1.9 Table 1 p10-13: real 39-pad map.
# GND = pads 1/16/27/39 (all must tie to the host GND plane, Table 1 Note 1);
# 26 = VDD_nRF (1.7-3.5 V normal voltage mode); 5 SWDIO, 6 SWDCLK, 7 NRESET
# (internal 13k pullup); 3 P2.08 (UARTE00 TXD), 4 P2.07 (UARTE00 RXD);
# 10 P2.01 (dedicated CLK pin -> I2C SCL), 9 P2.00 (SDA — adjacent pad, per
# Table 1 Note 2 data pins must sit close to their clock pin); 14 P1.03/NFC2,
# 15 P1.02/NFC1; 24/25 = XL2/XL1 optional 32.768 kHz crystal pads (reserved,
# NC in v1 — nRF54L15 has internal load caps); 31 P0.04 (GRTC LF-clock
# capable -> Geiger pulse timestamping). Remaining GPIO per-pin comments.
BL54L15 = mkpart("BL54L15", "U", [
    (26, "VCC", PWR),                        # VDD_nRF, 1.7-3.5 V
    (1, "GND", PWR), (16, "GND2", PWR), (27, "GND3", PWR), (39, "GND4", PWR),
    # SENTINEL_I2C master: BQ27427, BQ25620, IQS7222A, DRV2605L, accessory EEPROM
    (10, "SENT_SCL", BI),                    # P2.01 — dedicated clock pin
    (9, "SENT_SDA", BI),                     # P2.00
    # radiation pulse counting (comparator output, counts in ambient)
    (31, "GEIGER_PULSE_IN", IN),             # P0.04 (GRTC clock-capable)
    # power-tree enables (P1.x GPIO)
    (20, "EN_OPTICAL", OUT),                 # P1.07
    (21, "EN_AIR", OUT),                     # P1.06
    (22, "EN_CONTACT", OUT),                 # P1.05
    (23, "EN_RADAR", OUT),                   # P1.04
    (28, "EN_GNSS", OUT),                    # P1.10
    (29, "EN_WIFI", OUT),                    # P1.09
    (30, "EN_N6", OUT),                      # P1.08
    (32, "EN_FAN", OUT),                     # P1.14
    (33, "EN_ACC", OUT),                     # P1.13
    (34, "EN_HAPTIC", OUT),                  # P1.12
    (35, "INTERLOCK_OK", OUT),               # P1.11 — UV safety interlock (R5)
    # inter-MCU
    (3, "UART_TX", OUT),                     # P2.08 UARTE00 TXD
    (4, "UART_RX", IN),                      # P2.07 UARTE00 RXD
    (17, "WAKE_N6", OUT),                    # P0.00
    (18, "ATTN_FROM_N6", IN),                # P0.01
    # housekeeping interrupts
    (19, "TOUCH_RDY_IN", IN),                # P0.02 — IQS7222A RDY (wake source)
    (36, "GAUGE_INT_IN", IN),                # P0.03 — BQ27427 GPOUT
    (13, "CHG_INT_IN", IN),                  # P2.03 — BQ25620 /INT
    # glow ring PWM
    (2, "GLOW1", OUT),                       # P2.09
    (8, "GLOW2", OUT),                       # P2.02
    (11, "GLOW3", OUT),                      # P2.04
    (12, "GLOW4", OUT),                      # P2.05
    (37, "GLOW5", OUT),                      # P2.10
    (38, "GLOW6", OUT),                      # P2.06
    # NFC pins unused in v1 (antenna not fitted)
    (15, "NFC1", NCP),                       # P1.02/NFC1
    (14, "NFC2", NCP),                       # P1.03/NFC2
    # reserved for optional 32.768 kHz crystal (unfitted in v1)
    (25, "XL1", NCP), (24, "XL2", NCP),      # P1.00/XL1, P1.01/XL2
    # debug
    (5, "SWDIO", BI), (6, "SWCLK", IN), (7, "RESET_N", IN),
], description="Ezurio BL54L15 (nRF54L15) BLE sentinel module, 39-pad LGA (VERIFIED-DS EZ-DS v1.9 Table 1)")


# ============================================================================
# SENSORS — SPI
# ============================================================================

# VL53L8CH ToF 8x8 with CNH histograms, SPI mode.
# VERIFIED-DS DS14310 Rev 9 (real VL53L8CH DS) Table 3 p7: pin map is
# IDENTICAL to the VL53L8CX anchor (DS14161) — A1=GPIO1/INT, A2=LPn,
# A3=IOVDD, A4=SDA/MOSI, A5=SCL/MCLK, A6/A7=RSVD->GND, B1=GPIO2, B4=thermal
# pad->GND (AN5897), B7=CORE_1V8, C1=SPI_I2C_N, C2=NCS, C3/C7=GND,
# C4=AVDD(3.3V), C5=MISO, C6=RSVD->GND. SPI mode: C1 to IOVDD via 47k pullup;
# NCS needs its own 47k pullup to IOVDD (Table 3). No separate I2C_RST pin —
# C1 doubles as I2C-interface reset (toggle 0-1-0). Our I2C_RST model pin
# lands on GND-strapped RSVD.
# NOTE-ECO(H3): IOVDD is 1.2/1.8 V ONLY (DS14310 p1 features + Table 3 A3 —
# re-confirmed on the CH-specific DS); currently fed 3V3_OPTICAL — move
# IOVDD (+ CORE_1V8) to the 1V8 rail and level-shift or run SPI1 at 1.8V.
VL53L8CH = mkpart("VL53L8CH", "U", _seq([
    ("AVDD", PWR), ("IOVDD", PWR), ("GND", PWR),
    ("SCLK", IN), ("MOSI", IN), ("MISO", TRI), ("NCS", IN),
    ("SPI_I2C_N", IN),   # strap HIGH (47k to IOVDD) -> SPI mode  VERIFIED-DS p7
    ("I2C_RST", IN),     # legacy model pin -> RSVD/GND           VERIFIED-DS p7 (no such pin)
    ("LPN", IN), ("INT", OC),
]), description="ST VL53L8CH 8x8 ToF, SPI mode (straps in copper)")

# BNO086 IMU, SPI (SHTP) mode: PS1=HIGH, PS0/WAKE used as WAKE. pinout E0
# VERIFIED-DS BNO085 DS p9 Fig 1-5: PS1=1, PS0=1 -> SPI; p18: both pins must
# be high at reset, after which PS0 is repurposed as active-low WAKE (p19) —
# matches our 10k-pullup + host-GPIO topology. Real pins: 5=PS1, 6=PS0/WAKE
# (p10). I2C fallback addr would be 0x4A/0x4B via SA0 (p14). CLOSED.
BNO086 = mkpart("BNO086", "U", _seq([
    ("VDD", PWR), ("VDDIO", PWR), ("GND", PWR),
    ("PS0_WAKE", IN), ("PS1", IN),
    ("H_CSN", IN), ("H_SCLK", IN), ("H_MOSI", IN), ("H_MISO", TRI),
    ("H_INTN", OC), ("NRST", IN), ("BOOTN", IN),
]), description="CEVA/Bosch BNO086 IMU, SPI mode, raw+fused")

# ADS131M04 24-bit 4ch simultaneous delta-sigma ADC, WQFN-20-ish. pinout E0
ADS131M04 = mkpart("ADS131M04", "U", _seq([
    ("AVDD", PWR), ("DVDD", PWR), ("AGND", PWR), ("DGND", PWR),
    ("AIN0P", IN), ("AIN0N", IN),   # piezo (differential)
    ("AIN1P", IN), ("AIN1N", IN),   # PIN radiation charge-amp (energy proxy)
    ("AIN2P", IN), ("AIN2N", IN),   # accessory analog 2 / spare
    ("AIN3P", IN), ("AIN3N", IN),   # CO potentiostat VOUT / spare
    ("SCLK", IN), ("DIN", IN), ("DOUT", TRI), ("CS_N", IN),
    ("DRDY_N", OUT), ("SYNC_RESET_N", IN), ("CLKIN", IN),
]), description="TI ADS131M04 4ch 24b simultaneous ADC (piezo + PIN + spares)")

# Acconeer A121 60 GHz radar, fcCSP — SPI-only per DS. pinout E0
A121 = mkpart("A121", "U", _seq([
    ("VIO1", PWR), ("VIO2", PWR), ("GND", PWR),
    # VERIFIED-DS A121 DS v1.8 p10 Table 2: VRX/VTX/VDIG are 1.8 V rails
    # (abs-max 2.0 V — 3V3 would destroy them); VIO may be 1.8 V or 3.3 V
    # (abs-max 3.63 V). SPI is mode 0, max clock 50 MHz (p17 Table 12).
    # Model pins: VIO1=VIO (may stay 3V3_RADAR), VIO2=VDIG+VRX+VTX bundle.
    # NOTE-ECO(H3): feed VIO2 bundle from 1V8 (EN-gated / A121 ENABLE
    # hibernate), NOT from 3V3_RADAR as currently wired.
    ("SPI_SCLK", IN), ("SPI_MOSI", IN), ("SPI_MISO", TRI), ("SPI_SS_N", IN),
    ("INTERRUPT", OUT), ("ENABLE", IN),
]), description="Acconeer A121 pulsed coherent radar, Sparse-IQ raw")


# ============================================================================
# SENSORS — I2C-A (contact/thermal, 1 MHz capable)
# ============================================================================

# VERIFIED-DS MLX90642-Datasheet (DOC#3901090642 rev003) p4 Table 2:
# 1=SDA, 2=VDD, 3=GND, 4=SCL (old model had 2/3 SWAPPED — power-reversal bug).
# p16 Table 19: default slave address = 0x66 (EEPROM 0x11FE); 0x33 only if
# EEPROM SA is written to 0x00 (p6 NOTE 2). Package = TO-39 ("SF"), pin circle
# Ø5.84 with pins in two 45°-spaced pairs (p31 Fig 34) — generic TO-39-4
# footprint (90°, Ø5.08) does NOT fit -> generated/MLX90642_TO39.
MLX90642 = mkpart("MLX90642", "U", [
    (1, "SDA", BI), (2, "VDD", PWR), (3, "GND", PWR), (4, "SCL", BI),
], description="Melexis MLX90642 32x24 FIR array, TO-39, I2C-A 0x66 (VERIFIED-DS p16)")

# VERIFIED-DS MLX90632-Datasheet (DOC#3901090632 rev13) p8 Table 5:
# 1=SDA, 2=VDD, 3=GND, 4=SCL, 5=ADDR (LSB of addr; grounded -> 0x3A, p10
# Table 6 + p28). Order option code ...-000 (3.3V I2C level, p5). Pad 6 =
# central thermal pad (PCB footprint p47: 2.10x2.55 copper, 8 PTH vias) -> GND.
MLX90632 = mkpart("MLX90632", "U", [
    (1, "SDA", BI), (2, "VDD", PWR), (3, "GND", PWR), (4, "SCL", BI),
    (5, "ADDR", IN), (6, "EP", PWR),
], description="Melexis MLX90632 medical spot FIR, SFN 3x3, I2C-A 0x3A (ADDR=GND, VERIFIED-DS p10)")

MAX30102 = mkpart("MAX30102", "U", _seq([
    ("VDD", PWR),        # 1.8V analog supply
    ("VLED_P", PWR),     # LED supply (3.3V domain rail)
    ("GND", PWR), ("PGND", PWR),
    ("SDA", BI), ("SCL", BI), ("INT_N", OC),
]), description="MAX30102 PPG, I2C-A 0x57; VDD=1V8, VLED=3V3_CONTACT")
# pinout E0 (OLGA-14; unused NC pads omitted).
# VERIFIED-DS MAX30102 DS p2 (Abs Max): "All Other Pins to GND -0.3V to +6.0V"
# and p28: designed to be tolerant of any supply sequence -> SDA/SCL pulled to
# 3V3 with VDD=1.8V is within ratings. CLOSED.

AS7058 = mkpart("AS7058", "U", _seq([
    ("VDD", PWR), ("VDDIO", PWR), ("GND", PWR),
    ("SCL", BI), ("SDA", BI), ("INT", OUT),
    ("ECG_INP", IN), ("ECG_INN", IN), ("ECG_REF", OUT),
]), description="ams AS7058 PPG/ECG/BioZ AFE, I2C-A 0x30 # VERIFY addr (short DS silent)")
# pinout E0 (WLCSP42 subset). PARTIAL-DS AS7058_DS001085_short p9 Fig 2:
# WLCSP42 grid confirmed = rows A-G x cols 1-6, 0.4 mm pitch, die 2.545x2.815
# (footprint geometry now E1) — but the SHORT DS carries NO ball-signal map
# and NO I2C address. Full DS (DS001573) is NDA-gated; FAE contact queued.
# Digital pins are VIOVDD-referred (short DS p10 abs-max) -> 3.3V bus OK.


# ============================================================================
# SENSORS — I2C-B (air/optical/mag, 400 kHz)
# ============================================================================

BME688 = mkpart("BME688", "U", _seq([
    ("VDD", PWR), ("VDDIO", PWR), ("GND", PWR),
    ("SCK", BI), ("SDI", BI),
    ("SDO", IN),    # strap HIGH -> addr 0x77
    ("CSB", IN),    # strap HIGH -> I2C mode
]), description="Bosch BME688 gas/T/RH/P, I2C-B 0x77 (SDO=1)")  # pinout E0

SGP41 = mkpart("SGP41", "U", _seq([
    ("VDD", PWR), ("GND", PWR), ("SDA", BI), ("SCL", BI),
]), description="Sensirion SGP41 VOC/NOx, I2C-B 0x59 (fixed)")  # pinout E0

# VERIFIED-DS ENS161-Datasheet v1.1 p5 Table 1: 1 MOSI/SDA, 2 SCLK/SCL,
# 3 MISO/ADDR (high -> 0x53, low -> 0x52), 4 VDD, 5 VDDIO, 6 INTn, 7 CSn
# (high = I2C), 8+9 VSS. Abs-max p7: VDD 1.98V (1V8 rail correct), VDDIO 3.6V,
# SDA/SCL 3.6V-tolerant, ADDR/INTn/CSn VDDIO+0.3. LGA-9 = 3x3 GRID, pitch
# 1.05, pads 0.7 sq (p41 Table 40) -> generated/ENS161_LGA9 (E1).
ENS161 = mkpart("ENS161", "U", [
    (1, "SDA", BI), (2, "SCL", BI),
    (3, "ADDR", IN),      # strap HIGH -> 0x53  VERIFIED-DS p5
    (4, "VDD", PWR),      # 1.71-1.98V core     VERIFIED-DS p7
    (5, "VDDIO", PWR),    # IO supply (3V3 domain, <=3.6V)
    (6, "INT_N", OUT), (7, "CS_N", IN),
    (8, "GND", PWR), (9, "GND2", PWR),
], description="ScioSense ENS161 4-el MOX, I2C-B 0x53 (VERIFIED-DS p5); VDD=1V8")

SCD41 = mkpart("SCD41", "U", _seq([
    ("VDD", PWR), ("GND", PWR), ("SDA", BI), ("SCL", BI),
]), description="Sensirion SCD41 photoacoustic CO2, I2C-B 0x62 (fixed)")  # pinout E0

# VERIFIED-DS TCS3448 DS001121 v2-00: addr = 0x59 (Table 8 p19) — the AS7343
# family anchor 0x39 is REFUTED. 0x59 collides with SGP41 (fixed 0x59) on
# I2C-B -> device moved to I2C-A. Abs-max (Table 3 p9): VDD max 1.98 V and
# SCL/SDA max 1.98 V (1.2/1.8 V bus only!); INT and GPIO are 3.6 V tolerant.
# Pin map (Table 2 p8): 1 VDD, 2 SCL, 3 GND, 4 LDR (leave open if unused),
# 5 PGND, 6 GPIO (I2C bus-voltage select: >1.5V at startup -> 1.8V I/O; must
# NOT float, p21), 7 INT (OD, pull to 1.8V rec.), 8 SDA. OLGA8 3.1x2.0x1.0,
# land pattern Fig 11 p51 -> generated/TCS3448_OLGA8 (E1).
TCS3448 = mkpart("TCS3448", "U", [
    (1, "VDD", PWR), (2, "SCL", BI), (3, "GND", PWR), (4, "LDR", NCP),
    (5, "PGND", PWR), (6, "GPIO", IN), (7, "INT_N", OC), (8, "SDA", BI),
], description="ams TCS3448 14ch VIS spectral, I2C-A 0x59 (VERIFIED-DS p19); 1.8V-only part")

AS7331 = mkpart("AS7331", "U", _seq([
    ("VDD", PWR), ("GND", PWR), ("SDA", BI), ("SCL", BI),
    ("A0", IN), ("A1", IN),    # both LOW -> 0x74
    ("READY", OUT), ("SYN", IN),
]), description="ams AS7331 UV A/B/C, I2C-B 0x74 (A1A0=00)")  # pinout E0

# VERIFIED-DS AS7421 DS000667 v2-00: addr 0x64 CONFIRMED (Fig 21 p23).
# Pin map (Fig 3/4 p6-7): 1 INT (OD, pull to 1.8 or 3.3V), 2 VDD, 3 GND,
# 4/5 PGND, 6 LEDA (anode supply for the FOUR INTEGRATED NIR LEDs —
# 760/830/950/1040 nm, p10; there is NO external-LED sink pin), 7 RST
# (active-high, internal pulldown), 8 GPIO, 9 SDA, 10 SCL, 11 EP=GND,
# 12 EP=LEDA. Abs-max p8: VDD/LEDA 3.6V; SCL/SDA VDD+0.3 -> 3.3V bus OK.
# OLGA10 is 6.60 x 6.0 x 2.21 mm (p45-46) — NOT 3.5x3.5 as previously guessed.
AS7421 = mkpart("AS7421", "U", [
    (1, "INT", OC), (2, "VDD", PWR), (3, "GND", PWR),
    (4, "PGND1", PWR), (5, "PGND2", PWR), (6, "LEDA", PWR),
    (7, "RST", IN), (8, "GPIO", IN), (9, "SDA", BI), (10, "SCL", BI),
    (11, "EP_GND", PWR), (12, "EP_LEDA", PWR),
], description="ams AS7421 64ch NIR + 4 integrated NIR LEDs, I2C-B 0x64 (VERIFIED-DS p23)")

SHT41 = mkpart("SHT41", "U", _seq([
    ("VDD", PWR), ("GND", PWR), ("SDA", BI), ("SCL", BI),
]), description="Sensirion SHT41 ref T/RH, I2C-B 0x44 (fixed)")  # pinout E0

MMC5983MA = mkpart("MMC5983MA", "U", _seq([
    ("VDD", PWR), ("VDDIO", PWR), ("GND", PWR),
    ("SDA", BI), ("SCL", BI), ("INT_DRDY", OUT),
]), description="Memsic MMC5983MA nT mag, I2C-B 0x30")  # pinout E0

TMAG5273 = mkpart("TMAG5273", "U", [
    (1, "SCL", BI), (2, "GND", PWR), (3, "SDA", BI),
    (4, "INT_N", OC), (5, "VCC", PWR), (6, "NC", NCP),
    # SOT-23-6 # pinout E0 — verify pin order vs TMAG5273 DS
    # VERIFIED-DS tmag5273 p16 Table 6-2: TMAG5273A1 default 7-bit addr = 0x35
    # (A2 also 0x35; B1=0x22, C1=0x78, D1=0x44). Order the A1 variant. CLOSED.
], description="TI TMAG5273A1 hall, I2C-B 0x35 (VERIFIED-DS p16)")

BMV080 = mkpart("BMV080", "U", _seq([
    ("VDD", PWR), ("VDDIO", PWR), ("GND", PWR),
    ("SDA", BI), ("SCL", BI), ("IRQ", OUT),
    # VERIFIED-DS bst-bmv080-ds000 p26/p32: PS (protocol select) to VDDIO
    # selects I2C (low = SPI); CSB and MISO become address straps and must
    # not float: CSB=1 & MISO=1 -> addr 0x57 (Table 14, p32).
    ("PS", IN), ("CSB", IN), ("MISO_ADDR", IN),
]), description="Bosch BMV080 PM2.5, I2C-B 0x57 (VERIFIED-DS: PS=VDDIO, CSB=MISO=1)")  # pinout E0


# ============================================================================
# SENSORS/ANALOG — misc
# ============================================================================

# Large-area PIN photodiode (BPW34-class) — radiation detector (replaces BG51)
BPW34 = mkpart("PIN_BPW34", "D", [
    (1, "A", PAS), (2, "K", PAS),
], description="BPW34S-class large-area PIN photodiode, light-tight cavity")

# Charge-sensitive amplifier (OPA381-class placeholder) # pinout E0
OPA381 = mkpart("OPA381", "U", _seq([
    ("V+", PWR), ("V-", PWR), ("+IN", IN), ("-IN", IN), ("OUT", OUT),
]), description="OPA381-class transimpedance/charge amp for PIN detector")

# Fast comparator (TLV3201-class) # pinout E0
TLV3201 = mkpart("TLV3201", "U", _seq([
    ("V+", PWR), ("V-", PWR), ("+IN", IN), ("-IN", IN), ("OUT", OUT),
]), description="TLV3201-class comparator -> GEIGER_PULSE counting")

# RF shield can over the radiation front-end (guard net SHIELD_RAD)
SHIELD_CAN = mkpart("SHIELD_CAN", "SH", [
    (1, "S1", PAS), (2, "S2", PAS), (3, "S3", PAS), (4, "S4", PAS),
], description="Shield can, radiation charge-amp cavity (light-tight)")

# AD8317 RF log detector (module-level placeholder) # pinout E0
AD8317 = mkpart("AD8317", "U", _seq([
    ("VPOS", PWR), ("GND", PWR), ("INHI", IN), ("INLO", IN),
    ("VOUT", OUT), ("TADJ", PAS),
]), description="AD8317 1M-10GHz RF power detector -> N657 ADC_IN0")

# MEMS PDM microphone (bottom port) # pinout E0
PDM_MIC = mkpart("PDM_MIC", "MK", _seq([
    ("VDD", PWR), ("GND", PWR), ("CLK", IN), ("DATA", TRI), ("SEL", IN),
]), description="MEMS PDM mic, bottom port (heart/lung + acoustic)")

# u-blox MIA-M10Q GNSS SiP — VERIFIED-DS UBX-22015849 p9-11 Fig 2/Table 10:
# M-LGA53 (4.5x4.5x1.0, 53 pads Ø0.27 on sparse 9x9 grid, 0.5 pitch — p19
# Fig 4; land = 1:1 copper, mask Ø0.37, IM UBX-21028173 p83). Pads used here:
# B1 VCC, J4 V_IO (REQUIRED IO supply — was missing), J5 V_BCKP, J6 VIO_SEL
# (open = 3.3V V_IO), G1 TX, H1 RX, A7 TIMEPULSE, B9 RF_IN, A5 RTC_O (GND if
# unused), D2+E2 reserved pair (connect to each other), F9/G7 reserved
# (to GND — DS recommends 0R for dual-band/crystal-variant compat, fn17/18),
# C4 RESET_N (open), remaining pads = GND. All other reserved pads left open.
MIA_M10Q = mkpart("MIA_M10Q", "U", [
    ("B1", "VCC", PWR), ("J4", "V_IO", PWR), ("J5", "V_BCKP", PWR),
    ("J6", "VIO_SEL", IN), ("C4", "RESET_N", IN),
    ("G1", "TXD", OUT), ("H1", "RXD", IN), ("A7", "TIMEPULSE", OUT),
    ("B9", "RF_IN", IN),
    ("A5", "RTC_O", OUT), ("D2", "RSVD_D2", PAS), ("E2", "RSVD_E2", PAS),
    ("F9", "RSVD_F9", PAS), ("G7", "RSVD_G7", PAS),
] + [(p, f"GND_{p}", PWR) for p in
     ("A1", "A2", "A3", "A8", "A9", "B2", "B8", "C3", "C9", "E3", "E4", "E9",
      "F1", "F3", "F4", "G3", "G4", "G5", "G6", "H8", "J8", "J9")],
    description="u-blox MIA-M10Q GNSS (RAWX), UART + PPS, M-LGA53 (VERIFIED-DS p9-11)")

# GNSS chip antenna
ANT_GNSS = mkpart("ANT_GNSS", "AE", [
    (1, "FEED", PAS), (2, "GND", PAS),
], description="GNSS L1 chip antenna (keepout corner)")

# SGX-4CO electrochemical CO cell (3-electrode).
# VERIFIED-DS DS-0138 SGX-4CO Issue 3 p1 (outline): body Ø20 mm, height
# 16.50 + 3.90 mm pins; 3 pins Ø1.55 on a 13.5 mm PCD — Working top,
# Reference and Counter on the lower pair (drawing is a BOTTOM/pin-face
# view; footprint mirrors it for top-view placement). p3 note 1: do NOT
# glue or solder the pins — use PSB socket receptacles (warranty void
# otherwise) -> BOM: fit 3x Ø1.7 socket receptacles; cell is field-
# replaceable (R2 serviceability). Electricals p1: 70±20 nA/ppm output,
# 10 Ω recommended load, >24 months life in air, -30..+50 °C.
SGX_4CO = mkpart("SGX_4CO", "U", [
    (1, "WE", PAS), (2, "RE", PAS), (3, "CE", PAS),
], description="SGX 4-CO CO cell, 3x O1.55 pins on 13.5 PCD, SOCKET-MOUNT ONLY (VERIFIED-DS DS-0138 p1/p3)")

# LMP91000 potentiostat AFE for the CO cell.
# VERIFIED-DS LMP91000 SNAS506I p3 (Pin Functions, WSON-14): 1 DGND, 2 MENB
# (active-low module enable — may be tied to GND when it is the only
# LMP91000 on the bus, §7.5.2 p20), 3 SCL, 4 SDA, 5 NC (not internally
# connected), 6 VDD, 7 AGND, 8 VOUT, 9 C2, 10 C1, 11 VREF, 12 WE, 13 RE,
# 14 CE; DAP "connect to AGND" -> modeled as pin 15 EP. Old model was 11
# sequential pins with a single GND and NO VREF/NC — netlist binds pads by
# NUMBER, so it would have scrambled the WSON-14 footprint.
# I2C addr: fixed 7-bit 1001000 = 0x48 (§7.5.1 p20). Reference: REFCN
# register default 0x20 -> REF_SOURCE=0 = internal (VDD) reference
# (§7.6.4 p22); VREF pin is tied to the AIR rail via 0R so the external-ref
# option stays open at H3 (VREF must not float if ext mode is selected).
LMP91000 = mkpart("LMP91000", "U", [
    (1, "DGND", PWR), (2, "MENB_N", IN), (3, "SCL", BI), (4, "SDA", BI),
    (5, "NC", NCP), (6, "VDD", PWR), (7, "AGND", PWR), (8, "VOUT", OUT),
    (9, "C2", PAS), (10, "C1", PAS), (11, "VREF", IN),
    (12, "WE", PAS), (13, "RE", PAS), (14, "CE", PAS),
    (15, "EP", PWR),   # DAP -> AGND (VERIFIED-DS p3)
], description="TI LMP91000 potentiostat, I2C-B 0x48 (fixed) -> ADS AIN3 (VERIFIED-DS SNAS506I p3)")

# Piezo contact/vibration transducer (2-pad)
PIEZO = mkpart("PIEZO", "PZ", [
    (1, "P1", PAS), (2, "P2", PAS),
], description="Piezo disc, contact vibration -> ADS131M04 AIN0 diff")


# ============================================================================
# POWER
# ============================================================================

# Cypress/Infineon CYPD3177 USB-C PD sink controller (BCR).
# VERIFIED-DS 002-25383 Rev*B Table 1 p5-6: real QFN-24 pin numbers below.
# Straps are resistor DIVIDERS from VDDD (internal 3.3V LDO out, pin 23,
# needs 1uF + 2x100nF; VCCD pin 24 needs 1uF), NOT single resistors to GND
# (old model was wrong). Divider tables p8: Table 2 (VBUS_MIN/MAX),
# Table 3/4 (ISNK coarse/fine). FAULT (pin 9) is driven HIGH on fault —
# not an open-drain active-low. Package: QFN-24 4x4 P0.5, EP 2.75 typ (p20).
# D+/D- (16/17) leave unconnected; VBUS_FET_EN/SAFE_PWR_EN/VDC_OUT unused —
# VBUS_C feeds the BQ25620 input directly (charger tolerates the 9V contract).
CYPD3177 = mkpart("CYPD3177", "U", [
    (18, "VBUS", PWR), (19, "GND", PWR), (22, "VSS", PWR), (25, "EP", PWR),
    (15, "CC1", BI), (14, "CC2", BI),
    (23, "VDDD", PWO), (24, "VCCD", PWO),
    (1, "VBUS_MIN", IN), (2, "VBUS_MAX", IN),     # divider-strap voltage window
    (5, "ISNK_COARSE", IN), (6, "ISNK_FINE", IN), # divider-strap current request
    (9, "FAULT", OUT), (10, "FLIP", OUT),  # both actively driven high/low (p6)
], description="CYPD3177 autonomous USB-C PD sink; VDDD dividers request 5-9V/3A (VERIFIED-DS p8)")

# TI BQ25620 I2C buck charger — VERIFIED-DS SLUSEG2D Table 6-1 p5-6:
# WQFN-18 "RYK" 2.5x3.0 (NOT WQFN-16 RTE 3x3 as previously footprinted).
# 1 BTST (47nF to SW), 2 REGN (4.7uF), 3 PG (OD, opt.), 4 D-, 5 D+ (BC1.2
# detect, may float — PD contract sets input), 6 TS, 7 QON (internal pullup),
# 8 BAT, 9 SYS, 10 STAT (float if unused), 11 INT, 12 SDA, 13 SCL, 14 CE
# (must not float), 15 GND, 16 SW, 17 PMID, 18 VBUS. Addr 0x6B (p37/p39).
BQ25620 = mkpart("BQ25620", "U", [
    (18, "VBUS", PWR), (17, "PMID", PAS), (2, "REGN", PWO),
    (16, "SW", OUT), (1, "BTST", PAS),
    (9, "SYS", PWO), (8, "BAT", PWR),
    (12, "SDA", BI), (13, "SCL", BI), (11, "INT_N", OC), (14, "CE_N", IN),
    (6, "TS", IN), (7, "QON_N", IN), (15, "GND", PWR),
    (3, "PG_N", OC), (4, "DM", BI), (5, "DP", BI), (10, "STAT", OC),
], description="TI BQ25620 3.5A charger, ~1C fast charge, SENTINEL_I2C 0x6B (VERIFIED-DS)")

# TI BQ27427 fuel gauge — VERIFIED-DS SLUSEB5B Table 4-1 p3 + Fig 4-1:
# DSBGA-9 balls A1 GPOUT, A2 SDA, A3 SCL, B1 BIN, B2 VSS, B3 VDD, C1 VSS,
# C2 SRX, C3 BAT. Sense topology is HIGH-side: internal 7mΩ sits between
# BAT (Kelvin to pack+) and SRX (to system rail VSYS side) — NOT low-side.
# VDD is the internal 1.8V LDO OUTPUT (2.2uF to VSS), never a supply input.
# BIN: embedded pack -> 10k pulldown to VSS (never short to rail, p3).
# SDA/SCL/GPOUT open-drain, VPU 1.62-3.6V (p4) -> 3.3V AON pullups legal.
# Addr fixed 0x55 (1010101, p16).
BQ27427 = mkpart("BQ27427", "U", [
    ("B3", "VDD", PWO),              # 1.8V LDO output (cap only)
    ("B1", "BIN", IN),               # battery-insertion detect (10k to VSS)
    ("C3", "BAT", PWR),              # Kelvin sense to pack+ (PACKP)
    ("C2", "SRX", PAS),              # system-rail side of internal 7mΩ
    ("A2", "SDA", BI), ("A3", "SCL", BI), ("A1", "GPOUT", OC),
    ("B2", "VSS", PWR), ("C1", "VSS2", PWR),
], description="TI BQ27427 gauge, SENTINEL_I2C 0x55; HIGH-side 7mΩ sense (VERIFIED-DS p3)")

# TI BQ29700 1S protector — VERIFIED-DS bq2970_family Table 5-1 p3 (DSE
# WSON-6): 1 NC, 2 COUT, 3 DOUT, 4 VSS, 5 BAT(VDD), 6 V-(VM). 330Ω VDD
# series R confirmed (p14: also limits current on reverse connection).
BQ29700 = mkpart("BQ29700", "U", [
    (5, "VDD", PWR), (4, "VSS", PWR),
    (6, "VM", IN),                      # charger-negative sense
    (2, "COUT", OUT), (3, "DOUT", OUT), # charge / discharge FET gates
    (1, "NC", NCP),
], description="TI BQ29700 1S Li+ protector (with dual NMOS) (VERIFIED-DS p3)")

# Dual common-drain NMOS for protection (CSD-class) # pinout E0
DUAL_NFET = mkpart("DUAL_NFET_PROT", "Q", _seq([
    ("S1", PAS), ("G1", IN), ("D1", PAS),
    ("D2", PAS), ("G2", IN), ("S2", PAS),
]), description="Dual NMOS, battery protection series pair (low-side)")

# TPS62840 60nA-IQ buck -> 3V3_AON.
# VERIFIED-DS SLVSEC6D p4-5 Pin Functions (DLC SON-8): 1 GND, 2 VIN, 3 MODE
# (must be terminated), 4 EN, 5 VSET (RSET to GND sets VOUT — 267k -> 3.3V,
# Table 1 p22), 6 STOP, 7 SW, 8 VOS. Old model had no VSET (output voltage
# was undefined!) and no STOP.
TPS62840 = mkpart("TPS62840", "U", [
    (2, "VIN", PWR), (1, "GND", PWR),
    (4, "EN", IN), (7, "SW", OUT), (8, "VOS", IN), (3, "MODE", IN),
    (5, "VSET", IN), (6, "STOP", IN),
], description="TI TPS62840DLC, 60nA IQ, 3V3_AON (VSET=267k, VERIFIED-DS p22)")

# TPS62823 3A buck (x2: VDD_CORE_N6 and 3V3_SYS).
# VERIFIED-DS SLVSDV6C p3 Pin Functions: 1 EN, 2 FB, 3 AGND, 4 NC, 5 PGND,
# 6 SW, 7 VIN, 8 PG (float if unused). There is NO MODE pin (old model had
# a phantom one); power-save transition is automatic.
TPS62823 = mkpart("TPS62823", "U", [
    (7, "VIN", PWR), (3, "AGND", PWR), (5, "PGND", PWR),
    (1, "EN", IN), (6, "SW", OUT), (2, "FB", IN),
    (8, "PG", OC), (4, "NC", NCP),
], description="TI TPS62823 3A buck (VERIFIED-DS p3)")

# TLV62568 1A buck -> 1V8 (SOT-23-5).
# VERIFIED-DS SLVSD89B p3 Pin Functions (DBV): 1 EN, 2 GND, 3 SW, 4 VIN,
# 5 FB — old model had 3=VIN/4=FB/5=SW (wrong).
TLV62568 = mkpart("TLV62568", "U", [
    (1, "EN", IN), (2, "GND", PWR), (3, "SW", OUT), (4, "VIN", PWR), (5, "FB", IN),
], description="TI TLV62568 1A buck -> 1V8 (VERIFIED-DS p3)")

# TPS22916 load switch — VERIFIED-DS SLVSDO5F p3 Table 5-1 (YFP WCSP-4,
# 0.78x0.78, 0.4 pitch): A1 VOUT, A2 VIN, B1 GND, B2 ON.
TPS22916 = mkpart("TPS22916", "U", [
    ("A2", "VIN", PWR), ("B1", "GND", PWR), ("B2", "ON", IN), ("A1", "VOUT", PWO),
], description="TI TPS22916 load switch (per-domain power gating) (VERIFIED-DS p3)")

# Signal/load NFET (AO3400/DMN-class) for LED / fan drive
NFET_SOT23 = mkpart("NFET_SOT23", "Q", [
    (1, "G", IN), (2, "S", PAS), (3, "D", PAS),
], description="N-ch FET, SOT-23 (LED / fan low-side drive)")

# Single AND gate for the UV interlock (74LVC1G08) # pinout E0
AND_1G08 = mkpart("74LVC1G08", "U", [
    (1, "A", IN), (2, "B", IN), (3, "GND", PWR), (4, "Y", OUT), (5, "VCC", PWR),
    # pinout E0 — verify SOT-353 order
], description="Single AND: EN_UV_REQ & INTERLOCK_OK -> UV LED gate (R5)")


# ============================================================================
# IO / HUMAN
# ============================================================================

# Azoteq IQS7222A cap touch — VERIFIED-DS IQS7222A DS v1.7 p6-7 Table 2.2/2.3
# (QFN20 3x3 P0.4): 1 VDD, 2 VREGD, 3 VSS, 4 VREGA, 5-12 CRx0-7, 13 CTx8,
# 14 OUTA, 15/16 NC, 17 RDY, 18 SCL, 19 SDA, 20 MCLR (internal 200k pullup),
# 21 = thermal TAB (recommend VSS). Each VREG pin needs 2.2uF (p45 §12.1.2).
# Addr: 0x44 for order code ...001, 0x57 for ...102 (p... §9.2) — ORDER THE
# 001 VARIANT. NOTE: QFN20 has only NINE sensor pins (CRx0-7 + CTx8), not 12.
IQS7222A = mkpart("IQS7222A", "U", [
    (1, "VDDHI", PWR), (2, "VREGD", PAS), (3, "GND", PWR), (4, "VREGA", PAS),
    (19, "SDA", BI), (18, "SCL", BI), (17, "RDY", OC), (20, "MCLR_N", IN),
    (5, "E0", PAS), (6, "E1", PAS), (7, "E2", PAS), (8, "E3", PAS),
    (9, "E4", PAS), (10, "E5", PAS), (11, "E6", PAS), (12, "E7", PAS),
    (13, "E8", PAS),   # CTx8 (Tx-only pad)
    (14, "OUTA", TRI), (15, "NC1", NCP), (16, "NC2", NCP), (21, "EP", PWR),
], description="Azoteq IQS7222A-001 touch, SENTINEL_I2C 0x44 (VERIFIED-DS; avoids SHT41 0x44 on I2C-B)")

# TI DRV2605L haptic driver — VERIFIED-DS SLOS854D p5 Pin Functions (DGS
# VSSOP-10): 1 REG (1.8V LDO out, 1uF required — was missing), 2 SCL, 3 SDA,
# 4 IN/TRIG (tie to GND if unused), 5 EN, 6 VDD/NC (tie to VDD or float),
# 7 OUT+, 8 GND, 9 OUT-, 10 VDD (1uF).
DRV2605L = mkpart("DRV2605L", "U", [
    (10, "VDD", PWR), (8, "GND", PWR), (6, "VDD_NC", PWR), (1, "REG", PWO),
    (3, "SDA", BI), (2, "SCL", BI), (5, "EN", IN), (4, "IN_TRIG", IN),
    (7, "OUT_P", OUT), (9, "OUT_N", OUT),
], description="TI DRV2605L LRA driver, SENTINEL_I2C 0x5A (VERIFIED-DS p5)")

# Electrode pad (ECG / touch shell electrodes)
ELECTRODE = mkpart("ELECTRODE", "E", [
    (1, "E", PAS),
], description="Exposed electrode pad (ECG contact / return)")


# ============================================================================
# CONNECTORS
# ============================================================================

J_BATT = mkpart("CONN_BATT_3P", "J", [
    (1, "BATT+", PAS), (2, "NTC", PAS), (3, "BATT-", PAS),
], description="1S LiPo battery connector (JST-ACH class) + pack NTC")

# USB-C 16P receptacle (GCT USB4105-GF-A)
USB_C_16P = mkpart("USB_C_16P", "J", [
    ("A1", "GND_A1", PWR), ("A4", "VBUS_A4", PWR),
    ("A5", "CC1", BI), ("A6", "DP1", BI), ("A7", "DN1", BI), ("A8", "SBU1", PAS),
    ("A9", "VBUS_A9", PWR), ("A12", "GND_A12", PWR),
    ("B1", "GND_B1", PWR), ("B4", "VBUS_B4", PWR),
    ("B5", "CC2", BI), ("B6", "DP2", BI), ("B7", "DN2", BI), ("B8", "SBU2", PAS),
    ("B9", "VBUS_B9", PWR), ("B12", "GND_B12", PWR),
    ("S1", "SHIELD", PAS),
], description="USB-C 16P receptacle, GCT USB4105 class")

J_POGO = mkpart("CONN_POGO_6P", "J", [
    (1, "VACC", PAS), (2, "GND", PWR), (3, "SDA", BI),
    (4, "SCL", BI), (5, "AN1", PAS), (6, "AN2", PAS),
], description="Magnetic 6-pogo accessory port (ADR-0002): pwr+I2C-ID+2 analog")

# 24-pin FPC for VD66GY camera module (DNP)
J_CAM_24P = mkpart("CONN_FPC_24P", "J",
    [(i, f"P{i}", PAS) for i in range(1, 25)],
    description="24p FPC, VD66GY camera (MIPI CSI-2) — DNP in v1")

TC2030 = mkpart("TC2030", "J", [
    (1, "VTREF", PWR), (2, "SWDIO", BI), (3, "NRST", PAS),
    (4, "SWCLK", PAS), (5, "GND", PWR), (6, "SWO", PAS),
], description="Tag-Connect TC2030-IDC-NL SWD footprint (no BOM cost)")

J_SMA = mkpart("SMA_EDGE", "J", [
    (1, "SIG", PAS), (2, "GND", PWR),
], description="SMA, RF survey input -> AD8317")

J_FAN = mkpart("CONN_FAN_2P", "J", [
    (1, "FAN+", PWR), (2, "FAN-", PAS),
], description="Blower fan (Sunon UB3F3-500 class), low-side switched")

J_LRA = mkpart("CONN_LRA_2P", "J", [
    (1, "OUT+", PAS), (2, "OUT-", PAS),
], description="LRA haptic actuator pads")

J_TOUCH_FPC = mkpart("CONN_TOUCH_13P", "J",
    [(i, f"E{i-1}", PAS) for i in range(1, 13)] + [(13, "GND", PWR)],
    description="Shell touch-electrode flex, 12 electrodes + guard GND")
