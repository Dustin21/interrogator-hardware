"""H2 stage-1 verification gate: netlist, ERC, library manifest coverage."""

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
NETLIST = REPO / "boards" / "v1" / "netlist" / "interrogator_v1.net"
MANIFEST = REPO / "library" / "manifest.json"
COMPONENTS = REPO / "boards" / "v1" / "components.json"
CIRCUIT = REPO / "boards" / "v1" / "circuit"

# Major refdes that must appear in the netlist (one per architectural block)
MAJOR_REFS = [
    "U_N657", "U_NOR", "U_BL54", "U_C6",
    "U_VL53", "U_BNO", "U_ADS", "U_A121",
    "U_MLX42", "U_MLX32", "U_MAX", "U_AS7058",
    "U_BME", "U_SGP", "U_ENS", "U_SCD", "U_SHT", "U_TCS",
    "U_AS7331", "U_AS7421", "U_MMC", "U_TMAG", "U_BMV",
    "U_GNSS", "MK1", "U_CO", "U_COAFE", "D_PIN", "U_CHAMP", "U_CMP",
    "U_PD", "U_CHG", "U_GAUGE", "U_PROT",
    "U_AON", "U_CORE", "U_SYS3V3", "U_1V8",
    "U_SW_OPTICAL", "U_SW_AIR", "U_SW_CONTACT", "U_SW_RADAR",
    "U_SW_GNSS", "U_SW_WIFI", "U_SW_ACC",
    # H3.0 adds: gated 1V8 sub-rail switches + level translators + HSE xtal
    "U_SW1V8_OPTICAL", "U_SW1V8_RADAR", "U_SW1V8_AIR",
    "U_LS_VL53", "U_XLAT_TCS", "X_HSE",
    "U_TOUCH", "U_HAP", "U_RF", "U_ILK",
    "J_USB", "J_BATT", "J_POGO", "J_CAM", "J_RF", "J_FAN",
    "J_SWD_N6", "J_SWD_BL",
]

# Nets that encode the architecture contract
MAJOR_NETS = [
    "VSYS", "VBAT", "3V3_AON", "3V3_SYS", "VDD_CORE_N6", "1V8",
    "3V3_OPTICAL", "3V3_AIR", "3V3_CONTACT", "3V3_RADAR", "3V3_GNSS", "3V3_WIFI",
    "SPI1_SCK", "I2CA_SDA", "I2CB_SDA", "SENT_SDA", "SDIO_CLK",
    "GNSS_PPS", "GEIGER_PULSE", "INTERLOCK_OK", "EN_N6", "EN_OPTICAL",
    # H3.0: gated 1.8V sub-rails + translated 1.8V bus segments
    "1V8_OPTICAL", "1V8_RADAR", "1V8_AIR", "I2CA_SDA_1V8", "VL53_MISO_1V8",
]


def test_netlist_exists_and_parses():
    assert NETLIST.exists(), "netlist not generated — run boards/v1/circuit/main.py"
    text = NETLIST.read_text()
    assert text.lstrip().startswith("(export"), "not a KiCad netlist"
    # S-expression sanity: balanced parens outside quoted strings
    depth = 0
    in_str = False
    prev = ""
    for ch in text:
        if ch == '"' and prev != "\\":
            in_str = not in_str
        elif not in_str:
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                assert depth >= 0, "unbalanced parens"
        prev = ch
    assert depth == 0, "unbalanced parens at EOF"
    for ref in MAJOR_REFS:
        assert f'(ref "{ref}")' in text, f"missing refdes {ref}"
    for net in MAJOR_NETS:
        assert f'"{net}"' in text, f"missing net {net}"


def test_manifest_covers_every_component():
    manifest = json.loads(MANIFEST.read_text())
    components = json.loads(COMPONENTS.read_text())
    covered = {p["components_json_name"] for p in manifest["parts"]}
    missing = [c["name"] for c in components if c["name"] not in covered]
    assert not missing, f"manifest missing components.json parts: {missing}"
    # every entry is honest about provenance
    for p in manifest["parts"]:
        assert p["symbol_source"] in ("skidl-custom", "espressif",
                                      "kicad-official", "kicad-official (Device lib)")
        assert p["footprint_source"], p["part"]
        if p["footprint_source"] in ("kicad-official", "espressif"):
            assert p["footprint_file"], f"{p['part']}: harvested but no file listed"
            first = p["footprint_file"].split(",")[0].strip()
            assert (REPO / "library" / "footprints" / first).exists(), \
                f"{p['part']}: listed footprint file not harvested: {first}"


def test_circuit_erc_clean():
    """main.py exits 0 iff ERC errors == 0 and the netlist was written."""
    r = subprocess.run([sys.executable, "main.py"], cwd=CIRCUIT,
                       capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, f"circuit build/ERC failed:\n{r.stdout[-2000:]}\n{r.stderr[-2000:]}"
    assert "erc_errors=0" in r.stdout


# ===========================================================================
# H2 stage-2 gates: footprint coverage 38/38, bean outline, board file
# ===========================================================================

GENERATED = REPO / "library" / "footprints" / "generated"
OUTLINE = REPO / "boards" / "v1" / "outline.json"
BOARD = REPO / "boards" / "v1" / "board" / "interrogator_v1.kicad_pcb"
DRC = REPO / "boards" / "v1" / "board" / "drc_baseline.json"


def test_manifest_coverage_55_of_55_no_to_generate():
    # 38 at H2 stage-2; 41 since H3.1 (crystal + H3.0 translators); 55 since
    # H3.2 (the 14 mechanical/connector parts got packed floorplan slots —
    # zero-overlap placement surfaced that they had none).
    m = json.loads(MANIFEST.read_text())
    cov = m["coverage"]
    assert cov["components_json_parts"] == 55
    assert cov["footprint_to_generate"] == 0, "TO-GENERATE parts remain"
    # H2.5: generated footprints may be promoted E0 -> E1 once the real
    # vendor land pattern has been overlaid; both still count as generated.
    assert (cov["footprint_harvested"] + cov["footprint_generated_E0"]
            + cov.get("footprint_generated_E1", 0)) == 55
    for p in m["parts"]:
        assert "TO-GENERATE" not in p["footprint_source"], p["part"]
        assert p["footprint_source"] in ("kicad-official", "espressif",
                                         "generated-E0", "generated-E1"), p["part"]


def test_every_footprint_file_exists():
    m = json.loads(MANIFEST.read_text())
    lib = REPO / "library" / "footprints"
    for p in m["parts"] + m["supporting_parts"]:
        ff = p.get("footprint_file")
        if not ff or ".kicad_mod" not in ff:
            continue
        for f in [s.strip() for s in ff.split(",") if ".kicad_mod" in s]:
            assert (lib / f).exists(), f"{p['part']}: missing {f}"


def test_generated_footprints_carry_e0_header():
    files = sorted(GENERATED.glob("*.kicad_mod"))
    assert len(files) >= 16, "expected the stage-2 generated footprint set"
    for f in files:
        head = f.read_text()[:1200]
        assert "overlay-verify" in head, f"{f.name}: no overlay-verify header"


def test_outline_is_valid_closed_bean():
    o = json.loads(OUTLINE.read_text())
    pts = o["points_mm"]
    assert len(pts) >= 64
    assert pts[0] != pts[-1], "polygon should not duplicate the closing point"
    # shoelace area, closed implicitly
    area = 0.0
    for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]):
        area += x1 * y2 - x2 * y1
    area = abs(area) / 2
    assert 1500 <= area <= 2600, f"bean area {area:.0f} mm^2 out of sanity range"
    assert abs(area - o["area_mm2"]) < 5


def test_board_file_loads_shape():
    assert BOARD.exists(), "run boards/v1/board/build_board.py"
    text = BOARD.read_text()
    assert '(layer "Edge.Cuts")' in text, "no board outline on Edge.Cuts"
    n_fp = text.count("(footprint ")
    assert n_fp >= 30, f"only {n_fp} footprint blocks"
    # bean outline is drawn as >=64 edge segments
    assert text.count('(layer "Edge.Cuts")') >= 64
    # DRC baseline was captured
    d = json.loads(DRC.read_text())
    assert d["counts"]["Footprint errors"] == 0
    assert d["counts"]["unconnected pads"] > 0, "baseline should predate routing"
