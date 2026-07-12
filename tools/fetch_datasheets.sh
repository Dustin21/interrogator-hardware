#!/bin/bash
# Fetch missing datasheets into registry_assets/<PART>/datasheet/ (structure-preserving).
# Run from anywhere:  bash tools/fetch_datasheets.sh [/path/to/registry_assets]
# URLs are vendor-canonical patterns; if one 404s (vendors move files), search
# "<part> datasheet pdf" and save into the printed folder. Re-run safe (skips existing).
set -u
R="${1:-$HOME/Development/registry_assets}"
get() { # get <PART> <filename> <url>
  d="$R/$1/datasheet"; mkdir -p "$d"
  if [ -s "$d/$2" ]; then echo "skip   $1/$2 (exists)"; return; fi
  echo "fetch  $1/$2"
  curl -fsSL --retry 2 -A "Mozilla/5.0" -o "$d/$2" "$3" \
    && echo "  ok   -> $d/$2" \
    || { rm -f "$d/$2"; echo "  FAIL $1 — get manually: $3 (or search '$1 datasheet pdf') -> $d/"; }
}
# --- CRITICAL: routing blocker ---
get STM32N657  stm32n657x0.pdf              "https://www.st.com/resource/en/datasheet/stm32n657x0.pdf"
# --- sensors ---
get MLX90642   MLX90642-Datasheet.pdf       "https://www.melexis.com/-/media/files/documents/datasheets/mlx90642-datasheet-melexis.pdf"
get MLX90632   MLX90632-Datasheet.pdf       "https://www.melexis.com/-/media/files/documents/datasheets/mlx90632-datasheet-melexis.pdf"
get TCS3448    TCS3448_DS.pdf               "https://look.ams-osram.com/m/6d9b0866e1efe58f/original/TCS3448-DS001235.pdf"
get AS7058     AS7058_DS.pdf                "https://look.ams-osram.com/m/2a3adb35f4c8adf7/original/AS7058-DS001417.pdf"
get AS7421     AS7421_DS.pdf                "https://look.ams-osram.com/m/76d1e50a77e6ef5b/original/AS7421-DS000657.pdf"
get MIA-M10Q   MIA-M10Q_DataSheet.pdf       "https://content.u-blox.com/sites/default/files/MIA-M10Q_DataSheet_UBX-22015849.pdf"
get MIA-M10Q   MIA-M10Q_IntegrationManual.pdf "https://content.u-blox.com/sites/default/files/documents/MIA-M10Q_IntegrationManual_UBX-22016387.pdf"
get SCD41      SCD4x_Datasheet.pdf          "https://sensirion.com/media/documents/48C4B7FB/64C134E7/Sensirion_SCD4x_Datasheet.pdf"
get SHT41      SHT4x_Datasheet.pdf          "https://sensirion.com/media/documents/33FD6951/662A593A/HT_DS_Datasheet_SHT4x.pdf"
get ENS161     ENS161-Datasheet.pdf         "https://www.sciosense.com/wp-content/uploads/2023/12/ENS161-Datasheet.pdf"
get IQS7222A   IQS7222A_Datasheet.pdf       "https://www.azoteq.com/images/stories/pdf/iqs7222a_datasheet.pdf"
get ADS131M04  ads131m04.pdf                "https://www.ti.com/lit/ds/symlink/ads131m04.pdf"
get SGX-4CO    SGX-4CO-Datasheet.pdf        "https://www.sgxsensortech.com/content/uploads/2014/08/DS-0143-SGX-4CO-Datasheet.pdf"
# --- power tree (TI symlink pattern is stable) ---
for p in tps62840 tps62823 tlv62568 bq25620 bq27427 bq29700 tps22916 drv2605l; do
  get "POWER-$p" "$p.pdf" "https://www.ti.com/lit/ds/symlink/$p.pdf"
done
get CYPD3177   CYPD3177_DS.pdf              "https://www.infineon.com/dgdl/Infineon-CYPD3177_EZ-PD_BCR_Datasheet-DataSheet-v03_00-EN.pdf?fileId=8ac78c8c7d0d8da4017d0ee7f44b70a7"
get ESP32-C6-MINI-1 esp32-c6-mini-1_datasheet_en.pdf "https://www.espressif.com/sites/default/files/documentation/esp32-c6-mini-1_mini-1u_datasheet_en.pdf"
get BL54L15    BL54L15_DS.pdf               "https://www.ezurio.com/documentation/datasheet-bl54l15-series"
get BNO086     BNO08x-Datasheet.pdf         "https://www.ceva-ip.com/wp-content/uploads/BNO080_085-Datasheet.pdf"
get VL53L8CH   vl53l8ch.pdf                 "https://www.st.com/resource/en/datasheet/vl53l8ch.pdf"
get VD66GY     vd66gy.pdf                   "https://www.st.com/resource/en/datasheet/vd66gy.pdf"
echo; echo "Done. Failures (if any) are listed above with target folders."
