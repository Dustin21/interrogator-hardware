"""Power tree — interrogator v1.1 (H2 stage-1).

VBAT (1S LiPo, J_BATT) -> BQ29700+dual-NFET protection (low-side)
 -> BQ25620 charger/powerpath (VBUS via CYPD3177 USB-C PD sink) -> VSYS
VSYS -> TPS62840 -> 3V3_AON     (always-on sentinel rail, 60nA IQ)
VSYS -> TPS62823 -> VDD_CORE_N6 (N657 core, EN_N6-gated)
VSYS -> TPS62823 -> 3V3_SYS     (main 3.3V, EN_N6-gated)  ** STAGE-1 ADD **
VSYS -> TLV62568 -> 1V8         (N657 VDD18 / NOR / ENS161 core, EN_N6-gated)
3V3_SYS -> 6x TPS22916 -> 3V3_{OPTICAL,AIR,CONTACT,RADAR,GNSS,WIFI} (EN_* from sentinel)
VSYS    -> TPS22916 #7 -> VACC (pogo accessory power, EN_ACC)      ** STAGE-1 ADD **

STAGE-1 ADDs found during circuit capture (components.json/floorplan update needed):
- U_SYS3V3 (second TPS62823): the ratified regulator set had no main 3.3V rail —
  the 6 domain load switches would otherwise switch raw VSYS (3.0-4.35V) into
  3.3V-rated sensors. SOT-583 + L + 2C fits the power zone.
- U_SW_ACC (7th TPS22916): ADR-0002 accessory port power must be switchable;
  "Load switches x6" in components.json becomes x7.
"""

from skidl import Net, POWER

from lib_parts import (CYPD3177, BQ25620, BQ27427, BQ29700, DUAL_NFET,
                       TPS62840, TPS62823, TLV62568, TPS22916, J_BATT,
                       USB_C_16P)
from util import join, C, R, L, decouple, gnd, tp


def build_power():
    GND = gnd()
    GND.drive = POWER  # board ground reference

    # ---------------- USB-C input + PD sink -----------------------------
    jusb = USB_C_16P(ref="J_USB",
                     footprint="Connector_USB:USB_C_Receptacle_GCT_USB4105-xx-A_16P_TopMnt_Horizontal")
    vbus = Net.fetch("VBUS_C")
    vbus.drive = POWER          # sourced by the upstream USB host/charger
    for p in ("VBUS_A4", "VBUS_A9", "VBUS_B4", "VBUS_B9"):
        vbus += jusb[p]
    for p in ("GND_A1", "GND_A12", "GND_B1", "GND_B12", "SHIELD"):
        GND += jusb[p]
    cc1, cc2 = Net.fetch("CC1"), Net.fetch("CC2")
    cc1 += jusb["CC1"]
    cc2 += jusb["CC2"]
    # USB data + SBU handled in compute/accessory modules via shared nets
    join("USB_DP", jusb["DP1"], jusb["DP2"])
    join("USB_DM", jusb["DN1"], jusb["DN2"])
    tp(Net.fetch("SBU1"))
    join("SBU1", jusb["SBU1"])
    tp(Net.fetch("SBU2"))
    join("SBU2", jusb["SBU2"])

    pd = CYPD3177(ref="U_PD", footprint="Package_DFN_QFN:HVQFN-24-1EP_4x4mm_P0.5mm_EP2.6x2.6mm")
    pd["VBUS"] += vbus
    pd["GND"] += GND
    pd["CC1"] += cc1
    pd["CC2"] += cc2
    # Resistor straps: request 5V-min/9V-max window at 3A (values E0 — set from
    # CYPD3177 DS strap tables at stage-2; ~1C fast charge needs >=15W input).
    for pin, val in (("VBUS_MIN", "10k"), ("VBUS_MAX", "24k"),
                     ("ISNK_COARSE", "13k"), ("ISNK_FINE", "16.9k")):
        r = R(val)
        pd[pin] += r[1]
        GND += r[2]
    flt = Net.fetch("PD_FAULT_N")
    flt += pd["FAULT_N"]
    tp(flt)
    pd["FLIP"] += Net.fetch("PD_FLIP")
    tp(Net.fetch("PD_FLIP"))
    decouple(vbus, n=1, bulk_uF=10)

    # ---------------- battery + protection ------------------------------
    jbat = J_BATT(ref="J_BATT",
                  footprint="Connector_JST:JST_ACH_BM03B-ACHSS-GAN-ETF_1x03-1MP_P1.20mm_Vertical")
    vbat = Net.fetch("VBAT")          # protected cell positive
    vbat.drive = POWER                # driven by the cell itself
    cell_n = Net.fetch("CELL_N")      # cell negative, ahead of protection FETs
    cell_n.drive = POWER              # ERC waiver W2: this IS the cell's - terminal
    vbat += jbat["BATT+"]
    cell_n += jbat["BATT-"]
    ntc = Net.fetch("BATT_NTC")
    ntc += jbat["NTC"]

    prot = BQ29700(ref="U_PROT", footprint="Package_SON:WSON-6_1.5x1.5mm_P0.5mm")
    q = DUAL_NFET(ref="Q_PROT", footprint="Package_SON:WSON-6-1EP_2x2mm_P0.65mm_EP1x1.6mm")
    # low-side protection: CELL_N -[DSG|CHG FETs]- GND (pack-)
    prot_mid = Net.fetch("PROT_MID")
    q["S1"] += cell_n
    q["D1"] += prot_mid
    q["D2"] += prot_mid
    q["S2"] += GND
    q["G1"] += prot["DOUT"]
    q["G2"] += prot["COUT"]
    rv = R("330R")   # VDD RC filter per BQ297xx DS
    vbat += rv[1]
    prot_vdd = Net.fetch("PROT_VDD")
    prot_vdd.drive = POWER   # ERC waiver W1: VDD fed from VBAT via 330R RC (DS topology)
    prot_vdd += rv[2], prot["VDD"]
    cvdd = C("100nF")
    prot_vdd += cvdd[1]
    cell_n += cvdd[2]
    prot["VSS"] += cell_n
    rvm = R("2k")
    prot["VM"] += rvm[1]
    GND += rvm[2]

    # ---------------- fuel gauge (SENTINEL_I2C) -------------------------
    # BQ27427 integrated low-side sense # VERIFY exact sense topology at stage-2
    gauge = BQ27427(ref="U_GAUGE", footprint="Package_BGA:Texas_DSBGA-9_1.62mmx1.58mm_Layout3x3_P0.5mm")
    sent_sda, sent_scl = Net.fetch("SENT_SDA"), Net.fetch("SENT_SCL")
    gauge["VDD"] += Net.fetch("3V3_AON")
    gauge["BIN"] += vbat
    gauge["SRX"] += GND     # internal 7mR to VSS # pinout E0 — verify
    gauge["VSS"] += GND
    gauge["SDA"] += sent_sda
    gauge["SCL"] += sent_scl
    gauge["GPOUT"] += Net.fetch("GAUGE_INT_N")
    decouple(Net.fetch("3V3_AON"), n=1)

    # ---------------- charger / power path ------------------------------
    chg = BQ25620(ref="U_CHG", footprint="Package_DFN_QFN:Texas_RTE_WQFN-16-1EP_3x3mm_P0.5mm_EP1.2x0.8mm")
    vsys = Net.fetch("VSYS")
    chg["VBUS"] += vbus
    cpmid = C("10uF", bulk=True)
    chg["PMID"] += cpmid[1]
    GND += cpmid[2]
    cregn = C("1uF")
    chg["REGN"] += cregn[1]
    GND += cregn[2]
    # buck: SW -> L -> VSYS
    lchg = L("1uH")
    chg["SW"] += lchg[1]
    vsys += lchg[2]
    cbtst = C("47nF")
    chg["BTST"] += cbtst[1]
    chg["SW"] += cbtst[2]
    chg["SYS"] += vsys
    chg["BAT"] += vbat
    chg["SDA"] += sent_sda           # SENTINEL_I2C addr 0x6B
    chg["SCL"] += sent_scl
    chg["INT_N"] += Net.fetch("CHG_INT_N")
    rce = R("10k")                    # /CE low = charge enabled
    chg["CE_N"] += rce[1]
    GND += rce[2]
    rqon = R("100k")
    chg["QON_N"] += rqon[1]
    vbat += rqon[2]
    # TS: pack NTC divider from REGN
    rts1, rts2 = R("5.23k"), R("30.1k")
    chg["REGN"] += rts1[1]
    chg["TS"] += rts1[2], rts2[1], ntc
    GND += rts2[2]
    chg["GND"] += GND
    chg["PGND"] += GND
    decouple(vsys, n=2, bulk_uF=22)
    decouple(vbat, n=1, bulk_uF=10)

    # ---------------- regulators -----------------------------------------
    aon = Net.fetch("3V3_AON")
    aon.drive = POWER   # rail sourced via L from TPS62840 SW (drive set: L/C output)
    u_aon = TPS62840(ref="U_AON", footprint="Package_TO_SOT_SMD:SOT-583-8")
    u_aon["VIN"] += vsys
    u_aon["EN"] += vsys            # always on
    u_aon["MODE"] += GND
    l_aon = L("2.2uH")
    u_aon["SW"] += l_aon[1]
    aon += l_aon[2]
    u_aon["VOS"] += aon
    u_aon["GND"] += GND
    cin = C("4.7uF", bulk=True)
    u_aon["VIN"] += cin[1]
    GND += cin[2]
    decouple(aon, n=1, bulk_uF=10)

    en_n6 = Net.fetch("EN_N6")

    vcore = Net.fetch("VDD_CORE_N6")
    vcore.drive = POWER  # L/C buck output
    u_core = TPS62823(ref="U_CORE", footprint="Package_TO_SOT_SMD:SOT-583-8")
    u_core["VIN"] += vsys
    u_core["EN"] += en_n6
    u_core["MODE"] += GND
    l_core = L("470nH")
    u_core["SW"] += l_core[1]
    vcore += l_core[2]
    rfb1, rfb2 = R("100k"), R("110k")   # FB divider for ~0.8V core (values E0)
    vcore += rfb1[1]
    u_core["FB"] += rfb1[2], rfb2[1]
    GND += rfb2[2]
    u_core["GND"] += GND
    cin2 = C("10uF", bulk=True)
    u_core["VIN"] += cin2[1]
    GND += cin2[2]
    decouple(vcore, n=2, bulk_uF=22)

    # STAGE-1 ADD: main 3.3V system rail (see module docstring)
    v3sys = Net.fetch("3V3_SYS")
    v3sys.drive = POWER  # L/C buck output
    u_sys = TPS62823(ref="U_SYS3V3", footprint="Package_TO_SOT_SMD:SOT-583-8")
    u_sys["VIN"] += vsys
    u_sys["EN"] += en_n6
    u_sys["MODE"] += GND
    l_sys = L("470nH")
    u_sys["SW"] += l_sys[1]
    v3sys += l_sys[2]
    rfa, rfb = R("332k"), R("100k")     # ~3.3V divider (values E0)
    v3sys += rfa[1]
    u_sys["FB"] += rfa[2], rfb[1]
    GND += rfb[2]
    u_sys["GND"] += GND
    cin3 = C("10uF", bulk=True)
    u_sys["VIN"] += cin3[1]
    GND += cin3[2]
    decouple(v3sys, n=2, bulk_uF=22)

    v18 = Net.fetch("1V8")
    v18.drive = POWER  # L/C buck output
    u18 = TLV62568(ref="U_1V8", footprint="Package_TO_SOT_SMD:SOT-23-5")
    u18["VIN"] += vsys
    u18["EN"] += en_n6
    l18 = L("2.2uH")
    u18["SW"] += l18[1]
    v18 += l18[2]
    r18a, r18b = R("187k"), R("100k")   # ~1.8V divider (values E0)
    v18 += r18a[1]
    u18["FB"] += r18a[2], r18b[1]
    GND += r18b[2]
    u18["GND"] += GND
    cin4 = C("4.7uF", bulk=True)
    u18["VIN"] += cin4[1]
    GND += cin4[2]
    decouple(v18, n=1, bulk_uF=10)

    # ---------------- domain load switches --------------------------------
    domains = ["OPTICAL", "AIR", "CONTACT", "RADAR", "GNSS", "WIFI"]
    for name in domains:
        sw = TPS22916(ref=f"U_SW_{name}", footprint="Package_CSP:TO_GENERATE_TPS22916_CSP4")
        rail = Net.fetch(f"3V3_{name}")
        sw["VIN"] += v3sys
        sw["VOUT"] += rail
        sw["ON"] += Net.fetch(f"EN_{name}")
        sw["GND"] += GND
        decouple(rail, n=1, bulk_uF=10)
        tp(rail)

    # STAGE-1 ADD: accessory-port switched power (from VSYS: accessories may
    # regulate locally; pogo pin carries battery-class voltage)
    sw_acc = TPS22916(ref="U_SW_ACC", footprint="Package_CSP:TO_GENERATE_TPS22916_CSP4")
    vacc = Net.fetch("VACC")
    sw_acc["VIN"] += vsys
    sw_acc["VOUT"] += vacc
    sw_acc["ON"] += Net.fetch("EN_ACC")
    sw_acc["GND"] += GND
    decouple(vacc, n=1, bulk_uF=10)

    # rail testpoints
    for n in ("VBUS_C", "VBAT", "VSYS", "3V3_AON", "3V3_SYS", "VDD_CORE_N6", "1V8"):
        tp(Net.fetch(n))
