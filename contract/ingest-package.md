# Ingest package spec — what a sensor change ships to interrogator (owner Q 2026-07-11)

The USR record is the SPINE; it POINTS to facet YAMLs (ADR-0013 references, never copies). A sensor
change therefore touches the whole semantic stack — otherwise the agent can stream a new sensor but
can't UNDERSTAND it. "Add a sensor → the agent knows more" is literally the sensor_semantics.yaml entry.

## Every downstream artifact a sensor change touches
| interrogator artifact | what it holds | AI role | drafter |
|---|---|---|---|
| `shared/schemas/sensors/<X>.yaml` (USR record) | identity, electrical, mechanical, asset pins, facet refs | the spine | **HW (E0)** |
| `shared/schemas/sensor_specs.yaml` | datasheet bounds (range/accuracy/rate) | valid-range / saturation awareness + conformance | **HW (E0)** — from H1 extraction |
| `shared/schemas/sensor_semantics.yaml` | per-channel quantity/unit/description, **bands**, claim_class, provenance | **core AI meaning** | **HW drafts channel structure/units (E0); SME authors meaning+bands (E1/E2)** |
| `shared/schemas/sensor_safety_limits.yaml` | exposure/safety limits | safety gating | SME+legal |
| `shared/schemas/sensor_calibration.yaml` | cal coeffs / raw↔cal | correct values | SME (factory) |
| `shared/schemas/sensor_baseline_seeds.yaml` | ambient baselines | anomaly/drift refs | SME |
| `shared/schemas/intent_catalog.yaml` + capability-coverage | intents a sensor unlocks | what the device can be ASKED | SME (HW notes new capability) |
| `shared/schemas/fusion_insights.yaml` + `derived_channels.yaml` | cross-sensor fusions | richer joint context | SME |
| `backend/commands/contract.py` | SET_*_RATE + domain on/off | command surface | HW specifies bounds, upstream lands |
| record schema (ADR-0001) | **state flags** (charging/docked/haptic_active/uv_active) | confidence weighting | HW specifies, upstream lands |
| device profile (#123) | per-instance bus/addr + **interference matrix ref** | reflex + active-sensing | HW authors, upstream loads |

**Rule: HW drafts the datasheet-derived / physical facets (E0); interrogator SME authors the MEANING
(bands, claim_class, fusion, intents) with KB provenance (E1/E2). Single-writer preserved — we deliver
PR-ready drafts, owner lands upstream.**

## v1 sensor deltas → semantic-stack work triggered
ADD (need full stack incl. new semantics/specs/intents): MLX90642, VL53L8CH, TCS3448, AS7058,
MMC5983MA, MIA_M10Q, IQS7222A, ADS131M04, BNO086.
DEPRECATE (mark successor, retire semantics/specs): AMG8833→MLX90642, AS7343→TCS3448, MPR121→IQS7222A,
NEO_M9N→MIA_M10Q, ADS1115→ADS131M04, VL53L8CX→VL53L8CH, BNO085→BNO086, drop AS7263.
NEW capability → new intents/fusions the SME should author:
- MMC5983MA nT: heading, ferrous-anomaly, current-loop mapping (navigation + "map reality" intents)
- AS7058 ECG/BioZ: cardiac observables beyond PPG (wellness intents)
- TCS3448 vs AS7343: richer 380–1000nm bands (material/food/health spectral intents)
- MLX90642 32×24 vs 8×8: higher-res thermal → thermal⊕ToF super-res fusion (derived_channels)
- MIA_M10Q RAWX: raw pseudorange/carrier-phase (precision-location intents)
- VL53L8CH histograms: raw per-zone bins → richer depth fusion

The HW ingest package for each of the 9 ADDs carries the E0 draft (USR + specs bounds + channel
structure/units from the H1 datasheet extraction); the SME authors the meaning. This is the
"sensor MCP" loop: HW defines the physical capability, the semantic layer turns raw → understanding.

## Flags & verbs → upstream placeholders (verified vs interrogator repo, 2026-07-11)
Placeholders CONFIRMED upstream: PLAN §5.3 "Cross-Signal Interference Matrix" (our matrix v1 is its
successor for the new board); record_schema.md field-8 `activeFlags` bitfield (0x01 motors · 0x02 wifi ·
0x04 LEDs · 0x08 valve — "Class A data-quality flags", fusion weights confidence);
sensor_semantics.yaml top-level `flags:` section + actuator-state channels (NIR-LED pattern:
"when on, reading is active-illumination, not environmental").

Routing corrections (supersedes the looser wording above):
1. **Bit assignments** extending the existing bitfield (no collisions; 0x08 valve stays reserved for
   v2 fluidics): `0x10 charging · 0x20 docked · 0x40 haptic_active · 0x80 uv_active`.
2. **Flags feed sensor_semantics.yaml too** — each new flag gets a semantics entry (what it MEANS,
   e.g. docked = mounted/placed-monitor/magnetometers gated), and each victim channel gets a confound
   description in the existing NIR-LED style (e.g. "AS7058 ECG during `charging`: switching-noise risk,
   weight down"). This is how the AI interprets flagged data, not just filters it.
3. **Verbs do NOT enter semantics** — tdm/mutex/stagger/gate are scheduler policy only (firmware
   reflex + edge policy via device-profile ref, §8 of interface-requirements.md).
4. **Upstream reconcile ask**: PLAN §7 lists `uncalibrated|error` flags that record_schema.md's 4-bit
   field doesn't define — upstream should reconcile schema↔PLAN before extending the bitfield.

## v1.1 sensor deltas (ADR-0002, 2026-07-11) — ingest-package additions
ADD USR records + specs + semantics (HW drafts E0 facts; SME authors meaning):
MLX90632, AS7421, MEMS_MIC, ENS161, SCD41, SGX_4CO, SHT41, PIN_RAD (radiation, replaces BG51).
DEPRECATE: BG51 → PIN_RAD. New intents unlocked for SME authoring: spot-temp/fever (MLX90632),
hydration/tissue-NIR (AS7421), phonocardiography/acoustic (MEMS_MIC), scent-granularity (ENS161),
true-CO2 occupancy/ventilation (SCD41), CO safety/breath (SGX_4CO). New accessory-port channel class:
attachments register via ID EEPROM (ECG/BioZ/probe/rad-wand) — device-profile addition.
