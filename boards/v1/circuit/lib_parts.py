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

# STM32N657X0 VFBGA142 — modeled connector-style with only the used signals.
# pinout E0 — logical numbering; real ball map (DS14791) at footprint stage.
STM32N657 = mkpart("STM32N657", "U", _seq([
    # --- power ---
    ("VDD_CORE1", PWR), ("VDD_CORE2", PWR),
    ("VDD18_1", PWR), ("VDD18_2", PWR),
    ("VDD33_1", PWR), ("VDD33_2", PWR), ("VDD33_3", PWR), ("VDD33_4", PWR),
    ("VSS1", PWR), ("VSS2", PWR), ("VSS3", PWR), ("VSS4", PWR),
    # --- SPI1 (sensor SPI: VL53L8CH, BNO086, ADS131M04, A121) ---
    ("SPI1_SCK", OUT), ("SPI1_MISO", IN), ("SPI1_MOSI", OUT),
    ("CS_VL53_N", OUT), ("CS_BNO_N", OUT), ("CS_ADS_N", OUT), ("CS_A121_N", OUT),
    # --- I2C ---
    ("I2C1_SCL", BI), ("I2C1_SDA", BI),      # I2C-A (1 MHz capable)
    ("I2C2_SCL", BI), ("I2C2_SDA", BI),      # I2C-B (400 kHz)
    # --- SDIO to ESP32-C6 (ESP-Hosted) ---
    ("SDIO_CLK", OUT), ("SDIO_CMD", BI),
    ("SDIO_D0", BI), ("SDIO_D1", BI), ("SDIO_D2", BI), ("SDIO_D3", BI),
    # --- UART1: GNSS + PPS input capture ---
    ("UART1_TX", OUT), ("UART1_RX", IN), ("PPS_IN", IN),
    # --- UART2: inter-MCU link to BL54L15 sentinel ---
    ("UART2_TX", OUT), ("UART2_RX", IN),
    # --- USB HS ---
    ("USB_DP", BI), ("USB_DM", BI),
    # --- camera (MIPI CSI-2 reserved; J_CAM is DNP) ---
    ("CSI_CKP", BI), ("CSI_CKN", BI),
    ("CSI_D0P", BI), ("CSI_D0N", BI), ("CSI_D1P", BI), ("CSI_D1N", BI),
    ("CAM_XCLK", OUT), ("CAM_RSTN", OUT),
    # --- PDM mic ---
    ("PDM_CLK", OUT), ("PDM_DATA", IN),
    # --- analog ---
    ("ADC_IN0", IN),                          # AD8317 RF detector output
    ("MCO_OUT", OUT),                         # 8.192 MHz clock for ADS131M04
    # --- debug / boot ---
    ("SWDIO", BI), ("SWCLK", IN), ("NRST", IN), ("BOOT0", IN),
    # --- XSPI (octal NOR) ---
    ("XSPI_D0", BI), ("XSPI_D1", BI), ("XSPI_D2", BI), ("XSPI_D3", BI),
    ("XSPI_D4", BI), ("XSPI_D5", BI), ("XSPI_D6", BI), ("XSPI_D7", BI),
    ("XSPI_CLK", OUT), ("XSPI_CS_N", OUT), ("XSPI_DQS", BI),
    # --- interrupt / data-ready inputs (R7: INT wired for every sensor) ---
    ("INT_VL53", IN), ("INT_BNO", IN), ("DRDY_ADS", IN),
    ("INT_MAX", IN), ("INT_AS7058", IN), ("IRQ_A121", IN),
    ("DRDY_MMC", IN), ("INT_TMAG", IN), ("INT_TCS", IN),
    ("RDY_AS7331", IN), ("INT_AS7421", IN), ("INT_BMV", IN), ("INT_ENS", IN),
    # --- inter-MCU wake ---
    ("WAKE_IN", IN),                          # WAKE_FROM_SENTINEL
    ("WAKE_OUT", OUT),                        # N6 -> sentinel attention
    # --- misc GPIO ---
    ("EN_UV_REQ", OUT),                       # UV request (ANDed w/ INTERLOCK_OK)
    ("EN_WHITE", OUT),                        # white illumination LED
    ("RSTN_BNO", OUT), ("LPN_VL53", OUT),
]), description="STM32N657X0 app MCU + NPU, VFBGA142 (used-signals model)")

# Octal xSPI NOR flash (MX25UW6445G-class, BGA24 / SOPB) — N6 is flashless.
# pinout E0
NOR_OCTAL = mkpart("NOR_OCTAL_XSPI", "U", _seq([
    ("VCC", PWR), ("VSS", PWR),
    ("CS_N", IN), ("CLK", IN), ("DQS", OUT), ("RESET_N", IN),
    ("DQ0", BI), ("DQ1", BI), ("DQ2", BI), ("DQ3", BI),
    ("DQ4", BI), ("DQ5", BI), ("DQ6", BI), ("DQ7", BI),
]), description="Octal xSPI NOR flash for STM32N657 (MX25UW6445G-class)")

# Ezurio BL54L15 module (nRF54L15) — always-on sentinel MCU + BLE.
# pinout E0 — module pad numbers from Ezurio DS at footprint stage.
BL54L15 = mkpart("BL54L15", "U", _seq([
    ("VCC", PWR), ("GND", PWR),
    # SENTINEL_I2C master: BQ27427, BQ25620, IQS7222A, DRV2605L, accessory EEPROM
    ("SENT_SCL", BI), ("SENT_SDA", BI),
    # radiation pulse counting (comparator output, counts in ambient)
    ("GEIGER_PULSE_IN", IN),
    # power-tree enables
    ("EN_OPTICAL", OUT), ("EN_AIR", OUT), ("EN_CONTACT", OUT),
    ("EN_RADAR", OUT), ("EN_GNSS", OUT), ("EN_WIFI", OUT),
    ("EN_N6", OUT), ("EN_FAN", OUT), ("EN_ACC", OUT), ("EN_HAPTIC", OUT),
    ("INTERLOCK_OK", OUT),                   # UV safety interlock (R5)
    # inter-MCU
    ("UART_TX", OUT), ("UART_RX", IN),
    ("WAKE_N6", OUT), ("ATTN_FROM_N6", IN),
    # housekeeping interrupts
    ("TOUCH_RDY_IN", IN),                    # IQS7222A RDY (wake source)
    ("GAUGE_INT_IN", IN),                    # BQ27427 GPOUT
    ("CHG_INT_IN", IN),                      # BQ25620 /INT
    # glow ring PWM
    ("GLOW1", OUT), ("GLOW2", OUT), ("GLOW3", OUT),
    ("GLOW4", OUT), ("GLOW5", OUT), ("GLOW6", OUT),
    # NFC pins unused in v1 (antenna not fitted)
    ("NFC1", NCP), ("NFC2", NCP),
    # debug
    ("SWDIO", BI), ("SWCLK", IN), ("RESET_N", IN),
]), description="Ezurio BL54L15 (nRF54L15) BLE sentinel module")


# ============================================================================
# SENSORS — SPI
# ============================================================================

# VL53L8CH ToF 8x8 with CNH histograms, SPI mode.
# Comm-mode straps per DS UM: SPI_I2C_N high = SPI; I2C_RST low. pinout E0
VL53L8CH = mkpart("VL53L8CH", "U", _seq([
    ("AVDD", PWR), ("IOVDD", PWR), ("GND", PWR),
    ("SCLK", IN), ("MOSI", IN), ("MISO", TRI), ("NCS", IN),
    ("SPI_I2C_N", IN),   # strap HIGH -> SPI mode  # VERIFY strap name/polarity vs DS
    ("I2C_RST", IN),     # strap LOW in SPI mode   # VERIFY
    ("LPN", IN), ("INT", OC),
]), description="ST VL53L8CH 8x8 ToF, SPI mode (straps in copper)")

# BNO086 IMU, SPI (SHTP) mode: PS1=HIGH, PS0/WAKE used as WAKE. pinout E0
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
    # VERIFY: A121 supply domains (VIO 1.8V nominal per DS) — may need local
    # 1.8V LDO instead of 3V3_RADAR; resolve at stage-2 against Acconeer DS.
    ("SPI_SCLK", IN), ("SPI_MOSI", IN), ("SPI_MISO", TRI), ("SPI_SS_N", IN),
    ("INTERRUPT", OUT), ("ENABLE", IN),
]), description="Acconeer A121 pulsed coherent radar, Sparse-IQ raw")


# ============================================================================
# SENSORS — I2C-A (contact/thermal, 1 MHz capable)
# ============================================================================

MLX90642 = mkpart("MLX90642", "U", [
    (1, "SDA", BI), (2, "GND", PWR), (3, "VDD", PWR), (4, "SCL", BI),
    # TO-39 4-lead; pin circle order # pinout E0 — verify vs MLX90642 DS
], description="Melexis MLX90642 32x24 FIR array, TO-39, I2C-A 0x33")

MLX90632 = mkpart("MLX90632", "U", _seq([
    ("VDD", PWR), ("GND", PWR), ("SDA", BI), ("SCL", BI),
]), description="Melexis MLX90632 medical spot FIR, I2C-A 0x3A")  # pinout E0

MAX30102 = mkpart("MAX30102", "U", _seq([
    ("VDD", PWR),        # 1.8V analog supply
    ("VLED_P", PWR),     # LED supply (3.3V domain rail)
    ("GND", PWR), ("PGND", PWR),
    ("SDA", BI), ("SCL", BI), ("INT_N", OC),
]), description="MAX30102 PPG, I2C-A 0x57; VDD=1V8, VLED=3V3_CONTACT")
# pinout E0 (OLGA-14; unused NC pads omitted).
# VERIFY: SDA/SCL are tolerant above VDD per DS abs-max (6V) -> 3V3 bus pull-ups
# acceptable with VDD=1.8V. Confirm at stage-2.

AS7058 = mkpart("AS7058", "U", _seq([
    ("VDD", PWR), ("VDDIO", PWR), ("GND", PWR),
    ("SCL", BI), ("SDA", BI), ("INT", OUT),
    ("ECG_INP", IN), ("ECG_INN", IN), ("ECG_REF", OUT),
]), description="ams AS7058 PPG/ECG/BioZ AFE, I2C-A 0x30 # VERIFY addr")
# pinout E0 (WLCSP42 subset)


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

ENS161 = mkpart("ENS161", "U", _seq([
    ("VDD", PWR),      # 1.8V core supply per DS
    ("VDDIO", PWR),    # IO supply (3V3 domain)
    ("GND", PWR),
    ("SDA", BI), ("SCL", BI),
    ("ADDR", IN),      # strap HIGH -> 0x53
    ("INT_N", OUT), ("CS_N", IN),  # CS high = I2C mode
]), description="ScioSense ENS161 4-el MOX, I2C-B 0x53; VDD=1V8")  # pinout E0

SCD41 = mkpart("SCD41", "U", _seq([
    ("VDD", PWR), ("GND", PWR), ("SDA", BI), ("SCL", BI),
]), description="Sensirion SCD41 photoacoustic CO2, I2C-B 0x62 (fixed)")  # pinout E0

TCS3448 = mkpart("TCS3448", "U", _seq([
    ("VDD", PWR), ("GND", PWR), ("SDA", BI), ("SCL", BI), ("INT_N", OC),
]), description="ams TCS3448 14ch VIS spectral, I2C-B 0x39 # VERIFY addr")  # pinout E0

AS7331 = mkpart("AS7331", "U", _seq([
    ("VDD", PWR), ("GND", PWR), ("SDA", BI), ("SCL", BI),
    ("A0", IN), ("A1", IN),    # both LOW -> 0x74
    ("READY", OUT), ("SYN", IN),
]), description="ams AS7331 UV A/B/C, I2C-B 0x74 (A1A0=00)")  # pinout E0

AS7421 = mkpart("AS7421", "U", _seq([
    ("VDD", PWR), ("GND", PWR), ("SDA", BI), ("SCL", BI),
    ("INT", OC), ("LED0", OC),   # integrated LED driver -> 970nm NIR LED
]), description="ams AS7421 64ch NIR, I2C-B 0x64 # VERIFY addr")  # pinout E0

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
], description="TI TMAG5273A1 hall, I2C-B 0x35 # VERIFY variant/addr")

BMV080 = mkpart("BMV080", "U", _seq([
    ("VDD", PWR), ("VDDIO", PWR), ("GND", PWR),
    ("SDA", BI), ("SCL", BI), ("IRQ", OUT),
    ("AB_SEL", IN),   # comm-select strap -> I2C  # VERIFY name vs DS
]), description="Bosch BMV080 PM2.5, I2C-B 0x57 # VERIFY addr")  # pinout E0


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

# u-blox MIA-M10Q GNSS SiP # pinout E0
MIA_M10Q = mkpart("MIA_M10Q", "U", _seq([
    ("VCC", PWR), ("V_BCKP", PWR), ("GND", PWR),
    ("TXD", OUT), ("RXD", IN), ("TIMEPULSE", OUT),
    ("RF_IN", IN),
]), description="u-blox MIA-M10Q GNSS (RAWX), UART + PPS")

# GNSS chip antenna
ANT_GNSS = mkpart("ANT_GNSS", "AE", [
    (1, "FEED", PAS), (2, "GND", PAS),
], description="GNSS L1 chip antenna (keepout corner)")

# SGX-4CO electrochemical CO cell (3-electrode)
SGX_4CO = mkpart("SGX_4CO", "U", [
    (1, "WE", PAS), (2, "RE", PAS), (3, "CE", PAS),
], description="SGX 4-CO electrochemical CO cell (serviceable, R2 flag)")

# LMP91000-class potentiostat AFE for the CO cell # pinout E0
LMP91000 = mkpart("LMP91000", "U", _seq([
    ("VDD", PWR), ("GND", PWR),
    ("SDA", BI), ("SCL", BI), ("MENB_N", IN),
    ("VOUT", OUT), ("C1", PAS), ("C2", PAS),
    ("WE", PAS), ("RE", PAS), ("CE", PAS),
]), description="LMP91000 potentiostat, I2C-B 0x48 (fixed) -> ADS AIN3")

# Piezo contact/vibration transducer (2-pad)
PIEZO = mkpart("PIEZO", "PZ", [
    (1, "P1", PAS), (2, "P2", PAS),
], description="Piezo disc, contact vibration -> ADS131M04 AIN0 diff")


# ============================================================================
# POWER
# ============================================================================

# Cypress/Infineon CYPD3177 USB-C PD sink controller (BCR) # pinout E0
CYPD3177 = mkpart("CYPD3177", "U", _seq([
    ("VBUS", PWR), ("GND", PWR),
    ("CC1", BI), ("CC2", BI),
    ("VBUS_MIN", IN), ("VBUS_MAX", IN),     # resistor-strap voltage window
    ("ISNK_COARSE", IN), ("ISNK_FINE", IN), # resistor-strap current request
    ("FAULT_N", OC), ("FLIP", OUT),
]), description="CYPD3177 autonomous USB-C PD sink; straps set 5V/3A request")

# TI BQ25620 I2C buck charger # pinout E0
BQ25620 = mkpart("BQ25620", "U", _seq([
    ("VBUS", PWR), ("PMID", PAS), ("REGN", PWO),
    ("SW", OUT), ("BTST", PAS),
    ("SYS", PWO), ("BAT", PWR),
    ("SDA", BI), ("SCL", BI), ("INT_N", OC), ("CE_N", IN),
    ("TS", IN), ("QON_N", IN), ("GND", PWR), ("PGND", PWR),
]), description="TI BQ25620 3.5A charger, ~1C fast charge, SENTINEL_I2C 0x6B")

# TI BQ27427 fuel gauge (integrated sense R) # pinout E0
BQ27427 = mkpart("BQ27427", "U", _seq([
    ("VDD", PWR), ("BIN", IN),      # battery voltage sense
    ("SRX", PAS),                    # internal-sense-resistor terminal
    ("SDA", BI), ("SCL", BI), ("GPOUT", OC), ("VSS", PWR),
]), description="TI BQ27427 gauge, SENTINEL_I2C 0x55; low-side sense # VERIFY topology")

# TI BQ29700 1S protector # pinout E0
BQ29700 = mkpart("BQ29700", "U", _seq([
    ("VDD", PWR), ("VSS", PWR),
    ("VM", IN),                      # pack- sense
    ("COUT", OUT), ("DOUT", OUT),    # charge / discharge FET gates
]), description="TI BQ29700 1S Li+ protector (with dual NMOS)")

# Dual common-drain NMOS for protection (CSD-class) # pinout E0
DUAL_NFET = mkpart("DUAL_NFET_PROT", "Q", _seq([
    ("S1", PAS), ("G1", IN), ("D1", PAS),
    ("D2", PAS), ("G2", IN), ("S2", PAS),
]), description="Dual NMOS, battery protection series pair (low-side)")

# TPS62840 60nA-IQ buck -> 3V3_AON # pinout E0
TPS62840 = mkpart("TPS62840", "U", _seq([
    ("VIN", PWR), ("GND", PWR),
    ("EN", IN), ("SW", OUT), ("VOS", IN), ("MODE", IN),
]), description="TI TPS62840, 60nA IQ, always-on 3.3V sentinel rail")

# TPS62823 3A buck (x2: VDD_CORE_N6 and 3V3_SYS) # pinout E0
TPS62823 = mkpart("TPS62823", "U", _seq([
    ("VIN", PWR), ("GND", PWR),
    ("EN", IN), ("SW", OUT), ("FB", IN), ("MODE", IN),
]), description="TI TPS62823 3A buck")

# TLV62568 1A buck -> 1V8 (SOT-23-5) # pinout E0
TLV62568 = mkpart("TLV62568", "U", [
    (1, "EN", IN), (2, "GND", PWR), (3, "VIN", PWR), (4, "FB", IN), (5, "SW", OUT),
    # pinout E0 — verify SOT-23-5 order vs TLV62568 DS
], description="TI TLV62568 1A buck -> 1V8")

# TPS22916-class load switch # pinout E0
TPS22916 = mkpart("TPS22916", "U", [
    (1, "VIN", PWR), (2, "GND", PWR), (3, "ON", IN), (4, "VOUT", PWO),
    # pinout E0 — CSP-4 ball order at footprint stage
], description="TI TPS22916 load switch (per-domain power gating)")

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

# Azoteq IQS7222A 12ch cap touch # pinout E0
IQS7222A = mkpart("IQS7222A", "U", _seq([
    ("VDDHI", PWR), ("VREG", PAS), ("GND", PWR),
    ("SDA", BI), ("SCL", BI), ("RDY", OC), ("MCLR_N", IN),
    ("E0", PAS), ("E1", PAS), ("E2", PAS), ("E3", PAS),
    ("E4", PAS), ("E5", PAS), ("E6", PAS), ("E7", PAS),
    ("E8", PAS), ("E9", PAS), ("E10", PAS), ("E11", PAS),
]), description="Azoteq IQS7222A touch, SENTINEL_I2C 0x44 (deliberate: avoids SHT41 0x44 on I2C-B)")

# TI DRV2605L haptic driver # pinout E0
DRV2605L = mkpart("DRV2605L", "U", _seq([
    ("VDD", PWR), ("GND", PWR),
    ("SDA", BI), ("SCL", BI), ("EN", IN), ("IN_TRIG", IN),
    ("OUT_P", OUT), ("OUT_N", OUT),
]), description="TI DRV2605L LRA driver, SENTINEL_I2C 0x5A")

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
