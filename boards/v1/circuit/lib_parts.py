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
# OPT124 bits + VDDIOxVRSEL registers must match the chosen rail voltages —
# fw config for this board: VDD=3.3V (OPT124 bit17/VDDIOVRSEL), VDDIO3=1.8V
# (bit15/VDDIO3VRSEL), VDDIO4=3.3V (bit14/VDDIO4VRSEL). VFBGA142 bonds no
# VDDIO2/VDDIO5 balls (Table 18 fn5/10 pins absent on the 142 column).
# H3.0 1.8V-IO ECO: the two unused PN-port balls (VDDIO3 = 1.8V domain,
# Table 18 fn9) are repurposed as native-1.8V GPIO for the VL53L8CH:
#   PN7  (F14, XSPIM_P2_NCLK unused — single-ended NOR) -> INT_VL53 input
#   PN12 (K14, XSPIM_P2_NCS2 unused)                    -> LPN_VL53 output
# PN7 is a boot-ROM pin (fn7) but only as XSPI NCLK output during flash
# boot — legal against the open-drain INT + 47k pullup (OPTICAL domain is
# off at boot). This removes any 3.3V drive into the 1.8V-only VL53 pins
# without spending shifter channels; PE8/PG10 return to the spare pool.
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
    # --- interrupt / data-ready inputs (R7: INT wired for every sensor) ----
    ("F14", "INT_VL53", IN),        # PN7 — VDDIO3 (1.8V) domain GPIO, H3.0 ECO
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
    ("K14", "LPN_VL53", OUT),       # PN12 — VDDIO3 (1.8V) domain GPIO, H3.0 ECO
    ("R13", "VCORE_SEL", OUT),      # PG13 — VOS-high (0.89V) request to core buck
    # --- unused GPIO balls (kept NC; available for H3 reallocation) ---------
    ("R14", "PA0_NC", NCP), ("P12", "PA2_NC", NCP), ("L15", "PA15_NC", NCP),
    ("C14", "PB0_NC", NCP), ("B12", "PD1_NC", NCP), ("A12", "PE7_NC", NCP),
    ("P9", "PG14_NC", NCP),
    ("D12", "PE8_NC", NCP),         # freed by INT_VL53 -> PN7 (H3.0)
    ("P15", "PG10_NC", NCP),        # freed by LPN_VL53 -> PN12 (H3.0)
], description="STM32N657X0 app MCU + NPU, VFBGA142 — real ball map (VERIFIED-DS DS14791 Rev 9 Table 18)")

# HSE crystal for the N657 (USB HS PHY PLL + CSI/PLL reference; HSE range
# 16-48 MHz per DS14791 p13 — 48 MHz matches the ST N6 reference design).
# 3225 4-pad: 1/3 = crystal, 2/4 = GND. Load caps E0 (set per crystal CL).
XTAL_3225 = mkpart("XTAL_3225", "X", [
    (1, "X1", PAS), (2, "GND1", PWR), (3, "X2", PAS), (4, "GND2", PWR),
], description="48 MHz HSE crystal, 3225 (N657 USB-HS/CSI clock reference)")

# Octal xSPI NOR flash (MX25UW6445G-class, BGA24 / SOPB) — N6 is flashless.
# pinout E0 — BOTH the symbol numbering AND the generated numeric-pad BGA24
# footprint are placeholders that agree by construction (pins 1-14 <-> pads
# 1-14); pads 15-24 declared NC-pending. Renumber symbol + footprint
# together to the real MX25UW ball map when the Macronix DS is staged
# (docs/MISSING_VENDOR_ASSETS.md).
NOR_OCTAL = mkpart("NOR_OCTAL_XSPI", "U", _seq([
    ("VCC", PWR), ("VSS", PWR),
    ("CS_N", IN), ("CLK", IN), ("DQS", OUT), ("RESET_N", IN),
    ("DQ0", BI), ("DQ1", BI), ("DQ2", BI), ("DQ3", BI),
    ("DQ4", BI), ("DQ5", BI), ("DQ6", BI), ("DQ7", BI),
]) + [(n, f"PEND_{n}", NCP) for n in range(15, 25)],
    description="Octal xSPI NOR flash for STM32N657 (MX25UW6445G-class; pins PROVISIONAL-E0)")

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
# ECO EXECUTED (H3.0): IOVDD is 1.2/1.8 V ONLY (DS14310 p1 features + Table 3
# A3) — IOVDD + CORE_1V8 now fed from the gated 1V8_OPTICAL sub-rail;
# AVDD stays 3.3 V (3V3_OPTICAL). VERIFIED-DS DS14310 §3.3 p11: the device
# requires THREE supplies (AVDD 3.3V fixed, CORE_1V8 1.8V fixed, IOVDD
# 1.2/1.8V) and "if IOVDD is 1.8V, the same supply may be used for both
# IOVDD and CORE_1V8"; supplies may be applied in any order — so the gated
# 3.3/1.8 pair needs no sequencing parts. The old model had NO CORE_1V8 pin
# (the part would have been held in reset): pin added. SPI level shift:
# TXU0304 (see sensors_spi.py); INT/LPn go native-1.8V to N657 PN7/PN12.
# H3.2 pad-binding fix: symbol renumbered from sequential 1-12 to the REAL
# substrate pad names (the footprint pads are named A1..C7 — the netlist
# binds by NUMBER, so the sequential symbol left every VL53 pad netless).
# VERIFIED-DS DS14310 Rev 9 Table 3 p7 (full 17-pad list re-extracted):
# A1 GPIO1(INT), A2 LPn, A3 IOVDD, A4 SDA/MOSI, A5 SCL/MCLK, A6 RSVD1->GND,
# A7 RSVD2->GND, B1 GPIO2 (defaults OD tristate; 47k pullup to IOVDD
# REQUIRED, used as SYNC input — Fig 5 p8 shows the pullup fitted even when
# unused), B4 thermal pad->GND (AN5897), B7 CORE_1V8, C1 SPI_I2C_N,
# C2 NCS, C3 GND, C4 AVDD, C5 MISO, C6 RSVD3->GND, C7 Ground.
VL53L8CH = mkpart("VL53L8CH", "U", [
    ("C4", "AVDD", PWR), ("A3", "IOVDD", PWR), ("B7", "CORE_1V8", PWR),
    ("C3", "GND", PWR), ("C7", "GND2", PWR),
    ("A6", "RSVD1", PWR), ("A7", "RSVD2", PWR), ("C6", "RSVD3", PWR),  # ->GND p7
    ("B4", "THERMAL", PWR),                       # ->GND plane (AN5897)
    ("A5", "SCLK", IN), ("A4", "MOSI", IN), ("C5", "MISO", TRI), ("C2", "NCS", IN),
    ("C1", "SPI_I2C_N", IN),  # strap HIGH (47k to IOVDD) -> SPI  VERIFIED-DS p7
    ("B1", "GPIO2", OC),      # SYNC in / OD out — 47k pullup to IOVDD req'd (p7)
    ("A2", "LPN", IN), ("A1", "INT", OC),
], description="ST VL53L8CH 8x8 ToF, SPI mode; AVDD 3.3V + IOVDD/CORE 1.8V; real A1..C7 pads (VERIFIED-DS DS14310 Table 3 p7)")

# BNO086 IMU, SPI (SHTP) mode: PS1=HIGH, PS0/WAKE used as WAKE.
# H3.2 pad-binding fix: symbol renumbered from sequential 1-12 to the REAL
# LGA-28 map — VERIFIED-DS BNO08x-Datasheet v1.17 Fig 1-6 p10:
# 1/7/8/12/13/21/22/23/24 = RESV ("Reserved. No connect."), 2/25 GND,
# 3 VDD, 28 VDDIO, 4 BOOTN (10k pullup to VDDIO, note 4 p18), 5 PS1,
# 6 PS0/WAKE (host GPIO, notes 5/6 p18-19), 9 CAP (100nF to GND — was
# MISSING from the model), 10 CLKSEL0 (internal pulldown; p11 Fig 1-8:
# 0 = 32k crystal [not fitted!] -> must strap HIGH for the internal
# oscillator, legal for SPI — was MISSING: the part would have waited for
# an absent crystal), 11 NRST, 14 H_INTN, 15/16 ENV_SCL/ENV_SDA (must be
# pulled up even with no environmental sensor fitted — note 7 p19, "SW
# polls for sensors at reset"; pullups were MISSING), 17 SA0/H_MOSI,
# 18 H_CSN, 19 H_SCL/SCK/RX, 20 H_SDA/H_MISO/TX, 26 XOUT32/CLKSEL1
# (internal pulldown, low/NC = internal osc), 27 XIN32 (unused, NC).
BNO086 = mkpart("BNO086", "U", [
    (3, "VDD", PWR), (28, "VDDIO", PWR), (2, "GND", PWR), (25, "GND2", PWR),
    (6, "PS0_WAKE", IN), (5, "PS1", IN),
    (18, "H_CSN", IN), (19, "H_SCLK", IN), (17, "H_MOSI", IN), (20, "H_MISO", TRI),
    (14, "H_INTN", OC), (11, "NRST", IN), (4, "BOOTN", IN),
    (9, "CAP", PAS),          # 100nF to GND (Fig 1-6 p10)
    (10, "CLKSEL0", IN),      # strap HIGH = internal osc (Fig 1-8 p11)
    (15, "ENV_SCL", BI), (16, "ENV_SDA", BI),  # pullup req'd, no sensor (p19 n7)
    (26, "XOUT32_CLKSEL1", NCP), (27, "XIN32", NCP),  # internal-osc mode: unused
    (1, "RESV1", NCP), (7, "RESV7", NCP), (8, "RESV8", NCP), (12, "RESV12", NCP),
    (13, "RESV13", NCP), (21, "RESV21", NCP), (22, "RESV22", NCP),
    (23, "RESV23", NCP), (24, "RESV24", NCP),
], description="CEVA BNO086 IMU, SPI mode, raw+fused; real LGA-28 map (VERIFIED-DS BNO08x DS Fig 1-6 p10)")

# ADS131M04 24-bit 4ch simultaneous delta-sigma ADC.
# H3.2 pad-binding fix: package CONFIRMED as the RUK WQFN-20 3x3 0.4-pitch
# (VERIFIED-DS SBAS890D mech. drawing RUK0020B — exact match for the
# QFN-20-1EP_3x3mm_P0.4mm footprint in use; the only other package is
# TSSOP-20 PW with DIFFERENT pin numbers). Symbol renumbered from the
# sequential E0 order to the real RUK map — VERIFIED-DS Table 5-1 p4 (WQFN
# column): 1 AIN0P, 2 AIN0N, 3 AIN1N, 4 AIN1P, 5 AIN2P, 6 AIN2N, 7 AIN3N,
# 8 AIN3P, 9 SYNC/RESET, 10 CS, 11 DRDY, 12 SCLK, 13 DOUT, 14 DIN,
# 15 CLKIN, 16 CAP (digital LDO out, 220nF to DGND — was MISSING from the
# model), 17 DGND, 18 DVDD, 19 AVDD, 20 AGND; thermal pad (21) -> AGND.
ADS131M04 = mkpart("ADS131M04", "U", [
    (19, "AVDD", PWR), (18, "DVDD", PWR), (20, "AGND", PWR), (17, "DGND", PWR),
    (1, "AIN0P", IN), (2, "AIN0N", IN),   # piezo (differential)
    (4, "AIN1P", IN), (3, "AIN1N", IN),   # PIN radiation charge-amp (energy proxy)
    (5, "AIN2P", IN), (6, "AIN2N", IN),   # accessory analog 2 / spare
    (8, "AIN3P", IN), (7, "AIN3N", IN),   # CO potentiostat VOUT / spare
    (12, "SCLK", IN), (14, "DIN", IN), (13, "DOUT", TRI), (10, "CS_N", IN),
    (11, "DRDY_N", OUT), (9, "SYNC_RESET_N", IN), (15, "CLKIN", IN),
    (16, "CAP", PWO),                     # digital LDO out — 220nF to DGND (p4)
    (21, "EP", PWR),                      # thermal pad -> AGND (Table 5-1 p4)
], description="TI ADS131M04 4ch 24b ADC, WQFN-20 RUK real pin map (VERIFIED-DS SBAS890D Table 5-1 p4)")

# Acconeer A121 60 GHz radar, fcCSP50 — SPI-only per DS.
# H3.2 pad-binding fix: symbol rebuilt on the REAL 50-ball map (the 9-pin
# sequential E0 symbol left all 50 footprint pads netless). VERIFIED-DS
# A121-Datasheet v1.8 Table 1 p8-9 + Fig 3.1 p7: VRX = C2/D1, VTX = C9/D10,
# VDIG = J9, VIO = K9 (all supplies); SPI_SS J2, SPI_CLK K2, SPI_MISO K3,
# SPI_MOSI K6, INTERRUPT K8, ENABLE F10; RESET_N J1 "must be connected to
# VIO"; XIN J10 / XOUT H10 — the built-in oscillator REQUIRES an external
# 24 MHz crystal (p9 + §6.2 p19: BOM Table 13 = X1 24MHz + C5/C6 tuning
# caps; 8pF for CL=9pF/Cstray=5pF example) — the old model had NO crystal:
# the sensor would never clock. Grounded-by-DS balls: 27x GND ("solid
# ground plane"), Analog0 A2 / Analog1 B1 ("NC or ground; ground
# recommended"), CTRL A9 + GPIO1 F1 + GPIO2 H1 + GPIO3 B10 + GPIO4 K5
# ("for future use, connect to ground"), PLL_RF_TEST E10 ("must be
# connected to solid ground plane").
# Rails (VERIFIED-DS p10 Table 2): VRX/VTX/VDIG 1.8V-only (abs-max 2.0V,
# VRX/VTX must never exceed VDIG — trivially met, shared rail); VIO 1.8 or
# 3.3V. ECO H3.0: VRX/VTX/VDIG <- gated 1V8_RADAR; VIO <- 3V3_RADAR.
A121 = mkpart("A121", "U", [
    ("K9", "VIO", PWR),
    ("J9", "VDIG", PWR), ("C2", "VRX1", PWR), ("D1", "VRX2", PWR),
    ("C9", "VTX1", PWR), ("D10", "VTX2", PWR),
    ("K2", "SPI_SCLK", IN), ("K6", "SPI_MOSI", IN), ("K3", "SPI_MISO", TRI),
    ("J2", "SPI_SS_N", IN),
    ("K8", "INTERRUPT", OUT), ("F10", "ENABLE", IN),
    ("J1", "RESET_N", IN),        # "must be connected to VIO" (Table 1 p8)
    ("J10", "XIN", PAS), ("H10", "XOUT", PAS),   # 24MHz crystal (§6.2 p19)
    # DS-mandated grounds: Analog0/1, CTRL, GPIO1-4, PLL_RF_TEST (Table 1 p8)
    ("A2", "ANALOG0", PWR), ("B1", "ANALOG1", PWR), ("A9", "CTRL", PWR),
    ("F1", "GPIO1", PWR), ("H1", "GPIO2", PWR), ("B10", "GPIO3", PWR),
    ("K5", "GPIO4", PWR), ("E10", "PLL_RF_TEST", PWR),
] + [(b, f"GND_{b}", PWR) for b in
     ("A3", "A4", "A5", "A6", "A7", "A8", "B2", "B9", "C1", "C10", "D2", "D9",
      "E1", "E2", "E9", "F2", "F9", "G1", "G10", "H2", "H9", "J3", "J5", "J6",
      "J8", "K4", "K7")],
    description="Acconeer A121 radar, real fcCSP50 ball map + 24MHz XTAL (VERIFIED-DS v1.8 Table 1 p8-9)")


# ============================================================================
# LEVEL TRANSLATION (H3.0 1.8V-IO ECOs)
# ============================================================================

# TXU0304 — 4-bit fixed-direction translator (3x A->B, 1x B->A), used for the
# VL53L8CH SPI branch: SCLK/MOSI/NCS down to 1.8V, MISO up to 3.3V.
# Direction-fixed (not TXB auto-sense) = clean push-pull SPI to >50MHz and
# Ioff/partial-power-down: with VCCB (1V8_OPTICAL) gated off the B port is
# Hi-Z, so the shifter doubles as bus isolation for the powered-down domain.
# pinout E0 — TXU0304 DS (TI SCDS41x) not staged; TSSOP-14 pin numbers are
# PROVISIONAL, verify before H3.2 pad binding (docs/MISSING_VENDOR_ASSETS.md).
TXU0304 = mkpart("TXU0304", "U", _seq([
    ("VCCA", PWR), ("A1", IN), ("A2", IN), ("A3", IN),   # 3.3V side inputs
    ("A4", TRI),                                          # 3.3V side output (MISO up)
    ("NC1", NCP), ("GND", PWR), ("NC2", NCP),
    ("B4", IN),                                           # 1.8V side input (MISO)
    ("B3", OUT), ("B2", OUT), ("B1", OUT),                # 1.8V side outputs
    ("CE", IN), ("VCCB", PWR),
]), description="TI TXU0304 4-bit fixed-dir level shifter (VL53L8CH SPI 3.3<->1.8V)")

# PCA9306 — 2-bit bidirectional I2C level translator (pass-FET, auto
# direction). Bridges the 3.3V I2C-A bus to the TCS3448's 1.8V-only
# SCL/SDA segment. EN driven by EN_OPTICAL: with the OPTICAL domain off the
# switch is open and the dead 1.8V segment is isolated from the live bus.
# pinout per DCU (VSSOP-8): 1 GND, 2 VREF1, 3 SDA1, 4 SCL1, 5 SCL2, 6 SDA2,
# 7 VREF2, 8 EN — pinout E0, PCA9306 DS not staged; verify before H3.2
# (docs/MISSING_VENDOR_ASSETS.md).
PCA9306 = mkpart("PCA9306", "U", [
    (1, "GND", PWR),
    (2, "VREF1", PWR),    # low-side (1.8V) reference
    (3, "SDA1", BI), (4, "SCL1", BI),      # 1.8V side
    (5, "SCL2", BI), (6, "SDA2", BI),      # 3.3V side
    (7, "VREF2", IN),     # high-side reference — modeled IN, not PWR: it is
                          # deliberately tied to the EN node (GPIO-driven,
                          # 200k to 3V3) per the PCA9306 switched-EN app
    (8, "EN", IN),
], description="TI/NXP PCA9306 2-bit I2C level translator (TCS3448 1.8V segment)")


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

# H3.2 pad-binding fix: symbol renumbered from sequential 1-7 to the REAL
# OLGA-14 map — VERIFIED-DS MAX30102 DS p8 (Pin Description): 1/5/6/7/8/14 =
# N.C. ("No Connection. Connect to PCB pad for mechanical stability." — pads
# fitted, electrically open), 2 SCL, 3 SDA, 4 PGND, 9+10 VLED+ (two pads,
# both must be fed), 11 VDD, 12 GND, 13 INT (OD, active low).
# VERIFIED-DS p2 (Abs Max): "All Other Pins to GND -0.3V to +6.0V" and p28:
# tolerant of any supply sequence -> SDA/SCL on the 3V3 bus with VDD=1.8V
# is within ratings. CLOSED.
MAX30102 = mkpart("MAX30102", "U", [
    (11, "VDD", PWR),        # 1.8V analog supply
    (9, "VLED_P1", PWR), (10, "VLED_P2", PWR),  # LED supply (3.3V domain rail)
    (12, "GND", PWR), (4, "PGND", PWR),
    (3, "SDA", BI), (2, "SCL", BI), (13, "INT_N", OC),
    (1, "NC1", NCP), (5, "NC5", NCP), (6, "NC6", NCP),
    (7, "NC7", NCP), (8, "NC8", NCP), (14, "NC14", NCP),
], description="MAX30102 PPG, I2C-A 0x57; real OLGA-14 map (VERIFIED-DS p8); VDD=1V8, VLED=3V3_CONTACT")

# AS7058 — ball-SIGNAL map still OPEN (the only remaining VERIFY item).
# PARTIAL-DS AS7058_DS001085_short p9 Fig 2: WLCSP42 grid confirmed =
# rows A-G x cols 1-6, 0.4 mm pitch, die 2.545x2.815 (footprint geometry
# E1) — but the SHORT DS carries NO ball-signal map and NO I2C address.
# Full DS (DS001573) is NDA-gated; FAE contact queued.
# H3.2 pad-binding: the 9 used signals are bound to PROVISIONAL-E0 ball
# positions (corner block A1..B3) purely so the netlist<->pad binding is
# complete and auditable; the remaining 33 balls are declared NC-pending.
# DO NOT ROUTE the AS7058 fanout until DS001573 lands — every ball below
# WILL move. Digital pins are VIOVDD-referred (short DS p10 abs-max) ->
# 3.3V bus OK.
AS7058 = mkpart("AS7058", "U", [
    ("A1", "VDD", PWR), ("A2", "VDDIO", PWR), ("A3", "GND", PWR),      # PROVISIONAL-E0
    ("A4", "SCL", BI), ("A5", "SDA", BI), ("A6", "INT", OUT),          # PROVISIONAL-E0
    ("B1", "ECG_INP", IN), ("B2", "ECG_INN", IN), ("B3", "ECG_REF", OUT),  # PROVISIONAL-E0
] + [(b, f"PEND_{b}", NCP) for b in
     ("B4", "B5", "B6", "C1", "C2", "C3", "C4", "C5", "C6",
      "D1", "D2", "D3", "D4", "D5", "D6", "E1", "E2", "E3", "E4", "E5", "E6",
      "F1", "F2", "F3", "F4", "F5", "F6", "G1", "G2", "G3", "G4", "G5", "G6")],
    description="ams AS7058 PPG/ECG/BioZ AFE, I2C-A 0x30 # VERIFY addr+ballmap (DS001573 NDA-gated; balls PROVISIONAL-E0)")


# ============================================================================
# SENSORS — I2C-B (air/optical/mag, 400 kHz)
# ============================================================================

# H3.2 pad-binding fix: symbol renumbered from sequential 1-7 to the REAL
# LGA-8 map — VERIFIED-DS bst-bme688-ds000 §7.1 Table 26 p51: 1 GND, 2 CSB,
# 3 SDI, 4 SCK, 5 SDO ("cannot be left floating", p44), 6 VDDIO, 7 GND,
# 8 VDD. (Old sequential symbol had VDD on pad 1 = GND and CSB on pad 7 =
# GND — supply/strap scramble.) Numbering is CLOCKWISE in top view (p51).
BME688 = mkpart("BME688", "U", [
    (8, "VDD", PWR), (6, "VDDIO", PWR), (1, "GND", PWR), (7, "GND2", PWR),
    (4, "SCK", BI), (3, "SDI", BI),
    (5, "SDO", IN),    # strap HIGH -> addr 0x77
    (2, "CSB", IN),    # strap HIGH -> I2C mode
], description="Bosch BME688 gas/T/RH/P, I2C-B 0x77 (SDO=1); real LGA-8 map (VERIFIED-DS p51)")

# H3.2 pad-binding fix: symbol renumbered to the REAL DFN-6 map —
# VERIFIED-DS SGP41 DS Table 6 p7: 1 VDD, 2 VSS, 3 SDA, 4 "n/a — connect
# to ground (no electrical function)", 5 VDDH (hotplate supply — "VDD and
# VDDH must be connected to one single supply"; MISSING from the old model:
# the heater had no feed), 6 SCL; die pad internally GND, solder for
# mechanical stability. (Old sequential symbol put SCL on pad 4 = the n/a
# pad and left real SCL pad 6 netless.)
SGP41 = mkpart("SGP41", "U", [
    (1, "VDD", PWR), (2, "GND", PWR), (3, "SDA", BI), (6, "SCL", BI),
    (5, "VDDH", PWR),        # hotplate supply — tie to VDD (Table 6 p7)
    (4, "DNC_GND", PWR),     # "connect to ground" (Table 6 p7)
    (7, "EP", PWR),          # die pad = GND; solder for mech stability (p7)
], description="Sensirion SGP41 VOC/NOx, I2C-B 0x59 (fixed); real DFN-6 map (VERIFIED-DS Table 6 p7)")

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

# H3.2 pad-binding fix: symbol rebuilt on the REAL 21-pad map — VERIFIED-DS
# SCD4x_Datasheet §2.3 Table 6 p5: 6 GND, 7 VDD, 9 SCL, 10 SDA, 19 VDDH
# ("supply IR source — must be tied to VDD on the customer PCB"; MISSING
# from the old model: the photoacoustic emitter had no feed), 20 GND,
# 21 = the four large center pads (all numbered 21) = GND; pads 1-5, 8,
# 11-18 = DNC "solder to a floating pad on the customer PCB". (Old
# sequential symbol bound VDD/GND/SDA/SCL to pads 1-4 — ALL of which are
# DNC pads: the sensor was completely unconnected.)
SCD41 = mkpart("SCD41", "U", [
    (7, "VDD", PWR), (6, "GND", PWR), (10, "SDA", BI), (9, "SCL", BI),
    (19, "VDDH", PWR),      # IR source supply — tie to VDD (Table 6 p5)
    (20, "GND2", PWR), (21, "EP_GND", PWR),   # 4 center pads share number 21
] + [(n, f"DNC{n}", NCP) for n in
     (1, 2, 3, 4, 5, 8, 11, 12, 13, 14, 15, 16, 17, 18)],
    description="Sensirion SCD41 photoacoustic CO2, I2C-B 0x62 (fixed); real 21-pad map (VERIFIED-DS Table 6 p5)")

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

# H3.2 pad-binding fix: symbol rebuilt on the REAL OLGA16 map — VERIFIED-DS
# AS7331 DS001047 Fig 3/4 p7-8: 1/2/5/6/15/16 VSSA, 3 VDDA, 4 REXT
# (EXTERNAL 3.3 MOhm +/-1% reference resistor to VSSA, TC<=50ppm/K —
# Electrical Characteristics p~12; MISSING from the old model: the ADC
# reference had no return), 7 A1, 8 SYN, 9 READY, 10 VDDD, 11 VSSD,
# 12 SDA, 13 SCL, 14 A0. No NC pins on this package. (Old sequential
# symbol bound VDD to pad 1 = VSSA and SCL to pad 4 = REXT — scramble.)
AS7331 = mkpart("AS7331", "U", [
    (3, "VDDA", PWR), (10, "VDDD", PWR),
    (1, "VSSA1", PWR), (2, "VSSA2", PWR), (5, "VSSA3", PWR), (6, "VSSA4", PWR),
    (15, "VSSA5", PWR), (16, "VSSA6", PWR), (11, "VSSD", PWR),
    (4, "REXT", PAS),          # 3.3M 1% to VSSA (VERIFIED-DS elec. char.)
    (12, "SDA", BI), (13, "SCL", BI),
    (14, "A0", IN), (7, "A1", IN),    # both LOW -> 0x74
    (9, "READY", OUT), (8, "SYN", IN),
], description="ams AS7331 UV A/B/C, I2C-B 0x74 (A1A0=00); real OLGA16 map (VERIFIED-DS Fig 4 p7-8)")

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

# H3.2 pad-binding fix: symbol renumbered to the REAL DFN-4 map —
# VERIFIED-DS SHT4x_Datasheet v7.1 §5.4 Fig 18 p16: 1 SDA, 2 SCL, 3 VDD,
# 4 VSS. (Old sequential symbol had VDD on pad 1 = SDA and SCL on pad 4 =
# VSS — full scramble.) Die pad not connected to any pin; no copper under
# the sensor besides the pin pads (p15-16).
SHT41 = mkpart("SHT41", "U", [
    (3, "VDD", PWR), (4, "GND", PWR), (1, "SDA", BI), (2, "SCL", BI),
], description="Sensirion SHT41 ref T/RH, I2C-B 0x44 (fixed); real DFN-4 map (VERIFIED-DS Fig 18 p16)")

# MMC5983MA — Memsic DS is NOT staged (not in registry_assets; added to
# docs/MISSING_VENDOR_ASSETS.md). The 6 used signals stay on PROVISIONAL-E0
# sequential pins 1-6 of the generic LGA-16 footprint; pads 7-16 are
# declared NC-pending. DO NOT ROUTE the MMC fanout until the Memsic DS
# lands — these pins WILL move.
MMC5983MA = mkpart("MMC5983MA", "U", [
    (1, "VDD", PWR), (2, "VDDIO", PWR), (3, "GND", PWR),        # PROVISIONAL-E0
    (4, "SDA", BI), (5, "SCL", BI), (6, "INT_DRDY", OUT),       # PROVISIONAL-E0
] + [(n, f"PEND_{n}", NCP) for n in range(7, 17)],
    description="Memsic MMC5983MA nT mag, I2C-B 0x30 # VERIFY pin map (DS not staged; pins PROVISIONAL-E0)")

TMAG5273 = mkpart("TMAG5273", "U", [
    (1, "SCL", BI), (2, "GND", PWR), (3, "SDA", BI),
    (4, "INT_N", OC), (5, "VCC", PWR), (6, "NC", NCP),
    # SOT-23-6 # pinout E0 — verify pin order vs TMAG5273 DS
    # VERIFIED-DS tmag5273 p16 Table 6-2: TMAG5273A1 default 7-bit addr = 0x35
    # (A2 also 0x35; B1=0x22, C1=0x78, D1=0x44). Order the A1 variant. CLOSED.
], description="TI TMAG5273A1 hall, I2C-B 0x35 (VERIFIED-DS p16)")

# H3.2 pad-binding fix: symbol renumbered to the REAL 13-position flex
# pin order — VERIFIED-DS bst-bmv080-ds000 Table 11 p27 (flex numbering
# 01->13, Fig 24 p26): 1 VDDL (laser supply 3.3V, >1uF to VSSA), 2 VSSA,
# 3 VDDA (ADC supply 2.5-3.3V), 4 CSB (I2C addr bit 1), 5 MOSI/SDA,
# 6 SCK/SCL, 7 PS (protocol select: VDDIO = I2C), 8 VDDIO (1.2-3.3V),
# 9 VSSD, 10 VDDD (2.5-3.3V), 11 MISO (I2C addr bit 0), 12 IRQ,
# 13 "Do not connect — keep floating, no GND, no voltage". CSB=1 & MISO=1
# -> addr 0x57 (Table 14 p32/31). The old sequential symbol had one VDD/GND
# and scrambled every strap (e.g. PS on flex pin 7 was correct only by
# luck of the draw — VDD sat on the LASER supply pin etc.). ZIF MP nail
# pads -> GND. NOTE Fig 11 p16-17: flex 01->13 numbering vs the Molex
# 503566-1302 contact numbering — footprint pads 1-13 follow the FLEX
# order; overlay-verify against the Molex drawing at fab (footprint E1
# note carries this).
BMV080 = mkpart("BMV080", "U", [
    (1, "VDDL", PWR), (3, "VDDA", PWR), (10, "VDDD", PWR), (8, "VDDIO", PWR),
    (2, "VSSA", PWR), (9, "VSSD", PWR),
    (5, "SDA", BI), (6, "SCL", BI), (12, "IRQ", OUT),
    (7, "PS", IN), (4, "CSB", IN), (11, "MISO_ADDR", IN),
    (13, "DNC", NCP),          # "keep floating" (Table 11 p27)
    ("MP1", "MP1", PAS), ("MP2", "MP2", PAS),   # ZIF nail pads -> GND
], description="Bosch BMV080 PM2.5, I2C-B 0x57; real 13-pin flex map (VERIFIED-DS Table 11 p27)")


# ============================================================================
# SENSORS/ANALOG — misc
# ============================================================================

# Large-area PIN photodiode (BPW34-class) — radiation detector (replaces BG51)
BPW34 = mkpart("PIN_BPW34", "D", [
    (1, "A", PAS), (2, "K", PAS),
], description="BPW34S-class large-area PIN photodiode, light-tight cavity")

# Charge-sensitive amplifier (OPA381-class placeholder) # pinout E0 —
# MSOP-8 pads 6-8 declared NC-pending; renumber to the real OPA381 pin map
# when the TI DS is staged (docs/MISSING_VENDOR_ASSETS.md).
OPA381 = mkpart("OPA381", "U", _seq([
    ("V+", PWR), ("V-", PWR), ("+IN", IN), ("-IN", IN), ("OUT", OUT),
]) + [(n, f"PEND_{n}", NCP) for n in (6, 7, 8)],
    description="OPA381-class transimpedance/charge amp for PIN detector (pins PROVISIONAL-E0)")

# Fast comparator (TLV3201-class) # pinout E0
TLV3201 = mkpart("TLV3201", "U", _seq([
    ("V+", PWR), ("V-", PWR), ("+IN", IN), ("-IN", IN), ("OUT", OUT),
]), description="TLV3201-class comparator -> GEIGER_PULSE counting")

# RF shield can over the radiation front-end (guard net SHIELD_RAD)
SHIELD_CAN = mkpart("SHIELD_CAN", "SH", [
    (1, "S1", PAS), (2, "S2", PAS), (3, "S3", PAS), (4, "S4", PAS),
], description="Shield can, radiation charge-amp cavity (light-tight)")

# AD8317 RF log detector (module-level placeholder) # pinout E0 —
# LFCSP-8 pads 7/8 + EP pad 9 declared NC-pending; renumber (and bind the
# EP once its internal tie is known) when the ADI DS is staged
# (docs/MISSING_VENDOR_ASSETS.md).
AD8317 = mkpart("AD8317", "U", _seq([
    ("VPOS", PWR), ("GND", PWR), ("INHI", IN), ("INLO", IN),
    ("VOUT", OUT), ("TADJ", PAS),
]) + [(7, "PEND_7", NCP), (8, "PEND_8", NCP), (9, "PEND_EP", NCP)],
    description="AD8317 1M-10GHz RF power detector -> N657 ADC_IN0 (pins PROVISIONAL-E0)")

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
# H3.2 pad-binding completion: the remaining 17 pads modeled explicitly —
# VERIFIED-DS UBX-22015849 Table 10 p9-11 (re-extracted; GND list of 22
# re-confirmed exact): A4 RTC_I / A6 EXTINT / C7 SAFEBOOT_N / D1 SDA /
# E1 SCL / F7 PIO6 = "leave open if not used"; C6 VCC_RF (filtered supply
# for an external active antenna/LNA — SR4G013 is passive, leave open);
# H9 LNA_EN (drives external LNA, unused); C1/C5/D9/E7/G9/J1/J2/J3/J7 =
# "Reserved — leave open".
MIA_M10Q = mkpart("MIA_M10Q", "U", [
    ("B1", "VCC", PWR), ("J4", "V_IO", PWR), ("J5", "V_BCKP", PWR),
    ("J6", "VIO_SEL", IN), ("C4", "RESET_N", IN),
    ("G1", "TXD", OUT), ("H1", "RXD", IN), ("A7", "TIMEPULSE", OUT),
    ("B9", "RF_IN", IN),
    ("A5", "RTC_O", OUT), ("D2", "RSVD_D2", PAS), ("E2", "RSVD_E2", PAS),
    ("F9", "RSVD_F9", PAS), ("G7", "RSVD_G7", PAS),
    ("A4", "RTC_I", NCP), ("A6", "EXTINT", NCP), ("C7", "SAFEBOOT_N", NCP),
    ("D1", "I2C_SDA", NCP), ("E1", "I2C_SCL", NCP), ("F7", "PIO6", NCP),
    ("C6", "VCC_RF", NCP), ("H9", "LNA_EN", NCP),   # passive antenna: unused
] + [(p, f"RSVD_{p}", NCP) for p in
     ("C1", "C5", "D9", "E7", "G9", "J1", "J2", "J3", "J7")]
  + [(p, f"GND_{p}", PWR) for p in
     ("A1", "A2", "A3", "A8", "A9", "B2", "B8", "C3", "C9", "E3", "E4", "E9",
      "F1", "F3", "F4", "G3", "G4", "G5", "G6", "H8", "J8", "J9")],
    description="u-blox MIA-M10Q GNSS (RAWX), UART + PPS, full M-LGA53 map (VERIFIED-DS Table 10 p9-11)")

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
# H3.2 pad-binding completion — VERIFIED-DS 002-25383 Table 1 p5-6, full
# QFN-24 pin list: previously-unmodeled pins added. 16 D- / 17 D+ / 20 DNU1 /
# 21 DNU2 = "Leave this pin unconnected" (Table 1 p5); 7 HPI_INT / 8 GPIO_1 =
# marked no-connect in the Fig 3 app diagram p7 when HPI unused; 12/13
# HPI_SDA/SCL = host I2C slave, no host here -> NC per the no-HPI app
# diagram; 3 VBUS_FET_EN / 4 SAFE_PWR_EN = PFET gate drivers, unused (no
# VBUS FET in this design) -> NC; 11 VDC_OUT = "connect to the output
# (drain) side of the VBUS PFETs" — our VBUS path is DIRECT to the BQ25620
# input, so the monitor ties to VBUS_C itself (the 'output' equals the
# input with no FET fitted).
CYPD3177 = mkpart("CYPD3177", "U", [
    (18, "VBUS", PWR), (19, "GND", PWR), (22, "VSS", PWR), (25, "EP", PWR),
    (15, "CC1", BI), (14, "CC2", BI),
    (23, "VDDD", PWO), (24, "VCCD", PWO),
    (1, "VBUS_MIN", IN), (2, "VBUS_MAX", IN),     # divider-strap voltage window
    (5, "ISNK_COARSE", IN), (6, "ISNK_FINE", IN), # divider-strap current request
    (9, "FAULT", OUT), (10, "FLIP", OUT),  # both actively driven high/low (p6)
    (11, "VDC_OUT", IN),                   # VBUS output monitor -> VBUS_C (direct path)
    (3, "VBUS_FET_EN", NCP), (4, "SAFE_PWR_EN", NCP),   # gate drivers unused
    (7, "HPI_INT", NCP), (8, "GPIO_1", NCP),            # NC per Fig 3 p7
    (12, "HPI_SDA", NCP), (13, "HPI_SCL", NCP),         # no HPI host in v1
    (16, "DM", NCP), (17, "DP", NCP),                   # "leave unconnected" p5
    (20, "DNU1", NCP), (21, "DNU2", NCP),               # "leave unconnected" p5
], description="CYPD3177 autonomous USB-C PD sink; VDDD dividers request 5-9V/3A; full QFN-24 map (VERIFIED-DS Table 1 p5-6)")

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

# Dual common-drain NMOS for protection (CSD-class) # pinout E0 —
# WSON-6 EP (pad 7) declared NC-pending: on most CSD-class common-drain
# duals the EP IS the shared drain, but the exact part is unpicked — bind
# EP to PROT_MID once the FET is chosen (docs/MISSING_VENDOR_ASSETS.md).
DUAL_NFET = mkpart("DUAL_NFET_PROT", "Q", _seq([
    ("S1", PAS), ("G1", IN), ("D1", PAS),
    ("D2", PAS), ("G2", IN), ("S2", PAS),
]) + [(7, "PEND_EP", NCP)],
    description="Dual NMOS, battery protection series pair (low-side) (pins PROVISIONAL-E0)")

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
    ("MP", "MP", PAS),   # metal retention tabs -> GND (H3.2 pad binding)
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
    [(i, f"P{i}", PAS) for i in range(1, 25)]
    + [("MP", "MP", PAS)],   # shell/nail pads -> GND (H3.2 pad binding)
    description="24p FPC, VD66GY camera (MIPI CSI-2) — DNP in v1")

TC2030 = mkpart("TC2030", "J", [
    (1, "VTREF", PWR), (2, "SWDIO", BI), (3, "NRST", PAS),
    (4, "SWCLK", PAS), (5, "GND", PWR), (6, "SWO", PAS),
], description="Tag-Connect TC2030-IDC-NL SWD footprint (no BOM cost)")

J_SMA = mkpart("SMA_EDGE", "J", [
    (1, "SIG", PAS), (2, "GND", PWR),
], description="RF survey input -> AD8317 (U.FL + shell SMA pigtail, ECO-H3.2)")

J_FAN = mkpart("CONN_FAN_2P", "J", [
    (1, "FAN+", PWR), (2, "FAN-", PAS),
], description="Blower fan (Sunon UB3F3-500 class), low-side switched")

J_LRA = mkpart("CONN_LRA_2P", "J", [
    (1, "OUT+", PAS), (2, "OUT-", PAS),
], description="LRA haptic actuator pads")

J_TOUCH_FPC = mkpart("CONN_TOUCH_13P", "J",
    [(i, f"E{i-1}", PAS) for i in range(1, 13)] + [(13, "GND", PWR)]
    + [("MP1", "MP1", PAS), ("MP2", "MP2", PAS)],  # ZIF nail pads -> GND
    description="Shell touch-electrode flex, 12 electrodes + guard GND (0.3mm ZIF, ECO-H3.2)")
