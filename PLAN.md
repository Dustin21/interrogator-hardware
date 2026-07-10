# Interrogator Hardware — Build Plan

**Status: v0.1 DRAFT — for owner review. Nothing below is executed until ratified.**
Date: 2026-07-10 · Owner: Dustin21 · Repo: `interrogator-hardware` (this repo) · Tracker: [GitHub Project 3 — Interrogator Device Hardware Build](https://github.com/users/Dustin21/projects/3)

This plan merges (a) the owner's hardware-build brief ("Closed-Loop AI EDA Pipeline for Ultra-Dense Interrogator Device"), (b) a full read-only review of the `interrogator` repo (registry, PLAN.md, build docs, deviation log, ADRs), and (c) a July-2026 state-of-the-art review of AI-EDA tooling. Corrections to the original brief are catalogued in [`docs/draft-review.md`](docs/draft-review.md) — read that alongside this plan.

---

## 0. Mission and scope

Design, fabricate, and bring up the **first custom PCB ("v1 board") plus chassis** for the Reality Interrogator, closing the upstream **PCB Gate (interrogator #7)**, and stand up a **repeatable, contract-driven design pipeline** so that future sensor swaps/additions regenerate a fab-ready board revision in few cycles rather than a redesign.

**In scope here:** PCB architecture, schematic, layout, fab/assembly packages, footprint/3D asset library, enclosure co-design, bring-up plan, the EDA automation pipeline and its CI.
**Out of scope here (lives upstream in `interrogator`):** firmware, the sensor registry and all facet YAMLs, diagnostics/conformance, backend, semantics, regulatory validation content. The hardware repo is *a consumer* of the upstream contract — never a fork of it.

## 1. Requirements (from the owner brief, reconciled with repo reality)

| # | Requirement | Reconciliation with repo / research |
|---|---|---|
| R1 | Many orthogonal solid-state sensors (15 now → 100+ over time) | v1 carries the 16 registered sensor types (see §2.2). Scaling past ~20 concurrent sensors is a bus-architecture problem: concurrency unit is one task **per bus** (PLAN §7.5.3.18); I3C is the designated successor, deferred to v2 (driver maturity). |
| R2 | Solid-state, 3+ years without replacement | All sensors solid-state (BMV080 MTTF 10 y). **Exception the brief already implies:** fan, pumps, valve are electromechanical actuators — they are serviceable parts, not sensors. Design them on a replaceable sub-path. |
| R3 | 8 h+ battery in ambient mode | **Tension:** current budget is ~400 mA passive → ~5 h on 2000 mAh (PLAN §10). Closing this needs INT-driven acquisition (already the PCB plan), per-domain power gating, a modern power tree, and/or a larger cell. Tracked as workstream W-PWR with a hard budget table. |
| R4 | As small as feasible; north star = AirPods-case sleekness | Repo's stated v1 PCB target ≈ **120×70×35 mm** (PLAN §6.2), charter long-term 80×45×30 mm. v1 optimizes for *validated density*, not the north star; miniaturization is v2+. |
| R5 | Battery-powered, pocket-safe (heat) | Thermal zoning rules exist and are binding (PLAN §6.1, §13 "Rule of Zero Drift"); BMV080 self-heats ~15 K; LDO dissipation lesson from bring-up (~0.5 W) → use bucks, not LDOs, for heavy rails. |
| R6 | Modular: sensors added/deprecated without chassis churn | Achieved via (a) the contract-driven regeneration pipeline (§6), (b) a **frozen chassis interface**: board outline + mounting + an *aperture plate* as the swappable part (§5.7), (c) reserved bus/power headroom. Full board-level plug-in modules are explicitly **not** v1 (density cost). |
| R7 | Simultaneous parallel raw streaming, AI-controlled prioritization | Upstream contract already defines this (stream-raw-decide-downstream, PLAN §7.11; command surface §3.5). Hardware must deliver parallel buses + INT/data-ready wiring + PPS-disciplined timestamping (§5.3). |
| R8 | Contact / air-entry / liquid-entry / internal sensor classes | Exposure classes defined per sensor in §5.6; microfluidics is **deferred upstream** (PLAN Stage 16–17) → liquid path is a chassis *provision* (port + volume reservation), not populated in v1. |
| R9 | Right medium → right sensor; minimize interaction effects | Zoning + EMI/thermal rules from bench lessons (§5.5); data-quality flags (`motors_active` etc.) already in the record contract. |
| R10 | Regulated posture: wellness-only claims until validated | Matches upstream: capability-coverage ratifies `body-physiological` as **wellness-only**; ship-gate #10 requires a per-modality privacy/regulatory pack (SEM-5/#54). Hardware side: laser class 1 (BMV080), UV-LED eye-safety, skin-contact material safety. |
| R11 | MCU syncs+streams all sensors comfortably; on-device AI nice-to-have | MCU selection is decision D1 (§9). Baseline ESP32-S3 (continuity); alternatives evaluated in H1 spike. On-device AI not a v1 gate. |
| R12 | Pipeline regenerates ship-ready state when sensors change | §6 — but with 2026-realistic trust boundaries: automated BOM/netlist/ERC/DRC/fab-export; human-owned placement and critical routing. "Zero-touch ship-ready" is not achievable today and is not claimed. |

## 2. Baseline — what exists today (from the interrogator repo, read-only)

### 2.1 Prototype state
Three-board Perma-Proto prototype, **Phase 0 closed 2026-06-29** (single-device live loop, laptop hub): Board A "Brain" (XIAO ESP32-S3 Sense; 14 I²C sensors via PCA9548A mux @400 kHz; OV5640 camera; USB-CDC telemetry; SD), Board B "Muscle" (no MCU; MT3608 boost 5.09 V + Pololu 3.38 V + motor MOSFETs), Board C "Sentry" (XIAO nRF52840; Geiger, MPR121 touch on own I²C, haptic, NeoPixel, battery monitor; UART relay to A with CRC8 framing). Definitive pinmaps: interrogator `PLAN.md §2.4–2.6`. **Warning: `archive/legacy_docs/{master_topology,fabrication_netlist}.md` are deprecated and conflict with the live pinmap — never use them as PCB input.**

### 2.2 Sensor set (the 16 registered types, `shared/schemas/sensors/*.yaml`)

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

### 2.3 The upstream gate this plan must close — interrogator issue #7
Exit KPIs (verbatim anchors): full local e2e loop **re-validated on PCB**; **binary IDL (ADR-0004) live with text debug mode**; **diagnostics suite re-run on a PCB capture with no regression vs the breadboard baseline** (golden-CI #37 makes this checkable); **PLAN §7.10 latency budget still met**. Cloud phases (1+) start only after this gate. These four KPIs are the *definition of done* for the v1 board (§7, phase H6).

### 2.4 Pre-scoped electrical architecture (PLAN §7.5.3.18 — research-backed upstream, adopted here)
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

### 5.1 Consolidation
**One main PCB** replacing Boards A+B+C, carrying both MCU domains: **ESP32-S3 module** (brain: sensors, camera, USB, WiFi) + **nRF52840 module** (sentry: Geiger, touch, haptics, NeoPixel, battery monitor, BLE, power gating — preserves the ~5 mA sentinel mode and the existing firmware split). UART link becomes PCB traces with the existing CRC8 framing. *(Decision D2 confirms or rejects the two-MCU consolidation.)*

### 5.2 Buses
Per §2.4: SPI+DMA (VL53L8CX, BNO085) with INT lines; I²C-A and I²C-B (small mux for spectral chain only); UART (GNSS if needed, inter-MCU); calculated pull-up budget per segment; per-segment load switches for fault isolation and power gating. Reserve: one spare I²C header-accessible segment + spare GPIO/INT bank for future sensors (R6 headroom).

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

### 5.7 Modularity mechanism (R6)
v1 modularity = **contract-driven regeneration + frozen chassis interface**: (a) board outline, mounting bosses, connector positions, and the aperture plate geometry are frozen after H5; (b) sensor churn re-enters at H2 with the pipeline regenerating schematic/layout deltas inside the frozen envelope; (c) the aperture plate (the one part that must physically change when an exposed sensor changes) is a cheap, replaceable, separately-versioned part. Physical plug-in sensor modules (mezzanine/flex) are a v2 study item (D6) — they cost density, which is the primary v1 constraint.

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
| **H0 — Foundations** (~1–2 wk) | Repo scaffold (this PR); toolchain pin (KiCad 10.0.x, kicad-cli CI container); submodule/pin mechanism to `interrogator`; LFS; stage-1 contract-ingest script; **draft USR-3 electrical resolution packets** for all 16 sensors (PR-ready for upstream); kick D1–D6 decision spikes | CI green on empty board; ingest script emits the IO map from pinned records; resolution packets delivered upstream |
| **H1 — Architecture lock** (~2–3 wk) | MCU selection spike (D1/D2); bus topology finalized from §2.4; power tree + **power budget table vs R3**; block diagram; layer stack (6 vs 8) + fab capability freeze (D3); battery/cell choice (D4) | Owner ratifies architecture doc + budget; upstream electrical facets `approved` for v1 sensors |
| **H2 — Schematic** (~2–4 wk) | Library build with AssetPins (all 16 sensors + MCUs + power, verified footprints); full schematic; ERC clean; LLM review packet; atopile spike verdict (D5) | ERC = 0; human review sign-off; BOM 100 % sourced (LCSC/stock) |
| **H3 — Layout** (~3–5 wk) | Floorplan per §5.5; placement review; critical-net hand routing; Freerouting pass on grunt nets; DRC clean; thermal/EMI review; STEP export | DRC = 0 vs JLCPCB 6/8-layer rules; SI/thermal review sign-off; board envelope frozen → chassis interface freeze |
| **H4 — Fab + bring-up** (~4–6 wk incl. lead time) | JLCPCB fab + PCBA (SMT where catalog allows, hand-finish rest); bring-up plan mirroring upstream diagnostics (per-bus smoke → per-sensor conformance → all-sensor coherence F-04 → soak R-02); deviation log continues here | Board powers, all buses enumerate, every sensor streams conformant records |
| **H5 — Chassis v0** (parallel from H3 freeze) | FreeCAD enclosure from STEP; aperture plate; fan path; contact window; light pipes; 3D-printed shells; drop/fit iteration | Assembled device; thermal chimney verified; apertures validated per exposure class |
| **H6 — PCB Gate closure** | With upstream: binary IDL live (+text debug), diagnostics re-run vs breadboard golden baseline, §7.10 latency check, e2e re-validation | **interrogator #7 KPIs all green** → v1 done; v2 planning opens (I3C, gap-register sensors, miniaturization) |

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
| Two-MCU consolidation complexity | D2 spike; fallback = v1 keeps ESP32-S3-only board + Board-C-as-daughter |
| Regulatory exposure (UV, laser, skin contact, health claims) | Wellness-only posture (upstream SEM-5); class-1 laser unchanged; UV interlock; materials choice at H5 |
| Upstream contract churn mid-design | Pinned SHA + CI drift tripwire; bumps only at phase boundaries |

## 9. Open decisions (owner/SME calls — proposed defaults)

| # | Decision | Proposed default |
|---|---|---|
| D1 | v1 MCU | **ESP32-S3 (WROOM module)** — firmware continuity, 2×SPI/2×I²C suffices for §2.4 topology; RT1170/ESP32-P4/STM32H7 re-evaluated for v2 |
| D2 | One PCB with both MCUs vs S3-only | **Both** (S3 + nRF52840 modules) — preserves sentinel mode + BLE + firmware split |
| D3 | Fab/process | **JLCPCB, 6-layer through-via + POFV via-in-pad**; escalate to 8-layer not to microvia |
| D4 | Battery | Size cell to the H1 budget (likely 2500–3500 mAh Li-ion pouch) vs relaxing R3 — needs the budget table first |
| D5 | Schematic-as-code (atopile) | **Spike only** in H2; KiCad capture is the baseline |
| D6 | Physical sensor-module system (mezzanine/flex) | **Defer to v2 study**; v1 modularity = §5.7 |
| D7 | Camera on v1 | **Yes** (OV5640 via FPC connector, S3 DVP) — matches upstream stream contract |
| D8 | UV LED | Swap 400 nm → **365 nm** (biofluorescence, per upstream PLAN §9) with eye-safety interlock |
| D9 | Fluidics | **Chassis provision only** in v1 (port + volume + connector reservation) |

## 10. Proposed Project 3 structure (created only after this plan is ratified)

Epics = H0–H6 + two cross-cutting tracks (W-PWR power budget; W-PIPE pipeline/CI). Each epic gets issues matching the phase deliverables above, with fields: Phase, Status, Blocked-by (cross-repo deps flagged), Evidence (link to ADR/artifact). The sensory-gap register drives the v2 backlog column.

---
*Sources: interrogator repo (read-only) — PLAN.md §2, §5–7, §10, §13; docs/architecture/{0013,unified-sensor-registry*,board-acceptance-criteria,capability-coverage,system-architecture}.md; docs/build/{deviation_log,board_a_*,phase-0-build-scope,interboard_harness}.md; shared/schemas/{sensors/*,sensor_specs.yaml}; issue #7. Tooling research: see docs/draft-review.md §3 for full source list.*
