#!/usr/bin/env python3
"""interrogator v1.1 — top-level circuit build (H2 stage-1).

Wires the full electrical design, runs ERC, and generates the KiCad netlist at
boards/v1/netlist/interrogator_v1.net.  Exit code 0 iff ERC reports 0 errors
and the netlist was written.  Waived warnings are documented in WAIVERS.md.

Run:  cd boards/v1/circuit && python3 main.py
"""

import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

# KiCad-official symbol libraries (Ubuntu-packaged KiCad 7.0.11)
os.environ.setdefault("KICAD7_SYMBOL_DIR", "/usr/share/kicad/symbols")

from skidl import ERC, generate_netlist, set_default_tool, KICAD7  # noqa: E402
import skidl  # noqa: E402

set_default_tool(KICAD7)

from power import build_power              # noqa: E402
from compute import build_compute          # noqa: E402
from sensors_spi import build_sensors_spi  # noqa: E402
from sensors_i2c import build_sensors_i2c  # noqa: E402
from sensors_misc import build_sensors_misc  # noqa: E402
from accessory import build_accessory      # noqa: E402


def main():
    build_power()
    build_compute()
    build_sensors_spi()
    build_sensors_i2c()
    build_sensors_misc()
    build_accessory()

    ERC()
    erc_errors = skidl.erc_logger.error.count
    erc_warnings = skidl.erc_logger.warning.count

    out = HERE.parent / "netlist" / "interrogator_v1.net"
    out.parent.mkdir(parents=True, exist_ok=True)
    generate_netlist(file_=str(out))
    gen_errors = skidl.logger.active_logger.error.count if hasattr(
        skidl.logger, "active_logger") else 0

    n_parts = len(default_circuit.parts)  # default_circuit is a skidl builtin
    n_nets = len(default_circuit.get_nets())
    print(f"parts={n_parts} nets={n_nets} "
          f"erc_errors={erc_errors} erc_warnings={erc_warnings}")
    print(f"netlist: {out} ({out.stat().st_size} bytes)")

    if erc_errors:
        print("FAIL: ERC errors present", file=sys.stderr)
        return 1
    if not out.exists() or out.stat().st_size < 1000:
        print("FAIL: netlist missing/too small", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
