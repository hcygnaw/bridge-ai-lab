import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bridge
from opt_helper import eval_design, save_submission


def make_l2_cable_truss(n_seg=13, tower_h=6.0, bot_y=-1.8, mat_bot="wood", mat_web="wood", mat_tower="steel"):
    """Cable-stayed Warren truss for Level 2 (0..30)."""
    nodes = []
    members = []
    dx = 30.0 / n_seg
    for i in range(1, n_seg):
        nodes.append([round(i * dx, 3), 0.0])
    for i in range(n_seg):
        u = "A0" if i == 0 else i - 1
        v = "A4" if i == n_seg - 1 else i
        members.append([u, v, "road"])

    bot_start = len(nodes)
    for i in range(n_seg):
        x = (i + 0.5) * dx
        nodes.append([round(x, 3), round(bot_y, 3)])

    for i in range(n_seg - 1):
        members.append([bot_start + i, bot_start + i + 1, mat_bot])
    for i in range(n_seg):
        dl = "A0" if i == 0 else i - 1
        dr = "A4" if i == n_seg - 1 else i
        members.append([bot_start + i, dl, mat_web])
        members.append([bot_start + i, dr, mat_web])

    members.append(["A1", bot_start, "steel"])
    members.append(["A5", bot_start + n_seg - 1, "steel"])

    tl = len(nodes)
    nodes.append([0.0, round(tower_h, 3)])
    tr = len(nodes)
    nodes.append([30.0, round(tower_h, 3)])

    members.append(["A0", tl, mat_tower])
    members.append(["A4", tr, mat_tower])
    members.append(["A3", tl, "cable"])
    members.append(["A7", tr, "cable"])

    mid = (n_seg - 1) // 2
    for i in range(1, n_seg - 2):
        if i <= mid:
            members.append([tl, i, "cable"])
        if i >= mid:
            members.append([tr, i, "cable"])

    return {"nodes": nodes, "members": members}


def make_l3_pier_truss(n_half=6, bot_y=-1.8, mat_bot="wood", mat_web="wood"):
    """Two-span Warren truss for Level 3 (0..28, center pier A2=(14,-4))."""
    nodes = []
    members = []
    n_seg = n_half * 2
    dx = 28.0 / n_seg
    for i in range(1, n_seg):
        nodes.append([round(i * dx, 3), 0.0])
    for i in range(n_seg):
        u = "A0" if i == 0 else i - 1
        v = "A3" if i == n_seg - 1 else i
        members.append([u, v, "road"])

    bot_start = len(nodes)
    for i in range(n_seg):
        x = (i + 0.5) * dx
        nodes.append([round(x, 3), round(bot_y, 3)])

    members.append(["A1", bot_start, mat_bot])
    for i in range(n_seg - 1):
        members.append([bot_start + i, bot_start + i + 1, mat_bot])
    members.append([bot_start + n_seg - 1, "A4", mat_bot])

    for i in range(n_seg):
        dl = "A0" if i == 0 else i - 1
        dr = "A3" if i == n_seg - 1 else i
        members.append([bot_start + i, dl, mat_web])
        members.append([bot_start + i, dr, mat_web])

    center_deck = n_half - 1
    members.append(["A2", center_deck, "steel"])
    members.append(["A2", bot_start + n_half - 1, "steel"])
    members.append(["A2", bot_start + n_half, "steel"])

    return {"nodes": nodes, "members": members}


if __name__ == "__main__":
    print("=== LEVEL 2 ===")
    best2 = None
    for n_seg in [13, 14]:
        for tower_h in [5.5, 6.0]:
            for bot_y in [-1.5, -2.0]:
                d = make_l2_cable_truss(n_seg=n_seg, tower_h=tower_h, bot_y=bot_y)
                ok, cost, stress, msg = eval_design(2, d)
                print(f"L2 {'PASS' if ok else 'FAIL'} n={n_seg} th={tower_h} by={bot_y} cost={cost:.1f} stress={stress:.2f} {msg}")
                if ok and (best2 is None or cost < best2[0]):
                    best2 = (cost, d)
    if best2:
        save_submission("level2.json", best2[1])
        print(f"Saved best level2.json with cost {best2[0]:.1f}")

    print("\n=== LEVEL 3 ===")
    best3 = None
    for n_half in [6, 7]:
        for bot_y in [-1.5, -1.8, -2.1]:
            d = make_l3_pier_truss(n_half=n_half, bot_y=bot_y)
            ok, cost, stress, msg = eval_design(3, d)
            print(f"L3 {'PASS' if ok else 'FAIL'} n_half={n_half} by={bot_y} cost={cost:.1f} stress={stress:.2f} {msg}")
            if ok and (best3 is None or cost < best3[0]):
                best3 = (cost, d)
    if best3:
        save_submission("level3.json", best3[1])
        print(f"Saved best level3.json with cost {best3[0]:.1f}")
