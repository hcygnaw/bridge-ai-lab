import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bridge
from opt_helper import eval_design, save_submission


def make_warren_arch_l2(n_seg=14, arch_mid_y=-1.2, arch_end_y=-4.0, anchor_l="A1", anchor_r="A5",
                        mat_arch="wood", mat_web="wood", deck_camber=0.0):
    """Warren-style under-deck arch for Level 2 (0..30)."""
    nodes = []
    members = []
    dx = 30.0 / n_seg
    # Deck nodes: 0 .. n_seg-2 (n_seg-1 nodes)
    for i in range(1, n_seg):
        x = i * dx
        t = x / 30.0
        y = 4.0 * deck_camber * t * (1.0 - t)
        nodes.append([round(x, 3), round(y, 3)])
    for i in range(n_seg):
        u = "A0" if i == 0 else i - 1
        v = "A4" if i == n_seg - 1 else i
        members.append([u, v, "road"])

    # Arch nodes at half-stations: x = (i + 0.5) * dx, i = 0 .. n_seg-1
    # Actually, let's place arch nodes at x = (i + 0.5) * dx for i = 0..n_seg-1
    arch_start = len(nodes)
    for i in range(n_seg):
        x = (i + 0.5) * dx
        t = x / 30.0
        # parabola from arch_end_y at t=0,1 to arch_mid_y at t=0.5
        y = arch_end_y + (arch_mid_y - arch_end_y) * 4.0 * t * (1.0 - t)
        nodes.append([round(x, 3), round(y, 3)])

    # Arch chord
    members.append([anchor_l, arch_start, mat_arch])
    for i in range(n_seg - 1):
        members.append([arch_start + i, arch_start + i + 1, mat_arch])
    members.append([arch_start + n_seg - 1, anchor_r, mat_arch])

    # Warren web: each arch node i connects to deck node i-1 (or A0) and deck node i (or A4)
    for i in range(n_seg):
        dl = "A0" if i == 0 else i - 1
        dr = "A4" if i == n_seg - 1 else i
        members.append([arch_start + i, dl, mat_web])
        members.append([arch_start + i, dr, mat_web])

    return {"nodes": nodes, "members": members}


def make_warren_l3(n_half=6, bot_y=-2.0, mid_bot_y=-3.0, mat="wood"):
    """Two-span Warren truss for Level 3 (0..28, center pier A2=(14,-4))."""
    nodes = []
    members = []
    n_seg = n_half * 2
    dx = 28.0 / n_seg
    # Deck nodes: 0 .. n_seg-2
    for i in range(1, n_seg):
        x = i * dx
        nodes.append([round(x, 3), 0.0])
    for i in range(n_seg):
        u = "A0" if i == 0 else i - 1
        v = "A3" if i == n_seg - 1 else i
        members.append([u, v, "road"])

    # Bottom nodes at half-stations: 0 .. n_seg-1
    bot_start = len(nodes)
    for i in range(n_seg):
        x = (i + 0.5) * dx
        # Dip toward center pier at x=14
        dist_mid = abs(x - 14.0) / 14.0
        y = mid_bot_y * (1.0 - dist_mid) + bot_y * dist_mid
        nodes.append([round(x, 3), round(y, 3)])

    # Bottom chord
    members.append(["A1", bot_start, mat])
    for i in range(n_seg - 1):
        members.append([bot_start + i, bot_start + i + 1, mat])
    members.append([bot_start + n_seg - 1, "A4", mat])

    # Connect center pier A2=(14,-4) to the two bottom nodes adjacent to x=14
    members.append(["A2", bot_start + n_half - 1, mat])
    members.append(["A2", bot_start + n_half, mat])
    # Also connect A2 to the center deck node? Distance is 4.0m > 3.0m for wood, so use steel or omit
    # Warren web
    for i in range(n_seg):
        dl = "A0" if i == 0 else i - 1
        dr = "A3" if i == n_seg - 1 else i
        members.append([bot_start + i, dl, mat])
        members.append([bot_start + i, dr, mat])

    return {"nodes": nodes, "members": members}


if __name__ == "__main__":
    print("=== LEVEL 2 ===")
    best2 = None
    for n_seg in [13, 14, 15]:
        for arch_mid_y in [-1.5, -2.0, -2.5]:
            for arch_end_y, al, ar in [(-4.0, "A1", "A5"), (-8.0, "A2", "A6")]:
                for mat_arch in ["wood", "steel"]:
                    d = make_warren_arch_l2(n_seg=n_seg, arch_mid_y=arch_mid_y, arch_end_y=arch_end_y,
                                            anchor_l=al, anchor_r=ar, mat_arch=mat_arch, mat_web="wood")
                    ok, cost, stress, msg = eval_design(2, d)
                    if ok:
                        print(f"L2 PASS n={n_seg} mid={arch_mid_y} end={arch_end_y} mat={mat_arch} cost={cost:.1f} stress={stress:.2f}")
                        if best2 is None or cost < best2[0]:
                            best2 = (cost, d)
    if best2:
        save_submission("level2.json", best2[1])
        print(f"Saved best level2.json with cost {best2[0]:.1f}")

    print("\n=== LEVEL 3 ===")
    best3 = None
    for n_half in [6, 7]:
        for bot_y in [-1.5, -2.0]:
            for mid_bot_y in [-2.2, -2.8, -3.2]:
                d = make_warren_l3(n_half=n_half, bot_y=bot_y, mid_bot_y=mid_bot_y, mat="wood")
                ok, cost, stress, msg = eval_design(3, d)
                if ok:
                    print(f"L3 PASS n_half={n_half} bot_y={bot_y} mid_bot_y={mid_bot_y} cost={cost:.1f} stress={stress:.2f}")
                    if best3 is None or cost < best3[0]:
                        best3 = (cost, d)
                else:
                    print(f"L3 FAIL n_half={n_half} bot_y={bot_y} mid_bot_y={mid_bot_y} cost={cost:.1f} {msg}")
    if best3:
        save_submission("level3.json", best3[1])
        print(f"Saved best level3.json with cost {best3[0]:.1f}")
