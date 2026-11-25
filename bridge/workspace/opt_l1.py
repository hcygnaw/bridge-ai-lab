import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bridge

lv = bridge.load_level("1")
scenarios = [bridge.load_json(p) for p in bridge.sample_paths(lv)]


def eval_design(d):
    try:
        P = bridge.parse_design(lv, d)
    except bridge.DesignError as e:
        return False, float("inf"), str(e), []
    max_ratio = 0.0
    for sc in scenarios:
        res, _ = bridge.simulate(lv, P, sc, replay=False)
        if not res["ok"]:
            return False, P["cost"], f"fail {sc.get('name','')}: {res}", []
        for mr in res.get("peak_members", []):
            if mr > max_ratio:
                max_ratio = mr
    return True, P["cost"], f"max_ratio={max_ratio:.3f}", []


def make_under_truss(n_seg=6, depth=2.0, road_y_arch=0.0, use_cable=False):
    # n_seg segments from x=0 to x=15
    dx = 15.0 / n_seg
    nodes = []
    members = []
    # Top road nodes: n_seg - 1 nodes (indices 0 .. n_seg-2)
    for i in range(1, n_seg):
        x = i * dx
        # parabolic arch height if road_y_arch > 0
        t = (x - 7.5) / 7.5
        y = road_y_arch * (1.0 - t * t)
        nodes.append([round(x, 4), round(y, 4)])

    def top_node(i):
        if i == 0:
            return "A0"
        if i == n_seg:
            return "A2"
        return i - 1

    for i in range(n_seg):
        members.append([top_node(i), top_node(i + 1), "road"])

    # Bottom nodes under each interior road node, or shifted
    bot_start = len(nodes)
    for i in range(1, n_seg):
        x = i * dx
        t = (x - 7.5) / 7.5
        y = -depth * (1.0 - 0.3 * t * t)
        nodes.append([round(x, 4), round(y, 4)])

    # Connect A1 -> bot[0], bot[i] -> bot[i+1], bot[-1] -> A3
    bot_mat = "cable" if use_cable else "wood"
    members.append(["A1", bot_start, bot_mat])
    for i in range(n_seg - 2):
        members.append([bot_start + i, bot_start + i + 1, bot_mat])
    members.append([bot_start + n_seg - 2, "A3", bot_mat])

    # Verticals and diagonals
    for i in range(1, n_seg):
        members.append([top_node(i), bot_start + i - 1, "wood"])

    # Diagonals: symmetric toward center
    # Left half: A0 -> bot[0] or A1 -> top[1]?
    # A1=(0,-2) to top[1] is compression/tension
    for i in range(1, n_seg):
        if i * dx <= 7.5:
            # A0/top[i-1] to bot[i-1]
            if i == 1:
                members.append(["A0", bot_start, "wood"])
            else:
                members.append([top_node(i - 1), bot_start + i - 1, "wood"])
        if i * dx >= 7.5:
            if i == n_seg - 1:
                members.append(["A2", bot_start + i - 1, "wood"])
            else:
                members.append([top_node(i + 1), bot_start + i - 1, "wood"])

    return {"nodes": nodes, "members": members}


def make_arch_deck(n_seg=6, road_y_arch=0.8, strut_h=-2.0):
    # Just road arch + struts to A1, A3? Wait: 15m/6 = 2.5m.
    # Let's try simple Pratt/Warren over or under truss
    return make_under_truss(n_seg=n_seg, depth=2.0, road_y_arch=road_y_arch)


best = (float("inf"), None, "")
for n_seg in [6, 7]:
    for depth in [1.5, 2.0, 2.5, 3.0]:
        for arch in [0.0, 0.3, 0.6]:
            for use_cable in [False, True]:
                d = make_under_truss(n_seg=n_seg, depth=depth, road_y_arch=arch, use_cable=use_cable)
                ok, cost, msg, _ = eval_design(d)
                if ok and cost < best[0]:
                    best = (cost, d, msg)
                    print(f"NEW BEST: n={n_seg} depth={depth} arch={arch} cable={use_cable} cost={cost:.1f} {msg}")

if best[1]:
    with open("submission/level1.json", "w") as f:
        json.dump(best[1], f, indent=2)
    print("Saved submission/level1.json, cost =", best[0])
