# ERC waivers & annotations — interrogator v1.1 stage-1

Final ERC result: **0 errors / 0 warnings** (`python3 main.py`, SKiDL 2.2.3).
Three findings were resolved by *drive annotations* rather than topology
changes; they are recorded here because they suppress a class of check.

| # | Net | Annotation | Justification |
|---|-----|-----------|---------------|
| W1 | `PROT_VDD` | `drive = POWER` | BQ29700 VDD is fed from VBAT through the DS-mandated 330R/100nF RC filter; ERC cannot see through the resistor. Electrically it is the cell supply. |
| W2 | `CELL_N` | `drive = POWER` | This net IS the battery cell's negative terminal (protection FETs sit between it and pack GND, per BQ297xx low-side topology). |
| W3 | `GNSS_VBCKP` | `drive = POWER` | MIA-M10Q V_BCKP is fed from 3V3_AON through D_BCKP (BAT54); ERC cannot see through the diode. |
| W4 | `VBAT` | `drive = POWER` | H2.5 update: VBAT is now the SYSTEM-side battery node, fed from `PACKP` (the cell + terminal) through the BQ27427's internal 7 mΩ high-side sense resistor (SLUSEB5B p3); ERC cannot see through the gauge. `PACKP` carries the cell drive. |

Rail nets driven through buck L/C output stages (`3V3_AON`, `3V3_SYS`,
`VDD_CORE_N6`, `1V8`) and source nets (`GND`, `VBUS_C`, `VBAT`) also carry
`drive = POWER` — standard practice for regulator outputs modeled with real
SW→L→rail passives (ERC has no netlist-level concept of a buck output).

Netlist-generation notes (not ERC):
- SKiDL emits per-part "Missing tag / Random tag" INFO-class warnings (~665)
  because we do not assign hierarchical tags; harmless for netlist import.
- 0 netlist-generation errors; every part carries a footprint field
  (`TO_GENERATE:*` placeholders are deliberate — see library/manifest.json).
