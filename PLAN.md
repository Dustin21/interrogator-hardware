# Interrogator Hardware — Build Plan

**Status: v0.1 DRAFT — for owner review. Nothing below is executed until ratified.**
Date: 2026-07-10 · Owner: Dustin21 · Repo: `interrogator-hardware` (this repo) · Tracker: [GitHub Project 3 — Interrogator Device Hardware Build](https://github.com/users/Dustin21/projects/3)

This plan merges (a) the owner's hardware-build brief ("Closed-Loop AI EDA Pipeline for Ultra-Dense Interrogator Device"), (b) a full read-only review of the `interrogator` repo (registry, PLAN.md, build docs, deviation log, ADRs), and (c) a July-2026 state-of-the-art review of AI-EDA tooling. Corrections to the original brief are catalogued in [`docs/draft-review.md`](docs/draft-review.md) — read that alongside this plan.

---

## 0. Mission and scope

Design, fabricate, and bring up the **first custom PCB ("v1 board") plus chassis** for the Reality Interrogator, closing the upstream **PCB Gate (interrogator #7)**, and stand up a **repeatable, contract-driven design pipeline** so that future sensor swaps/additions regenerate a fab-ready board revision in few cycles rather than a redesign.

**In scope here:** PCB architecture, schematic, layout, fab/assembly packages, footprint/3D asset library, enclosure co-design, bring-up plan, the EDA automation pipeline and its CI.
**Out of scope here (lives upstream in `interrogator`):** firmware, the sensor registry and all facet YAMLs, diagnostics/conformance, backend, semantics, regulatory validation content. The hardware repo is *a consumer* of the upstream contract — never a fork of it. Firmware changes needed to accommodate this board (binary IDL, INT-driven acquisition, ESP-IDF or other port) are **upstream work owned by the separate interrogator project**; this repo publishes the interface requirements they build against.

### 0.1 Design stance — commercial hardware, clean sheet, chip-down

This is the **commercial device, designed from scratch to the owner's spec (§1)**. Raw sensor silicon on our own board — no breakouts, no dev-modules-as-components, no breadboard heritage. Modules are used only where that is the *commercially correct* engineering choice (pre-certified radio to keep the intentional-radiator cert path modular; GNSS module class where an antenna-integrated part wins on performance/cert). The plan takes positions (a recommended reference architecture, §5.1) based on independent analysis of the spec; H1 exists to *validate* those positions on eval hardware, not to reopen everything.

**The interrogator repo's role here is narrow:** it supplies the sensor-truth contract (USR facets + AssetPins + device profile) and the data/command semantics the device must ultimately speak — and **interrogator adapts to this design**, not the reverse. Firmware accommodations (new MCU port, binary IDL, INT-driven acquisition) are the upstream project's work against the interface-requirements doc we publish at H1. The PCB Gate (#7) remains the later *integration checkpoint*, not a design constraint.

**Explicitly non-binding:** the three-board split, XIAO/any dev modules, the PCA9548A mux topology, prototype pinmaps, its power tree, and interim size targets. Bench lessons (§2.5) carry over only where they encode physics and protocol reality (I²C lockup modes, thermal cross-talk, address collisions, pull-up budgets) — those hold for any implementation.

## 1. Requirements (from the owner brief, reconciled with repo reality)

| # | Requirement | Reconciliation with repo / research |
|---|---|---|
| R1 | Many orthogonal solid-state sensors (15 now → 100+ over time) | v1 starts from the 16 registered candidate types (§2.2), **re-validated and possibly upgraded at H1 (§5.7)**. Scaling past ~20 concurrent sensors is a bus-architecture problem: parallel buses with per-bus concurrency; I3C enters when the chosen MCU's support is mature (v1 if D1 allows, else v2). |
| R2 | Solid-state, 3+ years without replacement | All sensors solid-state (BMV080 MTTF 10 y). **Exception the brief already implies:** fan, pumps, valve are electromechanical actuators — they are serviceable parts, not sensors. Design them on a replaceable sub-path. |
| R3 | 8 h+ battery in ambient mode | **Tension:** current budget is ~400 mA passive → ~5 h on 2000 mAh (PLAN §10). Closing this needs INT-driven acquisition (already the PCB plan), per-domain power gating, a modern power tree, and/or a larger cell. Tracked as workstream W-PWR with a hard budget table. |
| R4 | As small as feasible; north star = AirPods-case sleekness; **the chassis is defined by the PCB envelope we achieve** | Size is an *output* of the density optimization (§5.8 dynamic boundary method), not a preset. The board floor = component footprints + layout clearance multiplier, grown only when routing demands it (layers first, then 0.5 mm XY steps). Repo figures (120×70×35 mm interim, 80×45×30 mm charter) are reference points only, not targets. If the achieved envelope is phone-attachable, the camera drops (D7). |
| R5 | Battery-powered, pocket-safe (heat) | Thermal zoning rules exist and are binding (PLAN §6.1, §13 "Rule of Zero Drift"); BMV080 self-heats ~15 K; LDO dissipation lesson from bring-up (~0.5 W) → use bucks, not LDOs, for heavy rails. |
| R6 | Modular: sensors added/deprecated without chassis churn | Achieved via (a) the contract-driven regeneration pipeline (§6), (b) a **frozen chassis interface**: board outline + mounting + an *aperture plate* as the swappable part (§5.7), (c) reserved bus/power headroom. Full board-level plug-in modules are explicitly **not** v1 (density cost). |
| R7 | Simultaneous parallel raw streaming, AI-controlled prioritization | Upstream contract already defines this (stream-raw-decide-downstream, PLAN §7.11; command surface §3.5). Hardware must deliver parallel buses + INT/data-ready wiring + PPS-disciplined timestamping (§5.3). |
| R8 | Contact / air-entry / liquid-entry / internal sensor classes | Exposure classes defined per sensor in §5.6; microfluidics is **deferred upstream** (PLAN Stage 16–17) → liquid path is a chassis *provision* (port + volume reservation), not populated in v1. |
| R9 | Right medium → right sensor; minimize interaction effects | Zoning + EMI/thermal rules from bench lessons (§5.5); data-quality flags (`motors_active` etc.) already in the record contract. |
| R10 | Regulated posture: wellness-only claims until validated | Matches upstream: capability-coverage ratifies `body-physiological` as **wellness-only**; ship-gate #10 requires a per-modality privacy/regulatory pack (SEM-5/#54). Hardware side: laser class 1 (BMV080), UV-LED eye-safety, skin-contact material safety. |
| R11 | MCU syncs+streams all sensors comfortably; on-device AI nice-to-have | Answered by the §5.1 reference architecture: NPU-class application MCU (STM32N6 primary candidate) gives real on-device-AI headroom + the bus/DMA/timestamping fabric; always-on sentinel domain covers ambient. H1 eval-kit spike validates before freeze (D1/D2). |
| R12 | Pipeline regenerates ship-ready state when sensors change | §6 — but with 2026-realistic trust boundaries: automated BOM/netlist/ERC/DRC/fab-export; human-owned placement and critical routing. "Zero-touch ship-ready" is not achievable today and is not claimed. |

## 2. Evidence base — what exists today (context and inputs, **not constraints** — see §0.1)

### 2.1 Prototype state
Three-board Perma-Proto prototype, **Phase 0 closed 2026-06-29** (single-device live loop, laptop hub): Board A "Brain" (XIAO ESP32-S3 Sense; 14 I²C sensors via PCA9548A mux @400 kHz; OV5640 camera; USB-CDC telemetry; SD), Board B "Muscle" (no MCU; MT3608 boost 5.09 V + Pololu 3.38 V + motor MOSFETs), Board C "Sentry" (XIAO nRF52840; Geiger, MPR121 touch on own I²C, haptic, NeoPixel, battery monitor; UART relay to A with CRC8 framing). Definitive pinmaps: interrogator `PLAN.md §2.4–2.6`. **Warning: `archive/legacy_docs/{master_topology,fabrication_netlist}.md` are deprecated and conflict with the live pinmap — never use them as PCB input.**

### 2.2 Sensor candidate set (the 16 registered types, `shared/schemas/sensors/*.yaml` — re-validated at H1 per §5.7)

| Sensor | Domain | Bus today (mux CH / addr) | Exposure class (§5.6) |
|---|---|---|---|
| BME688 | gas/VOC/T/RH/P | CH0 / 0x77 | air |
| SGP41 | VOC+NOx | CH0 / 0x59 | air |
| BMV080 | PM2.5 (laser, class 1) | CH0 / 0x57 | air (needs free-air window) |
| AMG8833 | 8×8 thermal IR | CH1 / 0x69 | optical window (8–14 µm) |
| MAX30102 | PPG HR/SpO₂ | CH1 / 0x57 (fixed) | **contact** window |
| VL53L8CX | 8×8 ToF depth | CH2 / 0x29 | optical window (940 nm) |
| AS7343 | 14-ch visible spectral | CH3 / 0x39 | optical window + LED |
| AS7331 | UVA/B/C | CH3 / 0x74 | **direct aperture** (glass kills UV-C) |
| AS7263 | NIR spectral | CH3 / 0x49 | optical window + NIR LED |
| BNO085 | 9-DoF IMU | CH4 / 0x4A | internal |
| TMAG5273 | 3D Hall | CH4 / 0x22 | internal (>30 mm from motors) |
| ADS1115 | 16-bit ADC (AD8317 RF, piezo) | CH5 / 0x48 | internal + external probes |
| XM125 (A121) | 60 GHz radar | CH6 / 0x52 | behind radome (plastic OK) |
| NEO-M9N | GNSS | CH7 / 0x42 | antenna window, >50 mm from MCU |
| MPR121 | capacitive touch | Board C bus / 0x5A | **contact** (shell electrodes) |
| MIKROE-4036 (BG51) | gamma/beta | GPIO pulse, 5 V | internal (thin window ideal for beta) |

Plus OV5640 camera (FPC), UV/White LEDs, haptic, NeoPixel, fan, pumps, valve. Future sensors come from the ROI-ranked **sensory-gap register** (capability-coverage.md; e.g. GAP-01 AC E-field, GAP-02 selective gas, electrochemical NO for FeNO) — that register, not ad-hoc choice, is the input queue for board revisions.

### 2.3 The integration checkpoint — interrogator issue #7 (joint, not this repo's DoD)
Exit KPIs (verbatim anchors): full local e2e loop **re-validated on PCB**; **binary IDL (ADR-0004) live with text debug mode**; **diagnostics suite re-run on a PCB capture with no regression vs the breadboard baseline** (golden-CI #37 makes this checkable); **PLAN §7.10 latency budget still met**. This is where the new board is *accepted into the system* — the firmware side of it is the upstream project's work. The hardware DoD is the §1 spec scorecard (phase H6a); #7 is the joint milestone (H6b).

### 2.4 Upstream's own PCB research (PLAN §7.5.3.18) — **input evidence for the H1 trade study, not a decision**

Upstream already researched what a PCB should change relative to the breadboard; its conclusions are strong candidate answers that H1 confirms, amends, or discards against the §1 spec:
- Concurrency unit = **one task per bus**, not per sensor.
- **VL53L8CX + BNO085 move to SPI+DMA, INT-driven** (they are the rate/bandwidth drivers; VL53L8CX needs a ~90 KB blob load at init).
- Two I²C buses: **I²C-A** (AMG8833, ADS1115, TMAG5273, MAX30102), **I²C-B** with a *small* mux retained only for the address-colliding spectral chain (BME688, BMV080, AS7343/31/63, SGP41, NEO-M9N, XM125).
- **INT/data-ready lines wired for every sensor that has one** (never wired on the breadboard — a known gap), FIFO watermark batch reads where supported.
- **GPS-PPS-disciplined shared input-capture timer** for cross-sensor timestamping.
- The PCA9548A leaves the critical path; I3C is the v2 successor (ESP-IDF/Zephyr driver maturity was the blocker at last check — re-verify at H1).

### 2.5 Bench lessons that are now PCB design rules (deviation log + PLAN §5.3/§13)
1. **XIAO A-pin/D-pin GPIO aliasing** cost real debugging — on custom PCB, reference GPIO numbers only; pin-map is generated from the contract (§6.1).
2. **0x57 collision (BMV080 vs MAX30102)** — without a big mux, plan address straps / XSHUT sequencing / bus assignment explicitly (they land on different buses in §2.4).
3. **VL53L8CX carrier straps**: interface-select must be tied for the chosen mode; wrong strap = silent NACK. On-board strap resistors, not jumpers.
4. **Spectral chain is 100 kHz-bound** (stacked breakout pull-ups → rise-time violation). On the PCB *we* own the pull-up budget: one calculated pull-up set per bus segment; design for 400 kHz (1 MHz where qualified).
5. **A single faulty slave wedges a shared bus** (SGP41 DOA locked everything): per-segment **power gating (load switches)** + bus segmentation + PCA9548A-style isolation where retained + 9-clock SCL recovery + watchdog (currently disabled upstream — G6) are all mandatory v1 features.
6. **MAX30102 1.8 V pull-up trap** on clone modules: on-board we control this — bare sensor + correct level domain.
7. **Wrong-library-but-init-passes** (TMAG5273, AS7331): bring-up validates *values*, not enumeration — feeds the H6 diagnostics re-run.
8. **Thermal**: CPU/regulator heat corrupts BME688/SGP41/AMG8833 — thermal chimney (air over gas sensors first, exhaust over CPU), ≥20 mm separation or slotting/moats, AMG8833 kept off the hot side. BMV080 self-heat budget respected.
9. **EMI**: motor rails on a separate noisy domain, flyback diodes, ferrites at gate escapes, star/partitioned grounds (explicitly a PCB-phase constraint per DESIGN_NOTES.md), Geiger >30 mm from motors, GPS antenna >50 mm from processors, RF-silence mode retained.
10. **Every claimed dimension gets provenance** — the 15.77 mm XIAO row-spacing miss is why: bootstrap "verified" values are suspect until datasheet/caliper-confirmed. This is exactly the AssetPin discipline (§3).

## 3. Contract boundary with `interrogator` (binding decisions)

1. **The Unified Sensor Registry (USR, ADR-0013) is the single source of truth** for per-sensor identity, electrical, mechanical, and asset facts. This repo **consumes** `shared/schemas/sensors/*.yaml` — pinned, never copied. Mechanism: **git submodule pinned to a reviewed SHA** (or a vendored, checksummed snapshot with the pin recorded), bumped only by explicit PR.
2. **What we bind to (read-only):** `facets.electrical` (bus, i2c_addresses, logic_level_v, relay), `facets.mechanical` (footprint_ref, dimensions_mm), `assets` pins (datasheet/cad_footprint/model_3d with rev + sha256). Per-instance placement (bus assignment, address, board) binds to the **device profile (#123)** view, which the PCB v1 profile will instantiate.
3. **Single-writer stays upstream.** Registry facets are `pending` today (electrical facts knowingly inconsistent across inventory CSV / build docs / contract.py — USR-3 is the resolution task, owner: embedded-SME; mechanical owner: pcb). This repo **drafts resolution packets** (per-sensor electrical/mechanical fact sheets with datasheet citations) as PR-ready proposals, but **the owner applies them upstream** — we never write into `interrogator`.
4. **AssetPin discipline extends to everything heavy here:** datasheets already live in `registry_assets/<SENSOR>/{datasheet,schematics,standards}` (14 parts populated; only BMV080 has a STEP today). Footprints, symbols, 3D models, gerbers, renders live in **this repo via Git LFS**, each referenced by `{asset_id, version/rev, sha256}`. An upstream asset rev-bump reopens the citing facets and (by CI tripwire) flags the affected board areas — the anti-drift loop.
5. **Cadence separation:** upstream CI = pytest/contract; this repo's CI = ERC/DRC/asset-checksum/fab-output checks (§6.4). The PCB is "just another registry consumer."
6. **Firmware co-changes** (binary IDL, ESP-IDF port, INT-driven acquisition) are upstream work items; this plan flags them as cross-repo dependencies at each phase boundary rather than absorbing them.

## 4. 2026 tooling verdict (what changed vs the draft brief)

Full detail + sources in [`docs/draft-review.md`](docs/draft-review.md). The decision-relevant findings:

1. **Drop the HDI blind/buried-microvia assumption.** JLCPCB standard production doesn't offer blind/buried vias; it *does* offer free resin-filled copper-capped **via-in-pad (POFV) on 6–20 layer boards**, 0.2 mm min drill, 3.5 mil trace/space. A **6–8 layer through-via board with POFV** comfortably escapes every package in our BOM (largest challenge is LGA/module-class parts, not fine-pitch BGA) at hobby-scale cost. This also makes the "can Freerouting do blind/buried vias" question moot — and the evidence says it can't anyway.
2. **Freerouting (v2.2.4, active, headless CLI + self-hostable API)** has **no signal-integrity awareness** (no diff pairs, no length matching, no copper-pour awareness) and known convergence issues on dense boards. Verdict: usable as a *grunt-net* router with `-inc` protecting hand-routed critical nets; never for USB/RF/clock/analog.
3. **KiCad 10 (Mar 2026) is the platform.** Headless automation = `kicad-cli` (ERC/DRC with JSON reports + exit codes, gerber/STEP/BOM export). The official IPC API (kipy) is **PCB-only and GUI-attached until KiCad 11** — so the pipeline's headless loop rests on kicad-cli + S-expression tooling, not the IPC API.
4. **KiCad MCP servers are demo-grade.** mixelpixx/KiCAD-MCP-Server's auto_route/JLCPCB claims have **no independently verified end-to-end use**; lamaalrajih/kicad-mcp is read-only. The most technically serious agent toolkit is **rjwalters/kicad-tools** (v0.13.0 Apr 2026: format-preserving S-expression round-trip, pure-Python DRC with JLCPCB rule presets, A* router, MCP server included). Strategy: **evaluate, don't depend** — every AI edit happens on a git-versioned project and is diffed by a human.
5. **LLM datasheet extraction of pinouts/footprints is unproven** (no public benchmark even exists). The reliable 2026 path: **verified libraries first** — `easyeda2kicad.py` (LCSC/JLCPCB catalog → KiCad symbol+footprint+STEP), SnapMagic/Ultra Librarian/SamacSys fallback, ProtoFlow-class AI generation only for stragglers — then **1:1 print/overlay + pin-1 check by a human**, with the LLM as a *second reader* (netlist vs datasheet cross-check). This slots perfectly into the repo's existing E0/E1/E2 evidence-tier discipline.
6. **Optional accelerators:** Quilter (native KiCad output; free program exists) or DeepPCB trial as *placement/routing candidate generators* only; atopile (schematic-as-code compiling to KiCad — attractive for the regeneration goal, but pre-1.0 churn) as an H2 spike, not the baseline.
7. **MCAD loop:** `kicad-cli pcb export step` + KiCad StepUp (FreeCAD) for bidirectional board↔enclosure sync. This is mature and free.

**Net effect on the draft's architecture:** the five-agent flow (Ingestion → Placement → MCP Orator → Auto-Router → DRC Loop) survives as a *pipeline skeleton*, but the trust boundaries move: agents own facts-gathering, netlist generation, rule-checking loops, BOM and fab packaging; **humans own placement and critical routing**; and the "eliminates Quilter for $0" claim is replaced by "Freerouting for grunt nets only, optional Quilter free-tier candidates."

## 5. Target v1 hardware architecture

### 5.1 Compute — recommended reference architecture (position taken; H1 validates on eval kits)

**Two-domain architecture on one board.** The spec pulls in two opposite directions — burst compute for parallel multi-sensor streaming + on-device AI (R7, R11), and week-scale always-on ambient vigilance inside an 8 h+ active budget (R3). No single 2026 MCU is best at both; a two-domain design is the honest answer, and it also cleanly implements "AI decides what runs" (R7) as hardware power domains.

**Application domain — primary candidate: STM32N6 class** (Cortex-M55 ~800 MHz + Neural-ART NPU, MIPI-CSI camera pipeline, USB-HS, rich I²C/I3C/SPI+DMA set, hardware timers for input-capture timestamping). Rationale against the spec: the NPU gives real on-device AI headroom (R11) instead of "maybe later"; native I3C is the R1 growth path (dynamic addressing kills the address-collision class entirely); the integrated ISP makes the camera decision (D7) a stuff-option rather than an architecture fork. **Fallback: NXP i.MX RT1170 class** (mature, 6×I²C + 6×SPI + eDMA — the widest bus fabric in the segment) if N6 toolchain/supply disappoints at H1. **Cost-down option: ESP32-P4** (native I3C, cheap; weaker AI story, no radio). The application domain sleeps in ambient mode and is woken by the sentinel on triggers or user intent.

**Sentinel + connectivity domain — pre-certified BLE module, nRF54L15 class.** Always-on at µA–mA: radiation pulse counting, capacitive touch wake, battery/fuel-gauge supervision, haptic + glow control, BLE link, RTC hold, and power-domain sequencing for everything else. Using a **pre-certified module** here is the deliberate commercial choice: the intentional-radiator (FCC/ISED/CE-RED) burden stays modular instead of forcing full radio certification of our board. Wi-Fi burst offload (if the H1 bandwidth analysis demands more than BLE + USB-C) is likewise a pre-certified companion module, added only on evidence.

This is pattern (b) — big MCU + always-on companion — chosen from first principles (power physics + certification economics), not inherited. D1/D2 record the owner's ratification; H1 spikes both candidates on eval kits against the streaming + timestamping + power targets before schematic freeze.

### 5.2 Buses
Candidate topology (from §2.4 evidence, confirmed or amended at H1): high-rate sensors on SPI+DMA with INT lines; remaining I²C split across ≥2 controllers with per-segment isolation; address-colliding parts resolved by bus assignment/straps rather than a monolithic mux; calculated pull-up budget per segment; per-segment load switches for fault isolation and power gating (this is also how "why stream fluidic if there's no fluid around" becomes hardware: the AI layer can power/clock-gate whole sensor domains). If the H1 MCU choice brings mature I3C, it may enter v1 rather than v2. Reserve: one spare expansion segment (I²C/I3C + power + INT) for future sensors (R6 headroom).

### 5.3 Timing
GPS PPS → MCU input-capture; all sensor INTs timestamped in hardware where the MCU allows; `utc_ms = millis() + gps_offset` contract preserved; target = the §7.10 latency budget and the T-01/T-02 skew diagnostics.

### 5.4 Power
Redesigned tree replacing MT3608/Pololu: Li-ion cell (capacity per D4) → charger + fuel gauge (USB-C) → high-efficiency bucks for 3V3_SENSORS (split quiet/noisy sub-rails via load switches), 3V3_MCU, 5V_ACT (actuators, gated); reverse-polarity + fuse retained; battery lockout 3.4 V. Budget table with per-sensor ambient/active currents is a deliverable of H1 and must show **≥8 h ambient** (R3) or force D4 (bigger cell / reduced ambient set).

### 5.5 Floorplan zoning (carried from PLAN §6.1 + bench EMI/thermal rules)
Quiet Nose (camera, spectral, optical windows) — Brain Middle (MCUs, buses, IMU) — Noisy Tail (actuator drivers, battery, charger). Gas-sensor cluster at fan intake with thermal moat/slots; exhaust over CPU; AMG8833 thermally isolated; Geiger and TMAG >30 mm from motor paths; GNSS antenna corner with keepout >50 mm from MCUs; analog (PPG, AD8317, piezo) partitioned ground region; RF keepouts per module datasheets.

### 5.6 Exposure classes → chassis features (maps to the owner's sketches)
- **Contact field**: MAX30102 window + MPR121 electrode zones on the shell ("touch and it extracts").
- **Air path**: micro-fan-driven channel — intake over BME688/SGP41/BMV080 (BMV080 free-air window requirement), exhaust past CPU (thermal chimney). Small shell holes only.
- **Liquid provision**: reserved port + internal volume + flex/connector allowance for the Stage 16–17 microfluidic module — **not populated in v1**.
- **Optical apertures**: VL53L8CX + AMG8833 + spectral trio + camera + UV/White LEDs; AS7331 needs a direct (or quartz) aperture for UV-C.
- **Radome**: XM125 behind plastic.
- **Sky window**: GNSS antenna.
- **Feedback**: NeoPixel light-pipe ring/zones for the "twinkling stars" per-sensor activity glow + haptic — the subtle-glow shell from sketch 2.

### 5.7 Sensor BOM — raw silicon, chip-down (breakout parts are dead)
The 16 registered types are the **capability baseline**, not a BOM of breakouts. Every channel is re-sourced as raw silicon on our board; H1 confirms packages/successors from the datasheets in `registry_assets` (land patterns and dimensions get pinned there — no dimension is asserted here without a datasheet citation):

| Capability | Chip-down part (position) | Note |
|---|---|---|
| Gas/T/RH/P | **BME688** (LGA) | direct solder; keep out of thermal plume |
| VOC/NOx | **SGP41** (DFN) | co-located in air path |
| PM2.5 | **BMV080** (solderable miniature unit) | smallest PM sensor extant; free-air window is a chassis feature |
| Thermal imaging | **AMG8833** (SMD) | evaluate higher-res successors at H1 (32×24 class) if power/price fit |
| PPG (HR/SpO₂) | **MAX30102EFD** (OLGA) | per the brief; evaluate current ADI/ams successors for regulated-grade optical front end (R10) |
| ToF depth 8×8 | **VL53L8CX** (LGA) | strap interface-select in copper; SPI mode per §5.2 |
| Visible spectral | **AS7343** (OLGA) | |
| UV A/B/C | **AS7331** (OLGA) | direct/quartz aperture (UV-C) |
| NIR spectral | **AS7263** (LGA) | + NIR LED |
| IMU 9-DoF | **BNO085** (LGA) | INT wired; vibration-isolated mount zone |
| 3D magnetics | **TMAG5273** (SOT-23) | trivially chip-down |
| Precision analog | **re-evaluate ADS1115** | the application MCU's own ADCs may absorb this; keep an external Δ-Σ ADC only if the RF-power (AD8317) / piezo chains demand it |
| 60 GHz radar | **Acconeer A121 (raw, antenna-in-package)** — not the XM125 module | AiP makes chip-down feasible; RF keepout + radome per datasheet |
| GNSS | **antenna-integrated module class (u-blox MIA/NEO-M9/M10)** | module is the correct commercial choice here (RF + antenna certification/performance); exact part at H1 |
| Touch | **MPR121 (QFN) or MCU-native cap-touch** | sentinel MCU class has capable touch peripherals — absorb if electrode count allows (fewer parts, lower ambient power) |
| Radiation | **BG51-class solid-state detector (raw, not the carrier board)** | evaluate current solid-state alternatives at H1 |
| Camera (if D7 = yes) | raw sensor + FPC connector into the app MCU's CSI/DVP | not a dev-board camera |

Additions come from the gap register + market scan (the "new sensor ships → we ship" loop). Every selected part gets a USR record upstream (new/updated) **before** it enters the schematic — the contract stays the single source of truth, and interrogator's firmware follows our interface doc.

### 5.8 Dynamic boundary co-optimization (R4 — the sizing method, from the brief)
Board size is elastic, not preset: baseline floor area = sum of component courtyards + a layout clearance multiplier (~40 % starting point, tuned per zone — analog and RF zones need more, digital less). When placement/routing fails inside the boundary, escalate in order: **Z-axis lever** (4 → 6 → 8 layers; JLCPCB through-via + POFV keeps this cheap) before **XY lever** (grow unconstrained edges in 0.5 mm steps). The final envelope — outline, max component heights top/bottom, keepouts — exports as STEP and *defines the chassis* (§5.6 apertures wrap around it). The phone-attach question (D7) is answered by this output, not assumed.

### 5.9 Modularity mechanism (R6)
v1 modularity = **contract-driven regeneration + frozen chassis interface**: (a) board outline, mounting bosses, connector positions, and the aperture plate geometry are frozen after H5; (b) sensor churn re-enters at H2 with the pipeline regenerating schematic/layout deltas inside the frozen envelope; (c) the aperture plate (the one part that must physically change when an exposed sensor changes) is a cheap, replaceable, separately-versioned part. Physical plug-in sensor modules (mezzanine/flex) are a v2 study item (D6) — they cost density, which is the primary v1 constraint.

### 5.10 Commercial-grade requirements (new — DFM/DFT/certification/production)

Because this is a product, not a lab board:

- **Certification path (W-CERT):** unintentional radiator EMC (FCC Part 15B / CE-EMC / ISED) planned from H1 — pre-scan at H4 on the first spin; intentional-radiator scope kept inside pre-certified radio modules (§5.1); BMV080 laser class 1 carried; UV-LED photobiological safety (IEC 62471) with hardware interlock; skin-contact materials biocompat considerations at H5; battery system to IEC 62133-class expectations (protected cell + protection circuitry + fuel gauge + thermal cutoff); RoHS/REACH-compatible BOM from the start.
- **DFM/DFT:** design against the chosen fab/assembly class from day one (JLCPCB 6–8-layer + POFV baseline, D3); paneling with fiducials + tooling; controlled-impedance stackup documented; **test points on every rail and every bus**; a bring-up/test header (SWD/JTAG via tag-connect footprint, UART console); per-domain current-measurement shunt points (this is how the R3 power budget gets *measured*, not estimated); DNP options for camera + Wi-Fi companion so one layout serves both D7 outcomes.
- **Production programming + identity:** flash/provision path (SWD gang or bootloader), per-unit serial + device identity (the sentinel MCU class carries crypto/KeyStore for later fleet mTLS — matches upstream's P1+ security posture without binding to it).
- **Serviceability:** actuators (fan/pump/valve — the only wear parts, R2) on a replaceable sub-assembly path; battery replaceable without board rework.

## 6. The design pipeline (closed-loop, human-gated)

### 6.1 Stages
1. **Contract ingest (automated):** script reads the pinned USR records + v1 device profile → generates the sensor IO map, bus/address table, pin-budget, and netlist skeleton. Any `pending` electrical facet blocks with a named upstream ask (USR-3).
2. **Library (automated + human gate):** for each part, fetch verified symbol/footprint/3D (easyeda2kicad → SnapMagic/UL → last-resort AI generation); record AssetPin (version, sha256, source, evidence tier); **human overlay-check** (1:1 print or render diff) promotes E0→E1.
3. **Schematic (human-owned, AI-reviewed):** KiCad 10 capture per block (power, MCU×2, per-bus sensor clusters, actuators, analog). LLM review pass: address conflicts, pull-up budget, decoupling audit, strap resistors, INT routing completeness — against the datasheets in `registry_assets`. *(atopile spike runs in parallel as D5.)*
4. **ERC/DRC loop (automated):** `kicad-cli sch erc` / `pcb drc` with `--format json --exit-code-violations` in CI, plus a `kicad-cli jobset run` pipeline for the full output set; agent proposes fixes as diffs; human applies/approves. Rule presets = JLCPCB 6-layer class.
5. **Placement (human-owned, tool-advised):** floorplan per §5.5 encoded as keepout/zone rules in the board file; optional Quilter/DeepPCB candidate for comparison only.
6. **Routing (split):** hand-route USB, crystals, SPI, PPS, PPG/analog, antennas/keepouts, power; then Freerouting headless with `-inc` for remaining slow nets; final SI sanity review.
7. **Fab package (automated):** kicad-jlcpcb-tools → gerber/drill/BOM/CPL with LCSC part numbers; InteractiveHtmlBom; `kicad-cli` STEP export.
8. **MCAD co-design:** STEP → FreeCAD (StepUp) enclosure; collision/aperture checks; 3D-print v0 shells.
9. **Design rationale log:** every non-obvious choice logged as a lightweight ADR in `docs/decisions/` (the brief's "Design Rationale Log").

### 6.2 Trust boundaries (explicit)
Automated & trusted: BOM/sourcing, contract-derived netlist data, ERC/DRC loops, fab packaging, STEP export, checksum tripwires. AI-assisted with human sign-off: schematic review, placement suggestions, fix proposals, datasheet cross-checks. Human-only: footprint promotion to E1, critical-net routing, final fab release, anything touching safety (battery, laser, UV).

### 6.3 Regeneration promise (R12)
A sensor swap = new USR record upstream → pin bump here → stages 1–2 regenerate the delta automatically → stages 3–7 replay on the delta inside the frozen envelope. Measured goal: **sensor-swap respin in ≤2 human-days of touch time** by v2.

### 6.4 CI (this repo)
On PR: ERC/DRC (kicad-cli, JSON artifacts), AssetPin checksum verification, contract-pin drift check (fails if upstream SHA moved without a pin PR), fab-output regeneration diff, LFS integrity. Releases: tagged fab packages with full provenance (contract SHA + asset checksums + toolchain versions).

## 7. Phases

| Phase | Content | Exit criteria |
|---|---|---|
| **H0 — Foundations** (~1–2 wk) | Repo scaffold (this PR); toolchain pin (KiCad 10.0.x, kicad-cli CI container); submodule/pin mechanism to `interrogator`; LFS; stage-1 contract-ingest script; **draft USR-3 electrical resolution packets** for the candidate set (PR-ready for upstream); kick D1–D6 decision spikes | CI green on empty board; ingest script emits the IO map from pinned records; resolution packets delivered upstream |
| **H1 — Architecture validation** (~2–3 wk) | Eval-kit spikes validating the §5.1 reference architecture (streaming + timestamping + sentinel power); **chip-down BOM confirmation (§5.7)** incl. successor parts, from `registry_assets` datasheets; bus topology finalized; power tree + **measured-basis power budget vs R3**; block diagram; layer stack + fab class freeze (D3); battery/cell choice (D4); certification plan v0 (W-CERT); **interface-requirements doc → upstream firmware project** | Owner ratifies architecture + budget + v1 BOM; upstream electrical facets `approved` for the ratified set |
| **H2 — Schematic** (~2–4 wk) | Library build with AssetPins (the ratified v1 sensor set + compute + power, verified footprints); full schematic; ERC clean; LLM review packet; atopile spike verdict (D5) | ERC = 0; human review sign-off; BOM 100 % sourced (LCSC/stock) |
| **H3 — Layout** (~3–5 wk) | Floorplan per §5.5; placement review; critical-net hand routing; Freerouting pass on grunt nets; DRC clean; thermal/EMI review; STEP export | DRC = 0 vs JLCPCB 6/8-layer rules; SI/thermal review sign-off; board envelope frozen → chassis interface freeze |
| **H4 — Fab + bring-up** (~4–6 wk incl. lead time) | JLCPCB fab + PCBA (SMT where catalog allows, hand-finish rest); bring-up plan mirroring upstream diagnostics (per-bus smoke → per-sensor conformance → all-sensor coherence F-04 → soak R-02); deviation log continues here | Board powers, all buses enumerate, every sensor streams conformant records |
| **H5 — Chassis v0** (parallel from H3 freeze) | FreeCAD enclosure from STEP; aperture plate; fan path; contact window; light pipes; 3D-printed shells; drop/fit iteration | Assembled device; thermal chimney verified; apertures validated per exposure class |
| **H6 — Spec sign-off + integration gate** | (a) **Hardware DoD:** R1–R12 scorecard against the built device (power budget measured, envelope recorded, exposure classes validated, modularity respin demo). (b) **Joint integration milestone with upstream** (their firmware work, our board): binary IDL live, diagnostics no-regression, latency budget — i.e. interrogator #7 | (a) Spec scorecard ratified by owner → **v1 hardware done**; (b) #7 green → board accepted into the system; v2 planning opens (gap-register sensors, further miniaturization toward the north star) |

Cross-repo dependencies (upstream work, flagged not owned): USR-3 sign-off, #27 datasheet bounds confirmation (conformance currently 100 % conditional), binary IDL implementation (ADR-0004), ESP-IDF port decision, watchdog re-enable (G6).

## 8. Risks

| Risk | Mitigation |
|---|---|
| Power budget misses 8 h ambient (R3) | H1 hard budget gate; INT-driven duty cycling; per-segment gating; D4 cell escalation |
| Footprint/pinout error → dead board | Verified-library-first + AssetPin + human overlay check + LLM second-reader; no raw-LLM footprints |
| Freerouting non-convergence / bad routes (documented v2.x quality regression vs v1.9) | Critical nets hand-routed first, `-inc` protected; benchmark v2.2.4 vs v1.9.0 on our board; Freerouting scoped to grunt nets; fallback = full hand route |
| MCP/agent tooling immaturity corrupts files | Git-versioned everything; agents produce diffs, humans merge; rjwalters/kicad-tools evaluated in a sandbox first |
| VL53L8CX SPI unknowns (max clock, blob load) | H1 bench spike on breakout before schematic freeze |
| Thermal cross-talk on dense board (BMV080 15 K self-heat, bucks) | Zoning + moats/slots; thermal review at H3; measured at H4 soak |
| I²C lockup in the field | Per-segment power gating + SCL recovery + watchdog + retained mux isolation on spectral chain |
| Compute choice wrong (bus/power/AI headroom) | H1 trade study with bench spikes on eval kits before schematic freeze; interface-requirements doc keeps the upstream firmware port decoupled from the silicon choice |
| Regulatory exposure (UV, laser, skin contact, health claims) | Wellness-only posture (upstream SEM-5); class-1 laser unchanged; UV interlock; materials choice at H5 |
| Upstream contract churn mid-design | Pinned SHA + CI drift tripwire; bumps only at phase boundaries |
| EMC failure at pre-scan (dense mixed-signal + 60 GHz + optical emitters) | Zoning §5.5; per-domain filtering; pre-certified radios; H4 pre-scan budget + one respin allowance |
| New-silicon risk (STM32N6-class part or sensor successors) | H1 eval-kit gate; fallback parts named in D1/§5.7; DNP-friendly layout keeps options open |

## 9. Open decisions (owner/SME calls — proposed defaults)

| # | Decision | Proposed default |
|---|---|---|
| D1 | v1 application MCU | **Recommended: STM32N6 class** (NPU + I3C + CSI, §5.1); fallback i.MX RT1170; cost-down ESP32-P4. H1 eval-kit spike confirms before schematic freeze |
| D2 | Compute pattern | **Recommended: two-domain** — app MCU + pre-certified nRF54L15-class sentinel/BLE module (§5.1) — chosen on power physics + certification economics |
| D3 | Fab/process | **JLCPCB, 6-layer through-via + POFV via-in-pad**; escalate to 8-layer not to microvia |
| D4 | Battery | Size cell to the H1 budget (likely 2500–3500 mAh Li-ion pouch) vs relaxing R3 — needs the budget table first |
| D5 | Schematic-as-code (atopile) | **Spike only** in H2; KiCad capture is the baseline |
| D6 | Physical sensor-module system (mezzanine/flex) | **Defer to v2 study**; v1 modularity = §5.9 |
| D7 | Camera on v1 | **Conditional on the achieved envelope (§5.8)**: if the device lands phone-attachable, no camera (per the brief); otherwise a camera goes in. Decide at H3 when the envelope is real; schematic carries the camera interface either way so the layout answer, not the schematic, decides |
| D8 | UV LED | Swap 400 nm → **365 nm** (biofluorescence, per upstream PLAN §9) with eye-safety interlock |
| D9 | Fluidics | **Chassis provision only** in v1 (port + volume + connector reservation) |

## 10. Proposed Project 3 structure (created only after this plan is ratified)

Epics = H0–H6 + three cross-cutting tracks (W-PWR power budget; W-PIPE pipeline/CI; W-CERT certification/compliance). Each epic gets issues matching the phase deliverables above, with fields: Phase, Status, Blocked-by (cross-repo deps flagged), Evidence (link to ADR/artifact). The sensory-gap register drives the v2 backlog column.

---
*Sources: interrogator repo (read-only) — PLAN.md §2, §5–7, §10, §13; docs/architecture/{0013,unified-sensor-registry*,board-acceptance-criteria,capability-coverage,system-architecture}.md; docs/build/{deviation_log,board_a_*,phase-0-build-scope,interboard_harness}.md; shared/schemas/{sensors/*,sensor_specs.yaml}; issue #7. Tooling research: see docs/draft-review.md §3 for full source list.*
