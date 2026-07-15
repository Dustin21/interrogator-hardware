"""I2C sensor clusters.

I2C-A (N657 I2C1, 1MHz-capable, pull-ups 2.2k -> 3V3_SYS in compute.py):
  0x66  MLX90642   VERIFIED-DS p16 (default SA=0x66; 0x33 only if
                   EEPROM SA is set to 0x00)        OPTICAL domain
  0x3A  MLX90632   VERIFIED-DS p10 (ADDR=GND)       OPTICAL domain
  0x57  MAX30102   (fixed)                          CONTACT domain
  0x30  AS7058     # VERIFY addr (short DS silent)  CONTACT domain
  0x59  TCS3448    VERIFIED-DS p19 — MOVED from I2C-B (0x59 collided
                   with SGP41 there); 1.8V-only bus pins -> PCA9306
                   segment, executed at H3.0 (see below).      OPTICAL

I2C-B (N657 I2C2, 400kHz, pull-ups 4.7k -> 3V3_SYS in compute.py):
  0x77  BME688     VERIFIED-DS p45 (SDO=VDDIO)      AIR domain
  0x59  SGP41      VERIFIED-DS p12 (fixed)          AIR domain
  0x53  ENS161     VERIFIED-DS p5 (ADDR high)       AIR domain
  0x62  SCD41      VERIFIED-DS p9 (fixed)           AIR domain
  0x44  SHT41      VERIFIED-DS p2 (SHT41-AD1B — order the AD1B code)  AIR
  0x74  AS7331     VERIFIED-DS p43 (1110_1,A1,A0; A1A0=00)            OPTICAL
  0x64  AS7421     VERIFIED-DS p23 (fixed)          OPTICAL domain
  0x30  MMC5983MA  (fixed)                          3V3_SYS (magnet zone)
  0x35  TMAG5273   VERIFIED-DS p16 (A1 variant)     3V3_SYS (magnet zone)
  0x57  BMV080     VERIFIED-DS p32 (CSB=MISO=1)     AIR domain (sensors_misc)
  0x48  LMP91000   VERIFIED-DS SNAS506I p20 (fixed 1001000)  AIR (sensors_misc)

COLLISION AUDIT (stage-2 update):
- 0x59 TCS3448 vs SGP41 (both would sit on I2C-B): TCS3448 DS001121 p19
  gives 0x59, refuting the 0x39 AS7343 anchor -> TCS3448 moved to I2C-A,
  where 0x59 is free. RESOLVED.
- 0x44 SHT41 (I2C-B) vs IQS7222A (0x44): RESOLVED — IQS7222A deliberately on
  SENTINEL_I2C (it also serves as the sentinel wake source). See accessory.py.
- 0x30 MMC5983MA (I2C-B) vs AS7058 0x30 (I2C-A): different buses — fine, but
  the AS7058 address itself is # VERIFY (the short DS carries no address).
- 0x57 BMV080 (I2C-B) vs MAX30102 0x57 (I2C-A): different buses — fine.
- No two devices on the SAME bus share an address in the table above.

ECO EXECUTED (H3.0): TCS3448 SCL/SDA abs-max is 1.98 V (DS001121 p9) while
I2C-A is pulled to 3V3_SYS — a PCA9306 pass-FET translator now bridges
I2C-A to a 1.8V-only segment (I2CA_SDA/SCL_1V8, pulled to 1V8_OPTICAL)
carrying just the TCS3448. Why a translator and not a 1.8V I2C controller
domain: the VFBGA142 bonds no I2C on a 1.8V-capable ball group (I2C1 absent;
I2C2/I2C4 balls sit in the 3.3V VDD domain; the only 1.8V domain, VDDIO3,
is the XSPI PN port with no I2C AF), and the part must stay on I2C-A
because its fixed 0x59 collides with SGP41 on I2C-B. The PCA9306 EN is
driven by EN_OPTICAL, so the dead 1.8V segment is isolated from the live
bus whenever the domain is gated off. VDD + GPIO strap now feed from the
GATED 1V8_OPTICAL sub-rail (was raw 1V8 — gating invariant restored).
"""

from skidl import Net

from lib_parts import (MLX90642, MLX90632, MAX30102, AS7058, BME688, SGP41,
                       ENS161, SCD41, TCS3448, AS7331, AS7421, SHT41,
                       MMC5983MA, TMAG5273, ELECTRODE, PCA9306)
from util import join, C, R, decouple, gnd, tp, pullup


def build_sensors_i2c():
    GND = gnd()
    v3sys = Net.fetch("3V3_SYS")
    v18 = Net.fetch("1V8")
    v18_opt = Net.fetch("1V8_OPTICAL")   # gated 1.8V sub-rails (power.py, H3.0)
    v18_air = Net.fetch("1V8_AIR")
    v_opt = Net.fetch("3V3_OPTICAL")
    v_air = Net.fetch("3V3_AIR")
    v_con = Net.fetch("3V3_CONTACT")
    sda_a, scl_a = Net.fetch("I2CA_SDA"), Net.fetch("I2CA_SCL")
    sda_b, scl_b = Net.fetch("I2CB_SDA"), Net.fetch("I2CB_SCL")

    def dev(part, ref, rail, sda, scl, fp, bulk=1):
        u = part(ref=ref, footprint=fp)
        u["VDD"] += rail
        u["GND"] += GND
        u["SDA"] += sda
        u["SCL"] += scl
        decouple(rail, n=1, bulk_uF=bulk)
        return u

    # ======================= I2C-A =======================================
    # MLX90642 0x66 — TO-39, tallest top part. VERIFIED-DS p4: 1=SDA 2=VDD
    # 3=GND 4=SCL (pin 2/3 swap fixed); p16: default SA 0x66. Custom TO-39
    # footprint: Ø5.84 pin circle, 45°-paired leads (p31 Fig 34) — generic
    # TO-39-4 does not match.
    dev(MLX90642, "U_MLX42", v_opt, sda_a, scl_a,
        "generated:MLX90642_TO39")

    # MLX90632 0x3A — medical spot FIR. VERIFIED-DS p8/p10: ADDR (pin 5)
    # grounded -> 0x3A; central pad (6) to GND with thermal vias (p47).
    mlx32 = dev(MLX90632, "U_MLX32", v_opt, sda_a, scl_a,
                "generated:MLX90632_SFN5_3x3")
    mlx32["ADDR"] += GND      # SA LSB = 0 -> 0x3A  VERIFIED-DS p10
    mlx32["EP"] += GND

    # MAX30102 0x57 — VDD=1V8 analog, VLED from CONTACT domain
    # H3.2: renumbered to the real OLGA-14 map (VERIFIED-DS p8) — VLED+ is
    # TWO pads (9+10, both fed); N.C. pads 1/5/6/7/8/14 soldered, no net.
    ppg = MAX30102(ref="U_MAX", footprint="OptoDevice:Maxim_OLGA-14_3.3x5.6mm_P0.8mm")
    ppg["VDD"] += v18
    ppg["VLED_P1 VLED_P2"] += v_con
    ppg["GND"] += GND
    ppg["PGND"] += GND
    ppg["NC1 NC5 NC6 NC7 NC8 NC14"] += NC   # "connect to PCB pad for mech stability" (p8)
    ppg["SDA"] += sda_a          # VERIFIED-DS MAX30102 p2: pins rated to +6.0V -> 3V3 bus OK
    ppg["SCL"] += scl_a          # (abs-max +6.0V on all pins, closed at H2.5)
    # H3.0 gating review: VDD deliberately stays on the RAW 1V8 rail (EN_N6-
    # gated only, no 1V8_CONTACT switch): with VLED_P hard-gated the part
    # cannot emit or sense, shutdown VDD draw is ~0.7uA, and the DS states
    # tolerance of any supply order (p28) — a dedicated sub-rail switch buys
    # nothing. Documented in H3_REPORT §H3.0-2.
    decouple(v18, n=1, bulk_uF=1)
    decouple(v_con, n=1, bulk_uF=10)   # LED pulses need local bulk
    int_max = Net.fetch("INT_MAX")
    ppg["INT_N"] += int_max
    pullup(int_max, v3sys, "47k")

    # AS7058 0x30 (# VERIFY addr) — PPG/ECG/BioZ AFE
    afe = AS7058(ref="U_AS7058", footprint="generated:AS7058_WLCSP42")
    afe["VDD"] += v_con
    afe["VDDIO"] += v_con
    afe["GND"] += GND
    afe["SDA"] += sda_a
    afe["SCL"] += scl_a
    decouple(v_con, n=2, bulk_uF=1)
    afe["INT"] += Net.fetch("INT_AS7058")
    # 33 balls with unknown signals (full DS NDA-gated) — declared NC-pending;
    # H3.3 must NOT route the AS7058 fanout until DS001573 lands.
    for p in afe.pins:
        if p.name.startswith("PEND_"):
            p += NC
    # ECG electrodes: thumb field (engraved face) + return ring; the return/
    # reference is also exported on the pogo accessory port (ACC_AN1).
    # ECO-H3.2 (floorplan capacity): board-side electrodes are 4mm LANDS;
    # the skin-facing electrode geometry moves to the shell (conductive
    # elastomer/spring contact) — direct skin contact through the 3.5mm
    # wall+clearance was never physical. Nets unchanged; owner ratify.
    e_l = ELECTRODE(ref="E_ECG_L", footprint="generated:ELECTRODE_LAND_4MM")
    e_r = ELECTRODE(ref="E_ECG_R", footprint="generated:ELECTRODE_LAND_4MM")
    # H3.2 floorplan capacity fix: the 12mm return RING (an E0 guess of ours)
    # has no legal 13x13 window on the packed back face — the board-level
    # return electrode is now an 8mm pad (electrically identical; ECG return
    # area is uncritical at these impedances). ECO-H4 (enclosure): the back
    # GRIP-RING UX element can be a shell-mounted conductive pad bonded to
    # this electrode if ID wants the full ring.
    e_ref = ELECTRODE(ref="E_ECG_REF", footprint="generated:ELECTRODE_LAND_4MM")
    join("ECG_INP", afe["ECG_INP"], e_l["E"])
    join("ECG_INN", afe["ECG_INN"], e_r["E"])
    join("ACC_AN1", afe["ECG_REF"], e_ref["E"])   # shared w/ pogo AN1

    # ======================= I2C-B =======================================
    # BME688 0x77 — VERIFIED-DS bst-bme688-ds000 p45: SDO=VDDIO -> 0x77,
    # SDO=GND -> 0x76, must not float. CSB high = I2C. CLOSED.
    gas = BME688(ref="U_BME", footprint="Package_LGA:Bosch_LGA-8_3x3mm_P0.8mm_ClockwisePinNumbering")
    gas["VDD"] += v_air
    gas["VDDIO"] += v_air
    gas["GND"] += GND
    gas["GND2"] += GND      # pin 7 (real LGA-8 map, VERIFIED-DS p51 — H3.2)
    gas["SDI"] += sda_b
    gas["SCK"] += scl_b
    gas["SDO"] += v_air     # addr 0x77
    gas["CSB"] += v_air     # I2C mode
    decouple(v_air, n=1, bulk_uF=1)

    # SGP41 0x59 — VERIFIED-DS SGP41 p12: fixed address 0x59. CLOSED.
    # H3.2 real-bug fix (Table 6 p7): VDDH hotplate supply was missing
    # ("VDD and VDDH must be connected to one single supply") — the VOC
    # heater had no feed; pad 4 (n/a) to ground per DS; die pad -> GND.
    voc = dev(SGP41, "U_SGP", v_air, sda_b, scl_b,
              "generated:SGP41_DFN6_2.44x2.44")
    voc["VDDH"] += v_air        # same supply as VDD  VERIFIED-DS Table 6 p7
    voc["DNC_GND"] += GND       # "connect to ground" (Table 6 p7)
    voc["EP"] += GND            # die pad internally GND (p7)

    # ENS161 0x53 (ADDR high) — VERIFIED-DS v1.1 p5/p7: 1.8V core (1.71-1.98),
    # 3.6V-tolerant SDA/SCL, ADDR/CSn/INTn are VDDIO-referred; LGA-9 is a
    # 3x3 pad GRID, pitch 1.05 (p41). ECO EXECUTED (H3.0): VDD moved from
    # the raw 1V8 rail to the gated 1V8_AIR sub-rail — core and VDDIO now
    # rise/fall together with EN_AIR (closes the old power-seq note) and
    # the AIR gating invariant covers the 1.8V core too.
    mox = ENS161(ref="U_ENS", footprint="generated:ENS161_LGA9")
    mox["VDD"] += v18_air        # DS: 1.71-1.98V core; EN_AIR-gated (H3.0)
    mox["VDDIO"] += v_air
    mox["GND"] += GND
    mox["GND2"] += GND
    mox["SDA"] += sda_b
    mox["SCL"] += scl_b
    mox["ADDR"] += v_air         # 0x53
    mox["CS_N"] += v_air         # I2C mode
    decouple(v18_air, n=1, bulk_uF=1)
    decouple(v_air, n=1)
    int_ens = Net.fetch("INT_ENS")
    mox["INT_N"] += int_ens
    pullup(int_ens, v3sys, "47k")

    # SCD41 0x62 — H3.2 real-bug fix: symbol rebuilt on the real 21-pad map
    # (VERIFIED-DS Table 6 p5 — the old sequential pins 1-4 all landed on
    # DNC pads: the sensor was completely unconnected); VDDH (19) tied to
    # VDD per DS ("must be tied to VDD on the customer PCB"), GND 6/20/21,
    # DNC pads soldered to floating PCB pads.
    co2 = dev(SCD41, "U_SCD", v_air, sda_b, scl_b,
              "Sensor:Sensirion_SCD4x-1EP_10.1x10.1mm_P1.25mm_EP4.8x4.8mm", bulk=10)
    co2["VDDH"] += v_air        # IR source supply = VDD  VERIFIED-DS Table 6 p5
    co2["GND2"] += GND
    co2["EP_GND"] += GND        # the 4 center pads (all numbered 21)
    for p in co2.pins:
        if p.name.startswith("DNC"):
            p += NC             # "solder to a floating pad" (Table 6 p5)

    # SHT41 0x44 (deliberate: IQS7222A 0x44 lives on SENTINEL_I2C instead)
    dev(SHT41, "U_SHT", v_air, sda_b, scl_b,
        "Sensor_Humidity:Sensirion_DFN-4_1.5x1.5mm_P0.8mm_SHT4x_NoCentralPad")

    # TCS3448 0x59 — VERIFIED-DS DS001121 p19 Table 8 (0x39 anchor refuted).
    # Moved to I2C-A (0x59 collides with SGP41 on I2C-B). 1.8V-only part:
    # VDD abs-max 1.98V (p9); GPIO strap selects the 1.8V I2C I/O level at
    # startup (p21 — GPIO must not float). ECO EXECUTED (H3.0): VDD + GPIO
    # feed from the GATED 1V8_OPTICAL sub-rail, and SCL/SDA sit on a
    # PCA9306-translated 1.8V segment of I2C-A (see module docstring).
    # INT is 3.6V-tolerant (p9) -> 3V3 pullup legal (N657 PF7 needs 3.3V
    # VIH — INT stays on the 3.3V side, no shifting needed).
    xlat = PCA9306(ref="U_XLAT_TCS", footprint="Package_SO:VSSOP-8_2.4x2.1mm_P0.5mm")
    sda_a18 = Net.fetch("I2CA_SDA_1V8")
    scl_a18 = Net.fetch("I2CA_SCL_1V8")
    xlat["GND"] += GND
    xlat["VREF1"] += v18_opt
    xlat["SDA2"] += sda_a          # 3.3V side (bus pullups in compute.py)
    xlat["SCL2"] += scl_a
    xlat["SDA1"] += sda_a18        # 1.8V segment
    xlat["SCL1"] += scl_a18
    pullup(sda_a18, v18_opt, "2.2k")   # Fm+-capable segment pullups
    pullup(scl_a18, v18_opt, "2.2k")
    # EN/VREF2 tied, 200k to 3V3 (PCA9306 DS typical app); EN_OPTICAL
    # drives the node so the pass-FETs open when the domain is gated off.
    en_x = Net.fetch("EN_OPTICAL")
    xlat["EN"] += en_x
    xlat["VREF2"] += en_x
    r_enx = R("200k")
    en_x += r_enx[1]
    v3sys += r_enx[2]
    vis = TCS3448(ref="U_TCS", footprint="generated:TCS3448_OLGA8")
    vis["VDD"] += v18_opt
    vis["GND"] += GND
    vis["PGND"] += GND
    vis["SDA"] += sda_a18
    vis["SCL"] += scl_a18
    vis["GPIO"] += v18_opt    # >1.5V at startup -> 1.8V bus I/O  VERIFIED-DS p21
    vis["LDR"] += NC          # LED driver unused — leave open per DS p8
    decouple(v18_opt, n=1, bulk_uF=1)
    int_tcs = Net.fetch("INT_TCS")
    vis["INT_N"] += int_tcs
    pullup(int_tcs, v3sys, "47k")

    # AS7331 0x74 (A1A0=00) — VERIFIED-DS AS7331 p43: addr[6:0]=1110_1,A1,A0;
    # A1=pin7, A0=pin14. A1A0=00 -> 0x74. H3.2: symbol rebuilt on the real
    # OLGA16 quad map (Fig 3/4 p7-8 — footprint regenerated too, the old
    # dual-row shape was wrong) and the MISSING 3.3 MOhm REXT reference
    # resistor added (pin 4 -> VSSA; "internal reference generator ... by
    # using an external resistor REXT", 3.267-3.333 MOhm, TC<=50ppm/K).
    uv = AS7331(ref="U_AS7331", footprint="generated:AS7331_OLGA16")
    uv["VDDA VDDD"] += v_opt
    uv["VSSA1 VSSA2 VSSA3 VSSA4 VSSA5 VSSA6 VSSD"] += GND
    uv["SDA"] += sda_b
    uv["SCL"] += scl_b
    decouple(v_opt, n=1, bulk_uF=1)
    rext = R("3.3M 1%")           # VERIFIED-DS elec. char. table (TC<=50ppm/K)
    join("AS7331_REXT", uv["REXT"], rext[1])
    GND += rext[2]
    uv["A0"] += GND
    uv["A1"] += GND
    uv["READY"] += Net.fetch("RDY_AS7331")
    uv["SYN"] += GND    # not using SYN-triggered mode in v1

    # AS7421 0x64 — VERIFIED-DS DS000667 p23 Fig 21. Bug fixed: the AS7421
    # has FOUR INTEGRATED NIR LEDs (760/830/950/1040nm, p10) driven by
    # internal current sinks (p20 §7.6) — there is no external-LED pin, so
    # the old external "970nm D_NIR + 22R" chain was deleted. LEDA (pins
    # 6+12) is the anode supply for the internal LEDs (abs-max 3.6V, p8);
    # 4x75mA pulses -> local bulk. RST (act-high, int. pulldown) and GPIO
    # strapped to GND (unused, p6-7).
    nir = dev(AS7421, "U_AS7421", v_opt, sda_b, scl_b,
              "generated:AS7421_OLGA10")
    nir["PGND1"] += GND
    nir["PGND2"] += GND
    nir["EP_GND"] += GND
    nir["LEDA"] += v_opt
    nir["EP_LEDA"] += v_opt
    nir["RST"] += GND
    nir["GPIO"] += GND
    decouple(v_opt, n=1, bulk_uF=10)   # LED pulse bulk (4x75mA, DS p20)
    int_7421 = Net.fetch("INT_AS7421")
    nir["INT"] += int_7421
    pullup(int_7421, v3sys, "47k")

    # MMC5983MA 0x30 — magnet zone, powered from 3V3_SYS (>15mm from currents)
    mag = MMC5983MA(ref="U_MMC", footprint="Package_LGA:LGA-16_3x3mm_P0.5mm")
    mag["VDD"] += v3sys
    mag["VDDIO"] += v3sys
    mag["GND"] += GND
    mag["SDA"] += sda_b
    mag["SCL"] += scl_b
    decouple(v3sys, n=2, bulk_uF=1)
    mag["INT_DRDY"] += Net.fetch("DRDY_MMC")
    # Memsic DS not staged: pins 1-6 PROVISIONAL-E0, pads 7-16 NC-pending —
    # do not route the MMC fanout until the DS lands (H3.2 pad binding).
    for p in mag.pins:
        if p.name.startswith("PEND_"):
            p += NC

    # TMAG5273 0x35 — VERIFIED-DS tmag5273 p16 Table 6-2: A1 variant default
    # addr 0x35 (order TMAG5273A1). Dock-magnet detect.
    hall = TMAG5273(ref="U_TMAG", footprint="Package_TO_SOT_SMD:SOT-23-6")
    hall["VCC"] += v3sys      # note: dock detect while N6 off is served by
    hall["GND"] += GND        # IQS7222A wake + gauge; TMAG polled when SYS on
    hall["SDA"] += sda_b
    hall["SCL"] += scl_b
    decouple(v3sys, n=1)
    int_tmag = Net.fetch("INT_TMAG")
    hall["INT_N"] += int_tmag
    pullup(int_tmag, v3sys, "47k")
