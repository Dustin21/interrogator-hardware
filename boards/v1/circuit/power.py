"""Power tree — interrogator v1.1 (H2 stage-1).

VBAT (1S LiPo, J_BATT) -> BQ29700+dual-NFET protection (low-side)
 -> BQ25620 charger/powerpath (VBUS via CYPD3177 USB-C PD sink) -> VSYS
VSYS -> TPS62840 -> 3V3_AON     (always-on sentinel rail, 60nA IQ)
VSYS -> TPS62823 -> VDD_CORE_N6 (N657 core 0.81/0.89V, gated by N6 PWR_ON
                                 handshake per DS14791 Fig 3; VOS-high leg
                                 switched by N6_VCORE_SEL)   ** H2.6 fix **
VSYS -> TPS62823 -> 3V3_SYS     (main 3.3V, EN_N6-gated)  ** STAGE-1 ADD **
VSYS -> TLV62568 -> 1V8         (N657 VDDA18*/VDDIO3 / NOR / ENS161 core;
                                 EN from 3V3_SYS rail — VDD-first sequencing
                                 per DS14791 Table 24 fn1)   ** H2.6 fix **
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
                       USB_C_16P, NFET_SOT23)
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
    pd["VSS"] += GND
    pd["EP"] += GND
    pd["CC1"] += cc1
    pd["CC2"] += cc2
    # Straps — VERIFIED-DS 002-25383 p8 Tables 2/3/4: each strap is a
    # resistor DIVIDER from VDDD (internal 3.3V LDO, pin 23), not a single
    # R to GND (old stage-1 values replaced). Request: 5V min (pin to GND),
    # 9V max (5.1k up / 1k down), 3A coarse (5.1k/5.1k), +0mA fine (GND).
    vddd = Net.fetch("PD_VDDD")
    vddd += pd["VDDD"]
    for cval in ("1uF", "100nF", "100nF"):   # VDDD needs 1uF + 2x100nF (p6)
        c = C(cval)
        vddd += c[1]
        GND += c[2]
    cvccd = C("1uF")                          # VCCD needs 1uF (p6)
    pd["VCCD"] += cvccd[1]
    GND += cvccd[2]
    pd["VBUS_MIN"] += GND                     # 5V min  (ratio 0/6, Table 2)
    pd["ISNK_FINE"] += GND                    # +0 mA   (ratio 0/6, Table 4)
    for pin, rup, rdn in (("VBUS_MAX", "5.1k", "1k"),      # 9V max, Table 2
                          ("ISNK_COARSE", "5.1k", "5.1k")):  # 3A, Table 3
        ru, rd = R(rup), R(rdn)
        vddd += ru[1]
        pd[pin] += ru[2], rd[1]
        GND += rd[2]
    # FAULT is driven HIGH on fault (p8 — push, not OD-low): testpoint only,
    # no pullup (old PD_FAULT_N pullup removed in compute.py).
    flt = Net.fetch("PD_FAULT")
    flt += pd["FAULT"]
    tp(flt)
    # FLIP: OD; no pull-up fitted -> UFP VDO reports data-capable (p6) — OK,
    # USB data goes to the N657.
    pd["FLIP"] += Net.fetch("PD_FLIP")
    tp(Net.fetch("PD_FLIP"))
    decouple(vbus, n=1, bulk_uF=10)

    # ---------------- battery + protection ------------------------------
    jbat = J_BATT(ref="J_BATT",
                  footprint="Connector_JST:JST_ACH_BM03B-ACHSS-GAN-ETF_1x03-1MP_P1.20mm_Vertical")
    # PACKP = cell positive at the connector; VBAT = system-side battery node.
    # The BQ27427's INTERNAL 7mΩ high-side sense resistor sits between them
    # (PACKP -> BAT ... SRX -> VBAT). VERIFIED-DS bq27427 p3 Table 4-1: "SRX —
    # integrated high-side sense resistor ... between battery pack and system
    # power rail". The old low-side "SRX->GND" wiring was a real bug (it
    # would have shorted the sense terminal to ground).
    packp = Net.fetch("PACKP")
    packp.drive = POWER               # the cell's + terminal
    vbat = Net.fetch("VBAT")          # system-side node, fed through the 7mΩ
    vbat.drive = POWER                # ERC waiver W4: sourced via gauge 7mΩ
    packp += jbat["BATT+"]
    cell_n = Net.fetch("CELL_N")      # cell negative, ahead of protection FETs
    cell_n.drive = POWER              # ERC waiver W2: this IS the cell's - terminal
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
    rv = R("330R")   # VDD RC filter per BQ297xx DS (330Ω VERIFIED-DS p14)
    packp += rv[1]   # protector monitors the true cell terminal (ahead of gauge 7mΩ)
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
    # BQ27427 — VERIFIED-DS SLUSEB5B p3 Table 4-1 (three stage-1 bugs fixed):
    #  * HIGH-side sense: BAT (C3) -> PACKP Kelvin, SRX (C2) -> VBAT system
    #    node (old wiring shorted SRX to GND).
    #  * VDD (B3) is the internal 1.8V LDO OUTPUT — 2.2µF to VSS only (old
    #    wiring back-drove it from 3V3_AON).
    #  * BIN (B1) is battery-insertion detect — 10kΩ to VSS for an embedded
    #    pack, never tied to a rail (old wiring tied it to VBAT).
    # SDA/SCL/GPOUT are OD, VPU 1.62-3.6V (p4) -> AON-rail pullups legal.
    gauge = BQ27427(ref="U_GAUGE", footprint="Package_BGA:Texas_DSBGA-9_1.62mmx1.58mm_Layout3x3_P0.5mm")
    sent_sda, sent_scl = Net.fetch("SENT_SDA"), Net.fetch("SENT_SCL")
    gauge["BAT"] += packp
    cbat = C("1uF")                  # BAT-VSS cap per DS p3
    packp += cbat[1]
    GND += cbat[2]
    gauge["SRX"] += vbat             # system side of internal 7mΩ
    gauge_vdd = Net.fetch("GAUGE_VDD")
    gauge_vdd += gauge["VDD"]        # PWROUT pin drives the net (internal LDO)
    cldo = C("2.2uF")                # CLDO18 per DS p4
    gauge_vdd += cldo[1]
    GND += cldo[2]
    rbin = R("10k")                  # embedded-pack BIN pulldown (DS p3)
    gauge["BIN"] += rbin[1]
    GND += rbin[2]
    gauge["VSS"] += GND
    gauge["VSS2"] += GND
    gauge["SDA"] += sent_sda
    gauge["SCL"] += sent_scl
    gauge["GPOUT"] += Net.fetch("GAUGE_INT_N")

    # ---------------- charger / power path ------------------------------
    # BQ25620 — VERIFIED-DS SLUSEG2D p5-6 Table 6-1: package is WQFN-18
    # "RYK" 2.5x3.0 (footprint replaced — the stage-1 WQFN-16 RTE was the
    # wrong package). REGN cap corrected 1uF -> 4.7uF (p5). D+/D- (BC1.2
    # detect) left open: input current comes from the PD contract via I2C.
    # PG/STAT open-drain, floating allowed (p5-6).
    chg = BQ25620(ref="U_CHG", footprint="generated:BQ25620_WQFN18_RYK")
    vsys = Net.fetch("VSYS")
    chg["VBUS"] += vbus
    cpmid = C("10uF", bulk=True)
    chg["PMID"] += cpmid[1]
    GND += cpmid[2]
    cregn = C("4.7uF")               # REGN cap 4.7uF VERIFIED-DS p5
    chg["REGN"] += cregn[1]
    GND += cregn[2]
    chg["DP"] += NC
    chg["DM"] += NC
    chg["PG_N"] += NC                # unused OD status, float per DS
    chg["STAT"] += NC                # "leave floating if unused" (p5)
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
    chg["GND"] += GND                # single GND pin on RYK (15) + thermal
    decouple(vsys, n=2, bulk_uF=22)
    decouple(vbat, n=1, bulk_uF=10)

    # ---------------- regulators -----------------------------------------
    aon = Net.fetch("3V3_AON")
    aon.drive = POWER   # rail sourced via L from TPS62840 SW (drive set: L/C output)
    # TPS62840 — VERIFIED-DS SLVSEC6D p4-5: VSET resistor added (267k ->
    # VOUT 3.3V, Table 1 p22 — the stage-1 model had NO VSET, leaving the
    # rail voltage undefined); STOP tied low (normal switching); MODE low =
    # power-save (must be terminated, p5).
    u_aon = TPS62840(ref="U_AON", footprint="Package_TO_SOT_SMD:SOT-583-8")
    u_aon["VIN"] += vsys
    u_aon["EN"] += vsys            # always on
    u_aon["MODE"] += GND
    u_aon["STOP"] += GND
    rset = R("267k")               # VOUT = 3.3V  VERIFIED-DS Table 1 p22
    u_aon["VSET"] += rset[1]
    GND += rset[2]
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
    # TPS62823 — VERIFIED-DS SLVSDV6C p3: no MODE pin exists (stage-1 model
    # had a phantom one); AGND+PGND to GND, PG/NC left floating per DS.
    # N657 VDDCORE — VERIFIED-DS DS14791 Table 24 p139: SoC Run VOS low =
    # 0.782-0.842V (0.81 typ), VOS high (800MHz overdrive) = 0.858-0.921V
    # (0.89 typ). The stage-1 100k/110k divider gave 1.145V (VFB=0.6V,
    # SLVSDV6C p5) — OVER the 0.921V operating max: REAL BUG, fixed.
    # Two-level divider: 34.8k/100k -> 0.809V at boot (VOS low, legal in
    # every mode); N6 GPIO N6_VCORE_SEL switches a 255k leg in parallel
    # (via Q_VSEL) -> 0.891V before firmware raises VOS high for 800MHz.
    # EN comes from N6_PWR_ON (DS14791 §3.4.7 Fig 3 p27: with an external
    # VCORE supply the N657 asserts PWR_ON once VDD/VDDA18AON are valid and
    # the external regulator must then bring VDDCORE up) — NOT from EN_N6
    # directly; 100k pulldown on the net (compute.py) keeps it off during
    # the VDD ramp. Whole-domain gating still works: EN_N6 off -> VDD off
    # -> PWR_ON low -> core buck off.
    u_core = TPS62823(ref="U_CORE", footprint="Package_TO_SOT_SMD:SOT-583-8")
    u_core["VIN"] += vsys
    u_core["EN"] += Net.fetch("N6_PWR_ON")   # VERIFIED-DS DS14791 Fig 3 p27
    u_core["PG"] += NC
    u_core["NC"] += NC
    l_core = L("470nH")
    u_core["SW"] += l_core[1]
    vcore += l_core[2]
    rfb1, rfb2 = R("34.8k"), R("100k")  # 0.809V VOS-low  VERIFIED-DS Table 24
    vcore += rfb1[1]
    u_core["FB"] += rfb1[2], rfb2[1]
    GND += rfb2[2]
    # VOS-high leg: 255k to GND via NFET -> FB bottom = 100k||255k -> 0.891V
    rfb3 = R("255k")
    q_vsel = NFET_SOT23(ref="Q_VSEL", footprint="Package_TO_SOT_SMD:SOT-23")
    u_core["FB"] += rfb3[1]
    join("VSEL_LEG", rfb3[2], q_vsel["D"])
    q_vsel["S"] += GND
    rg_vsel = R("100k")                 # gate pulldown: boots at 0.81V
    join("N6_VCORE_SEL", q_vsel["G"], rg_vsel[1])
    GND += rg_vsel[2]
    u_core["AGND"] += GND
    u_core["PGND"] += GND
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
    u_sys["PG"] += NC              # VERIFIED-DS SLVSDV6C p3 (no MODE pin)
    u_sys["NC"] += NC
    l_sys = L("470nH")
    u_sys["SW"] += l_sys[1]
    v3sys += l_sys[2]
    # VFB = 0.6V (VERIFIED-DS SLVSDV6C p5) -> 449k/100k = 3.294V. The old
    # E0 332k/100k gave only 2.59V — every "3.3V" domain undervolted: BUG.
    rfa, rfb = R("449k"), R("100k")
    v3sys += rfa[1]
    u_sys["FB"] += rfa[2], rfb[1]
    GND += rfb[2]
    u_sys["AGND"] += GND
    u_sys["PGND"] += GND
    cin3 = C("10uF", bulk=True)
    u_sys["VIN"] += cin3[1]
    GND += cin3[2]
    decouple(v3sys, n=2, bulk_uF=22)

    v18 = Net.fetch("1V8")
    v18.drive = POWER  # L/C buck output
    u18 = TLV62568(ref="U_1V8", footprint="Package_TO_SOT_SMD:SOT-23-5")
    u18["VIN"] += vsys
    # EN from the 3V3_SYS RAIL (not EN_N6): DS14791 Table 24 fn1 p140 — the
    # N657's VDD "must be present before any other supply". Sequencing the
    # 1V8 rail (VDDA18*/VDDIO3) behind the 3.3V rail satisfies that with no
    # extra parts; TLV62568 EN is VIN-tolerant (SLVSD89B p3).
    u18["EN"] += v3sys
    l18 = L("2.2uH")
    u18["SW"] += l18[1]
    v18 += l18[2]
    # VFB = 0.6V (VERIFIED-DS SLVSD89B p4) -> 200k/100k = 1.800V exactly.
    # The old E0 187k/100k gave 1.722V — inside most abs-mins but sloppy.
    r18a, r18b = R("200k"), R("100k")
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
        sw = TPS22916(ref=f"U_SW_{name}", footprint="generated:TPS22916_CSP4")
        rail = Net.fetch(f"3V3_{name}")
        sw["VIN"] += v3sys
        sw["VOUT"] += rail
        sw["ON"] += Net.fetch(f"EN_{name}")
        sw["GND"] += GND
        decouple(rail, n=1, bulk_uF=10)
        tp(rail)

    # STAGE-1 ADD: accessory-port switched power (from VSYS: accessories may
    # regulate locally; pogo pin carries battery-class voltage)
    sw_acc = TPS22916(ref="U_SW_ACC", footprint="generated:TPS22916_CSP4")
    vacc = Net.fetch("VACC")
    sw_acc["VIN"] += vsys
    sw_acc["VOUT"] += vacc
    sw_acc["ON"] += Net.fetch("EN_ACC")
    sw_acc["GND"] += GND
    decouple(vacc, n=1, bulk_uF=10)

    # rail testpoints
    for n in ("VBUS_C", "VBAT", "VSYS", "3V3_AON", "3V3_SYS", "VDD_CORE_N6", "1V8"):
        tp(Net.fetch(n))
