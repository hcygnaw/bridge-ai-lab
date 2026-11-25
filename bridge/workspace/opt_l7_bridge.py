import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bridge

lv = bridge.load_level("final")
scenarios = [bridge.load_json(p) for p in bridge.sample_paths(lv)]


def make_final_bridge(depth=3.0, arch_rise=0.4, n_seg=14):
    # 28m river: x=0 to x=28, n_seg=14 -> dx = 2.0m
    # Anchors: A0=(0,0), A1=(0,-2), A2=(-5,0), A3=(28,0), A4=(28,-2), A5=(33,0)
    dx = 28.0 / n_seg
    nodes = []
    members = []

    def pt(u):
        if isinstance(u, str):
            return lv["anchors"][int(u[1:])]
        return nodes[u]

    def dist(u, v):
        p1, p2 = pt(u), pt(v)
        return math.hypot(p2[0] - p1[0], p2[1] - p1[1])

    def add_m(u, v, mat):
        members.append([u, v, mat])

    # Road nodes: 1..n_seg-1 with slight arch
    for i in range(1, n_seg):
        t = i / n_seg
        x = i * dx
        y = arch_rise * 4.0 * t * (1.0 - t)
        nodes.append([round(x, 4), round(y, 4)])

    def top(i):
        if i == 0:
            return "A0"
        if i == n_seg:
            return "A3"
        return i - 1

    for i in range(n_seg):
        add_m(top(i), top(i + 1), "road")

    # Bottom steel arch/truss chord: A1=(0,-2) to A4=(28,-2), dipping to -depth at center
    bot_start = len(nodes)
    for i in range(1, n_seg):
        t = i / n_seg
        x = i * dx
        y = -2.0 - (depth - 2.0) * 4.0 * t * (1.0 - t)
        nodes.append([round(x, 4), round(y, 4)])

    def bot(i):
        if i == 0:
            return "A1"
        if i == n_seg:
            return "A4"
        return bot_start + i - 1

    for i in range(n_seg):
        add_m(bot(i), bot(i + 1), "steel")

    # Verticals: steel
    for i in range(1, n_seg):
        add_m(top(i), bot(i), "steel")

    # Diagonals: steel (Pratt/Warren)
    for i in range(n_seg):
        if i < n_seg // 2:
            add_m(top(i), bot(i + 1), "steel")
        else:
            add_m(bot(i), top(i + 1), "steel")

    # Overhead cable/steel tie from A2=(-5,0) and A5=(33,0)?
    # Let's add a steel/cable over-arch or stays from A2/A5 if budget allows!
    # Actually let's check cost first!
    return {"nodes": nodes, "members": members}


d = make_final_bridge(depth=3.2, arch_rise=0.4, n_seg=14)
P = bridge.parse_design(lv, d)
print("Cost:", P["cost"], "/ Budget:", lv["budget"])
for sc in scenarios:
    res, _ = bridge.simulate(lv, P, sc, replay=False)
    print(bridge.summarize(res, P, sc)["text"])
    print("\n".join(bridge.peak_report(res, P, 5)))
if res["ok"]:
    with open("submission/final_bridge.json", "w") as f:
        json.dump(d, f, indent=2)
    print("Saved submission/final_bridge.json")
