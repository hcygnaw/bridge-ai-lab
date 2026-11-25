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
    except bridge.DesignError:
        return False, float("inf")
    for sc in scenarios:
        res, _ = bridge.simulate(lv, P, sc, replay=False)
        if not res["ok"]:
            return False, P["cost"]
    return True, P["cost"]


def make_warren_l1(n_seg=6, h=1.8, road_arch=0.0):
    dx = 15.0 / n_seg
    nodes, members = [], []
    for i in range(1, n_seg):
        t = i / n_seg
        nodes.append([round(i * dx, 4), round(road_arch * 4 * t * (1 - t), 4)])
    def top(i): return "A0" if i == 0 else ("A2" if i == n_seg else i - 1)
    for i in range(n_seg):
        members.append([top(i), top(i + 1), "road"])
    ut = []
    for i in range(n_seg):
        x = (i + 0.5) * dx
        t = x / 15.0
        y = h * (1.0 - 0.15 * (2 * t - 1) ** 2)
        nodes.append([round(x, 4), round(y, 4)])
        ut.append(len(nodes) - 1)
    for i in range(n_seg - 1):
        members.append([ut[i], ut[i + 1], "wood"])
    for i in range(n_seg):
        members.append([top(i), ut[i], "wood"])
        members.append([ut[i], top(i + 1), "wood"])
    return {"nodes": nodes, "members": members}


best = (4484.03, None)
for n_seg in [6, 7]:
    for h in [1.2, 1.5, 1.8, 2.1]:
        for ra in [0.0, 0.3, 0.6]:
            d = make_warren_l1(n_seg=n_seg, h=h, road_arch=ra)
            ok, cost = eval_design(d)
            if ok and cost < best[0]:
                best = (cost, d)
                print(f"NEW BEST L1: n={n_seg} h={h} ra={ra} cost={cost:.1f}")

if best[1]:
    with open("submission/level1.json", "w") as f:
        json.dump(best[1], f, indent=2)
    print("Saved submission/level1.json, cost =", best[0])
