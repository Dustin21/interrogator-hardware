# interrogator-hardware

**Proprietary & Confidential — © 2026 Dustin. All Rights Reserved.**

Hardware design repo for the [Reality Interrogator](https://github.com/Dustin21/interrogator): the custom PCB(s), enclosure/chassis, footprint & 3D asset library, fabrication packages, and the contract-driven design pipeline that regenerates them when the sensor set changes.

> Status: **planning — v0.1 plan under owner review.** See [`PLAN.md`](PLAN.md) (the build plan) and [`docs/draft-review.md`](docs/draft-review.md) (audit of the original brief vs the interrogator repo + 2026 tooling research).

## Relationship to `interrogator` (the contract)

- The **Unified Sensor Registry** (`interrogator: shared/schemas/sensors/*.yaml`, ADR-0013) is the single source of truth for per-sensor identity/electrical/mechanical facts and versioned asset pins. This repo **consumes it at a pinned SHA — never forks or edits it**.
- This repo binds read-only to the `electrical` + `mechanical` facets and `assets` pins; per-instance placement binds to the device profile view.
- Findings that should change upstream facts are delivered as **resolution packets** (PR-ready proposals); the owner applies them upstream. Single-writer discipline is preserved.
- Heavy binaries (footprints, 3D models, gerbers, renders) live **here via Git LFS**, referenced by `{asset_id, version, sha256}` — the same AssetPin discipline as datasheets.
- This repo's CI = ERC/DRC (`kicad-cli`), asset-checksum, and contract-pin drift checks. Upstream CI (pytest/contract) is untouched.

## Definition of done for the v1 board

The upstream **PCB Gate — [interrogator#7](https://github.com/Dustin21/interrogator/issues/7)**: e2e loop re-validated on PCB · binary IDL live with text debug mode · diagnostics re-run with no regression vs the breadboard golden baseline · PLAN §7.10 latency budget met.

## Layout (will grow per PLAN.md §7 phases)

| Path | Contents |
|---|---|
| `PLAN.md` | The hardware build plan (source of truth for this repo). |
| `docs/draft-review.md` | Audit: original brief vs interrogator repo + July-2026 EDA tooling research. |
| `docs/decisions/` | Lightweight ADRs — the design rationale log. *(to come)* |
| `contract/` | Pinned upstream registry consumption + ingest scripts. *(to come, H0)* |
| `library/` | Verified symbols/footprints/3D with AssetPins (LFS). *(to come, H2)* |
| `boards/v1/` | KiCad project, fab packages, bring-up docs. *(to come, H2+)* |
| `enclosure/` | FreeCAD/STEP chassis, aperture plate. *(to come, H5)* |

## Toolchain (pinned at H0)

KiCad 10.0.x (`kicad-cli` for ERC/DRC/exports + jobsets) · easyeda2kicad / SnapMagic / Ultra Librarian for verified footprints · Freerouting 2.2.x (grunt nets only, `-inc`-protected) · kicad-jlcpcb-tools for fab packages · FreeCAD + StepUp for MCAD co-design. Trust boundaries in [`PLAN.md`](PLAN.md) §6.2.
