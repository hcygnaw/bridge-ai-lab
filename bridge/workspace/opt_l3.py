import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bridge

lv = bridge.load_level("3")
scenarios = [bridge.load_json(p) for p in bridge.sample_paths(lv)]


def eval_design(d):
    try:
        P = bridge.parse_design(lv, d)
    except bridge.DesignError as e:
        return False, float("inf"), str(e)
    max_ratio = 0.0
    for sc in scenarios:
        res, _ = bridge.simulate(lv, P, sc, replay=False)
        if not res["ok"]:
            return False, P["cost"], f"fail {sc.get('name','')}: {bridge.summarize(res, P, sc)['text']}"
        for mr in res.get("peak_members", []):
            if mr > max_ratio:
                max_ratio = mr
    return True, P["cost"], f"max_ratio={max_ratio:.3f}"


def make_two_span(n_half=6, arch_h=2.5, pier_y=-2.0, use_steel_arch=False):
    # 2 * n_half segments from 0 to 28
    n_seg = 2 * n_half
    dx = 28.0 / n_seg
    nodes = []
    members = []

    # Road nodes: 1..n_seg-1
    for i in range(1, n_seg):
        nodes.append([round(i * dx, 4), 0.0])

    def top(i):
        if i == 0:
            return "A0"
        if i == n_seg:
            return "A3"
        return i - 1

    for i in range(n_seg):
        members.append([top(i), top(i + 1), "road"])

    # Center pier node at (14, pier_y) -> connects to A2=(14,-4) and top(n_half)=(14,0)
    pier_idx = len(nodes)
    nodes.append([14.0, pier_y])
    members.append(["A2", pier_idx, "wood" if abs(-4.0 - pier_y) <= 2.99 else "steel"])
    members.append([pier_idx, top(n_half), "wood" if abs(pier_y) <= 2.99 else "steel"])

    # Over-truss (arch/truss above road) for each half-span, or under-truss?
    # Let's do an over-truss (Warren/Pratt) above each 14m span, plus braces from A2 to top(n_half-1) and top(n_half+1)
    # Wait: distance from A2=(14,-4) to top(n_half-1)=(14-dx, 0) is hypot(dx, 4) = hypot(2.33, 4) = 4.63m (steel)
    # Or from pier_idx=(14,-2) to top(n_half-1)=(11.67, 0) is hypot(2.33, 2) = 3.07m (steel) or with n_half=7, dx=2, hypot(2,2)=2.83m (wood!)
    # Let's try an over-truss above road!
    # Top chord nodes at x = (i + 0.5) * dx for i = 0..n_seg-1? Or at x = i * dx for i = 1..n_seg-1
    top_chord_start = len(nodes)
    for i in range(1, n_seg):
        x = i * dx
        if i <= n_half:
            t = (x - 7.0) / 7.0
        else:
            t = (x - 21.0) / 7.0
        y = arch_h * (1.0 - 0.3 * t * t)
        nodes.append([round(x, 4), round(y, 4)])

    def tc(i):
        return top_chord_start + i - 1

    # Connect A0 -> tc(1), tc(1)..tc(n_seg-1), tc(n_seg-1) -> A3
    def dist(u, v):
        p1 = lv["anchors"][int(u[1:])] if isinstance(u, str) else nodes[u]
        p2 = lv["anchors"][int(v[1:])] if isinstance(v, str) else nodes[v]
        return math.hypot(p2[0] - p1[0], p2[1] - p1[1])

    def add_m(u, v, prefer="wood"):
        L = dist(u, v)
        if prefer == "wood" and L <= 2.99:
            members.append([u, v, "wood"])
        else:
            members.append([u, v, "steel"])

    chord_mat = "steel" if use_steel_arch else "wood"
    add_m("A0", tc(1), chord_mat)
    for i in range(1, n_seg - 1):
        add_m(tc(i), tc(i + 1), chord_mat)
    add_m(tc(n_seg - 1), "A3", chord_mat)

    # Verticals
    for i in range(1, n_seg):
        add_m(top(i), tc(i), "wood")

    # Diagonals in each half
    for i in range(1, n_half):
        if i * dx <= 7.0:
            add_m(top(i), tc(i + 1), "wood")
        else:
            add_m(tc(i), top(i + 1), "wood")
    for i in range(n_half, n_seg - 1):
        if i * dx <= 21.0:
            add_m(top(i), tc(i + 1), "wood")
        else:
            add_m(tc(i), top(i + 1), "wood")

    # Brace pier_idx to top(n_half-1) and top(n_half+1), and A1/A4 to top(1)/top(n_seg-1)
    add_m(pier_idx, top(n_half - 1), "wood")
    add_m(pier_idx, top(n_half + 1), "wood")
    add_m("A1", top(1), "wood")
    add_m("A4", top(n_seg - 1), "wood")

    return {"nodes": nodes, "members": members}


best = (float("inf"), None, "")
for n_half in [6, 7]:
    for arch_h in [2.0, 2.5, 3.0]:
        for pier_y in [-2.0]:
            for use_steel in [False, True]:
                d = make_two_span(n_half=n_half, arch_h=arch_h, pier_y=pier_y, use_steel_arch=use_steel)
                ok, cost, msg = eval_design(d)
                print(f"n_half={n_half} h={arch_h} steel={use_steel} ok={ok} cost={cost:.1f} {msg}")
                if ok and cost < best[0]:
                    best = (cost, d, msg)
                    print(f"NEW BEST: n_half={n_half} h={arch_h} steel={use_steel} cost={cost:.1f} {msg}")

if best[1]:
    with open("submission/level3.json", "w") as f:
        json.dump(best[1], f, indent=2)
    print("Saved submission/level3.json, cost =", best[0])
