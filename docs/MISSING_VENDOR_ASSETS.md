# Missing vendor assets — exact URLs for manual download

The cloud sandbox egress proxy allows only GitHub, so these official vendor files could not be fetched. Each URL below was located and verified to exist; download and drop into `registry_assets/<PART>/{schematics,3d}/`.


## A121
- **schematic_vendor_evalkit**: https://developer.acconeer.com/
  - XE121/XM125 official eval schematic: developer.acconeer.com and acconeer.com host blocked by session egress proxy (CONNECT 403); per rules no mirrors/workarounds used
- **3d_step**: (no public URL — requires vendor login: SnapEDA/UltraLibrarian/vendor portal)
  - No A121/XM125 STEP via allowed hosts; acconeer.com blocked

## ADS1115
- **step**: https://www.ti.com/product/ADS1115
  - NOT OBTAINED. www.ti.com is blocked by the network proxy (CONNECT 403); TI CAD/3D models (X2QFN RUG / VSSOP-10 DGS packages) are otherwise delivered via UltraLibrarian, which requires login.

## AMG8833
- **3d_step**: https://industrial.panasonic.com/ww/products/pt/grid-eye/models/AMG8833/cad
  - Official Panasonic AMG88 series 3D CAD (STEP) NOT retrieved: industrial.panasonic.com (and na.industrial.panasonic.com) blocked by network egress proxy (CONNECT 403). Panasonic Grid-EYE evaluation-kit docs on the same domain also unreachable.

## AS7263
- **datasheet_app_circuit**: https://ams-osram.com/products/sensor-solutions/ambient-light-color-spectral-proximity-sensors/ams-as7263-nir-spectral-sensor
  - AS7263 datasheet: ams-osram.com host blocked by session egress proxy (CONNECT 403); per rules no mirrors/workarounds used; no copy present in SparkFun AS726X repo
- **3d_step**: (no public URL — requires vendor login: SnapEDA/UltraLibrarian/vendor portal)
  - No public AS7263 STEP via allowed hosts; vendor site blocked, SnapEDA requires login

## AS7331
- **3d_step**: (no public URL — requires vendor login: SnapEDA/UltraLibrarian/vendor portal)
  - No AS7331 STEP in any allowed public source; ams-osram.com host blocked by session egress proxy (CONNECT 403); per rules no mirrors/workarounds used; SnapEDA/UltraLibrarian require login

## AS7343
- **schematic_vendor_evalkit**: https://look.ams-osram.com/m/41cfc630bb4e80ba/original/AS7343_UG001009_2-00.pdf
  - AS7343 EVK user guide UG001009: look.ams-osram.com host blocked by session egress proxy (CONNECT 403); per rules no mirrors/workarounds used

## BG51
- **schematic**: https://www.teviso.com/en/publications (application notes); datasheet: https://www.teviso.com/documents/bg51-data-specification.pdf
  - Teviso BG51 application note / application circuit PDF NOT retrieved: www.teviso.com blocked by network egress proxy (CONNECT 403). No SparkFun/Adafruit open-hardware fallback exists for BG51 (MikroE 'Radiation Click' schematic is hosted on mikroe.com/teviso.com, both outside allowed egress, and MikroE is not an approved fallback source).
- **3d_step**: https://www.teviso.com/documents/bg51-data-specification.pdf (mechanical drawing section)
  - BG51 mechanical drawing / 3D file NOT retrieved: teviso.com blocked by egress proxy (CONNECT 403). Teviso publishes no STEP model publicly; mechanical outline is only inside the (unreachable) datasheet.

## BME688
- **schematic**: https://www.bosch-sensortec.com/media/boschsensortec/downloads/shuttle_board_flyer/application_board_3_1/bst-bme688-sf000.pdf
  - Vendor reference schematic (BME688 Shuttle Board 3.0 flyer) NOT retrieved: www.bosch-sensortec.com is blocked by the network egress proxy (CONNECT tunnel 403, policy denial). Per rules, no mirrors/workarounds used (Mouser/DigiKey mirrors also blocked and are mirrors anyway).
- **3d_step**: https://www.bosch-sensortec.com/en/products/downloads (CAD/3D section)
  - Official Bosch Sensortec BME688 3D STEP NOT retrieved: www.bosch-sensortec.com blocked by egress proxy (CONNECT 403). Third-party libraries (SnapEDA/SnapMagic, Ultra Librarian, DigiKey models) require login/registration and are not vendor sources, so skipped per rules.

## BMV080
- **schematic**: https://www.bosch-sensortec.com/media/boschsensortec/downloads/shuttle_board_flyer/shuttle_bard_fleyer_3_1/bst-bmv080-sf000.pdf
  - Vendor BMV080 Shuttle Board 3.1 flyer / design-integration guideline NOT retrieved: www.bosch-sensortec.com blocked by network egress proxy (CONNECT 403). Datasheet + STEP already on hand per task, so no 3d entry needed for BMV080.

## BNO085
- **3d_step**: (no public URL — requires vendor login: SnapEDA/UltraLibrarian/vendor portal)
  - CEVA publishes no STEP; SnapEDA links require login (skipped per rules)

## MAX30102
- **schematic_evalkit**: https://www.analog.com/media/en/technical-documentation/data-sheets/max30102accevkit.pdf
  - MAX30102ACCEVKIT EV kit data sheet with schematic: www.analog.com host blocked by session egress proxy (CONNECT 403); per rules no mirrors/workarounds used
- **datasheet**: https://www.analog.com/media/en/technical-documentation/data-sheets/max30102.pdf
  - MAX30102 datasheet: www.analog.com host blocked by session egress proxy (CONNECT 403); per rules no mirrors/workarounds used; no sanctioned open-hardware fallback repo exists for MAX30102 (SparkFun boards use MAX30101/MAX30105)
- **3d_step**: (no public URL — requires vendor login: SnapEDA/UltraLibrarian/vendor portal)
  - OLGA-14 STEP: analog.com blocked; SnapEDA login required

## MPR121
- **step**: https://www.nxp.com/products/no-longer-manufactured/nxp-sensor-toolbox-mpr121-evaluation-kit:KITMPR121EVM
  - NOT OBTAINED. www.nxp.com is blocked by the network proxy (CONNECT 403). MPR121 is an NXP legacy (formerly Freescale) part in QFN-20; no downloadable NXP STEP model could be retrieved.

## NEO-M9N
- **integration_manual**: https://content.u-blox.com/sites/default/files/NEO-M9N_Integrationmanual_UBX-19014286.pdf
  - KEY DOCUMENT NEO-M9N Integration manual UBX-19014286 (reference design): content.u-blox.com host blocked by session egress proxy (CONNECT 403); per rules no mirrors/workarounds used; SparkFun CDN copy also on blocked cdn.sparkfun.com
- **integration_manual_alt**: https://content.u-blox.com/sites/default/files/documents/MIA-M10Q_IntegrationManual_UBX-21028173.pdf
  - MIA-M10Q Integration manual: content.u-blox.com host blocked by session egress proxy (CONNECT 403); per rules no mirrors/workarounds used
- **3d_step**: (no public URL — requires vendor login: SnapEDA/UltraLibrarian/vendor portal)
  - u-blox NEO form-factor STEP hosted on u-blox.com/content.u-blox.com, host blocked by session egress proxy (CONNECT 403); per rules no mirrors/workarounds used

## SGP41
- **schematic**: https://sensirion.com/media/documents/FBD0A26B/61EA8BFA/Sensirion_Gas_Sensors_SEK-SVM4x_Technical_Description.pdf
  - Vendor eval-kit documentation (SEK-SVM4x technical description; also SGP41 datasheet with application circuit at https://sensirion.com/media/documents/5FE8673C/61E96F50/Sensirion_Gas_Sensors_Datasheet_SGP41.pdf) NOT retrieved: sensirion.com blocked by network egress proxy (CONNECT 403).
- **3d_step**: https://sensirion.com/products/downloads (SGP41 3D CAD STEP)
  - Official Sensirion SGP41 STEP NOT retrieved: sensirion.com (download center hosting the 3D CAD ZIP) blocked by egress proxy (CONNECT 403). SnapEDA/Ultra Librarian alternatives require login and are not vendor sources; skipped.

## TMAG5273
- **step**: https://www.ti.com/product/TMAG5273
  - NOT OBTAINED. www.ti.com/download.ti.com are blocked by the network proxy (CONNECT 403), so no TI-hosted STEP for the SOT-23-6 (DBV0006A) package could be downloaded. TI also routes CAD/3D model downloads through UltraLibrarian, which requires login.

## VL53L8CX
- **schematic**: https://www.st.com/resource/en/schematic_pack/satel-vl53l8-schematic.pdf
  - NOT OBTAINED. ST publishes the SATEL-VL53L8 breakout schematic PDF at this URL, but www.st.com is blocked by the network proxy (CONNECT 403 policy denial), so it could not be downloaded. No SparkFun/Adafruit VL53L8CX board exists as an allowed fallback (only Pololu #3419 carries VL53L8CX, which is outside the allowed fallback sources).
- **step**: https://www.st.com/en/imaging-and-photonics-solutions/vl53l8cx.html
  - NOT OBTAINED. st.com is blocked by the network proxy (CONNECT 403). Additionally, ST's product page delivers EDA symbols/footprints/3D models only via third parties (UltraLibrarian/SamacSys), which require registration/login.