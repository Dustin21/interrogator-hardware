# ADR-0001 (hardware) — Mounting: ferrous target + external magnets, not an onboard magnet

**Status:** Proposed (2026-07-11, owner-initiated).

## Context
In-pocket ambient sensing is weak for air/particulate/spore channels: no airflow across
the intake, enclosed dead volume, and body heat corrupting gas/thermal. Owner wants a
convenient "stick it somewhere / use out of pocket" mode, floated a magnet, and correctly
flagged magnet↔sensor interference.

## Decision
**No permanent magnet in the device.** A permanent magnet would saturate the ±0.8 mT
MMC5983MA (killing the nT heading/ferrous-mapping capability) and swamp the TMAG5273 —
losing two sensors to gain a mount. Sitting on ferrous surfaces (fridge) worsens it.

Instead — **MagSafe pattern, inverted**:
1. Device carries a thin **ferromagnetic steel target** (passive disc/ring in the back
   shell, no field of its own). Placed diagonally opposite the magnetometer "quiet" zone;
   its fixed **soft-iron** distortion is removed by standard one-time factory hard/soft-iron
   calibration (target is stationary relative to the board).
2. **Magnets live in accessories**: wall puck (adhesive/screw), vent clip, desk dock.
3. **Dock detection via TMAG5273**: the accessory magnet's signature = "docked" →
   firmware auto-switches to **placed-monitor mode** and gates/flags the magnetometer
   channels (no magnetic mapping while parked, by design).
4. **Non-magnetic mounts for magnetically-sensitive work**: spring clip, lanyard hole,
   ¼-20 tripod thread — nothing ferrous/magnetic near the device when doing precision mag.
5. **Optional dock charging** (pogo pads on the target ring) → indefinite always-on room
   monitoring with the fan running continuously (no longer battery-bound). Pogo pads sealed
   against the air path.

## Placed-monitor mode (the payoff)
Mounted on vent / wall / range hood / dash / bag strap: continuous fan, free airflow,
no body-heat contamination, glow visible across a room — the device's best environmental
posture. This is the answer to weak in-pocket air sensing.

## Consequences
- (+) Zero active field from device; magnetometers stay valid in-hand; dock magnet becomes
  a useful "docked" signal.
- (+) One platform, many mounts (magnetic + mechanical) → fits B2C convenience and B2B
  fixed-install without a new device.
- (−) Steel target adds ~0.3–0.5 mm + mass and a factory soft-iron cal step.
- (−) Charging dock needs pogo contacts sealed vs the air path; mount magnet strength vs
  drop-retention is an H5 tuning item.
- Flags for H2/H5: target placement keepout vs MMC5983MA (model residual field), pogo
  charging path, IP rating with mesh membrane + pogo pads.
