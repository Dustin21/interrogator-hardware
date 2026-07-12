#!/bin/bash
# Round 2b — verified URLs + hard timeouts (no hangs). ST last (Akamai may block curl entirely;
# browser fallback links printed). Run: bash tools/fetch_datasheets_round2.sh
set -u
R="${1:-$HOME/Development/registry_assets}"
UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"
get() { d="$R/$1/datasheet"; mkdir -p "$d"
  [ -s "$d/$2" ] && { echo "skip   $1/$2"; return; }
  echo "fetch  $1/$2"
  curl -fSL --http1.1 --connect-timeout 8 --max-time 90 --retry 1 -A "$UA" -o "$d/$2" "$3" 2>/dev/null \
    && echo "  ok   -> $d/$2" || { rm -f "$d/$2"; echo "  FAIL $1 — browser it: $3"; }
}
get TCS3448    TCS3448_DS001121.pdf      "https://look.ams-osram.com/m/1c24b057e65ee61e/original/TCS3448-14-Channel-multi-spectral-sensor.pdf"
get AS7058     AS7058_DS001085_short.pdf "https://look.ams-osram.com/m/264ac284b30311c3/original/AS7058-IC-for-PPG-ECG-and-body-impedance-measurement.pdf"
get AS7421     AS7421_DS000667.pdf       "https://look.ams-osram.com/m/1164a4e1da5c19a9/original/AS7421-DS000667.pdf"
get MIA-M10Q   MIA-M10Q_DataSheet_UBX-22015849.pdf "https://content.u-blox.com/sites/default/files/documents/MIA-M10Q_DataSheet_UBX-22015849.pdf"
get MIA-M10Q   MIA-M10Q_IntegrationManual_UBX-21028173.pdf "https://content.u-blox.com/sites/default/files/documents/MIA-M10Q_IntegrationManual_UBX-21028173.pdf"
get SHT41      SHT4x_Datasheet_v7.1.pdf  "https://sensirion.com/media/documents/33FD6951/67EB9032/HT_DS_Datasheet_SHT4x_5.pdf"
get ENS161     ENS161-Datasheet_v1.1.pdf "https://www.sciosense.com/wp-content/uploads/2024/12/ENS161-Datasheet.pdf"
get POWER-bq29700 bq2970_family.pdf      "https://www.ti.com/lit/ds/symlink/bq2970.pdf"
get CYPD3177   CYPD3177_002-25383.pdf    "https://www.infineon.com/dgdl/Infineon-EZ-PD_BCR_Datasheet_USB_Type-C_Port_Controller_for_Power_Sinks-DataSheet-v03_00-EN.pdf?fileId=8ac78c8c7d0d8da4017d0ee7ce9d70ad"
# --- ST last (Akamai): may fail under curl even with headers ---
get STM32N657  stm32n657x0_DS14791.pdf   "https://www.st.com/resource/en/datasheet/stm32n657x0.pdf"
get VL53L8CH   vl53l8ch_DS14310.pdf      "https://www.st.com/resource/en/datasheet/vl53l8ch.pdf"
get VD66GY     vd66gy_DS13838.pdf        "https://www.st.com/resource/en/datasheet/vd66gy.pdf"
echo
echo "If the 3 ST files FAILED: open these in your browser (they download instantly there),"
echo "then move each into registry_assets/<PART>/datasheet/ :"
echo "  https://www.st.com/resource/en/datasheet/stm32n657x0.pdf   -> STM32N657/datasheet/"
echo "  https://www.st.com/resource/en/datasheet/vl53l8ch.pdf      -> VL53L8CH/datasheet/"
echo "  https://www.st.com/resource/en/datasheet/vd66gy.pdf        -> VD66GY/datasheet/"
