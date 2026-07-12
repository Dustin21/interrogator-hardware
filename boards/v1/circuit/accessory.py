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
    pogo = J_POGO(ref="J_POGO", footprint="Connector:TO_GENERATE_POGO6_MAGRING")
    pogo["VACC"] += Net.fetch("VACC")        # switched VSYS (U_SW_ACC, EN_ACC)
    pogo["GND"] += GND
    pogo["SDA"] += sent_sda                  # accessory ID EEPROM lives at 0x50
    pogo["SCL"] += sent_scl                  #   (reserved — no on-board device)
    pogo["AN1"] += Net.fetch("ACC_AN1")      # AS7058 ECG_REF / return electrode
    pogo["AN2"] += Net.fetch("ACC_AN2")      # ADS131M04 AIN2P (probe input)

    # ---------------- IQS7222A touch — SENTINEL_I2C 0x44 -------------------
    # Deliberately on the sentinel bus: (a) resolves the 0x44 collision with
    # SHT41 on I2C-B, (b) touch is the always-on wake source (RDY -> sentinel).
    touch = IQS7222A(ref="U_TOUCH", footprint="Package_DFN_QFN:QFN-20-1EP_3x3mm_P0.4mm_EP1.65x1.65mm")
    touch["VDDHI"] += aon
    touch["GND"] += GND
    decouple(aon, n=1, bulk_uF=1)
    creg = C("1uF")
    touch["VREG"] += creg[1]
    GND += creg[2]
    touch["SDA"] += sent_sda
    touch["SCL"] += sent_scl
    rdy = Net.fetch("TOUCH_RDY_N")
    touch["RDY"] += rdy
    pullup(rdy, aon, "47k")
    mclr = Net.fetch("TOUCH_MCLR_N")
    touch["MCLR_N"] += mclr
    pullup(mclr, aon, "10k")
    # 12 shell electrodes out on a flex connector (engraved-face field)
    jt = J_TOUCH_FPC(ref="J_TOUCH", footprint="Connector_FFC-FPC:TO_GENERATE_FPC13_0.5mm")
    for i in range(12):
        join(f"TOUCH_E{i}", touch[f"E{i}"], jt[f"E{i}"])
    jt["GND"] += GND

    # ---------------- DRV2605L haptic — SENTINEL_I2C 0x5A ------------------
    hap = DRV2605L(ref="U_HAP", footprint="Package_SO:VSSOP-10_3x3mm_P0.5mm")
    hap["VDD"] += aon
    hap["GND"] += GND
    decouple(aon, n=1, bulk_uF=1)
    hap["SDA"] += sent_sda
    hap["SCL"] += sent_scl
    hap["EN"] += Net.fetch("EN_HAPTIC")
    hap["IN_TRIG"] += GND            # I2C-triggered playback only in v1
    lra = J_LRA(ref="J_LRA", footprint="TO_GENERATE:LRA_PADS")
    join("LRA_P", hap["OUT_P"], lra["OUT+"])
    join("LRA_N", hap["OUT_N"], lra["OUT-"])

    # ---------------- TAG-Connect TC2030 x2 --------------------------------
    tc1 = TC2030(ref="J_SWD_N6", footprint="Connector:Tag-Connect_TC2030-IDC-NL_2x03_P1.27mm_Vertical")
    tc1["VTREF"] += v3sys
    tc1["SWDIO"] += Net.fetch("N6_SWDIO")
    tc1["NRST"] += Net.fetch("N6_NRST")
    tc1["SWCLK"] += Net.fetch("N6_SWCLK")
    tc1["GND"] += GND
    swo1 = Net.fetch("N6_SWO")
    tc1["SWO"] += swo1
    tp(swo1)

    tc2 = TC2030(ref="J_SWD_BL", footprint="Connector:Tag-Connect_TC2030-IDC-NL_2x03_P1.27mm_Vertical")
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
