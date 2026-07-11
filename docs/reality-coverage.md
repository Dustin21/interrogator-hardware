# Reality Coverage Map — full sensor rundown, FDA capacity, gaps (v1 + proposed)

**2026-07-11.** Maps the sensor set to the physical phenomena a user can interrogate, the diagnostic/regulatory ceiling of each, and what is missing or not yet possible. Aligns to the spec (solid-state, 3+ yr, raw-parallel-streaming, modular, ambient-first, exposure classes, regulated-where-possible).

**FDA/regulatory legend** — *no chip is ever "FDA-cleared"; clearance is a system property (hardware + algorithm + clinical study + labeling). This column = whether the part can SUPPORT a clearance path.*
- ✅ **Clearance-capable** — part can meet the relevant standard at system level; ship as wellness first, clear later.
- 〜 **Wellness / adjunctive** — supports wellness claims + adjunctive/"indication" clearances (not standalone diagnosis).
- 🌍 **Environmental/safety-regulated** — governed by EPA/OSHA/IEC, not FDA; accuracy-graded, not "diagnostic".
- 🔧 **Utility** — non-regulated sensing (navigation, distance, vision, fields).
- 🧩 **Extension/reserved** — capability reached via the accessory port or a reserved bay, not the core pebble.
- ❌ **Not possible now** — physics or regulation blocks it in a pocket device today.

## A. Core sensor set (solid-state, inside the pebble)

| # | Sensor | Physical domain | Captures (raw) | Exposure | Reality intents it serves | FDA/reg capacity |
|---|---|---|---|---|---|---|
| 1 | **VL53L8CH** | Optical / ToF | 8×8 depth + per-zone photon histograms | window | distance, presence, gesture, room mapping, material hints | 🔧 |
| 2 | **MLX90642** | Optical / LWIR | 32×24 thermal image | window | heat maps, hot-spots, insulation, fever *screening* | 〜 (adjunctive w/ ref) |
| 3 | **MLX90632** *(add)* | Optical / LWIR | single-point radiometric temp ±0.2–0.3 °C | window | accurate spot temperature, elevated-temp indication | 〜 |
| 4 | **TCS3448** | Optical / VIS spectral | 14-ch 380–1000 nm counts | window+LED | color, material ID, food, bilirubin/melanin index | 〜 (bilirubin/melanin precedent) |
| 5 | **AS7331** | Optical / UV | UVA/UVB/UVC irradiance (24-bit) | UV aperture | UV index, sterilization check, forensic, counterfeit | 🌍 |
| 6 | **AS7421** *(add)* | Optical / NIR spectral | 64-ch 750–1050 nm | window+LED | hydration (970 nm), tissue, moisture, material chemistry | 〜 |
| 7 | **MAX30102** | Optical / PPG | red+IR PPG (18-bit FIFO) | contact | HR, SpO2 (wellness turnkey) | 〜 → ✅ at system level |
| 8 | **AS7058** | Optical+electrical / vitals AFE | PPG + **ECG + BioZ + EDA** (20-bit) | contact + electrodes | HR/HRV, ECG rhythm, body-composition, hydration, stress | ✅ (ECG to IEC 60601-2-47; needs electrodes 🧩) |
| 9 | **VD66GY** *(DNP option)* | Optical / imaging | global-shutter raw Bayer | window | vision grounding, OCR, visual context | 🔧 |
| 10 | **BME688** | Chemical / MOX + env | gas resistance (heater-swept) + T/RH/P | air | air quality, VOC fingerprint, scent, environment | 🌍 |
| 11 | **SGP41** | Chemical / MOX | raw VOC + **NOx** ticks | air | air quality, NOx, complements BME688 | 🌍 |
| 12 | **ENS161** *(add)* | Chemical / MOX array | 4-element raw resistances | air | scent/breath granularity, perfume/material discrimination | 🌍 |
| 13 | **SCD41** *(add)* | Chemical / photoacoustic NDIR | true CO2 (abs.) | air | CO2 (occupancy, ventilation, agriculture, safety) | 🌍 (capnography ❌ — too slow) |
| 14 | **SGX-4CO** *(add)* | Chemical / electrochemical | raw CO current | air | CO safety, breath-CO (smoking/oxidative stress) | 〜 (breath-CO precedent) |
| 15 | **SHT41** *(add)* | Environmental | reference T/RH (unheated) | air | accurate humidity/temp; anchors all MOX comp | 🌍 |
| 16 | **BMV080** | Particle / laser scattering | PM2.5 mass | air window | particulates, air quality, smoke, dust | 🌍 |
| 17 | **BNO086** | Motion / inertial | 9-DoF raw + fused quaternion | internal | orientation, gesture, tremor, gait, activity | 〜 (tremor/gait precedent) |
| 18 | **TMAG5273** | Field / Hall | 3-axis B-field (mT) | internal | magnets, current, ferrous mass, dock detect | 🔧 |
| 19 | **MMC5983MA** *(add)* | Field / AMR | 3-axis B-field (nT) | internal | heading/compass, ferrous anomaly, EM mapping | 🔧 |
| 20 | **MEMS mic** *(add)* | Acoustic | audio + ultrasonic-adjacent PDM | port | heart/lung sounds, machine acoustics, leaks, environment | 〜 (phonocardiography precedent) |
| 21 | **A121** | EM / 60 GHz radar | complex Sparse-IQ | radome | micro-motion, respiration, presence, through-material, range | 〜 (contactless-resp precedent) |
| 22 | **ADS131M04 + AD8317** | EM / precision analog | 4×24-bit; RF power (dBm) | internal + probes | piezo/vibration/acoustic, RF-field strength, external analog | 🌍/🔧 |
| 23 | **BG51 → see §D** | Radiation | β/γ dose (TTL pulses) | thin window | radiation dose, safety screening | 🌍 (isotope ID 🧩) |
| 24 | **MIA-M10Q** | Location / GNSS | position + **raw pseudorange/carrier** | sky window | location, time, geo-tagging, precision positioning | 🔧 |
| 25 | **IQS7222A** | Interaction / cap-touch | 12-ch raw counts | shell electrodes | touch, swipe, squeeze, grip, hover, contact-quality | 🔧 |

## B. Reality-domain coverage — what a user can ask about

| Phenomenon | Covered? | By |
|---|---|---|
| Light / color / spectrum (VIS) | ✅ | TCS3448, camera |
| UV | ✅ | AS7331 |
| Near-IR / tissue / moisture | ✅ | AS7421 |
| Thermal / heat | ✅ | MLX90642 + MLX90632 |
| Distance / depth / 3D | ✅ | VL53L8CH, A121 radar, (camera) |
| Motion / orientation / vibration | ✅ | BNO086, ADS131M04(piezo) |
| Sound / acoustics / ultrasound-adjacent | ✅ | MEMS mic |
| Air gases / VOC / chemistry | ✅✅ | BME688, SGP41, ENS161, SCD41, SGX-CO |
| Particulates / PM | ✅ | BMV080 |
| Humidity / pressure / temp (env) | ✅ | BME688, SHT41 |
| Magnetic / EM fields | ✅ | TMAG5273 (mT), MMC5983MA (nT) |
| RF field strength | ✅ | AD8317 → ADS131M04 |
| Radar / micro-motion / through-wall | ✅ | A121 |
| Radiation (dose) | ✅ | BG51 / PIN |
| Radiation (isotope ID / energy) | 🧩 | SiPM+scintillator (Pro bay) |
| Location / time | ✅ | MIA-M10Q |
| Cardiac electrical (ECG) | ✅🧩 | AS7058 + electrodes |
| Blood oxygen / pulse | ✅ | MAX30102 / AS7058 |
| Body composition / hydration (BioZ) | ✅🧩 | AS7058 + electrodes |
| Breath biomarkers (CO) | ✅ | SGX-4CO |
| Breath biomarkers (NO/FeNO, acetone) | ❌ | needs purpose-built subsystem |
| AC E-field / mains EMF | ⚠ gap | (see §E — candidate add) |
| Sound-source direction / array | ⚠ partial | single mic (array = future) |
| True molecular speciation (GC/MS) | ❌ | benchtop only |
| Blood glucose (non-invasive) | ❌ | physics + regulation |

## C. FDA-clearance-capable channels (ship wellness first, clear later)
- **SpO2 / HR** (MAX30102, AS7058) — ISO 80601-2-61; needs hypoxia study + ARMS ≤3–3.5% + skin-tone diversity.
- **ECG** (AS7058 + electrodes) — IEC 60601-2-47; single-lead AFib/HRV (Apple/Kardia precedent).
- **Spot body temperature** (MLX90632) — elevated-temperature indication (adjunctive).
- **Fever screening** (MLX90642 array) — adjunctive 510(k) *with* reference source + workflow.
- **Phonocardiography** (MEMS mic) — murmur/low-EF screening w/ AI (Eko precedent).
- **Tremor / gait** (BNO086) — movement-disorder quantification (PKG/Kinesia precedent).
- **Breath CO** (SGX-4CO) — smoking/oxidative-stress (Bedfont precedent).
- **Cuffless BP** (PPG PTT, AS7058+MAX30102) — spot BP; moat is algorithm+study (Aktiia precedent), sensor is capable.
- **Bilirubin / melanin index** (TCS3448) — transcutaneous approximation (JM-105 precedent).
All others are environmental/safety-graded or utility. **The hardware ceiling is high; the gating work is clinical validation + labeling, not the parts.**

## D. Radiation — BG51 procurement + the differentiation upgrade
BG51 is ~$50, quote-only (Teviso direct), TTL-pulse-out, dose-only (no energy/type). Three paths:
1. **Bare PIN photodiode + our own charge-amp on the ADS131M04 analog domain** — cheapest silicon, **freely procurable** (e.g. First Sensor/Osram large-area PIN), and it *reuses the precision-analog front-end we already have*. Trade: needs a light-tight cavity + low-noise charge amp; slightly less turnkey than BG51's TTL. **Recommended for v1 dose** — better procurement, lower cost, and it is the same front-end that scales to spectroscopy.
2. **Keep BG51** — turnkey TTL, 25 µA, but pricey + quote-only supply risk.
3. **SiPM (onsemi MicroFC C-series) + GAGG/CsI scintillator + MCA readout** — true **isotope ID / energy discrimination** (~5–8% @662 keV). This is the "distance/granularity/differentiation" answer for radiation, but the crystal (~1 cm³) + ~30 V bias + shaper grows the device toward Radiacode thickness. **Reserve as a Pro/field-safety bay or accessory wand (🧩), not core v1.**
Recommendation: **v1 = bare-PIN dose on the precision-analog domain** (procurable, cheap, foundation for spectroscopy); **Pro/extension = SiPM+scintillator** for isotope ID.

## E. What's MISSING (handheld-viable — candidate adds via gap register)
- **AC E-field / mains EMF** (GAP-01 upstream) — TMAG is DC/Hall; a dedicated E-field front end adds "is this wire live / EMF hotspot". Small, cheap. **Recommend add.**
- **NH3 / H2S electrochemical** — kidney/halitosis breath channels; small cells; add if breath-biomarker breadth is a priority.
- **Sound-source array** (2nd/3rd MEMS mic) — direction-of-arrival, beamforming; future.
- **Methane NDIR** — gut biomarker + safety; PID-blind gas.

## F. What's NOT POSSIBLE now in a pocket device
- **Non-invasive blood glucose** — no cleared device; FDA safety warning (2024). **Avoid entirely.**
- **True breath speciation (acetone/isoprene ppb, FeNO sub-25 ppb)** — needs micro-GC / QCL photoacoustic / NIOX-class flow subsystem; benchtop or dedicated sub-project.
- **Clinical gamma spectroscopy at ±<3% resolution** — CZT (~$16k) or HPGe (cryogenic); pocket SiPM gets ~5–8% (isotope ID yes, quantitative spectroscopy no).
- **Ultrasound imaging** — CMUT-on-chip exists only as a $3.9k standalone probe, not an embeddable component.
- **Clinical wound morphometry / contactless respiration rate to spec** — needs a depth camera or dedicated radar processing, beyond the 8×8 ToF.
- **SWIR tissue chemistry (>1050 nm: water/lipid/protein/glucose bands)** — InGaAs, ~25 mm, ~$3k, ~1 W. Real tissue chemistry lives here but won't fit a pocket build.

## G. Extension architecture — one convenient outlet for attachments (ECG, probes, wands)
Some capabilities need physical contact/attachments (ECG electrodes, BioZ pads, external probes, radiation wand, future fluidic cartridge). To keep the pebble sleek, expose **one accessory interface** rather than scattering connectors:

**Recommended: magnetic pogo accessory interface on the back (reuses the ferrous-target/dock ring, ADR-0001).** Pins carry: VBAT-switched power, I²C (attachment ID EEPROM → plug-and-play auto-config, the sensor-MCP idea made physical), and 2 analog lines routed to AS7058 (ECG/BioZ) or ADS131M04 (probes). Magnetic, sealed, no open port → preserves the monolithic shell; snaps to an ECG chest-strap, electrode cable, probe, or the radiation wand.

**Wired option: USB-C accessory mode** on the existing port. USB-C exposes SBU1/SBU2 (analog sideband) + CC (ID) + VBUS; role-detected so the port is charge OR data OR accessory. Caveat: **patient-isolation** — ECG electrodes on skin while USB-C could reach a mains charger is a safety issue, so accessory mode disables charging (or requires an isolated attachment). This is why the **magnetic pogo interface is preferred for body-contact medical attachments** (galvanically simpler to isolate), with USB-C accessory mode as the wired/industrial fallback.

Both make attachments first-class registry consumers: the attachment's ID → loads its USR record + semantics → the agent gains the new channel exactly like an internal sensor. This *is* the modularity requirement extended into the physical/accessory dimension.

## H. Spec compliance check
- Solid-state, 3+ yr: ✅ all core sensors solid-state; fan/pump are the only wear parts (serviceable path). Electrochemical CO cell has a finite life (~2–5 yr typ) — flag for the reliability rollup.
- 8 h+ ambient: ✅ additions are duty-cycled/gated; SCD41 (~15 mA) and electrochemical bias are gated, not always-on.
- Small + modular: ✅ core adds are ≤3.5 mm parts; SCD41 (10 mm) and mic fit the air/acoustic zones; extension port offloads bulky/contact items.
- Raw parallel streaming, ambient-first: ✅ every part is raw-capable; activation classes gate what runs.
- Exposure classes: ✅ ambient/contact/air/fluid(reserved)/attachment all represented.
- Orthogonal physics: ✅ optical, thermal, chemical(3 transductions), particle, acoustic, inertial, magnetic, RF, radar, radiation, GNSS, bio-electrical — 12+ distinct physics.
- Regulated-where-possible: ✅ medical channels chosen for clearance-capability; non-medical clearly scoped.
