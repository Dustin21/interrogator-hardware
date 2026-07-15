# ADR-0004 (hardware) — Board-first: the PCB outline is an OUTPUT of minimum-area packing

**Status:** Accepted (2026-07-15, owner direction). Supersedes the *board-containment*
aspect of ADR-0003 only — the Product Stone / scanner form (ADR-0003) remains the
industrial-design north star, but is **no longer a hard boundary the PCB must fit inside.**

## Owner direction (verbatim intent)
> "Don't fixate on the bean or chassis — focus on what is needed (our sensors and hardware,
> goal = as small as possible). From there the chassis can be better defined, then optimized
> together. First get a PCB actually functional with a proper floorplan; once we have something
> working, optimizing the chassis jointly makes more sense — otherwise the optimization space
> is even harder."

## Decision
The v1 PCB **outline is a derived output**, not an input:
1. Pack the real footprint courtyards to minimum area (FFDH per face, width swept for the
   smallest shared board, aspect ≤ 1.55).
2. Wrap a tight **rounded rectangle** (corner R = 2 mm) around the packed courtyards + a
   passive/route ring (+2.6 mm) that restores bean-class part density and gives the router
   straight channels.
3. Chassis is derived **downstream** from the real board, then co-optimized in a later pass.

Objective ranking: (1) minimum board area, (2) minimum layer count if achievable,
(3) aperture-cluster coherence, (4) short critical-net lengths.

## Why (evidence)
Every H2/H3 placement and routing crisis — courtyard overflow, the 33-part spill, the USB-C
mid-back **enclosure tunnel**, the mechanical-ECO backlog, and the H3.3 routing **stall at
XSPI 9/11 + partial diff pairs** — was caused by forcing the board into the 67.9 × 39.9 mm
bean polygon. The bean has **no straight routing channels** and wastes its curved corners.
Empirically, at the stall the bottom face had ~960 mm² free but no *usable* routing corridors.

## Result (H3.1R)
Derived board: **47.7 × 44.7 mm = 2129 mm²** (≈ 103 % of the 2065 mm² bean by area, but fully
**rectangular** — zero wasted corners, straight route channels on every layer). All 55 placed
rectangles (41 majors + 14 mech) pack collision-free with **zero spills**; ~360 supporting
passives/TPs interleave in the shelf gaps + ring. The win is **routability + no enclosure
tunnels**, not raw area — the part set genuinely needs ~2000 mm²/face, which the bean also
provided but un-routably.

## Physical constraints kept (hard)
- **Edge-access:** USB-C (short edge), pogo dock, SGX gas inlet + can overhang, ECG/contact
  lands, touch flex, SMA/U.FL, battery lead — each tagged to a board edge (`EDGE:` flow to
  build_board for flush-to-edge).
- **RF keep-outs:** BL54L15 trace-antenna, ESP32-C6 module, MIA-M10Q GNSS — at board edges with
  the keep-out extending OFF-board (zero copper in keep-outs).
- **Thermal:** N657 + power bucks kept off the MLX IR/thermopile parts and the BQ27427 NTC.
- **Shield can** over the radiation front-end; **battery** is a mating/stacked part
  (LP503450-class 50×34×5.2 mm via J_BATT) — excluded from board area, stacks in the enclosure.

## Consequences
- The chassis is re-derived from this board at a later pass (ADR-0003 form language preserved,
  its *engineering-consequences §1 board-reshape-to-fit-the-bean* is retired).
- Routing (H3.3R) restarts on the clean rectangle with the preserved A* router machinery.
