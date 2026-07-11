# Sensor cross-contamination & interference analysis (v1 set, 2026-07-11)

18 modalities on one pebble: each is source AND victim. Nine channels, mitigations at three
layers — MECH (zoning/baffle/material/mesh), FW (scheduler: TDM/mutex/gate/flags), CAL.
Machine-readable pairs in interference-matrix.yaml (scheduler input, MEASURED at H4).

| # | Channel | Sources | Victims | Mitigation |
|---|---|---|---|---|
| 1 | Optical crosstalk | ToF 940nm VCSEL, PPG red/IR, UV/white/NIR LEDs, camera | TCS3448, AS7331, PPG PDs, camera | FW time-division (no emitter-on during victim integrate); MECH baffles/light-pipe walls in aperture plate; separate apertures |
| 2 | Thermal drift ("Zero Drift") | BMV080 (~15K self-heat), MCU, WiFi PA, charger, LEDs | BME688, SGP41, MLX90642 | MECH zoning (gas at cool intake, upstream of hot; imager isolated) + moat slots; FW duty-cycle hot parts; CAL on-die temp comp |
| 3 | Chemical poisoning | silicone/siloxane adhesives, flux residue, enclosure outgassing | BME688, SGP41 (MOX) | MECH low-outgassing material whitelist + silicone-exclusion keepout + conformal-coat exclusion; PROCESS bake-out/burn-in, flux clean |
| 4 | Magnetic | LED/charger/fan current loops, ferrous target, MMC set/reset | MMC5983MA (nT), TMAG5273 | MECH quiet-zone placement far from current loops; route high-I away; CAL hard/soft-iron; FW TDM MMC-setreset vs TMAG read |
| 5 | GNSS RF desense | buck harmonics, USB-HS 480MHz, MIPI clocks, WiFi TX | MIA-M10Q (~1.5GHz), AD8317 | MECH antenna keepout corner + shield can; integrated SAW+LNA; spread-spectrum bucks; FW gate WiFi during RAWX |
| 6 | Vibration/microphonics | fan/blower, haptic LRA | BNO086 (flag=signal), piezo/ADS131M04, BG51 | MECH isolated fan mount, damped piezo; FW motors_active/haptic flags; mutex haptic vs precision read |
| 7 | Switching noise → analog | BQ25620 charger, bucks | AS7058 ECG/BioZ, ADS131M04, IQS7222A | MECH partitioned analog ground island + filtering; FW gate precision/ECG during fast charge (charging flag) |
| 8 | Light into radiation det. | ambient/emitter light | BG51 PIN | MECH light-tight cavity + opaque, radiation-transparent window/coating |
| 9 | PM vs lint mesh | hydrophobic mesh (added for pocket lint) | BMV080 (needs particles IN) | MECH mesh pore passes PM2.5 (~2.5um) blocks lint (~50um); dedicated PM aperture; CAL characterize derating |

Extra watch items: condensation on optical windows/PM laser after temp swings (MECH vent/hydrophobic
coat); UV LED degrades nearby plastics over life (MECH UV-stable materials); WiFi TX vs A121 (bands far
apart, low risk, flag). BME688⊕SGP41 shared-air "cross-sensitivity" is ORTHOGONALITY (both see same air,
different chemistry) — a feature, not contamination, as long as poisoning (#3) is controlled.

Layer ownership: MECH → H3 layout + H5 chassis; FW → interrogator (interface-requirements.md maps the
scheduler primitives); CAL → factory + on-device; all pairwise couplings MEASURED at H4 (activation tests)
and fed back as rules-as-code.
