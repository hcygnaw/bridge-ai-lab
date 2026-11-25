import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bridge

lv = bridge.load_level("2")
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


def make_arch_bridge(n_seg=12, y_arch_mid=-2.0, y_road_mid=0.5, arch_anchor="A1", arch_mat="wood", diag=True):
    # Anchors: A0=(0,0), A1=(0,-4), A2=(0,-8), A3=(-6,0), A4=(30,0), A5=(30,-4), A6=(30,-8), A7=(36,0)
    dx = 30.0 / n_seg
    nodes = []
    members = []

    # Road nodes: 1..n_seg-1
    for i in range(1, n_seg):
        x = i * dx
        t = (x - 15.0) / 15.0
        y = y_road_mid * (1.0 - t * t)
        nodes.append([round(x, 4), round(y, 4)])

    def top(i):
        if i == 0:
            return "A0"
        if i == n_seg:
            return "A4"
        return i - 1

    for i in range(n_seg):
        members.append([top(i), top(i + 1), "road"])

    y0 = -4.0 if arch_anchor == "A1" else -8.0
    a_left = arch_anchor
    a_right = "A5" if arch_anchor == "A1" else "A6"

    # Arch nodes at x = i * dx for i = 1..n_seg-1
    arch_start = len(nodes)
    for i in range(1, n_seg):
        x = i * dx
        t = (x - 15.0) / 15.0
        y = y_arch_mid + (y0 - y_arch_mid) * (t * t)
        nodes.append([round(x, 4), round(y, 4)])

    def bot(i):
        if i == 0:
            return a_left
        if i == n_seg:
            return a_right
        return arch_start + i - 1

    for i in range(n_seg):
        # Check length
        p1 = (0, y0) if i == 0 else nodes[bot(i)]
        p2 = (30, y0) if i == n_seg - 1 else nodes[bot(i + 1)]
        L = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
        m = arch_mat
        if m == "wood" and L > 2.99:
            m = "steel"
        members.append([bot(i), bot(i + 1), m])

    # Verticals
    for i in range(1, n_seg):
        L = abs(nodes[top(i)][1] - nodes[bot(i)][1])
        if L >= 0.3:
            m = "wood" if L <= 2.99 else "steel"
            members.append([top(i), bot(i), m])

    # Diagonals
    if diag:
        for i in range(n_seg):
            if i < n_seg // 2:
                u, v = top(i), bot(i + 1)
            else:
                u, v = bot(i), top(i + 1)
            p1 = lv["anchors"][int(u[1:])] if isinstance(u, str) else nodes[u]
            p2 = lv["anchors"][int(v[1:])] if isinstance(v, str) else nodes[v]
            L = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
            if L <= 2.99:
                members.append([u, v, "wood"])
            elif L <= 5.99:
                members.append([u, v, "steel"])
            else:
                members.append([u, v, "cable"])

    return {"nodes": nodes, "members": members}


best = (float("inf"), None, "")
for n_seg in [12, 13, 14]:
    for arch_anchor in ["A1", "A2"]:
        for y_arch_mid in [-2.0, -1.5, -1.0]:
            for y_road_mid in [0.0, 0.8, 1.5]:
                for arch_mat in ["wood", "steel"]:
                    d = make_arch_bridge(n_seg, y_arch_mid, y_road_mid, arch_anchor, arch_mat, True)
                    ok, cost, msg = eval_design(d)
                    if ok and cost < best[0]:
                        best = (cost, d, msg)
                        print(f"NEW BEST: n={n_seg} anc={arch_anchor} ym={y_arch_mid} yr={y_road_mid} mat={arch_mat} cost={cost:.1f} {msg}")

if best[1]:
    with open("submission/level2.json", "w") as f:
        json.dump(best[1], f, indent=2)
    print("Saved submission/level2.json, cost =", best[0])
