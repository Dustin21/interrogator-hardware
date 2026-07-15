# ADR-0003 (hardware) — "Scanner" form factor: ergonomic hand-scanner, not a case

**Status:** Accepted-pending-owner-review of renders (2026-07-12). Supersedes the AirPods-case
shell concept (chassis_v0) as the primary industrial design; chassis_v0 retained as reference.
**PARTIALLY SUPERSEDED (2026-07-15, ADR-0004):** the *board must fit inside this form* premise
(Engineering-consequences §1) is retired — the PCB outline is now a min-area-packing OUTPUT and
the chassis is derived downstream from the real board. The scanner form language below remains
the industrial-design north star.

## Owner direction
Magic-Mouse-inspired but MORE ergonomic: a small device you grasp with a few fingers, sweep to
scan, touch, and use to retrieve liquid samples. No buttons, sleek. Must still pocket, stick
(fridge/knapsack), hang (neck), and sit on a desk. Ambidextrous.

## The form
Bilaterally symmetric teardrop, **~86 × 54 × 24 mm**: low **sensing prow** (front, ~6–9 mm tall)
sweeping into a **rear palm arch** (24 mm crest, rear-biased like a mouse). Orientation is tactile
and visual — the prow *points*; the arch *fills the palm*. Works identically in either hand
(symmetry about the long axis).

## Feature mapping (all prior capabilities carried over)
- **Sensing prow window** (front slope glass band): the optical strip (thermal, ToF, spectral, UV,
  NIR, camera) aims forward-down — you *sweep* it across surfaces; IMU pose-stamping turns the
  sweep into super-resolution (UX §motion). Radar behind the prow radome region.
- **Liquid port at the prow tip**: dip the nose to a droplet — capillary wick to the (v2) fluidic
  module. The tip is the natural "touch it to the sample" affordance.
- **Crown touch dish** (fingertip scoop at the arch crest): PPG/ECG contact read + touch surface;
  rim swipe/squeeze zones on the flanks (IQS7222A electrodes); ECG return on the base shell.
- **Underside**: flat base = desk-sit + dock ring (ferrous target + 6-pogo accessory port,
  ADR-0001/0002) + air intake grid + mic port; USB-C on the rear skirt; glow light-pipe ring
  around the base skirt ("twinkling stars" visible from any angle on a desk).
- **Carry**: pocketable (24 mm max, teardrop drops into a pocket nose-down), magnetic mounts via
  the dock ring, lanyard bore through the rear skirt (H5 detail), desk-native by shape.

## Engineering consequences (honest)
1. **Board reshape at H3**: the rectangular 60×46 v1.1 board fits the mid/rear shell, but the low
   prow only fits a thin **angled optical sub-board or rigid-flex** carrying the sensing strip —
   the "sensing face" rotates from up-facing to forward-facing. The zone-packer gains a polygonal
   (teardrop) outline mode; sensors redistribute: optical→prow flex, air pocket→mid-right,
   compute/power→rear arch volume (tallest), battery under the arch.
2. Fan duct: intake stays underside-front; exhaust through the rear skirt (was side wall).
3. GNSS sky window moves to the arch crest rear (still upward-facing when hand-held or desk-sat).
4. Volume ≈ comparable to chassis_v0 (arch adds height where the case was uniform); weight target
   <90 g. Drop/roll behavior of the dome — H5 test item.
5. Renders are concept-grade (parametric mesh); chassis_scanner.step (CAD loft) + the smooth STL
   (chassis_scanner_smooth.stl) both in enclosure/; surfacing refinement is H5 CAD work.

## Files
enclosure/scanner_form.py (parametric form + renders) · chassis_scanner.py (CAD/STEP) ·
chassis_scanner_smooth.stl · scanner_{iso_front,iso_rear,side,top,front}.png

---
## REVISION B (2026-07-12) — owner chose the Pebble, evolved to the **Pebble-Bean**
Owner rejected the mouse-derived Scanner ("looks like a mouse — wrong verbs") and, from the three
rendered candidates (Compass Puck / River Pebble / Wand, docs/form-options.html), chose the
**Pebble**, directing: more ergonomic, bean-like, palm-fitting, defined thumb area, easy hold,
must sit on a desk.

**The Pebble-Bean (enclosure/pebble_bean.py, pebble_bean.stl, bean_*.png): 72 × 51 × 18 mm**
- Bean plan-form: curved spine; the concave inner edge is where thumb + fingers wrap naturally.
- Domed palm-filling top with an elliptical **thumb scoop** (PPG/ECG contact + touch) biased to
  the inner edge — the thumb finds it blind.
- **Ambidextrous by flip**: the bean curve is handed, but the form is double-faced — flip it over
  and it's the other hand's version. Scoop/glass on both faces (electronics serve whichever face
  is up; orientation known from the IMU).
- **Desk-stable**: flatter underside dome clipped to a landing flat (dock ring, pogo port, air
  intake, mic port live there — same as ADR-0002).
- Glow = parting-line seam around the waist; liquid port at the taper tip (dip gesture);
  sensing band along the outer convex edge + taper end (edge-sweep to scan); USB-C in the fat-end
  skirt; lanyard bore at the fat end.
- Board impact (H3): teardrop/bean outline mode in the zone-packer; edge-facing sensor strip on a
  curved flex or chamfered sub-board along the outer edge; compute/battery in the thick middle.
**Supersedes rev A (Scanner) and the AirPods-case chassis_v0 as the flagship industrial design.**

---
## REVISION C (2026-07-12) — owner-supplied product design image is CANONICAL
Owner provided a 10-view turnaround ("follow this exactly"). Geometry extracted and rebuilt
(enclosure/product_stone.py, product_stone.stl, stone_*.png): **~75 × 47 × 18 mm** standing-stone
lens; subtle bean waist on ONE long edge offset toward the fat end; smooth faces — **no scoop**;
**flowing engraved S-curve strata on both faces are the interface marking** (touch/PPG field lives
under the engraving; the etch channels double as glow light-guides). No visible ports in the design:
air/mic apertures execute as sub-visible micro-perforations in the lower face; USB-C + pogo hidden
in the bottom-edge flat; liquid port concealed at the waist notch. Two rest poses per the sheet:
lying flat (primary, landing flat on back face) and standing on the fat end (display pose — small
edge flat added). Supersedes rev B geometry; rev B ergonomic intent (palm/bean/thumb) is preserved —
the thumb naturally lands on the engraved field over the waist. Board outline (H3): bean-lens
polygon; sensing strip along the convex edge; the design image is the master reference asset.
