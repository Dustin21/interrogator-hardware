#!/usr/bin/env python3
"""H3.3c — grunt routing sweep (runs on the H3.3b board state).

Every net that still has >1 connectivity cluster gets routed, shortest
cluster-gap first (Freerouting was tried once and is proxy-blocked for this
session — documented in H3_REPORT — so this is the deterministic A* from
route_router.py). PWR-class nets route at 0.25mm with a 0.15mm fallback;
everything else at 0.09mm with the fine-mode dru rules active inside the
via-in-pad courtyards. Clusters that consist solely of AS7058 / MMC5983MA
pads are excluded (PROVISIONAL-E0 ball maps — do-not-route stands).

Two sweeps: window 8 then window 14 with a bigger node budget for the
survivors. Run: python3 boards/v1/board/route_all.py
"""
import json
import time

import route_lib as RL
from route_router import Router

PWR_NETS_PREFIX = ("GND", "VSYS", "VBAT", "VBUS_C", "PACKP", "CELL_N",
                   "PROT_MID", "VACC", "VDD_CORE_N6", "3V3_", "1V8")


def is_pwr(name):
    return any(name == p or name.startswith(p) for p in PWR_NETS_PREFIX)


def main():
    t0 = time.time()
    board = RL.load()
    r = Router(board)
    r.build_fine_mask()
    r.exclude_refs = ("U_AS7058", "U_MMC")
    print(f"harvest {time.time() - t0:.0f}s; unconnected edges (incl "
          f"do-not-route): {r.unconnected_count()}")

    def todo():
        jobs = []
        for net in list(r.items):
            cls = r.clusters(net)
            if len(cls) <= 1:
                continue
            gap = 1e9
            for a in range(len(cls)):
                for b in range(a + 1, len(cls)):
                    d = min(g1.distance(g2) for _, g1, _ in cls[a]
                            for _, g2, _ in cls[b])
                    gap = min(gap, d)
            jobs.append((gap, net))
        jobs.sort()
        return jobs

    for sweep, (win, grow, budget) in enumerate(((8.0, 2, 350000),)):
        jobs = todo()
        print(f"sweep {sweep}: {len(jobs)} nets with open edges")
        done = fail = 0
        for k, (gap, net) in enumerate(jobs):
            name = r.netname.get(net, "?")
            if is_pwr(name):
                d, f, ln, nv = r.route_net(net, width=0.25, window=win,
                                           max_grow=grow, max_nodes=budget)
                if f:
                    d2, f2, ln2, nv2 = r.route_net(net, width=0.15,
                                                   window=win, max_grow=grow,
                                                   max_nodes=budget)
                    d, f = d + d2, f2
            else:
                d, f, ln, nv = r.route_net(net, width=0.09, window=win,
                                           fine=True, max_grow=grow,
                                           max_nodes=budget)
            done += d
            fail += f
            print(f"  [{k+1}/{len(jobs)}] {name}: +{d} fail {f} "
                  f"({time.time() - t0:.0f}s)")
        print(f"  sweep {sweep}: +{done} connected, {fail} still failing "
              f"({time.time() - t0:.0f}s)")

    rest = r.unconnected_count()
    print(f"unconnected edges after H3.3c (incl do-not-route clusters "
          f"excluded from routing but counted): {rest}")
    failed = sorted({n for _, n in getattr(r, "failed_edges", [])})
    print("failing nets:", failed)
    RL.save(board)
    (RL.HERE / "route_h33c.json").write_text(json.dumps(
        {"unconnected_after": rest, "failed_nets": failed}, indent=1))
    print(f"saved ({time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main()
