"""I2C sensor clusters.

I2C-A (N657 I2C1, 1MHz-capable, pull-ups 2.2k -> 3V3_SYS in compute.py):
  0x66  MLX90642   VERIFIED-DS p16 (default SA=0x66; 0x33 only if
                   EEPROM SA is set to 0x00)        OPTICAL domain
  0x3A  MLX90632   VERIFIED-DS p10 (ADDR=GND)       OPTICAL domain
  0x57  MAX30102   (fixed)                          CONTACT domain
  0x30  AS7058     # VERIFY addr (short DS silent)  CONTACT domain
  0x59  TCS3448    VERIFIED-DS p19 — MOVED from I2C-B (0x59 collided
                   with SGP41 there); 1.8V-only bus pins, ECO-H3 below.  OPTICAL

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

NOTE-ECO(H3): TCS3448 SCL/SDA abs-max is 1.98 V (DS001121 p9) while I2C-A is
pulled to 3V3_SYS — insert a 1.8V translator segment (PCA9306/LSF0102-class)
between I2C-A and the TCS3448 at H3, alongside the VL53L8/A121 1.8V-rail
ECOs. Its VDD + GPIO strap have already been moved to the 1V8 rail here.
"""

from skidl import Net

from lib_parts import (MLX90642, MLX90632, MAX30102, AS7058, BME688, SGP41,
                       ENS161, SCD41, TCS3448, AS7331, AS7421, SHT41,
                       MMC5983MA, TMAG5273, ELECTRODE)
from util import join, C, R, decouple, gnd, tp, pullup


def build_sensors_i2c():
    GND = gnd()
    v3sys = Net.fetch("3V3_SYS")
    v18 = Net.fetch("1V8")
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
    ppg = MAX30102(ref="U_MAX", footprint="OptoDevice:Maxim_OLGA-14_3.3x5.6mm_P0.8mm")
    ppg["VDD"] += v18
    ppg["VLED_P"] += v_con
    ppg["GND"] += GND
    ppg["PGND"] += GND
    ppg["SDA"] += sda_a          # VERIFIED-DS MAX30102 p2: pins rated to +6.0V -> 3V3 bus OK
    ppg["SCL"] += scl_a          # (DS abs-max 6V on SDA/SCL — confirm stage-2)
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
    # ECG electrodes: thumb field (engraved face) + return ring; the return/
    # reference is also exported on the pogo accessory port (ACC_AN1).
    e_l = ELECTRODE(ref="E_ECG_L", footprint="generated:ELECTRODE_PAD_8MM")
    e_r = ELECTRODE(ref="E_ECG_R", footprint="generated:ELECTRODE_PAD_8MM")
    e_ref = ELECTRODE(ref="E_ECG_REF", footprint="generated:ELECTRODE_RING_12MM")
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
    gas["SDI"] += sda_b
    gas["SCK"] += scl_b
    gas["SDO"] += v_air     # addr 0x77
    gas["CSB"] += v_air     # I2C mode
    decouple(v_air, n=1, bulk_uF=1)

    # SGP41 0x59 — VERIFIED-DS SGP41 p12: fixed address 0x59. CLOSED.
    dev(SGP41, "U_SGP", v_air, sda_b, scl_b,
        "generated:SGP41_DFN6_2.44x2.44")

    # ENS161 0x53 (ADDR high) — VERIFIED-DS v1.1 p5/p7: 1.8V core (1.71-1.98),
    # 3.6V-tolerant SDA/SCL, ADDR/CSn/INTn are VDDIO-referred; LGA-9 is a
    # 3x3 pad GRID, pitch 1.05 (p41). Wiring confirmed as modeled.
    mox = ENS161(ref="U_ENS", footprint="generated:ENS161_LGA9")
    mox["VDD"] += v18            # DS: 1.71-1.98V core; note: 1V8 rail is
    mox["VDDIO"] += v_air        # EN_N6-gated, not AIR-gated — power seq note
    mox["GND"] += GND
    mox["GND2"] += GND
    mox["SDA"] += sda_b
    mox["SCL"] += scl_b
    mox["ADDR"] += v_air         # 0x53
    mox["CS_N"] += v_air         # I2C mode
    decouple(v18, n=1)
    decouple(v_air, n=1)
    int_ens = Net.fetch("INT_ENS")
    mox["INT_N"] += int_ens
    pullup(int_ens, v3sys, "47k")

    # SCD41 0x62
    co2 = dev(SCD41, "U_SCD", v_air, sda_b, scl_b,
              "Sensor:Sensirion_SCD4x-1EP_10.1x10.1mm_P1.25mm_EP4.8x4.8mm", bulk=10)

    # SHT41 0x44 (deliberate: IQS7222A 0x44 lives on SENTINEL_I2C instead)
    dev(SHT41, "U_SHT", v_air, sda_b, scl_b,
        "Sensor_Humidity:Sensirion_DFN-4_1.5x1.5mm_P0.8mm_SHT4x_NoCentralPad")

    # TCS3448 0x59 — VERIFIED-DS DS001121 p19 Table 8 (0x39 anchor refuted).
    # Moved to I2C-A (0x59 collides with SGP41 on I2C-B). 1.8V-only part:
    # VDD abs-max 1.98V (p9) -> fed from 1V8, no longer 3V3_OPTICAL (bug
    # fixed); GPIO strap to 1V8 selects the 1.8V I2C I/O level at startup
    # (p21 — GPIO must not float). SCL/SDA still need the H3 level-shift
    # segment (see module docstring). INT is 3.6V-tolerant (p9) -> 3V3
    # pullup legal (DS recommends 1.8V; N657 needs 3.3V VIH — H3 revisit).
    vis = TCS3448(ref="U_TCS", footprint="generated:TCS3448_OLGA8")
    vis["VDD"] += v18
    vis["GND"] += GND
    vis["PGND"] += GND
    vis["SDA"] += sda_a
    vis["SCL"] += scl_a
    vis["GPIO"] += v18        # >1.5V at startup -> 1.8V bus I/O  VERIFIED-DS p21
    vis["LDR"] += NC          # LED driver unused — leave open per DS p8
    decouple(v18, n=1, bulk_uF=1)
    int_tcs = Net.fetch("INT_TCS")
    vis["INT_N"] += int_tcs
    pullup(int_tcs, v3sys, "47k")

    # AS7331 0x74 (A1A0=00) — VERIFIED-DS AS7331 p43: addr[6:0]=1110_1,A1,A0;
    # A1=pin7, A0=pin14 (p9). A1A0=00 -> 0x74. CLOSED.
    uv = dev(AS7331, "U_AS7331", v_opt, sda_b, scl_b,
             "generated:AS7331_OLGA16")
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
