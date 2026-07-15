"""SPI sensor cluster: VL53L8CH (SPI mode, 1.8V IO branch), BNO086 (SPI
mode), ADS131M04.

H3.0 1.8V-IO architecture: SPI1 itself stays a 3.3V bus — its N657 balls
(PA5/PB4/PB5 + CS GPIOs) live in the VDD general-GPIO supply domain, which
must stay at 3.3V for the BL54L15 UART/wake pins, both I2C buses and the
sentinel EN fabric (DS14791 Table 18 fn1: one OPT124/VDDIOVRSEL setting for
the whole domain). Of the four SPI1 devices only the VL53L8CH is 1.8V-only
(A121 VIO is 3.3V-legal, BNO086 VDDIO 1.7-3.6V, ADS131M04 DVDD 3.3V), so the
minimum-shifter architecture is ONE TXU0304 on the VL53L8CH branch; its
INT/LPn sidebands use the N657's two spare VDDIO3 (1.8V) PN-port balls
natively. See boards/v1/H3_REPORT.md §H3.0-1.
"""

from skidl import Net

from lib_parts import VL53L8CH, BNO086, ADS131M04, PIEZO, TXU0304
from util import join, C, R, decouple, gnd, tp, pullup


def build_sensors_spi():
    GND = gnd()
    v3sys = Net.fetch("3V3_SYS")
    v_opt = Net.fetch("3V3_OPTICAL")
    v18_opt = Net.fetch("1V8_OPTICAL")   # gated 1.8V sub-rail (power.py, H3.0)
    sck = Net.fetch("SPI1_SCK")
    miso = Net.fetch("SPI1_MISO")
    mosi = Net.fetch("SPI1_MOSI")

    # ---------------- VL53L8CH — SPI mode, 1.8V IO branch ------------------
    # Supplies — VERIFIED-DS DS14310 §3.3 p11: AVDD 3.3V fixed, CORE_1V8
    # 1.8V fixed, IOVDD 1.2/1.8V; IOVDD=1.8V may share the CORE_1V8 supply;
    # any power-up order. ECO EXECUTED (H3.0): IOVDD+CORE_1V8 -> 1V8_OPTICAL
    # (old 3.3V IOVDD feed violated the 1.2/1.8V-only rating).
    tof = VL53L8CH(ref="U_VL53", footprint="generated:ST_VL53L8_LGA16")
    tof["AVDD"] += v_opt
    tof["IOVDD"] += v18_opt
    tof["CORE_1V8"] += v18_opt         # shared per DS14310 §3.3 (H3.0 add)
    tof["GND"] += GND                  # C3
    tof["GND2"] += GND                 # C7
    # RSVD pads A6/A7/C6 "connect to ground"; B4 thermal pad -> GND plane
    # (AN5897) — VERIFIED-DS DS14310 Table 3 p7 (H3.2 pad-binding completion)
    tof["RSVD1 RSVD2 RSVD3 THERMAL"] += GND
    decouple(v_opt, n=2, bulk_uF=10)   # AVDD sees VCSEL pulses -> extra bulk
    decouple(v18_opt, n=2, bulk_uF=1)  # IOVDD + CORE_1V8 pair
    # SPI level shift 3.3 -> 1.8: TXU0304, fixed directions (SCLK/MOSI/NCS
    # down, MISO up). VCCB = gated 1V8_OPTICAL -> B port Hi-Z when the
    # domain is off (bus isolation). CE high = enabled whenever the domain
    # IO rail is up.
    ls = TXU0304(ref="U_LS_VL53", footprint="Package_SO:TSSOP-14_4.4x5mm_P0.65mm")
    ls["VCCA"] += v3sys
    ls["VCCB"] += v18_opt
    ls["GND"] += GND
    ls["CE"] += v18_opt
    ls["NC1"] += NC
    ls["NC2"] += NC
    decouple(v3sys, n=1)
    cs_vl53 = Net.fetch("CS_VL53_N")   # 3.3V side, from N657 PD8
    ls["A1"] += sck
    ls["A2"] += mosi
    ls["A3"] += cs_vl53
    join("VL53_SCLK_1V8", ls["B1"], tof["SCLK"])
    join("VL53_MOSI_1V8", ls["B2"], tof["MOSI"])
    ncs18 = Net.fetch("VL53_NCS_1V8")
    ncs18 += ls["B3"], tof["NCS"]
    miso18 = Net.fetch("VL53_MISO_1V8")
    miso18 += tof["MISO"], ls["B4"]
    ls["A4"] += miso
    # comm-mode straps — VERIFIED-DS DS14310 Rev 9 Table 3 p7: SPI mode =
    # SPI_I2C_N (pad C1) 47k pullup to IOVDD; NCS needs its own 47k pullup
    # to IOVDD (deselected while unconfigured); pullups now reference the
    # 1.8V IO rail (H3.0). A 47k pullup stays on the 3.3V CS segment so the
    # TXU input never floats while the N657 is in reset. No separate
    # I2C_RST pin exists (model pin lands on GND-strapped RSVD).
    spi_sel = Net.fetch("VL53_SPI_SEL")
    spi_sel += tof["SPI_I2C_N"]
    pullup(spi_sel, v18_opt, "47k")    # HIGH -> SPI   VERIFIED-DS DS14310 p7
    pullup(ncs18, v18_opt, "47k")      # NCS pullup    VERIFIED-DS DS14310 p7
    pullup(cs_vl53, v3sys, "47k")      # TXU A3 float guard during N657 reset
    # GPIO2 (B1): OD tristate default, "47k pullup to IOVDD required, used
    # as SYNC input" — the DS fits the pullup even when SYNC is unused
    # (Fig 5 p8). H3.2 add: pin was previously unmodeled.
    gpio2 = Net.fetch("VL53_GPIO2")
    tof["GPIO2"] += gpio2
    pullup(gpio2, v18_opt, "47k")      # VERIFIED-DS DS14310 Table 3 p7
    # LPn / INT sidebands: native 1.8V on the N657's spare VDDIO3-domain
    # PN-port balls (PN12 out / PN7 in — H3.0 ECO, DS14791 Table 18 fn9).
    lpn = Net.fetch("LPN_VL53")
    tof["LPN"] += lpn
    rlpn = R("100k")                   # keep LPn low until PN12 is configured
    lpn += rlpn[1]
    GND += rlpn[2]
    int_vl53 = Net.fetch("INT_VL53")
    tof["INT"] += int_vl53
    pullup(int_vl53, v18_opt, "47k")   # OD INT, pulled to the 1.8V IO rail
    # (fw note: mask the PN7 EXTI while EN_OPTICAL is low — the dead rail
    # reads as a constant low on INT_VL53)

    # ---------------- BNO086 — SPI (SHTP) mode ----------------------------
    imu = BNO086(ref="U_BNO", footprint="Package_LGA:LGA-28_5.2x3.8mm_P0.5mm")
    imu["VDD"] += v3sys
    imu["VDDIO"] += v3sys
    imu["GND"] += GND
    imu["GND2"] += GND                 # pin 25 (VERIFIED-DS Fig 1-6 p10)
    decouple(v3sys, n=2, bulk_uF=1)
    # PS1=HIGH, PS0/WAKE: pulled high (SPI mode), N657 can yank via wake later
    imu["PS1"] += v3sys
    rps0 = R("10k")
    ps0 = Net.fetch("BNO_PS0_WAKE")
    ps0 += imu["PS0_WAKE"], rps0[1]
    v3sys += rps0[2]
    tp(ps0)
    imu["H_SCLK"] += sck
    imu["H_MOSI"] += mosi
    imu["H_MISO"] += miso
    imu["H_CSN"] += Net.fetch("CS_BNO_N")
    int_bno = Net.fetch("INT_BNO")
    imu["H_INTN"] += int_bno
    pullup(int_bno, v3sys, "47k")
    imu["NRST"] += Net.fetch("RSTN_BNO")
    rbootn = R("10k")
    imu["BOOTN"] += rbootn[1]
    v3sys += rbootn[2]                 # BOOTN high = normal boot
    # H3.2 real-bug fixes from the full LGA-28 map (VERIFIED-DS BNO08x DS):
    # 1) CAP (pin 9): 100nF to GND required (Fig 1-6 p10) — was missing.
    ccap = C("100nF")
    join("BNO_CAP", imu["CAP"], ccap[1])
    GND += ccap[2]
    # 2) CLKSEL0 (pin 10, internal pulldown): low selects the 32.768kHz
    #    CRYSTAL clock source (Fig 1-8 p11) — no crystal is fitted, so the
    #    old (unmodeled = low) state left the part waiting on a dead clock.
    #    Strap HIGH -> internal oscillator (legal for SPI; only UART hosts
    #    are excluded, p11). CLKSEL1 (26) low/NC + XIN32 (27) NC.
    imu["CLKSEL0"] += v3sys            # internal osc  VERIFIED-DS Fig 1-8 p11
    imu["XOUT32_CLKSEL1"] += NC
    imu["XIN32"] += NC
    # 3) ENV_SCL/ENV_SDA (15/16): "should be pulled up via resistors
    #    regardless of the presence of the external sensor — SW polls for
    #    sensors at reset" (note 7 p19; Fig 1-20 shows 2.2k). Were missing.
    env_scl = Net.fetch("BNO_ENV_SCL")
    env_sda = Net.fetch("BNO_ENV_SDA")
    imu["ENV_SCL"] += env_scl
    imu["ENV_SDA"] += env_sda
    pullup(env_scl, v3sys, "2.2k")     # VERIFIED-DS Fig 1-20 p18
    pullup(env_sda, v3sys, "2.2k")
    # Reserved pads: "Reserved. No connect." (Fig 1-6 p10)
    imu["RESV1 RESV7 RESV8 RESV12 RESV13 RESV21 RESV22 RESV23 RESV24"] += NC

    # ---------------- ADS131M04 — precision 4ch ADC ------------------------
    adc = ADS131M04(ref="U_ADS", footprint="Package_DFN_QFN:QFN-20-1EP_3x3mm_P0.4mm_EP1.65x1.65mm")
    adc["AVDD"] += v3sys
    adc["DVDD"] += v3sys
    adc["AGND"] += GND
    adc["DGND"] += GND
    adc["EP"] += GND                   # thermal pad -> AGND (VERIFIED-DS Table 5-1 p4)
    # CAP (pin 16): digital LDO output, 220nF to DGND (VERIFIED-DS Table
    # 5-1 p4) — H3.2 add, the pin was missing from the model entirely.
    ccap_ads = C("220nF")
    join("ADS_CAP", adc["CAP"], ccap_ads[1])
    GND += ccap_ads[2]
    decouple(v3sys, n=2, bulk_uF=10)
    adc["SCLK"] += sck
    adc["DIN"] += mosi
    adc["DOUT"] += miso
    adc["CS_N"] += Net.fetch("CS_ADS_N")
    adc["DRDY_N"] += Net.fetch("DRDY_ADS")
    rsync = R("10k")
    adc["SYNC_RESET_N"] += rsync[1]
    v3sys += rsync[2]
    adc["CLKIN"] += Net.fetch("CLK_ADS")   # 8.192MHz from N657 MCO

    # AIN0: piezo, differential across P/N with bias resistors
    pz = PIEZO(ref="PZ1", footprint="generated:PIEZO_DISC_PADS")
    p_p = Net.fetch("PIEZO_P")
    p_n = Net.fetch("PIEZO_N")
    p_p += pz["P1"], adc["AIN0P"]
    p_n += pz["P2"], adc["AIN0N"]
    rb1, rb2 = R("1M"), R("1M")
    p_p += rb1[1]
    GND += rb1[2]
    p_n += rb2[1]
    GND += rb2[2]

    # AIN1: PIN radiation charge-amp output (net driven in sensors_misc)
    rad = Net.fetch("RAD_ANALOG")
    rad += adc["AIN1P"]
    adc["AIN1N"] += GND

    # AIN2: accessory analog 2 (pogo) + testpoint
    an2 = Net.fetch("ACC_AN2")
    an2 += adc["AIN2P"]
    adc["AIN2N"] += GND
    tp(an2)

    # AIN3: CO potentiostat VOUT (sensors_misc) + testpoint
    co = Net.fetch("CO_AFE_OUT")
    co += adc["AIN3P"]
    adc["AIN3N"] += GND
    tp(co)
