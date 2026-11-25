import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bridge
from opt_helper import eval_design, save_submission


def make_l5_catenary(n_pit=5, sag_pit=0.7, n_riv=10, sag_riv=1.8, add_cables=False):
    """Pure sagging road (catenary) across both the 11m pit (-11..0) and 24m river (0..24)."""
    nodes = []
    members = []

    # Pit: A2=(-11,0) to A0=(0,0)
    pit_nodes = []
    for i in range(1, n_pit):
        t = i / n_pit
        x = -11.0 + 11.0 * t
        y = -4.0 * sag_pit * t * (1.0 - t)
        idx = len(nodes)
        nodes.append([round(x, 3), round(y, 3)])
        pit_nodes.append(idx)
    for i in range(n_pit):
        u = "A2" if i == 0 else pit_nodes[i - 1]
        v = "A0" if i == n_pit - 1 else pit_nodes[i]
        members.append([u, v, "road"])

    # River: A0=(0,0) to A7=(24,0)
    riv_nodes = []
    for i in range(1, n_riv):
        t = i / n_riv
        x = 24.0 * t
        y = -4.0 * sag_riv * t * (1.0 - t)
        idx = len(nodes)
        nodes.append([round(x, 3), round(y, 3)])
        riv_nodes.append(idx)
    for i in range(n_riv):
        u = "A0" if i == 0 else riv_nodes[i - 1]
        v = "A7" if i == n_riv - 1 else riv_nodes[i]
        members.append([u, v, "road"])

    if add_cables:
        # Parallel cables from A0 and A7 to midspan of river
        mid = riv_nodes[len(riv_nodes) // 2]
        members.append(["A0", mid, "cable"])
        members.append(["A7", mid, "cable"])

    return {"nodes": nodes, "members": members}


if __name__ == "__main__":
    best = None
    for sag_pit in [0.5, 0.8, 1.1]:
        for sag_riv in [1.5, 2.0, 2.5, 3.0]:
            for add_cables in [False, True]:
                d = make_l5_catenary(n_pit=5, sag_pit=sag_pit, n_riv=10, sag_riv=sag_riv, add_cables=add_cables)
                ok, cost, stress, msg = eval_design(5, d)
                if ok:
                    print(f"L5 PASS sp={sag_pit} sr={sag_riv} cab={add_cables} cost={cost:.1f} stress={stress:.2f}")
                    if best is None or cost < best[0]:
                        best = (cost, d)
                else:
                    print(f"L5 FAIL sp={sag_pit} sr={sag_riv} cab={add_cables} cost={cost:.1f} stress={stress:.2f} {msg}")
    if best:
        save_submission("level5.json", best[1])
        print(f"Saved best level5.json with cost {best[0]:.1f}")
