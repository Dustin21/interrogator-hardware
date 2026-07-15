"""Accessory / human-IO / debug: pogo port, touch, haptics, TAG-Connect, TPs.

J_USB itself is instantiated in power.py (VBUS/CC are power-tree facts);
its DP/DM/SBU nets are shared by name.
"""

from skidl import Net

from lib_parts import J_POGO, IQS7222A, DRV2605L, TC2030, J_LRA, J_TOUCH_FPC
from util import join, C, R, decouple, gnd, tp, pullup


def build_accessory():
    GND = gnd()
    aon = Net.fetch("3V3_AON")
    v3sys = Net.fetch("3V3_SYS")
    sent_sda, sent_scl = Net.fetch("SENT_SDA"), Net.fetch("SENT_SCL")

    # ---------------- magnetic 6-pogo accessory port (ADR-0002) -----------
    # ECO-H3.2 (floorplan capacity): board side of the accessory port is a
    # compact 2x3 landing field; the ADR-0002 9mm magnetic ring geometry
    # moves to the shell part (dock pogo pins reach the lands through shell
    # inserts). Nets unchanged; owner ratify.
    pogo = J_POGO(ref="J_POGO", footprint="generated:POGO6_COMPACT")
    pogo["VACC"] += Net.fetch("VACC")        # switched VSYS (U_SW_ACC, EN_ACC)
    pogo["GND"] += GND
    pogo["SDA"] += sent_sda                  # accessory ID EEPROM lives at 0x50
    pogo["SCL"] += sent_scl                  #   (reserved — no on-board device)
    pogo["AN1"] += Net.fetch("ACC_AN1")      # AS7058 ECG_REF / return electrode
    pogo["AN2"] += Net.fetch("ACC_AN2")      # ADS131M04 AIN2P (probe input)

    # ---------------- IQS7222A touch — SENTINEL_I2C 0x44 -------------------
    # Deliberately on the sentinel bus: (a) resolves the 0x44 collision with
    # SHT41 on I2C-B, (b) touch is the always-on wake source (RDY -> sentinel).
    # VERIFIED-DS IQS7222A v1.7 p6-7: QFN20 real pin map; addr 0x44 requires
    # ORDER CODE IQS7222Axxx001 (code 102 would be 0x57). Each VREG pin needs
    # its own 2.2uF (p45 §12.1.2); MCLR has an internal 200k pullup (ext. 10k
    # kept). TAB (pad 21) to VSS per p6 note.
    # RATIFIED (H3.0): QFN20 exposes only NINE sensor pins (CRx0-7 + CTx8) —
    # v1 ships a 9-electrode SELF-CAP flex (3 of the 12 planned zones
    # dropped: both reserves + one merged squeeze pair, see
    # docs/user-experience.md). E0-E8 wired; the flex connector keeps its
    # 13 positions with E9-E11 grounded as guard/shield traces, so a v1.1
    # mutual-cap Rx/Tx matrix flex plugs into the SAME connector (CTx
    # re-mapping is firmware + flex artwork only, no board respin).
    touch = IQS7222A(ref="U_TOUCH", footprint="Package_DFN_QFN:QFN-20-1EP_3x3mm_P0.4mm_EP1.65x1.65mm")
    touch["VDDHI"] += aon
    touch["GND"] += GND
    touch["EP"] += GND               # thermal TAB -> VSS (DS p6)
    decouple(aon, n=1, bulk_uF=1)
    cregd = C("2.2uF")               # VREGD cap  VERIFIED-DS p45
    touch["VREGD"] += cregd[1]
    GND += cregd[2]
    crega = C("2.2uF")               # VREGA cap  VERIFIED-DS p45
    touch["VREGA"] += crega[1]
    GND += crega[2]
    touch["SDA"] += sent_sda
    touch["SCL"] += sent_scl
    rdy = Net.fetch("TOUCH_RDY_N")
    touch["RDY"] += rdy
    pullup(rdy, aon, "47k")
    mclr = Net.fetch("TOUCH_MCLR_N")
    touch["MCLR_N"] += mclr
    pullup(mclr, aon, "10k")
    touch["OUTA"] += NC              # configurable output, unused
    touch["NC1"] += NC
    touch["NC2"] += NC
    # shell electrodes on the flex connector (engraved-face field)
    # ECO-H3.2: J_TOUCH switches from the 0.5mm FH12-13 to the same Molex
    # 503566-1302 0.3mm ZIF the BMV080 uses (shell flex is our artwork; BOM
    # consolidation + 101->29mm2 courtyard).
    jt = J_TOUCH_FPC(ref="J_TOUCH", footprint="generated:ZIF13_MOLEX_503566")
    for i in range(9):               # CRx0-7 + CTx8 -> E0..E8
        join(f"TOUCH_E{i}", touch[f"E{i}"], jt[f"E{i}"])
    for i in range(9, 12):           # E9-E11: guard/shield positions on the
        jt[f"E{i}"] += GND           # v1 9-electrode flex (H3.0 ratified)
    jt["GND"] += GND
    jt["MP1 MP2"] += GND             # ZIF nail pads (H3.2 pad binding)

    # ---------------- DRV2605L haptic — SENTINEL_I2C 0x5A ------------------
    # VERIFIED-DS SLOS854D p5 (DGS/VSSOP-10 pin map): REG (pin 1, 1.8V LDO
    # out) needs 1uF — was missing; pin 6 VDD/NC tied to VDD per DS;
    # IN/TRIG to GND when unused — matches.
    hap = DRV2605L(ref="U_HAP", footprint="Package_SO:VSSOP-10_3x3mm_P0.5mm")
    hap["VDD"] += aon
    hap["VDD_NC"] += aon             # pin 6: tie to VDD or float (DS p5)
    hap["GND"] += GND
    decouple(aon, n=1, bulk_uF=1)
    creg_h = C("1uF")                # REG LDO cap  VERIFIED-DS p5
    hap["REG"] += creg_h[1]
    GND += creg_h[2]
    hap["SDA"] += sent_sda
    hap["SCL"] += sent_scl
    hap["EN"] += Net.fetch("EN_HAPTIC")
    hap["IN_TRIG"] += GND            # I2C-triggered playback only in v1  VERIFIED-DS p5
    lra = J_LRA(ref="J_LRA", footprint="generated:LRA_PADS")
    join("LRA_P", hap["OUT_P"], lra["OUT+"])
    join("LRA_N", hap["OUT_N"], lra["OUT-"])

    # ---------------- TAG-Connect TC2030 x2 --------------------------------
    # ECO-H3.2-D: TC2030 -> plain 1.27mm pad row (the TC2030 NPTH locating
    # holes had no both-face-clear window left on the packed bean); same
    # 6-signal order as the TC2030 cable, debug via pogo bar/soldered leads.
    tc1 = TC2030(ref="J_SWD_N6", footprint="generated:SWD_PADROW_6")
    tc1["VTREF"] += v3sys
    tc1["SWDIO"] += Net.fetch("N6_SWDIO")
    tc1["NRST"] += Net.fetch("N6_NRST")
    tc1["SWCLK"] += Net.fetch("N6_SWCLK")
    tc1["GND"] += GND
    swo1 = Net.fetch("N6_SWO")
    tc1["SWO"] += swo1
    tp(swo1)

    tc2 = TC2030(ref="J_SWD_BL", footprint="generated:SWD_PADROW_6")  # ECO-H3.2-D
    tc2["VTREF"] += aon
    tc2["SWDIO"] += Net.fetch("BL_SWDIO")
    tc2["NRST"] += Net.fetch("BL_RESET_N")
    tc2["SWCLK"] += Net.fetch("BL_SWCLK")
    tc2["GND"] += GND
    swo2 = Net.fetch("BL_SWO")
    tc2["SWO"] += swo2
    tp(swo2)

    # ---------------- remaining bus/system testpoints ----------------------
    for n in ("GND", "USB_DP", "USB_DM", "ACC_AN1", "GNSS_TX", "GNSS_RX",
              "RAD_ANALOG", "RF_DET_OUT", "CLK_ADS", "WAKE_N6", "ATTN_N6",
              "EN_N6", "INTERLOCK_OK"):
        tp(Net.fetch(n))
