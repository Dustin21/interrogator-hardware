#!/usr/bin/env python3
"""H3.3b — critical nets, routed by rule (runs on the H3.3a board state).

Order and rules:
 1. Radiation front-end (RAD_IN/RAD_VREF/RAD_VTH/PIN_BIAS) — confined to
    the shield-can interior region (region mask); RAD_ANALOG + GEIGER_PULSE
    leave the can and route normally.
 2. LMP91000 <-> SGX kelvin star (CO_WE/CO_RE/CO_CE, 0.2mm) + CO_VREF;
    CO_AFE_OUT routed early on a quiet board + guard-audited afterwards
    (no foreign track within 0.3mm on its layers along the run).
 3. USB_HS 90R pair: USB_DP reference, USB_DM shadow-routed with a
    distance-field attraction to the DP path; matched to +/-0.15mm.
 4. CSI pairs (CKP/CKN, D0P/D0N, D1P/D1N) — same method, 0.11mm.
 5. XSPI NOR bus (11 nets) on the B.Cu/In4 layer pair, then length-matched
    to a <=1mm spread with square-wave meanders (boot-critical bus).
 6. SDIO group, I2C-A/B + 1.8V segment, SPI1 + CS fabric, VL53 1.8V branch,
    UART/GNSS links, EN/interlock fabric.

Everything is emitted through the shared Router engine (0.1mm grid rules:
0.1/0.11 clearance, via 0.2/0.4, no copper in keep-outs, In2/In3 vias-only).
Run: python3 boards/v1/board/route_critical.py
"""
import json
import math
import time

import numpy as np
import pcbnew
from shapely.geometry import LineString, Point

import route_lib as RL
import route_router as RR
from route_router import Router, RES, NX, NY, LIDX, LAYERS

B, IN4, F, IN1 = RL.B, RL.IN4, RL.F, RL.IN1


def net_of(board, name):
    n = board.FindNet(name)
    return n.GetNetCode() if n else None


def track_len(board, netcode):
    tot = 0.0
    nvia = 0
    for t in board.GetTracks():
        if t.GetNetCode() != netcode:
            continue
        if t.GetClass() == "PCB_VIA":
            nvia += 1
        else:
            tot += RL.tomm(int(t.GetLength()))
    return tot, nvia


def attract_field(path_cells, weight=0.25, reach=2.0):
    """Penalty array: 0 on the reference path, growing with distance."""
    from scipy.ndimage import distance_transform_edt
    m = np.ones((NX, NY), bool)
    for _, i, j in path_cells:
        m[i, j] = False
    d = distance_transform_edt(m) * RES
    d = np.minimum(d, reach)
    return (d * weight).astype(np.float32)


def route_pair(r, board, pname, nname, width, results):
    """Route P; route N attracted to P; return (lenP, lenN)."""
    pn, nn = net_of(board, pname), net_of(board, nname)
    saved_path = []
    orig_emit = r.emit

    def capture_emit(net, path, width=None):
        saved_path.extend(path)
        return orig_emit(net, path, width=width)
    r.emit = capture_emit
    dp = r.route_net(pn, width=width, window=10.0,
                     fine=(width <= 0.10))
    r.emit = orig_emit
    # N-half: restrict the search to a corridor around the P path (fast +
    # guarantees pair proximity); mild attraction inside the corridor;
    # unrestricted fallback if the corridor is blocked.
    dm = (0, 1, 0, 0)
    if saved_path:
        from scipy.ndimage import binary_dilation, distance_transform_edt
        m = np.zeros((NX, NY), bool)
        for _, i, j in saved_path:
            m[i, j] = True
        corridor = binary_dilation(m, iterations=int(2.5 / RES))
        dfield = np.minimum(distance_transform_edt(~m) * RES, 1.2) * 0.12

        def attr(x, y):
            return float(dfield[min(NX - 1, int(x / RES)),
                                min(NY - 1, int(y / RES))])
        dm = r.route_net(nn, width=width, window=10.0, region=corridor,
                         attract=attr, fine=(width <= 0.10))
    if dm[1]:
        dm2 = r.route_net(nn, width=width, window=10.0, fine=(width <= 0.10))
        dm = (dm[0] + dm2[0], dm2[1], dm[2] + dm2[2], dm[3] + dm2[3])
    lp, vp = track_len(board, pn)
    ln, vn = track_len(board, nn)
    # intra-pair match to +/-0.15mm: meander the shorter half
    delta = lp - ln
    if abs(delta) > 0.15 and lp > 0 and ln > 0:
        short_net, need = (nn, delta) if delta > 0 else (pn, -delta)
        add_meander(r, board, short_net, need, width=width)
        lp, vp = track_len(board, pn)
        ln, vn = track_len(board, nn)
    results[f"{pname}/{nname}"] = dict(p_mm=round(lp, 2), n_mm=round(ln, 2),
                                       delta_mm=round(lp - ln, 3),
                                       vias=[vp, vn],
                                       failed=dp[1] + dm[1])
    return lp, ln


def add_meander(r, board, netcode, extra, width=0.10):
    """Lengthen a net by ~extra mm with a square-wave on its longest
    straight segment. Returns added length (0.0 if no legal meander)."""
    segs = [t for t in board.GetTracks()
            if t.GetNetCode() == netcode and t.GetClass() != "PCB_VIA"]
    segs.sort(key=lambda t: -t.GetLength())
    for seg in segs:
        L = RL.tomm(int(seg.GetLength()))
        if L < 1.2:
            continue
        x1, y1 = RL.tomm(seg.GetStart().x), RL.tomm(seg.GetStart().y)
        x2, y2 = RL.tomm(seg.GetEnd().x), RL.tomm(seg.GetEnd().y)
        li = LIDX[seg.GetLayer()]
        ux, uy = (x2 - x1) / L, (y2 - y1) / L
        px, py = -uy, ux
        # try amplitudes / bump counts
        for amp in (0.6, 0.45, 0.3):
            span = L - 0.6
            n = max(1, min(int(span / (4 * RES * 3)), int(math.ceil(extra / (2 * amp)))))
            pitch = span / n
            if pitch < 0.6:
                n = max(1, int(span / 0.6))
                pitch = span / n
            add = n * 2 * amp
            if add < extra * 0.5:
                continue
            # build square wave points
            pts = [(x1, y1)]
            s = 0.3
            sgn = 1
            for k in range(n):
                a0 = (x1 + ux * (s + k * pitch), y1 + uy * (s + k * pitch))
                a1 = (a0[0] + px * amp * sgn, a0[1] + py * amp * sgn)
                a2 = (a1[0] + ux * pitch * 0.8, a1[1] + uy * pitch * 0.8)
                a3 = (a2[0] - px * amp * sgn, a2[1] - py * amp * sgn)
                pts += [a0, a1, a2, a3]
                sgn = -sgn
            pts.append((x2, y2))
            # legality: rasterize each sub-seg, cells must be FREE or net
            ok = True
            for a, b_ in zip(pts, pts[1:]):
                line = LineString([a, b_]).buffer(width / 2 + 0.11, resolution=8)
                bb = line.bounds
                i0, i1 = max(0, int(bb[0] / RES)), min(NX - 1, int(bb[2] / RES) + 1)
                j0, j1 = max(0, int(bb[1] / RES)), min(NY - 1, int(bb[3] / RES) + 1)
                sub = r.g.owner[li][i0:i1 + 1, j0:j1 + 1]
                if not np.all((sub == RR.FREE) | (sub == netcode)):
                    # allow cells belonging to the original segment itself
                    ok = False
                    break
            if not ok:
                continue
            # apply: remove seg, add polyline
            board.Remove(seg)
            actual = -L
            for a, b_ in zip(pts, pts[1:]):
                if a == b_:
                    continue
                RL.add_track(board, a[0], a[1], b_[0], b_[1],
                             LAYERS[li], netcode, width)
                geom = LineString([a, b_]).buffer(width / 2)
                r.g.paint_copper(geom, netcode, [LAYERS[li]],
                                 r.clearance + width / 2, r.clearance + 0.22)
                actual += math.hypot(b_[0] - a[0], b_[1] - a[1])
            return actual
    return 0.0


def main():
    t0 = time.time()
    board = RL.load()
    r = Router(board)
    r.build_fine_mask()          # dru 0.09/0.09 inside via-in-pad courtyards
    print(f"harvest {time.time() - t0:.0f}s; unconnected edges: "
          f"{r.unconnected_count()}")
    results = {"pairs": {}, "buses": {}, "notes": []}

    # ---- 0. XSPI bus FIRST (boot-critical, BGA-locked, needs the clean
    # inner-layer channels) — B.Cu/In4 preference, fallback any layer -------
    # col-14 (landlocked) balls first, then col-15
    xspi = ["XSPI_CS_N", "XSPI_D2", "XSPI_D5", "XSPI_D6", "XSPI_D7",
            "XSPI_DQS", "XSPI_CLK", "XSPI_D0", "XSPI_D1", "XSPI_D3", "XSPI_D4"]
    for name in xspi:
        n = net_of(board, name)
        d, f, ln, nv = r.route_net(n, layers=[B, IN4], window=8.0,
                                   fine=True, width=0.09)
        if f:
            d, f, ln, nv = r.route_net(n, window=8.0, fine=True, width=0.09)
        print(f"  xspi {name}: +{d} fail {f} len {ln:.1f}")

    # ---- 4. CSI pairs -------------------------------------------------------
    for p, n in (("CSI_CKP", "CSI_CKN"), ("CSI_D0P", "CSI_D0N"),
                 ("CSI_D1P", "CSI_D1N")):
        route_pair(r, board, p, n, 0.10, results["pairs"])
    # ---- 2. CO kelvin star + guarded VOUT ---------------------------------
    for name, w in (("CO_WE", 0.2), ("CO_RE", 0.2), ("CO_CE", 0.2),
                    ("CO_VREF", 0.15), ("CO_AFE_OUT", 0.12)):
        n = net_of(board, name)
        d, f, ln, nv = r.route_net(n, width=w, window=8.0)
        print(f"  kelvin {name}: +{d} fail {f} len {ln:.1f} vias {nv}")
    # guard audit for CO_AFE_OUT happens at H3.3d (drc + proximity scan)

    # ---- 1. radiation front-end. PLACEMENT NOTE (H4 flag): the anchor
    # placer put the comparator + threshold divider OUTSIDE the shield can
    # (only the charge-amp loop is inside) — confinement is therefore only
    # auditable, not enforceable; routed unconstrained + audited at H3.3d.
    for name in ("RAD_IN", "RAD_VREF", "RAD_VTH", "PIN_BIAS",
                 "RAD_ANALOG", "GEIGER_PULSE", "SHIELD_RAD"):
        n = net_of(board, name)
        d, f, ln, nv = r.route_net(n, window=8.0)
        print(f"  rad {name}: +{d} fail {f} len {ln:.1f}")

    # ---- 2b. clocks early (crystals + ADC clock get short corridors) -------
    for name in ("N6_OSC_IN", "N6_OSC_OUT", "A121_XIN", "A121_XOUT", "CLK_ADS"):
        n = net_of(board, name)
        d, f, ln, nv = r.route_net(n, window=8.0, fine=True, width=0.09)
        print(f"  clk {name}: +{d} fail {f} len {ln:.1f} vias {nv}")

    # ---- 3. USB HS pair -----------------------------------------------------
    route_pair(r, board, "USB_DP", "USB_DM", 0.13, results["pairs"])
    print("  pairs:", json.dumps(results["pairs"]))

    # ---- 5. XSPI length match to <=1mm spread ------------------------------
    lens = {name: track_len(board, net_of(board, name))[0] for name in xspi}
    print("  xspi pre-match:", {k: round(v, 2) for k, v in lens.items()})
    target = max(lens.values())
    for name in xspi:
        need = target - lens[name]
        if need > 1.0:
            got = add_meander(r, board, net_of(board, name), need - 0.4)
            lens[name] += got
    spread = max(lens.values()) - min(lens.values())
    results["buses"]["XSPI"] = {k: round(v, 2) for k, v in lens.items()}
    results["buses"]["XSPI_spread_mm"] = round(spread, 2)
    print(f"  xspi post-match spread: {spread:.2f}mm")

    # ---- 6. SDIO / I2C / SPI1 / UART / EN fabric ---------------------------
    groups = {
        "SDIO": ["SDIO_CLK", "SDIO_CMD", "SDIO_D0", "SDIO_D1", "SDIO_D2", "SDIO_D3"],
        "I2C": ["I2CA_SDA", "I2CA_SCL", "I2CB_SDA", "I2CB_SCL",
                "SENT_SDA", "SENT_SCL", "I2CA_SDA_1V8", "I2CA_SCL_1V8",
                "BNO_ENV_SCL", "BNO_ENV_SDA"],
        "SPI1": ["SPI1_SCK", "SPI1_MISO", "SPI1_MOSI",
                 "CS_VL53_N", "CS_BNO_N", "CS_ADS_N", "CS_A121_N",
                 "VL53_SCLK_1V8", "VL53_MOSI_1V8", "VL53_NCS_1V8",
                 "VL53_MISO_1V8", "VL53_SPI_SEL", "VL53_GPIO2",
                 "LPN_VL53", "INT_VL53"],
        "UART": ["GNSS_TX", "GNSS_RX", "GNSS_PPS", "IMCU_N6_TX", "IMCU_N6_RX",
                 "C6_TXD0", "C6_RXD0", "C6_BOOT", "C6_EN"],
        "EN": ["EN_OPTICAL", "EN_AIR", "EN_CONTACT", "EN_RADAR", "EN_GNSS",
               "EN_WIFI", "EN_N6", "EN_FAN", "EN_ACC", "EN_HAPTIC",
               "INTERLOCK_OK", "WAKE_N6", "ATTN_N6", "EN_UV_REQ", "EN_WHITE",
               "UV_GATE", "N6_PWR_ON", "N6_VCORE_SEL"],
        "CLK": ["PDM_CLK", "PDM_DATA"],
        "RF": ["GNSS_RF", "RF_IN", "RF_DET_OUT"],
        "CAM": ["CAM_XCLK", "CAM_RSTN"],
    }
    stats = {}
    for gname, names in groups.items():
        gd = gf = 0
        gl = 0.0
        for name in names:
            n = net_of(board, name)
            if n is None:
                continue
            if gname == "RF":
                d, f, ln, nv = r.route_net(n, width=0.3, window=8.0)
            else:
                d, f, ln, nv = r.route_net(n, width=0.09, window=8.0, fine=True)
            gd += d
            gf += f
            gl += ln
        stats[gname] = (gd, gf, round(gl, 1))
        print(f"  group {gname}: +{gd} fail {gf} len {gl:.0f}mm")
    results["buses"]["groups"] = stats

    print(f"unconnected edges after H3.3b: {r.unconnected_count()}")
    results["unconnected_after"] = r.unconnected_count()
    failed = getattr(r, "failed_edges", [])
    results["failed_edges"] = sorted({n for _, n in failed})
    print("failed nets:", results["failed_edges"])

    RL.save(board)
    (RL.HERE / "route_h33b.json").write_text(json.dumps(results, indent=1))
    print(f"saved ({time.time() - t0:.0f}s total)")


if __name__ == "__main__":
    main()
