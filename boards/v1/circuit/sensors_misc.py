"""Misc sensors + emitters: BMV080, A121 radar, MIA-M10Q GNSS, PDM mic,
camera FPC (DNP), PIN radiation front-end, AD8317 RF survey, LEDs, fan,
SGX-4CO + potentiostat."""

from skidl import Net  # NC is a skidl builtin

from lib_parts import (BMV080, A121, MIA_M10Q, ANT_GNSS, PDM_MIC, J_CAM_24P,
                       BPW34, OPA381, TLV3201, SHIELD_CAN, AD8317, J_SMA,
                       NFET_SOT23, AND_1G08, J_FAN, SGX_4CO, LMP91000,
                       XTAL_3225)
from util import join, C, R, LED, SCHOTTKY, decouple, gnd, tp, pullup


def build_sensors_misc():
    GND = gnd()
    v3sys = Net.fetch("3V3_SYS")
    aon = Net.fetch("3V3_AON")
    vsys = Net.fetch("VSYS")
    v_opt = Net.fetch("3V3_OPTICAL")
    v_air = Net.fetch("3V3_AIR")
    v_gnss = Net.fetch("3V3_GNSS")
    v_radar = Net.fetch("3V3_RADAR")
    sda_b, scl_b = Net.fetch("I2CB_SDA"), Net.fetch("I2CB_SCL")

    # ---------------- BMV080 PM2.5 — I2C-B 0x57 ---------------------------
    # (0x57 collides with MAX30102 only nominally — MAX30102 is on I2C-A.)
    # H3.2 pad-binding fix (real flex pin order, VERIFIED-DS Table 11 p27):
    # the part has THREE separate supplies (VDDL laser 3.3V / VDDA ADC /
    # VDDD digital, all 2.5-3.3V legal) + VDDIO (1.2-3.3V) and split
    # VSSA/VSSD grounds — the old single-VDD model scrambled the ZIF pads.
    # All supplies <- 3V3_AIR (in-range for each, one gated domain).
    pm = BMV080(ref="U_BMV", footprint="generated:BMV080_Molex_503566-1302_ZIF13")
    pm["VDDL VDDA VDDD VDDIO"] += v_air
    pm["VSSA VSSD"] += GND
    pm["SDA"] += sda_b
    pm["SCL"] += scl_b
    # VERIFIED-DS bst-bmv080-ds000 p27: PS=VDDIO selects I2C (GND would be SPI);
    # p31 Table 13: CSB(IAB1)=1, MISO(IAB0)=1 -> device address 0x57.
    pm["PS"] += v_air
    pm["CSB"] += v_air
    pm["MISO_ADDR"] += v_air
    pm["DNC"] += NC              # pin 13: "keep floating" (Table 11 p27)
    pm["MP1 MP2"] += GND         # ZIF nail pads
    decouple(v_air, n=3, bulk_uF=10)   # >1uF each on VDDL/VDDA/VDDD (Table 11)
    pm["IRQ"] += Net.fetch("INT_BMV")

    # ---------------- A121 radar — SPI-only per DS ------------------------
    radar = A121(ref="U_A121", footprint="generated:A121_fcCSP50")
    # H3.2: symbol rebuilt on the REAL 50-ball map (VERIFIED-DS A121 v1.8
    # Table 1 p8-9 — the 9-pin sequential symbol left all 50 pads netless).
    # VERIFIED-DS p10: VIO=1.8/3.3V OK, but VRX/VTX/VDIG are 1.8V-only
    # (abs-max 2.0V). ECO EXECUTED (H3.0): VDIG+VRX+VTX fed from the gated
    # 1V8_RADAR sub-rail (same EN_RADAR as 3V3_RADAR, both levels gate
    # together); VIO stays 3.3V -> SPI/INT/ENABLE remain 3.3V-bus
    # compatible, no shifters.
    v18_radar = Net.fetch("1V8_RADAR")
    radar["VIO"] += v_radar      # K9 — 3.3V legal per DS p10
    radar["VDIG VRX1 VRX2 VTX1 VTX2"] += v18_radar   # 1.8V-only  VERIFIED-DS p10
    # 27 GND balls + DS-mandated grounded balls (Analog0/1, CTRL, GPIO1-4,
    # PLL_RF_TEST — Table 1 p8: "connect to ground")
    for p in radar.pins:
        if p.name.startswith("GND_"):
            p += GND
    radar["ANALOG0 ANALOG1 CTRL GPIO1 GPIO2 GPIO3 GPIO4 PLL_RF_TEST"] += GND
    # RESET_N "must be connected to VIO" (Table 1 p8) — H3.2 real-bug fix
    radar["RESET_N"] += v_radar
    decouple(v_radar, n=2, bulk_uF=10)
    decouple(v18_radar, n=4, bulk_uF=10)   # C1-C4 1uF class (BOM Table 13 p19)
    radar["SPI_SCLK"] += Net.fetch("SPI1_SCK")
    radar["SPI_MOSI"] += Net.fetch("SPI1_MOSI")
    radar["SPI_MISO"] += Net.fetch("SPI1_MISO")
    radar["SPI_SS_N"] += Net.fetch("CS_A121_N")
    radar["INTERRUPT"] += Net.fetch("IRQ_A121")
    radar["ENABLE"] += v_radar   # enabled whenever RADAR domain is powered
    # 24 MHz crystal — H3.2 REAL-BUG FIX: "the built-in crystal oscillator
    # REQUIRES an external crystal; supported frequency 24 MHz" (VERIFIED-DS
    # v1.8 p9 + §6.2 p19; BOM Table 13: X1 24MHz + C5/C6 tuning caps — 8pF
    # for the CL=9pF/Cstray=5pF worked example). The old circuit had NO
    # crystal: the sensor would never clock.
    xr = XTAL_3225(ref="X_A121",
                   footprint="Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm")
    xr.value = "24MHz"
    join("A121_XIN", radar["XIN"], xr["X1"])
    join("A121_XOUT", radar["XOUT"], xr["X2"])
    xr["GND1"] += GND
    xr["GND2"] += GND
    cx5, cx6 = C("8pF"), C("8pF")      # §6.2 p19 example values (E0: set per XTAL CL)
    join("A121_XIN", cx5[1])
    join("A121_XOUT", cx6[1])
    GND += cx5[2], cx6[2]

    # ---------------- MIA-M10Q GNSS ---------------------------------------
    # VERIFIED-DS UBX-22015849 p9-11: M-LGA53 pad map (footprint rebuilt —
    # old 20-pad castellated placeholder was wrong). Required wiring fixes:
    # V_IO (J4) supply added (was missing), VIO_SEL (J6) left OPEN -> 3.3V
    # V_IO, RTC_O (A5) grounded when unused, reserved D2-E2 tied together,
    # F9/G7 to GND (DS fn17/18 recommend 0R — H3 decides), RESET_N /
    # SAFEBOOT_N / EXTINT / RTC_I / SDA / SCL left open per DS.
    gnss = MIA_M10Q(ref="U_GNSS", footprint="generated:UBLOX_MIA_M10Q")
    gnss["VCC"] += v_gnss
    gnss["V_IO"] += v_gnss           # IO supply input  VERIFIED-DS p10
    gnss["VIO_SEL"] += NC            # open = 3.3V V_IO  VERIFIED-DS p11
    gnss["RESET_N"] += NC            # unused (>=1ms low to reset)
    gnss["RTC_O"] += GND             # "connect to GND if not used" (p9)
    join("GNSS_RSVD_D2E2", gnss["RSVD_D2"], gnss["RSVD_E2"])  # p10: tie D2-E2
    gnss["RSVD_F9"] += GND           # p10 fn17
    gnss["RSVD_G7"] += GND           # p10 fn18
    for p in gnss.pins:
        if p.name.startswith("GND_"):
            p += GND
    # H3.2 pad-binding completion — remaining 17 pads, all "leave open" per
    # VERIFIED-DS Table 10 p9-11: RTC_I/EXTINT/SAFEBOOT_N/I2C pads/PIO6 =
    # optional features unused; VCC_RF + LNA_EN = for an ACTIVE antenna
    # (SR4G013 is passive); 9x Reserved.
    gnss["RTC_I EXTINT SAFEBOOT_N I2C_SDA I2C_SCL PIO6 VCC_RF LNA_EN"] += NC
    for p in gnss.pins:
        if p.name.startswith("RSVD_") and not p.nets:
            p += NC
    decouple(v_gnss, n=1, bulk_uF=10)
    # backup supply from always-on rail via diode (hot-start ephemeris)
    dbk = SCHOTTKY("BAT54")
    dbk.ref = "D_BCKP"
    vbckp = Net.fetch("GNSS_VBCKP")
    from skidl import POWER
    vbckp.drive = POWER          # ERC waiver W3: backup rail fed via BAT54 from 3V3_AON
    aon += dbk["A"]
    vbckp += dbk["K"], gnss["V_BCKP"]
    cbk = C("1uF")
    vbckp += cbk[1]
    GND += cbk[2]
    gnss["TXD"] += Net.fetch("GNSS_TX")
    gnss["RXD"] += Net.fetch("GNSS_RX")
    gnss["TIMEPULSE"] += Net.fetch("GNSS_PPS")
    ant = ANT_GNSS(ref="AE_GNSS", footprint="RF_Antenna:Antenova_SR4G013_GPS")
    join("GNSS_RF", gnss["RF_IN"], ant["FEED"])
    ant["GND"] += GND

    # ---------------- PDM mic ----------------------------------------------
    mic = PDM_MIC(ref="MK1", footprint="Sensor_Audio:Knowles_LGA-5_3.5x2.65mm")
    mic["VDD"] += v3sys
    mic["GND"] += GND
    decouple(v3sys, n=1)
    mic["CLK"] += Net.fetch("PDM_CLK")
    mic["DATA"] += Net.fetch("PDM_DATA")
    mic["SEL"] += GND            # data on falling edge

    # ---------------- camera FPC (VD66GY, DNP) -----------------------------
    # VD66GY captured — VERIFIED-DS DS13838 Rev 9 (VB66GY/VD66GY, staged):
    # bare-die sensor (115 bonding pads, Table 6/7 p15-16) -> the v1 FPC mates
    # a MODULE built on it. Supplies p4/p15: VANA 2.8V, VDDIO 1.8V, VCORE
    # 1.15V (core + CSI-2 drivers). Interface checks vs this connector:
    #  * MIPI CSI-2 1 or 2 lanes, <=1.5 Gbps/lane (p2/p12) — 2-lane wiring
    #    below is correct; N657 CSI PHY handles 2 lanes to 2.5G (DS14791).
    #  * XSHUTDOWN reset ACTIVE LOW (Table 6) -> CAM_RSTN polarity correct.
    #  * CLKIN external input clock required (Table 6) -> CAM_XCLK correct.
    #  * I2C control (SDA/SCL, Table 6) -> CCI on I2C-A correct.
    # RATIFIED (H3.0): the camera MODULE carries its own local 2.8V (VANA)
    # and 1.15V (VCORE) LDOs on the module flex — the FPC pinout stays
    # 3V3_OPTICAL (16) + 1V8 (17) + CSI, and the reserved 19-24 group stays
    # reserved (NOT repurposed as rail feeds). DNP in v1; decision recorded
    # in boards/v1/H3_REPORT.md §H3.0-5.
    cam = J_CAM_24P(ref="J_CAM", footprint="Connector_FFC-FPC:Hirose_FH12-24S-0.5SH_1x24-1MP_P0.50mm_Horizontal")
    cam[1] += GND
    join("CSI_CKP", cam[2])
    join("CSI_CKN", cam[3])
    cam[4] += GND
    join("CSI_D0P", cam[5])
    join("CSI_D0N", cam[6])
    cam[7] += GND
    join("CSI_D1P", cam[8])
    join("CSI_D1N", cam[9])
    cam[10] += GND
    join("CAM_XCLK", cam[11])
    join("CAM_RSTN", cam[12])
    join("I2CA_SDA", cam[13])   # CCI
    join("I2CA_SCL", cam[14])
    cam[15] += GND
    cam[16] += v_opt
    cam[17] += Net.fetch("1V8")
    cam[18] += GND
    for i in range(19, 25):
        cam[i] += NC                    # reserved on DNP connector
    cam["MP"] += GND                    # shell/nail pads (H3.2 pad binding)

    # ---------------- PIN radiation detector front-end ---------------------
    # BPW34-class PIN, charge amp (OPA381-class), comparator -> GEIGER_PULSE.
    # Powered from 3V3_AON so the sentinel can count dose in ambient mode.
    pin_d = BPW34(ref="D_PIN", footprint="OptoDevice:Osram_BPW34S-SMD")
    champ = OPA381(ref="U_CHAMP", footprint="Package_SO:MSOP-8_3x3mm_P0.65mm")
    cmp_ = TLV3201(ref="U_CMP", footprint="Package_TO_SOT_SMD:SOT-23-5")
    shield = SHIELD_CAN(ref="SH_RAD", footprint="generated:SHIELD_CAN_RAD_10x10")

    champ["V+"] += aon
    champ["V-"] += GND
    for p in champ.pins:             # MSOP-8 pads 6-8: NC-pending (E0)
        if p.name.startswith("PEND_"):
            p += NC
    cmp_["V+"] += aon
    cmp_["V-"] += GND
    decouple(aon, n=2)

    # reverse bias the PIN from AON through RC filter; cathode to bias
    rbias = R("10M")
    cflt = C("100nF")
    vbias = Net.fetch("PIN_BIAS")
    aon += rbias[1]
    vbias += rbias[2], cflt[1], pin_d["K"]
    GND += cflt[2]
    # anode into the charge-amp virtual ground
    node_in = Net.fetch("RAD_IN")
    node_in += pin_d["A"], champ["-IN"]
    # mid-rail reference for the amp
    rr1, rr2 = R("1M"), R("1M")
    vref = Net.fetch("RAD_VREF")
    aon += rr1[1]
    vref += rr1[2], rr2[1], champ["+IN"]
    GND += rr2[2]
    crf = C("100nF")
    vref += crf[1]
    GND += crf[2]
    # charge-integration feedback
    rfb = R("100M")
    cfb = C("1pF")
    rad_out = Net.fetch("RAD_ANALOG")     # -> ADS131M04 AIN1P (energy proxy)
    node_in += rfb[1], cfb[1]
    rad_out += rfb[2], cfb[2], champ["OUT"]
    # comparator threshold + pulse output to sentinel counter
    rt1, rt2 = R("910k"), R("100k")       # threshold ~10% above VREF (E0)
    vth = Net.fetch("RAD_VTH")
    aon += rt1[1]
    vth += rt1[2], rt2[1], cmp_["-IN"]
    GND += rt2[2]
    cmp_["+IN"] += rad_out
    geiger = Net.fetch("GEIGER_PULSE")
    cmp_["OUT"] += geiger
    tp(geiger)
    # guard/shield: single-point ground tie through 0R
    sh_net = Net.fetch("SHIELD_RAD")
    sh_net += shield["S1"], shield["S2"], shield["S3"], shield["S4"]
    rsh = R("0R")
    sh_net += rsh[1]
    GND += rsh[2]

    # ---------------- AD8317 RF survey detector ----------------------------
    rf = AD8317(ref="U_RF", footprint="generated:AD8317_LFCSP8_2x3")
    # ECO-H3.2 (floorplan capacity): the vertical SMA (8.4x8.4 courtyard)
    # has no legal window left — RF survey input moves to a U.FL receptacle
    # (4.4x5.1); the external survey antenna attaches via a shell-mounted
    # SMA pigtail (owner ratify). Same 2-pad model, same nets.
    sma = J_SMA(ref="J_RF", footprint="Connector_Coaxial:U.FL_Hirose_U.FL-R-SMT-1_Vertical")
    rf["VPOS"] += v3sys
    rf["GND"] += GND
    decouple(v3sys, n=2)
    cin = C("47nF")
    rfin = Net.fetch("RF_IN")
    sma["SIG"] += rfin
    sma["GND"] += GND
    rfin += cin[1]
    rf["INHI"] += cin[2]
    cin2 = C("47nF")
    rf["INLO"] += cin2[1]
    GND += cin2[2]
    rf["VOUT"] += Net.fetch("RF_DET_OUT")   # -> N657 ADC_IN0
    rf["TADJ"] += GND
    for p in rf.pins:                # LFCSP pads 7/8 + EP: NC-pending (E0)
        if p.name.startswith("PEND_"):
            p += NC

    # ---------------- UV + white illumination (interlocked) ----------------
    # UV drive = EN_UV_REQ (N657) AND INTERLOCK_OK (sentinel) — R5 safety.
    ilk = AND_1G08(ref="U_ILK", footprint="Package_TO_SOT_SMD:SOT-353_SC-70-5")
    ilk["VCC"] += v3sys
    ilk["GND"] += GND
    decouple(v3sys, n=1)
    ilk["A"] += Net.fetch("EN_UV_REQ")
    ilk["B"] += Net.fetch("INTERLOCK_OK")
    uv_gate = Net.fetch("UV_GATE")
    ilk["Y"] += uv_gate

    q_uv = NFET_SOT23(ref="Q_UV", footprint="Package_TO_SOT_SMD:SOT-23")
    d_uv = LED("UV_365nm")
    d_uv.ref = "D_UV"
    r_uv = R("10R")
    rg1 = R("100R")
    uv_gate += rg1[1]
    q_uv["G"] += rg1[2]
    q_uv["S"] += GND
    v_opt += r_uv[1]            # VLED = 3V3_OPTICAL (domain-gated: 2nd interlock)
    join("UV_LED_A", r_uv[2], d_uv["A"])
    join("UV_LED_K", d_uv["K"], q_uv["D"])

    q_wh = NFET_SOT23(ref="Q_WHITE", footprint="Package_TO_SOT_SMD:SOT-23")
    d_wh = LED("White")
    d_wh.ref = "D_WHITE"
    r_wh = R("4.7R")
    rg2 = R("100R")
    join("EN_WHITE", rg2[1])
    q_wh["G"] += rg2[2]
    q_wh["S"] += GND
    v_opt += r_wh[1]
    join("WHITE_LED_A", r_wh[2], d_wh["A"])
    join("WHITE_LED_K", d_wh["K"], q_wh["D"])

    # ---------------- glow ring: 6x LED from sentinel PWM ------------------
    for i in range(1, 7):
        d = LED("glow")
        d.ref = f"D_GLOW{i}"
        r = R("330R")
        join(f"GLOW{i}", r[1])
        join(f"GLOW{i}_A", r[2], d["A"])
        GND += d["K"]

    # ---------------- blower fan (VSYS, low-side FET + flyback) ------------
    fan = J_FAN(ref="J_FAN", footprint="Connector_PinHeader_1.00mm:PinHeader_1x02_P1.00mm_Vertical_SMD_Pin1Left")
    q_fan = NFET_SOT23(ref="Q_FAN", footprint="Package_TO_SOT_SMD:SOT-23")
    d_fly = SCHOTTKY("SS14")
    d_fly.ref = "D_FLY"
    rg3 = R("100R")
    fan["FAN+"] += vsys
    fan_n = Net.fetch("FAN_N")
    fan_n += fan["FAN-"], q_fan["D"], d_fly["A"]
    vsys += d_fly["K"]
    join("EN_FAN", rg3[1])
    q_fan["G"] += rg3[2]
    q_fan["S"] += GND

    # ---------------- SGX-4CO + LMP91000 potentiostat ----------------------
    # Cell: VERIFIED-DS DS-0138 Issue 3 p1/p3 — 3 pins O1.55 on 13.5 PCD;
    # pins must NOT be soldered (p3 note 1) -> PSB socket receptacles
    # (~O1.7 drill), field-replaceable cell (R2). 70±20 nA/ppm, 10R load,
    # >24 mo life. ECO EXECUTED (H3.1): gas_b zone repacked — envelope now
    # 17x17 (pads+courtyard on-board; the O20 can is also on-board here).
    cell = SGX_4CO(ref="U_CO", footprint="generated:SGX_4CO_4SERIES_TH")
    # AFE: VERIFIED-DS LMP91000 SNAS506I p3 — real WSON-14 pin map (see
    # lib_parts); split grounds DGND(1)/AGND(7), DAP -> AGND.
    pot = LMP91000(ref="U_COAFE", footprint="Package_SON:WSON-14-1EP_4.0x4.0mm_P0.5mm_EP2.6x2.6mm")
    pot["VDD"] += v_air          # hard-gated with AIR domain (ADR-0002 note:
    pot["DGND"] += GND           # continuous-bias trade documented in report)
    pot["AGND"] += GND           # both grounds to GND net (star at the part)
    pot["EP"] += GND             # DAP: "connect to AGND"  VERIFIED-DS p3
    pot["NC"] += NC              # pin 5 not internally connected
    decouple(v_air, n=1, bulk_uF=1)
    pot["SDA"] += sda_b          # I2C-B, fixed 7-bit addr 1001000 = 0x48
    pot["SCL"] += scl_b          # VERIFIED-DS SNAS506I §7.5.1 p20
    pot["MENB_N"] += GND         # enabled whenever AIR domain is powered —
                                 # legal: only LMP91000 on the bus (§7.5.2 p20)
    # VREF: internal-ref mode is the register default (REFCN=0x20 ->
    # REF_SOURCE=internal/VDD, VERIFIED-DS §7.6.4 p22). Tie VREF to the AIR
    # rail through 0R so an external reference can be fitted at H3 without
    # a respin (pin must not float if REF_SOURCE is ever set external).
    r_vref = R("0R")
    v_air += r_vref[1]
    join("CO_VREF", r_vref[2], pot["VREF"])
    join("CO_WE", pot["WE"], cell["WE"])
    join("CO_RE", pot["RE"], cell["RE"])
    join("CO_CE", pot["CE"], cell["CE"])
    cc1 = C("2.2uF")
    pot["C1"] += cc1[1]
    pot["C2"] += cc1[2]          # C1-C2 external filter per DS p3 (E0 value)
    pot["VOUT"] += Net.fetch("CO_AFE_OUT")   # -> ADS131M04 AIN3P
