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
            pk = bridge.peak_report(res, P, top=5)
            return False, P["cost"], f"fail {sc.get('name','')}: {res['events'][:5]} | {pk}"
        for mr in res.get("peak_members", []):
            if mr > max_ratio:
                max_ratio = mr
    return True, P["cost"], f"max_ratio={max_ratio:.3f}"


def make_two_span_under(n_half=6, depth=2.0, arch_road=0.0):
    n_seg = 2 * n_half
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
        L = dist(u, v)
        if mat == "wood" and L > 2.99:
            mat = "steel"
        members.append([u, v, mat])

    for i in range(1, n_seg):
        x = i * dx
        if i <= n_half:
            t = (x - 7.0) / 7.0
        else:
            t = (x - 21.0) / 7.0
        y = arch_road * (1.0 - t * t)
        nodes.append([round(x, 4), round(y, 4)])

    def top(i):
        if i == 0:
            return "A0"
        if i == n_seg:
            return "A3"
        return i - 1

    for i in range(n_seg):
        members.append([top(i), top(i + 1), "road"])

    bot_start = len(nodes)
    for i in range(1, n_seg):
        x = i * dx
        if i == n_half:
            y = -2.0
        else:
            if i < n_half:
                t = (x - 7.0) / 7.0
            else:
                t = (x - 21.0) / 7.0
            y = -depth * (1.0 - 0.3 * t * t)
        nodes.append([round(x, 4), round(y, 4)])

    def bot(i):
        if i == 0:
            return "A1"
        if i == n_seg:
            return "A4"
        return bot_start + i - 1

    for i in range(n_seg):
        add_m(bot(i), bot(i + 1), "wood")

    add_m("A2", bot(n_half), "wood")
    add_m("A2", bot(n_half - 1), "wood")
    add_m("A2", bot(n_half + 1), "wood")

    for i in range(1, n_seg):
        add_m(top(i), bot(i), "wood")

    for i in range(n_half):
        if i < n_half // 2:
            add_m(top(i), bot(i + 1), "wood")
        else:
            add_m(bot(i), top(i + 1), "wood")
    for i in range(n_half, n_seg):
        if i - n_half < n_half // 2:
            add_m(top(i), bot(i + 1), "wood")
        else:
            add_m(bot(i), top(i + 1), "wood")

    return {"nodes": nodes, "members": members}


best = (float("inf"), None, "")
for n_half in [6, 7]:
    for depth in [1.5, 2.0, 2.5]:
        for arch_road in [0.0, 0.5]:
            d = make_two_span_under(n_half=n_half, depth=depth, arch_road=arch_road)
            ok, cost, msg = eval_design(d)
            print(f"n_half={n_half} depth={depth} arch={arch_road} ok={ok} cost={cost:.1f} {msg[:100]}")
            if ok and cost < best[0]:
                best = (cost, d, msg)

if best[1]:
    with open("submission/level3.json", "w") as f:
        json.dump(best[1], f, indent=2)
    print("Saved submission/level3.json, cost =", best[0])
