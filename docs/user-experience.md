# User experience spec — v1 (owner Q&A 2026-07-11)

Palm pebble 62x47x17mm. No buttons/screen; phone app = dialogue, device = instrument.
Orientation is tactile: thumb dish = anchor; dish-under-thumb => sensor strip points away.

## Modes
1. **Pocket ambient** (~61h): silent monitoring (air/pressure/radiation/motion/mag).
   Anomaly => one firm haptic + one color-coded ring segment + phone detail. Never nags.
2. **Point & interrogate**: aim strip at subject; intent from app or press-hold on dish.
   AI wakes relevant stack (thermal/ToF/spectral+illuminators/radar/camera); ring twinkles
   per active zone; double-tap haptic = done; findings on phone.
3. **Touch read**: thumb in dish 10s (breathing glow = progress): PPG HR/SpO2/HRV + ECG/BioZ.
   Optical emitters gated during contact (interference matrix).
4. **Air**: automatic; intake holes on face over gas/PM pocket, exhaust right wall;
   duty-cycled silent in ambient; continuous 10-60s in "sniff" deep-dive.
5. **Liquid (v2)**: left-wall capillary inlet (v1 ships blind port); droplet wicks to
   microfluidic module; respin + aperture-plate swap, no new product.
6. **Charge/lifecycle**: USB-C bottom, ~1C (~1h); signed A/B OTA overnight.

## Design deltas from this review (feed H2/H5)
- **ECG return electrode on back-shell grip zone** (thumb->fingers circuit) — single-point
  ECG impossible; add conductive grip zone wired to AS7058 + IQS7222A channel.
- **Hydrophobic mesh (IP52-class) behind air hole arrays** in the aperture plate (pocket lint).
- Explicit: contact mode and point mode share a face — arbitration is the interference
  matrix's job (touch trigger gates optical emitters).

## Motion + touch interaction language (owner Q&A, zero new BOM)
BNO086 on-chip classifiers (pickup/tap/shake/stability, uA-class, INT-driven) + IQS7222A 12ch:
- pick-up wake · double-tap shell = quick-scan (glove-proof) · hold-steady 500ms = auto-capture
- flick = dismiss · face-down = DND · rim swipe = cycle/dismiss · squeeze both walls = confirm/interrogate
- grip + pocket detection => glow suppression + UV/laser interlock input · hover proximity => ring fade-in
- dish contact-quality coaching (electrode coverage -> glow nudge -> clean PPG/ECG)
- **motion as sensing multiplier**: pose-stamped frames => ToF/thermal super-resolution stitching by
  hand sweep; radar micro-SAR; spectral surface painting; heading+GNSS point-to-tag (reality map).

### Hardware deltas (H2)
- Route BNO086 INT to BOTH N657 and sentinel (motion wake path from ambient).
- Electrode budget in shell/aperture plate: dish ring (2), rim slider (3), side-squeeze (2x2),
  back ECG-return/grip (1), reserve (2) = 12ch IQS7222A fully allocated.

## Mounting / placed-monitor mode (ADR-0001)
Ferrous steel target in device (passive, no field) + magnets in accessories (puck/vent-clip/
dock). Dock magnet detected by TMAG5273 => auto placed-monitor mode (continuous fan, free
airflow, magnetometer gated). Non-magnetic mounts (clip/lanyard/tripod) for precision-mag
work. Optional pogo dock charging => indefinite always-on room monitoring. Fixes weak
in-pocket air sensing: mount on vent/wall/hood/dash/strap for the device's best air posture.
