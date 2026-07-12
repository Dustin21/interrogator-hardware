# ADR-0002 (hardware) — v1.1 ratified adds, BG51→PIN swap, magnetic accessory port

**Status:** Accepted (owner ratification 2026-07-11).

## Decisions
1. **7 medical/coverage sensors added** (~$40 @1k, all raw-capable, gated/duty-cycled):
   MLX90632 (spot medical FIR), AS7421 (64-ch NIR / hydration), MEMS mic (heart-lung + acoustic),
   ENS161 (4-element MOX array), SCD41 (photoacoustic true CO2), SGX-4CO (electrochemical CO),
   SHT41 (reference T/RH). Keeps the diagnostic ceiling open (see reality-coverage.md).
2. **BG51 → bare large-area PIN photodiode** on the ADS131M04 precision-analog domain: cheaper,
   freely procurable, light-tight cavity, and the *same charge-amp front-end that scales to a
   SiPM+scintillator isotope-ID module* (Pro/accessory path). Dose sensing retained in v1.
3. **Magnetic pogo accessory port** (back, concentric with the dock/ferrous-target ring): power +
   I2C plug-and-play ID + 2 analog lines → AS7058 (ECG/BioZ) or ADS131M04 (probes). Attachments
   (ECG cable, BioZ pads, external probe, radiation wand, future fluidic cartridge) register as
   sensor-MCP modules via their ID EEPROM. USB-C accessory mode = wired fallback; magnetic preferred
   for body-contact medical (patient isolation).

## Consequences
- Board grew **54×40 → 60×46 mm** (§5.8 XY lever; the SGX-CO 14×14 cell + SCD41 10×10 drove it);
  chassis **62×47×17 → 66×50×18 mm** (still pocket / AirPods-Pro-case class). Ambient runtime
  ~56 h (>8 h target holds). Stack 12.1 mm.
- **Flags:** SGX-CO electrochemical cell finite life (~2–5 yr) — the one non-solid-state exception,
  on a serviceable/replaceable path (R2). SGX-CO + SCD41 sizes verified at H2; PIN part + charge-amp
  design at H2. Electrochemical + NDIR gas parts hard-gated in ambient (power).
- Floorplan/chassis regenerate from boards/v1/design_v1.py (zone-packer) + enclosure/chassis_v0.py —
  the R6/R12 respin promise demonstrated: 7 sensors added, placement + collision-freedom automatic.
