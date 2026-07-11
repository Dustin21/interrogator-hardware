# Interrogator Hardware — Build Plan

**Status: v0.2 DRAFT — incorporates owner review of 2026-07-11.**
Owner: Dustin21 · Repo: `interrogator-hardware` · Tracker: [Project 3](https://github.com/users/Dustin21/projects/3) (populated after ratification)

This plan merges the owner's brief ("Closed-Loop AI EDA Pipeline for Ultra-Dense Interrogator Device"), the owner's v0.1 review comments, a read-only review of the `interrogator` repo, and July-2026 AI-EDA tooling research. The v0.1 audit trail lives in [`docs/draft-review.md`](docs/draft-review.md).

---

## 0. Mission

Build the **iPhone of the sensor world**: a sleek, minimalist, handheld multi-modal sensing device — a *scientist in your pocket* — whose hardware works cohesively and reliably for years, competes with top technology companies, and is patentable. Not hobby tech.

The device is, conceptually, a **sensor MCP**: add a sensor and the system's raw streams and interrogation capabilities expand — the agent immediately knows more about reality. The hardware's job is to make that expansion cheap (fast respins, stable chassis) and the signal path pristine.

**Target markets (owner, 2026-07-11)** — near-term reachable, many out of the box: home & consumer · building & facilities · health & wellness · public safety · environmental · industrial & resources · agriculture & food · transportation · government & defense. One hardware platform, many intent catalogs: the H1 sensor market scan (§5.7) scores parts by *cross-vertical* information yield, and the SKU levers (DNP variants, feature gating §5.10) let one board family serve B2C and B2B without forking the design.

**P0 — Signal fidelity first.** Whatever we add, the signal of reality stays optimized and unencumbered. The device's success is measured by how accurately, sensitively, and at what range a handheld can extract information and fuse it into decisions. Every enclosure material, aperture, window, filter, gasket, keepout, and power rail is designed *from the sensing physics inward* — nothing may attenuate, distort, heat, or vibrate a signal path for the sake of convenience or cosmetics. When aesthetics and signal conflict, we engineer until they don't; signal wins any remaining tie.

### 0.1 Design stance — commercial hardware, clean sheet, silicon-on-merit

This is the **commercial device, designed from scratch to the spec (§1)**. Solder-down silicon on our own board — **no breakout boards, no dev modules, no muxes-as-crutches, no protoboard heritage**. "Chip-down" means *chosen on engineering merit per channel*, which includes **smart sensors with integrated, vendor-validated processing** where that wins:

- **BNO085 stays** — Bosch MEMS + CEVA SH-2 fusion on an embedded core. Years of vendor tuning and out-of-the-box validation (a regulatory asset, R10) for the everyday orientation utility. Configured to stream **raw accel/gyro/mag alongside the fused outputs** — the upstream **ADR-0014 "raw plus processed" posture**: raw substrate for discovery, fused outputs for utility, without us owning fusion.
- The same merit test applies everywhere: integrated front-end (PPG AFEs, gas sensors with on-chip DSP) vs bare transducer is decided per channel on signal quality, validation burden, power, and cost — not ideology.

Pre-certified modules are used only where that is the commercially correct choice (radio certification, GNSS antenna performance).

**The interrogator repo's role is narrow:** it supplies the sensor-truth contract (USR facets + AssetPins + device profile) and the data/command *semantics* — and **interrogator adapts to this design**. Firmware (new MCU port, binary IDL, INT-driven acquisition, OTA) is upstream work against the interface-requirements doc we publish. The prototype hardware is **not a design input** (§2.1); this design owns its own research (§2.4).

### 0.2 What "modular" means here (owner clarification)

Modularity is **the speed at which we can create and ship a new device revision** when the sensor set changes — not field-upgradability of already-shipped units. A gap-filling sensor is highlighted → we turn the board around and ship ASAP: same chassis interface where possible, regenerated board, downstream ingest (§3.3, §6.3). Shipped units evolve via firmware/OTA only.

## 1. Requirements (owner spec, v0.2-reconciled)

| # | Requirement | Engineering reconciliation |
|---|---|---|
| R1 | Many orthogonal solid-state sensors (15 now → 100+ future) | v1 from the candidate set (§2.2), **revised owner list incoming — the §6.3 change flow exists precisely so this lands cheaply**. Growth path: parallel buses + I3C dynamic addressing + reserved expansion segment. |
| R2 | **All parts** 3+ years without replacement — the concept fails if a fan or pump dies | Two-layer answer: (a) **part selection first** — long-life bearing-technology blowers/pumps (50k+ h class MTTF at our duty cycle ≫ 3 y), derated drive, filtered intake path, condensation control; solid-state everything else; (b) serviceable sub-assembly as *fallback*, not excuse. Reliability budget (MTBF rollup) is an H1 deliverable per part incl. actuators. |
| R3 | Battery: optimize toward **8 h ambient**; not set in stone — deep dives/multi-turn draw more; **must not explode size/feasibility; 5 h floor triggers owner review** | Two-mode budget: ambient (sentinel + duty-cycled acquisition) vs interrogation (deep-dive bursts). W-PWR delivers a measured table; cell sized to the smallest package meeting the ambient target; if physics forces <8 h at acceptable size, present the trade to owner at H1. |
| R4 | As small as feasible; **iPhone-grade industrial design**; chassis is constructed around the achieved envelope; **never compromise modularity for size** | Size = output of §5.8 boundary optimization. Chassis wraps the envelope **plus deliberate buffer (§5.8–5.9)** so respins don't churn it. Design language: minimalist shell, hidden apertures, subtle glow/haptics (§5.6). |
| R5 | Pocket-safe: heat, battery, emitters | Thermal zoning from sensing physics (§5.5); battery system to IEC 62133-class expectations; laser class 1; UV interlock (§5.10). |
| R6 | Modular per §0.2 — respin speed | Contract-driven regeneration (§6.3) + frozen-with-buffer chassis interface (§5.9). Target: **sensor-swap respin ≤2 human-days touch time by v2** (§6.6 drives it toward near-zero HITL). |
| R7 | Parallel raw streaming in ambient state; **AI layer controls prioritization/deep-dives**; no sweep bottleneck | **Hard requirement — the prototype's mux sweep is the anti-pattern.** True per-bus parallel acquisition, INT/DMA-driven, with the §5.2b concurrency & interference model: what runs together is governed by intent + a machine-readable compatibility matrix, not by wiring. |
| R8 | Exposure classes: contact / air-entry / liquid-entry / internal | §5.6. **Air path: yes in v1** (fan-driven). **Microfluidics: NOT populated in v1, but buffered** — reserved port, internal volume, connector allowance inside the frozen chassis interface, so adding it later is a respin, not a chassis redesign. |
| R9 | Right medium → right sensor; interaction effects minimized in hardware, then AI optimizes around the rest | Zoning + isolation (§5.5) + the interference matrix (§5.2b) exported as a contract artifact so the AI scheduler can avoid masking interactions. |
| R10 | Regulated posture: wellness-only claims until validated; prefer parts with regulatory-friendly validation | Vendor-validated smart sensors favored where claims matter (BNO085 pattern); W-CERT track (§5.10); upstream SEM-5 alignment. |
| R11 | MCU syncs+streams all comfortably; on-device AI very helpful | §5.1 reference architecture: NPU-class application MCU + always-on sentinel. |
| R12 | Sensor change → regenerate ship-ready state in few cycles | Ratified flow (§3.3/§6.3): **decided here → PCB+device approved → firmware+interrogator ingest and update.** In place before the revised sensor list lands. |
| R13 | **Unit economics (new):** shippable with reasonable margin, B2B + B2C | BOM cost is a first-class, tracked property of every revision: live-priced interactive BOM (LCSC/Octopart), cost column in the sensor matrix (§5.7), cost gates at H1 (architecture) and H2 (BOM freeze); DFM choices (§5.10) made with CM quoting in mind. |
| R14 | **Wireless-first + lifecycle (new):** syncs to a mobile device/app (WebRTC-class); fast charging; regular OTA updates, security fixes, feature gating | §5.1 connectivity (BLE control + Wi-Fi high-bandwidth), §5.4 USB-C PD fast charge, §5.10 secure boot + A/B OTA + hardware crypto identity enabling future feature gates/paywalls. |

## 2. Evidence base (context only — **not design inputs**)

### 2.1 Prototype
A three-board breadboard prototype exists upstream and closed its Phase 0 loop. **We do not consider what has been built** — this project has free rein to drive device hardware that competes with top technology companies and is patentable. The prototype's only exports to us are: the contract artifacts (§3), the sensing use-cases it validated, and the interrogation/alert flow it proved end-to-end (§3.5).

### 2.2 Sensor candidate set (baseline — owner's revised list incoming; every line re-sourced as solder-down silicon, §5.7)

| Capability | Baseline part | Class | Exposure |
|---|---|---|---|
| Gas/VOC/T/RH/P | BME688 | env | air |
| VOC/NOx | SGP41 | env | air |
| PM2.5 | BMV080 | env | air window |
| Thermal imaging 8×8 | AMG8833 | optical | IR window |
| PPG HR/SpO₂ | MAX30102EFD | bio | contact window |
| ToF depth 8×8 | VL53L8CX | optical | window (940 nm) |
| Visible spectral 14-ch | AS7343 | optical | window + LED |
| UV A/B/C | AS7331 | optical | direct/quartz aperture |
| NIR spectral | AS7263 | optical | window + NIR LED |
| IMU 9-DoF (fused+raw) | BNO085 | motion | internal |
| 3D magnetics | TMAG5273 | field | internal |
| Precision analog (RF power, piezo) | ADS1115 (re-eval) | field | internal + probes |
| 60 GHz radar | Acconeer A121 (raw AiP) | spatial | radome |
| GNSS | antenna-integrated module (MIA/NEO class) | location | sky window |
| Touch | MPR121 or MCU-native | contact | shell electrodes |
| Radiation β/γ | BG51-class solid-state | field | internal (thin window) |
| Camera (D7) | raw sensor + FPC | optical | aperture |

### 2.3 Integration checkpoint — interrogator #7 (joint milestone, later)
E2e re-validated on the new device · binary IDL live (+text debug) · diagnostics no-regression · latency budget. The firmware side is upstream's work against our interface doc.

### 2.4 Upstream's prior PCB research — historical input only
Interrogator's PLAN §7.5.3.18 (per-bus concurrency, SPI+DMA for high-rate parts, PPS-disciplined timestamping, I3C direction) is available evidence, **outdated by its own admission and superseded by our H1 research. We own the architecture; we are free to change all of it and likely will.**

### 2.5 Bench observations — physics checklist candidates only
The prototype bench logs contain *some* items that reflect physics/protocol reality rather than breadboard circumstance (I²C single-slave-wedges-bus failure mode; address-collision classes; pull-up/rise-time budgets; thermal cross-talk between hot parts and env sensors; EMI from actuators into counters/analog; sensor libraries that init but read garbage). These enter the H2/H3 review **checklists** as candidates — each is re-derived from datasheets and first principles for *our* topology, never applied as inherited rules.

## 3. Contract boundary & flows

1. **USR is the system's sensor-truth spine** (per-type records: identity/electrical/mechanical facets + AssetPins; per-instance device profile). This repo consumes it **pinned** (submodule/pinned SHA), never forked.
2. **We bind read-only** to `electrical`, `mechanical`, `assets`; the v1 device profile is instantiated from this design.
3. **Ratified change flow (2026-07-10): hardware originates, interrogator ingests.** Sensor change **decided here** → pipeline regenerates the board/device rev → **owner approves** → the approved delta ships downstream as an **ingest package** (USR record drafts, facets with datasheet citations, AssetPins, interface-requirements delta) → **firmware + interrogator repo ingest and update**, backend stacks on top. Single-writer preserved: we produce PR-ready packages; the owner lands them upstream.
4. **Asset storage (owner decision): no Git LFS.** Heavy artifacts (footprints, 3D, gerbers, renders) live **locally in the repo working tree for now**, referenced by `{asset_id, version, sha256}` in a checked-in manifest; **migration target: AWS S3** (assets addressed by `object_key` = S3 key + sha256 — exactly the USR `assets` schema, which was designed for an object store). Recommendation: agree with AWS; use standard S3 + versioned buckets, keep the access layer S3-API-generic (boto-compatible), which preserves the upstream no-lock-in posture at zero extra cost and makes any later move (or a Cloudflare R2 egress-cost hedge) a config change. CI verifies checksums either way.
5. **Cadence separation:** our CI = ERC/DRC/asset-checksum/fab-diff; upstream CI = pytest/contract.
6. **The interrogate-reality flow extends to this device — by construction.** What the prototype proved (ambient stream → detection/intent → active-sensing commands → deep-dive → alert to operator) binds at the *semantics* level (record schema, §3.5 command surface, intent catalog), which is exactly what we consume. The new hardware implements the physical layer of that loop better than the prototype could: per-domain power/clock gating = "AI decides what runs"; INT-driven parallel acquisition = real-time granularity; sentinel domain = always-on detection; glow zones + haptics = the alert surface; touch = the invocation surface. The interface-requirements doc (H1) maps each §3.5 command class onto this hardware so upstream's agent/alert stack ports without semantic change.

## 4. 2026 tooling verdict (unchanged from v0.1 — detail in [`docs/draft-review.md`](docs/draft-review.md))

6–8-layer through-via + POFV via-in-pad at JLCPCB-class fabs (no blind/buried vias there; Freerouting can't route them anyway and has zero SI awareness — grunt nets only, `-inc`-protected, benchmarked v2.2.4 vs v1.9). KiCad 10 + `kicad-cli` (ERC/DRC JSON + exit codes, jobsets) is the headless loop; the IPC API is GUI-bound until KiCad 11; KiCad MCP servers are demo-grade (rjwalters/kicad-tools the most serious). Verified footprint sources (easyeda2kicad/SnapMagic/UL) + human overlay check; LLMs as second readers, never footprint authors. Optional candidate generators: Quilter free program, DeepPCB trial. MCAD: kicad-cli STEP + FreeCAD/StepUp.

## 5. Target v1 architecture

### 5.1 Compute + connectivity — reference architecture (H1 validates on eval kits)

**Two-domain, one board** — burst compute vs always-on vigilance are opposite power regimes; two domains also *implement* R7's "AI decides what runs" as physical power domains.

- **Application domain — STM32N6-class** (Cortex-M55 ~800 MHz + Neural-ART NPU, MIPI-CSI ISP, USB-HS, I²C/I3C/SPI+DMA fabric, input-capture timers). On-device AI headroom (R11), native I3C growth path (R1), camera as stuff-option (D7). Fallbacks: i.MX RT1170 (widest bus fabric), ESP32-P4 (cost-down).
- **Sentinel domain — pre-certified BLE module, nRF54L15-class**, always-on at µA–mA: touch wake, radiation counting, fuel gauge, haptics/glow, RTC, power sequencing, secure-boot root + device identity (R14 feature gates), BLE control plane.
- **High-bandwidth radio — pre-certified Wi-Fi module (R14):** the device syncs wirelessly to a mobile app; deep-dive streams (multi-sensor raw + camera bursts, ~0.1–1 MB/s class) exceed sensible BLE throughput. Architecture: **BLE = control/ambient telemetry; Wi-Fi (station or P2P/direct) = interrogation streams**, carrying a WebRTC-class transport terminated by firmware/app (transport protocol is upstream's choice; we budget the bandwidth, power, and antenna keepouts). Wi-Fi module is power-gated by the sentinel — zero cost in ambient mode. H1 decides one-module (combo BLE+Wi-Fi) vs two; combo (e.g., current u-blox/Murata class) is preferred if its BLE low-power floor meets the sentinel budget, else nRF54 + gated Wi-Fi.

### 5.2 Buses
High-rate sensors on SPI+DMA with INT lines; remaining I²C/I3C split across ≥2 controllers; address collisions solved by bus assignment/straps (no monolithic mux); calculated pull-up budgets; **per-segment load switches** (fault isolation + power gating). Reserved expansion segment (bus + power + INT) for R1 growth.

### 5.2b Concurrency & interference model (R7/R9 — new, first-class)
The prototype's serial sweep degraded granularity and frequency; that bottleneck is designed out, but **"everything always parallel" is not the goal either** — it's *orchestrated* concurrency:

- **Hardware guarantee:** every sensor domain can stream simultaneously at its native rate (per-bus concurrency, DMA, FIFO watermarks, hardware-timestamped INTs). No sensor waits on another's transaction.
- **Interference matrix (contract artifact):** a machine-readable matrix of physical incompatibilities and couplings — optical emitters (UV/white/NIR LEDs, ToF 940 nm, PPG LEDs) vs spectral/optical receivers; actuators (fan/pump/haptic) vs IMU/piezo/radiation counting; Wi-Fi bursts vs RF-power measurement and GNSS; charger switching vs precision analog. Shipped in the ingest package so the **AI scheduler avoids masking interactions by construction** (and can deliberately exploit them, e.g., active illumination).
- **Activation classes:** always-ambient (env, IMU, sentinel) · triggered (touch-activated contact reads; presence-gated radar deep dives) · intent-driven (spectral scans w/ illumination, camera, max-rate multi-sensor fusion) · gated-off (mutually exclusive pairs per the matrix, arbitrated by firmware policy).
- Data-quality flags (emitters/actuators/radio active) ride every record so downstream fusion can weight confidence — semantics carried over from the upstream contract.

### 5.3 Timing
GNSS-PPS-disciplined input-capture timestamping; per-sensor INT latching in hardware; one canonical monotonic→UTC mapping per the wire contract. Cross-sensor skew budget defined at H1 and *measured* at H4.

### 5.4 Power (+ fast charging, R14)
Li-ion pouch (sized by W-PWR) → **USB-C PD fast-charge path**: PD sink controller + charger sized for ~1C+ charge with thermal supervision (charge thermals must not cook env sensors — zoning §5.5; fast charge only when sensing idle or thermally headroomed), fuel gauge, protection. High-efficiency bucks per domain (no heavy LDOs); per-segment load switches; battery lockout; per-domain current-shunt test points so the R3 budget is **measured**.

### 5.5 Floorplan zoning — from sensing physics inward (P0)
Quiet optical/analog nose (spectral, ToF, thermal IR, PPG AFE, camera) · compute midsection · "dirty" tail (actuator drivers, charger, Wi-Fi PA, battery). Gas cluster at intake with thermal moat; exhaust over compute; IR imager isolated from board heat; magnetics/radiation away from motors and switching; GNSS + Wi-Fi antennas with modeled keepouts; partitioned analog grounds; charger/PD switching isolated from precision channels. Every rule derives from a named signal path, not from prototype folklore.

### 5.6 Exposure classes → chassis features (the owner's sketches, engineered)
Contact field (PPG window + touch electrode zones: "touch it and it extracts") · air path (micro-fan channel: intake over gas/PM, exhaust over compute — the only visible holes) · liquid provision (buffered port + volume, v1 unpopulated, R8) · optical apertures (ToF, thermal, spectral trio, camera, emitters; UV-C-transparent window for AS7331) · radar radome (behind shell) · GNSS sky window · **feedback surface: per-zone light pipes ("twinkling stars" = sensors active/amplified) + haptics** · everything else invisible under the monolithic shell (R4 design language).

### 5.7 Sensor BOM — solder-down silicon on merit; alternatives scan mandated
Baseline = §2.2. **H1 runs a per-channel market scan** — the owner expects alternatives to be researched seriously, e.g. **ScioSense ENS161-class** parts vs BME688/SGP41 for the gas stack (noting channel shape differs: BME688 = gas+T/RH/P, ENS16x = TVOC/eCO₂ DSP outputs, SGP41 = raw VOC/NOx — the scan scores *information yield for the interrogation mission*, not spec-sheet vanity), higher-res thermal arrays vs AMG8833, current regulated-grade PPG AFEs vs MAX30102EFD, radiation detector alternatives vs BG51. Scan dimensions: **orthogonal information yield · sensitivity/range · raw-stream access (ADR-0014: raw + processed both available wherever the part allows) · vendor validation/regulatory posture · power · package · unit cost at 1k/10k (R13) · supply longevity**. Output: a scored matrix + recommended v1 BOM for owner sign-off; the owner's incoming revised list merges here via the §6.3 flow.

### 5.8 Dynamic boundary co-optimization → **chassis built with buffer**
Board floor = courtyards + tuned clearance multiplier; grow layers before XY (0.5 mm steps). The *chassis* is then constructed around the achieved envelope **plus explicit buffer** (owner-confirmed): reserved XY/Z margin, spare aperture blanks in the plate, the liquid port/volume (R8), and the expansion segment's reach — so future board revs land inside the same shell whenever physically possible. Envelope + buffer export as STEP and define the industrial design.

### 5.9 Modularity mechanism (R6/§0.2)
Frozen-with-buffer chassis interface (outline, bosses, connectors, aperture-plate geometry) + contract-driven regeneration. The aperture plate is the cheap, separately-versioned part that absorbs exposed-sensor changes. Respin speed is the KPI; §6.6 is the engine that drives HITL toward the minimum.

### 5.10 Commercial-grade (DFM/DFT · certification · lifecycle · IP)
- **Certification (W-CERT):** FCC 15B/CE-EMC/ISED plan from H1, pre-scan at H4; intentional radiators inside pre-certified modules; laser class 1; IEC 62471 UV interlock; battery IEC 62133-class; RoHS/REACH BOM.
- **DFM/DFT:** designed to the target fab/assembly class; test points on every rail/bus; per-domain current shunts; SWD/tag-connect; DNP options (camera, Wi-Fi variant) so one layout serves multiple SKUs; panelization + fiducials; **CM-quotable data from day one (R13)**.
- **Lifecycle (R14):** secure boot rooted in the sentinel's crypto/KeyStore; **A/B (dual-slot) OTA** for regular firmware/security updates; signed images; per-unit identity/serialization at production programming; hardware hooks for **feature gating** (entitlements enforced in firmware, future paywalls/security limits) — shipped units evolve by software (§0.2).
- **Reliability (R2):** MTBF rollup incl. actuators; long-life blower/pump selection + derating + intake filtration; connectors and flex rated for service life.
- **IP posture:** the design rationale log doubles as an **invention-capture log** — novel mechanisms (aperture-plate modularity, interference-matrix-driven orchestration, sentinel-gated sensing domains, contract-driven respin pipeline) get flagged as patent candidates at each phase gate.

## 6. The design pipeline (closed-loop, human-gated, learning)

### 6.1 Stages & artifacts
1. **Contract ingest** — pinned USR + device profile → IO map, bus/address plan, netlist skeleton.
2. **Library** — verified symbol/footprint/3D per part (easyeda2kicad → SnapMagic/UL → last-resort generation), AssetPin recorded (local now → S3), human overlay-check promotes E0→E1.
3. **Schematic** — KiCad 10 multi-sheet capture; LLM second-reader review (addresses, pull-ups, straps, INT completeness, decoupling) against `registry_assets` datasheets.
4. **ERC/DRC loop** — `kicad-cli` JSON + exit codes in CI; agent proposes diffs; human merges.
5. **Placement** — human-owned per §5.5 zoning encoded as keepouts; optional Quilter/DeepPCB candidates for comparison.
6. **Routing** — critical nets by hand (USB-HS, PD, crystals, SPI, PPS, PPG/analog, antenna feeds); Freerouting `-inc` for grunt nets; SI review.
7. **Outputs — yes to all four review artifacts (owner Q):** (a) **native KiCad project** (multi-sheet schematic + fully routed layout); (b) **interactive BOM cross-referenced to live inventory/pricing** (LCSC/Octopart — also feeds R13 cost gates); (c) **design rationale log** (ADRs: routing/layer/thermal choices + invention capture); (d) **the 3D structure for human review at every phase**: `kicad-cli` STEP + raytraced board renders (`pcb render`) at H2/H3, and at H3-freeze a **grounded prototype visual** — board envelope + chassis concept (FreeCAD/StepUp model, rendered) — for the owner and product teams to iterate the industrial design on facts, not sketches (owner-requested deliverable).
8. **MCAD co-design** — STEP ↔ FreeCAD enclosure, collision/aperture checks, 3D-printed shells at H5.

### 6.2 Trust boundaries
Automated & trusted: contract ingest, BOM/pricing, ERC/DRC loops, fab packaging, STEP/render export, checksums. AI-assisted + human gate: schematic review, placement candidates, fix diffs, datasheet cross-checks. Human-only: footprint E1 promotion, critical routing, fab release, safety (battery/laser/UV), phase gates.

### 6.3 Regeneration = the ratified change flow
Sensor change **decided here** → stages 1–2 regenerate the delta → 3–7 replay inside the frozen envelope → **owner approves board/device rev** → ingest package ships downstream → **firmware + interrogator update**, backend stacks on top.

### 6.4 CI
ERC/DRC · asset-checksum manifest (local now, S3 later — same manifest) · contract-pin drift tripwire · fab-output regeneration diff · release tags with full provenance (contract SHA + asset checksums + toolchain versions).

### 6.5 Learning loop — HIL data → less HITL each cycle (owner Q)
Answering "how do we capture HIL data to optimize the whole e2e over time": every human intervention and every physical measurement becomes **machine-readable pipeline input for the next cycle**:
- **Capture:** bring-up/diagnostics runs (conformance reports, skew/power/thermal measurements, EMC pre-scan results), every DRC/ERC violation + its fix diff, every hand-routing constraint, every footprint correction, every deviation — all logged as structured artifacts keyed to *(design SHA, AssetPins, part, rule)*.
- **Compound:** validated fixes graduate into **rules-as-code** — DRC rule files, keepout/zone templates, pull-up calculators, net-class definitions, placement affinity hints, the interference matrix — versioned in this repo. The pipeline's stage 1–4 automation consumes them; nothing is re-learned twice.
- **Converge:** v1 is human-heavy by design (first traversal writes the rulebook). By construction, a v2 sensor swap replays stages 1–7 against an accumulated rulebook where the only *novel* work is the delta sensor's physics — so HITL collapses toward: approve the BOM, eyeball the placement diff, sign the fab release. That is the near-automation the owner is targeting, and the golden-capture discipline upstream (diagnostics baselines) gives the objective no-regression check each time.

### 6.6 Manufacturing handoff (the ultimate goal: ship the design to a company that builds it)
The terminal artifact is a **CM-ready manufacturing data package**: gerbers + ODB++/IPC-2581, drill, stackup + impedance spec, BOM with AVL (approved vendor list + LCSC/DigiKey/Mouser alternates), CPL, assembly drawings, paneling, test specification (bed-of-nails/flying-probe points + functional bring-up script), programming/provisioning procedure, and the DFM report. Prototypes: JLCPCB-class. Production: package quoted to contract manufacturers (procurement optional per CM). H6 exits with this package released.

## 7. Phases

| Phase | Content | Exit |
|---|---|---|
| **H0 — Foundations** | Repo scaffold; toolchain pin (KiCad 10.0.x CI); contract pin mechanism; asset manifest (local, S3-ready); ingest script v0; USR-3 resolution packets drafted | CI green; ingest emits IO map |
| **H1 — Architecture validation** | Eval-kit spikes (§5.1 compute + radio); **per-channel sensor market scan (§5.7)** merged with owner's revised list; interference matrix v0; bus topology; power tree + **two-mode budget vs R3**; reliability (MTBF) rollup incl. actuators (R2); **BOM cost model v0 (R13)**; cert plan v0; layer stack + fab class; **interface-requirements doc → upstream** | Owner ratifies architecture + v1 BOM + budgets (power/cost) |
| **H2 — Schematic** | Verified library w/ AssetPins; multi-sheet schematic; ERC=0; LLM review packet; live-priced iBOM v0; board renders | Owner design review sign-off; BOM 100 % sourced + costed |
| **H3 — Layout** | Zoned floorplan; critical hand-routing; Freerouting grunt pass; DRC=0; SI/thermal review; **envelope freeze → STEP + grounded prototype visual (board + chassis concept) for product iteration** | Envelope + visual ratified; chassis interface frozen (with buffer) |
| **H4 — Fab + bring-up** | JLCPCB-class proto fab/assembly; structured bring-up (per-bus → per-sensor → all-parallel coherence → soak); **measured** power/skew/thermal; EMC pre-scan; HIL capture per §6.5 | Device streams all channels in parallel, conformant; measurements logged |
| **H5 — Chassis v0** | FreeCAD enclosure from frozen envelope+buffer; aperture plate; air path; contact/glow surfaces; 3D-printed shells; fit/thermal iteration with product teams (using the H3 visual) | Assembled device validated per exposure class |
| **H6 — Sign-off + handoff** | (a) R1–R14 scorecard vs built device; (b) joint #7 integration (upstream firmware); (c) **CM manufacturing package (§6.6) released** | v1 done; v2 loop opens (owner's new sensor list → §6.3 flow) |

Cross-cutting: **W-PWR** (power budget), **W-PIPE** (pipeline/CI/rules-as-code), **W-CERT** (compliance).

## 8. Risks
| Risk | Mitigation |
|---|---|
| Power: ambient target vs size (R3 explicitly flexible, floor 5 h) | Two-mode budget; sentinel-first architecture; owner trade review at H1 |
| Actuator longevity breaks R2 | Long-life part selection + derating + filtration; MTBF rollup; serviceable fallback path |
| Footprint/pinout error | Verified-library-first + AssetPins + human overlay + LLM second reader |
| Freerouting v2.x quality regression | Hand-route critical; `-inc`; benchmark vs v1.9; full hand-route fallback |
| New-silicon risk (N6-class, sensor successors) | H1 eval gate; named fallbacks; DNP-friendly layout |
| EMC failure (dense mixed-signal + 60 GHz + emitters + Wi-Fi) | Physics-first zoning; pre-certified radios; H4 pre-scan + respin allowance |
| Interference matrix incomplete → masked signals in field | Matrix seeded from datasheets at H1, *measured* at H4 (pairwise activation tests), shipped as versioned contract artifact |
| BOM cost misses margin (R13) | Live-priced iBOM + cost gates at H1/H2; alternates in AVL |
| Wi-Fi power breaks ambient budget | Wi-Fi hard-gated by sentinel; BLE-only ambient; measured duty costs |
| Upstream contract churn | Pinned SHA + drift tripwire; bumps at phase boundaries |

## 9. Open decisions (proposed defaults)
| # | Decision | Proposed |
|---|---|---|
| D1 | Application MCU | STM32N6-class; fallbacks RT1170 / ESP32-P4 (H1 gate) |
| D2 | Compute pattern | Two-domain: app MCU + pre-certified sentinel/BLE module |
| D3 | Fab class | JLCPCB 6-layer through-via + POFV; 8-layer before microvia; CM re-quote at production |
| D4 | Cell | Sized by H1 two-mode budget; fast-charge 1C+ capable (R14) |
| D5 | Schematic-as-code (atopile) | Spike only; KiCad capture baseline |
| D6 | Mezzanine/flex sensor modules | v2 study; v1 = §5.9 |
| D7 | Camera | Conditional on achieved envelope (phone-attachable → no camera); interface designed in, DNP decides |
| D8 | UV emitter | 365 nm + IEC 62471 interlock |
| D9 | Fluidics | Buffered provision only in v1 (R8) |
| D10 | Asset object store | **AWS S3** (versioned bucket, S3-generic access layer); local manifest until H1 |
| D11 | Radio topology | Combo BLE+Wi-Fi module if its LP floor meets sentinel budget, else nRF54-class + gated Wi-Fi module (H1) |
| D12 | Gas stack composition | BME688 vs ENS161-class vs SGP41 mix — settled by the H1 market-scan matrix on information yield + cost |

## 10. Project 3 structure (on owner go)
Epics H0–H6 + W-PWR/W-PIPE/W-CERT; issues per phase deliverable with Phase/Status/Blocked-by/Evidence fields; v2 backlog column fed by the gap register + owner's market feedback.

---
*v0.2 changelog (owner review 2026-07-11): silicon-on-merit incl. BNO085 raw+fused (ADR-0014); interrogate/alert flow continuity §3.6; concurrency & interference model §5.2b; R2 extended to actuators; R3 made flexible (5 h floor); chassis buffer confirmed §5.8; R13 unit economics; R14 wireless-first + fast charge + OTA/feature gates; Git LFS dropped → local + AWS S3 (D10); sensor market scan mandated §5.7 (ENS161 example, D12); §2.4/2.5 demoted to historical/checklist; sensor-MCP mission framing; learning loop §6.5; CM handoff §6.6; grounded prototype visual committed at H3.*
