"""I2C sensor clusters.

I2C-A (N657 I2C1, 1MHz-capable, pull-ups 2.2k -> 3V3_SYS in compute.py):
  0x33  MLX90642   (fixed per DS family)            OPTICAL domain
  0x3A  MLX90632   (default per DS)                 OPTICAL domain
  0x57  MAX30102   (fixed)                          CONTACT domain
  0x30  AS7058     # VERIFY addr vs AS7058 DS       CONTACT domain

I2C-B (N657 I2C2, 400kHz, pull-ups 4.7k -> 3V3_SYS in compute.py):
  0x77  BME688     (SDO strapped high)              AIR domain
  0x59  SGP41      (fixed)                          AIR domain
  0x53  ENS161     (ADDR strapped high)             AIR domain
  0x62  SCD41      (fixed)                          AIR domain
  0x44  SHT41      (fixed)                          AIR domain
  0x39  TCS3448    # VERIFY addr (AS7343-family)    OPTICAL domain
  0x74  AS7331     (A1A0 = 00)                      OPTICAL domain
  0x64  AS7421     # VERIFY addr                    OPTICAL domain
  0x30  MMC5983MA  (fixed)                          3V3_SYS (magnet zone)
  0x35  TMAG5273   # VERIFY variant (A1 default)    3V3_SYS (magnet zone)
  0x57  BMV080     # VERIFY addr                    AIR domain (sensors_misc)
  0x48  LMP91000   (fixed)                          AIR domain (sensors_misc)

COLLISION AUDIT (stage-1):
- 0x44 SHT41 (I2C-B) vs IQS7222A (0x44): RESOLVED — IQS7222A deliberately on
  SENTINEL_I2C (it also serves as the sentinel wake source). See accessory.py.
- 0x30 MMC5983MA (I2C-B) vs AS7058 0x30 (I2C-A): different buses — fine, but
  the AS7058 address itself is # VERIFY.
- 0x57 BMV080 (I2C-B) vs MAX30102 0x57 (I2C-A): different buses — fine.
- No two devices on the SAME bus share an address in the table above.
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
    # MLX90642 0x33 — TO-39, tallest top part
    dev(MLX90642, "U_MLX42", v_opt, sda_a, scl_a,
        "Package_TO_SOT_THT:TO-39-4")

    # MLX90632 0x3A — medical spot FIR
    dev(MLX90632, "U_MLX32", v_opt, sda_a, scl_a,
        "Package_DFN_QFN:TO_GENERATE_MLX90632_SFN")

    # MAX30102 0x57 — VDD=1V8 analog, VLED from CONTACT domain
    ppg = MAX30102(ref="U_MAX", footprint="OptoDevice:Maxim_OLGA-14_3.3x5.6mm_P0.8mm")
    ppg["VDD"] += v18
    ppg["VLED_P"] += v_con
    ppg["GND"] += GND
    ppg["PGND"] += GND
    ppg["SDA"] += sda_a          # VERIFY: 1.8V-core part on 3.3V-pulled bus
    ppg["SCL"] += scl_a          # (DS abs-max 6V on SDA/SCL — confirm stage-2)
    decouple(v18, n=1, bulk_uF=1)
    decouple(v_con, n=1, bulk_uF=10)   # LED pulses need local bulk
    int_max = Net.fetch("INT_MAX")
    ppg["INT_N"] += int_max
    pullup(int_max, v3sys, "47k")

    # AS7058 0x30 (# VERIFY addr) — PPG/ECG/BioZ AFE
    afe = AS7058(ref="U_AS7058", footprint="Package_CSP:TO_GENERATE_AS7058_WLCSP42")
    afe["VDD"] += v_con
    afe["VDDIO"] += v_con
    afe["GND"] += GND
    afe["SDA"] += sda_a
    afe["SCL"] += scl_a
    decouple(v_con, n=2, bulk_uF=1)
    afe["INT"] += Net.fetch("INT_AS7058")
    # ECG electrodes: thumb field (engraved face) + return ring; the return/
    # reference is also exported on the pogo accessory port (ACC_AN1).
    e_l = ELECTRODE(ref="E_ECG_L", footprint="TO_GENERATE:ELECTRODE_FIELD")
    e_r = ELECTRODE(ref="E_ECG_R", footprint="TO_GENERATE:ELECTRODE_FIELD")
    e_ref = ELECTRODE(ref="E_ECG_REF", footprint="TO_GENERATE:ELECTRODE_RING")
    join("ECG_INP", afe["ECG_INP"], e_l["E"])
    join("ECG_INN", afe["ECG_INN"], e_r["E"])
    join("ACC_AN1", afe["ECG_REF"], e_ref["E"])   # shared w/ pogo AN1

    # ======================= I2C-B =======================================
    # BME688 0x77 (SDO high)
    gas = BME688(ref="U_BME", footprint="Package_LGA:Bosch_LGA-8_3x3mm_P0.8mm_ClockwisePinNumbering")
    gas["VDD"] += v_air
    gas["VDDIO"] += v_air
    gas["GND"] += GND
    gas["SDI"] += sda_b
    gas["SCK"] += scl_b
    gas["SDO"] += v_air     # addr 0x77
    gas["CSB"] += v_air     # I2C mode
    decouple(v_air, n=1, bulk_uF=1)

    # SGP41 0x59
    dev(SGP41, "U_SGP", v_air, sda_b, scl_b,
        "Sensor_Humidity:TO_GENERATE_SGP41_DFN")

    # ENS161 0x53 (ADDR high) — 1.8V core, 3V3 IO
    mox = ENS161(ref="U_ENS", footprint="Package_LGA:TO_GENERATE_ENS161_LGA9")
    mox["VDD"] += v18            # DS: 1.71-1.98V core; note: 1V8 rail is
    mox["VDDIO"] += v_air        # EN_N6-gated, not AIR-gated — power seq note
    mox["GND"] += GND
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

    # TCS3448 0x39 (# VERIFY addr)
    vis = dev(TCS3448, "U_TCS", v_opt, sda_b, scl_b,
              "OptoDevice:TO_GENERATE_TCS3448_OLGA")
    int_tcs = Net.fetch("INT_TCS")
    vis["INT_N"] += int_tcs
    pullup(int_tcs, v3sys, "47k")

    # AS7331 0x74 (A1A0=00)
    uv = dev(AS7331, "U_AS7331", v_opt, sda_b, scl_b,
             "OptoDevice:TO_GENERATE_AS7331_OLGA16")
    uv["A0"] += GND
    uv["A1"] += GND
    uv["READY"] += Net.fetch("RDY_AS7331")
    uv["SYN"] += GND    # not using SYN-triggered mode in v1

    # AS7421 0x64 (# VERIFY addr) — NIR spectral + integrated 970nm LED drive
    nir = dev(AS7421, "U_AS7421", v_opt, sda_b, scl_b,
              "OptoDevice:TO_GENERATE_AS7421_OLGA")
    int_7421 = Net.fetch("INT_AS7421")
    nir["INT"] += int_7421
    pullup(int_7421, v3sys, "47k")
    # 970nm hydration LED, driven by AS7421 LED0 sink
    from util import LED
    d_nir = LED("970nm")
    d_nir.ref = "D_NIR"
    rnir = R("22R")
    v_opt += rnir[1]
    led_a = Net.fetch("NIR_LED_A")
    led_a += rnir[2], d_nir["A"]
    join("NIR_LED_K", d_nir["K"], nir["LED0"])

    # MMC5983MA 0x30 — magnet zone, powered from 3V3_SYS (>15mm from currents)
    mag = MMC5983MA(ref="U_MMC", footprint="Package_LGA:LGA-16_3x3mm_P0.5mm")
    mag["VDD"] += v3sys
    mag["VDDIO"] += v3sys
    mag["GND"] += GND
    mag["SDA"] += sda_b
    mag["SCL"] += scl_b
    decouple(v3sys, n=2, bulk_uF=1)
    mag["INT_DRDY"] += Net.fetch("DRDY_MMC")

    # TMAG5273 0x35 (# VERIFY A1-variant default addr) — dock-magnet detect
    hall = TMAG5273(ref="U_TMAG", footprint="Package_TO_SOT_SMD:SOT-23-6")
    hall["VCC"] += v3sys      # note: dock detect while N6 off is served by
    hall["GND"] += GND        # IQS7222A wake + gauge; TMAG polled when SYS on
    hall["SDA"] += sda_b
    hall["SCL"] += scl_b
    decouple(v3sys, n=1)
    int_tmag = Net.fetch("INT_TMAG")
    hall["INT_N"] += int_tmag
    pullup(int_tmag, v3sys, "47k")
