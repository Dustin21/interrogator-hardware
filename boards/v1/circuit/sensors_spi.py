"""SPI sensor cluster: VL53L8CH (SPI mode), BNO086 (SPI mode), ADS131M04."""

from skidl import Net

from lib_parts import VL53L8CH, BNO086, ADS131M04, PIEZO
from util import C, R, decouple, gnd, tp, pullup


def build_sensors_spi():
    GND = gnd()
    v3sys = Net.fetch("3V3_SYS")
    v_opt = Net.fetch("3V3_OPTICAL")
    sck = Net.fetch("SPI1_SCK")
    miso = Net.fetch("SPI1_MISO")
    mosi = Net.fetch("SPI1_MOSI")

    # ---------------- VL53L8CH — SPI mode --------------------------------
    tof = VL53L8CH(ref="U_VL53", footprint="Sensor_Distance:TO_GENERATE_ST_VL53L8")
    tof["AVDD"] += v_opt
    tof["IOVDD"] += v_opt
    tof["GND"] += GND
    decouple(v_opt, n=2, bulk_uF=10)   # AVDD sees VCSEL pulses -> extra bulk
    tof["SCLK"] += sck
    tof["MOSI"] += mosi
    tof["MISO"] += miso
    tof["NCS"] += Net.fetch("CS_VL53_N")
    # comm-mode straps in copper (DS: SPI select)  # VERIFY strap polarity
    tof["SPI_I2C_N"] += v_opt          # HIGH -> SPI
    tof["I2C_RST"] += GND              # LOW in SPI mode
    tof["LPN"] += Net.fetch("LPN_VL53")
    int_vl53 = Net.fetch("INT_VL53")
    tof["INT"] += int_vl53
    pullup(int_vl53, v3sys, "47k")     # INT is open-drain per DS

    # ---------------- BNO086 — SPI (SHTP) mode ----------------------------
    imu = BNO086(ref="U_BNO", footprint="Package_LGA:LGA-28_5.2x3.8mm_P0.5mm")
    imu["VDD"] += v3sys
    imu["VDDIO"] += v3sys
    imu["GND"] += GND
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

    # ---------------- ADS131M04 — precision 4ch ADC ------------------------
    adc = ADS131M04(ref="U_ADS", footprint="Package_DFN_QFN:TO_GENERATE_TI_ADS131M04_WQFN20")
    adc["AVDD"] += v3sys
    adc["DVDD"] += v3sys
    adc["AGND"] += GND
    adc["DGND"] += GND
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
    pz = PIEZO(ref="PZ1", footprint="TO_GENERATE:PIEZO_DISC_PADS")
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
