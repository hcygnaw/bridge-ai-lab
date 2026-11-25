import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bridge
from opt_helper import eval_design, save_submission
from solve_l2_l3_v3 import auto_upgrade_to_pass


def make_l2_cable_stayed(n_seg=13, tower_h=8.0, use_bottom_truss=False, bot_y=-1.6):
    """Pure cable-stayed bridge for Level 2 (0..30).
    A0=(0,0), A1=(0,-4), A2=(0,-8), A3=(-6,0), A4=(30,0), A5=(30,-4), A6=(30,-8), A7=(36,0).
    """
    nodes = []
    members = []
    dx = 30.0 / n_seg
    # Deck nodes 0..n_seg-2
    for i in range(1, n_seg):
        nodes.append([round(i * dx, 3), 0.0])
    for i in range(n_seg):
        u = "A0" if i == 0 else i - 1
        v = "A4" if i == n_seg - 1 else i
        members.append([u, v, "road"])

    # Braced towers at x=0 and x=30 (2 segments of tower_h/2, with backstay to A3/A7)
    tl1 = len(nodes); nodes.append([0.0, round(tower_h / 2, 3)])
    tl2 = len(nodes); nodes.append([0.0, round(tower_h, 3)])
    tr1 = len(nodes); nodes.append([30.0, round(tower_h / 2, 3)])
    tr2 = len(nodes); nodes.append([30.0, round(tower_h, 3)])

    members.append(["A0", tl1, "steel"])
    members.append([tl1, tl2, "steel"])
    members.append(["A3", tl1, "steel"])
    members.append(["A3", tl2, "cable"])

    members.append(["A4", tr1, "steel"])
    members.append([tr1, tr2, "steel"])
    members.append(["A7", tr1, "steel"])
    members.append(["A7", tr2, "cable"])

    # Cables from tower tops to every deck node
    mid = (n_seg - 1) // 2
    for i in range(n_seg - 1):
        if i <= mid:
            members.append([tl2, i, "cable"])
        if i >= mid:
            members.append([tr2, i, "cable"])

    return {"nodes": nodes, "members": members}


def make_l2_arch(n_seg=13, arch_mid=-2.0, arch_end=-4.0, al="A1", ar="A5"):
    """Under-deck arch with steel/wood web for Level 2."""
    nodes = []
    members = []
    dx = 30.0 / n_seg
    for i in range(1, n_seg):
        nodes.append([round(i * dx, 3), 0.0])
    for i in range(n_seg):
        u = "A0" if i == 0 else i - 1
        v = "A4" if i == n_seg - 1 else i
        members.append([u, v, "road"])

    # Arch nodes at x = i*dx for i=1..n_seg-1
    arch_start = len(nodes)
    for i in range(1, n_seg):
        x = i * dx
        t = x / 30.0
        y = arch_end + (arch_mid - arch_end) * 4.0 * t * (1.0 - t)
        nodes.append([round(x, 3), round(y, 3)])

    def add_m(u, v, pref="wood"):
        # Compute length to pick wood if <= 2.95 else steel
        def pos(idx):
            if isinstance(idx, str):
                anc = {"A0": (0,0), "A1": (0,-4), "A2": (0,-8), "A3": (-6,0),
                       "A4": (30,0), "A5": (30,-4), "A6": (30,-8), "A7": (36,0)}
                return anc[idx]
            return nodes[idx]
        x1, y1 = pos(u); x2, y2 = pos(v)
        L = math.hypot(x2 - x1, y2 - y1)
        mat = pref if (pref == "wood" and L <= 2.98) else "steel"
        members.append([u, v, mat])

    # Arch chord
    add_m(al, arch_start, "wood")
    for i in range(n_seg - 2):
        add_m(arch_start + i, arch_start + i + 1, "wood")
    add_m(arch_start + n_seg - 2, ar, "wood")

    # Verticals
    for i in range(n_seg - 1):
        add_m(i, arch_start + i, "wood")

    # Diagonals
    add_m("A0", arch_start, "wood")
    add_m("A4", arch_start + n_seg - 2, "wood")
    for i in range(n_seg - 2):
        if i < (n_seg - 2) // 2:
            add_m(i, arch_start + i + 1, "wood")
        else:
            add_m(arch_start + i, i + 1, "wood")

    return {"nodes": nodes, "members": members}


if __name__ == "__main__":
    best = None
    for th in [6.0, 7.5, 9.0]:
        d = make_l2_cable_stayed(n_seg=13, tower_h=th)
        ok, cost, stress, msg = eval_design(2, d)
        print(f"L2 CableStayed th={th}: {'PASS' if ok else 'FAIL'} cost={cost:.1f} stress={stress:.2f} {msg}")
        if ok and (best is None or cost < best[0]):
            best = (cost, d)

    for arch_mid in [-1.5, -2.0]:
        for arch_end, al, ar in [(-4.0, "A1", "A5"), (-8.0, "A2", "A6")]:
            d = make_l2_arch(n_seg=13, arch_mid=arch_mid, arch_end=arch_end, al=al, ar=ar)
            ok, cost, d_out, msg = auto_upgrade_to_pass(2, d, max_iters=20)
            print(f"L2 Arch mid={arch_mid} end={arch_end}: {'PASS' if ok else 'FAIL'} cost={cost:.1f} {msg}")
            if ok and (best is None or cost < best[0]):
                best = (cost, d_out)

    if best:
        save_submission("level2.json", best[1])
        print(f"Saved best level2.json with cost {best[0]:.1f}")
