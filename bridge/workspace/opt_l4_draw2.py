import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bridge

lv = bridge.load_level("4")
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


def make_drawbridge(n_leaf=5, truss_h=2.0, tower_h=5.5, ratio=0.55):
    nodes = []
    members = []

    def pt(u):
        if isinstance(u, str):
            return lv["anchors"][int(u[1:])]
        return nodes[u]

    def dist(u, v):
        p1, p2 = pt(u), pt(v)
        return math.hypot(p2[0] - p1[0], p2[1] - p1[1])

    def add_m(u, v, mat, group=None):
        L = dist(u, v)
        if mat == "wood" and L > 2.99:
            mat = "steel"
        if group is not None:
            members.append([u, v, mat, group])
        else:
            members.append([u, v, mat])

    dx_L = 11.9 / n_leaf

    def build_leaf(x0, sign, anc_base, anc_mid, anc_back, hyd_group):
        # Road nodes: 1..n_leaf
        road = [anc_base]
        for i in range(1, n_leaf + 1):
            nodes.append([round(x0 + sign * i * dx_L, 4), 0.0])
            road.append(len(nodes) - 1)
        for i in range(n_leaf):
            members.append([road[i], road[i + 1], "road"])

        # Under-truss or over-truss on leaf: let's use over-truss
        top = []
        for i in range(1, n_leaf):
            x = x0 + sign * i * dx_L
            y = truss_h * (1.0 - 0.25 * (i / n_leaf))
            nodes.append([round(x, 4), round(y, 4)])
            top.append(len(nodes) - 1)

        add_m(anc_base, top[0], "steel")
        for i in range(len(top) - 1):
            add_m(top[i], top[i + 1], "steel" if i == 0 else "wood")
        for i in range(len(top)):
            add_m(road[i + 1], top[i], "steel" if i == 0 else "wood")
            if i < len(top) - 1:
                add_m(top[i], road[i + 2], "steel" if i == 0 else "wood")
        add_m(top[-1], road[-1], "wood")

        # Tower: mid node at (x0, tower_h/2), top node at (x0, tower_h)
        nodes.append([x0, round(tower_h * 0.5, 4)])
        T_mid = len(nodes) - 1
        nodes.append([x0, round(tower_h, 4)])
        T_top = len(nodes) - 1

        add_m(anc_base, T_mid, "steel")
        add_m(T_mid, T_top, "steel")
        add_m(anc_mid, T_mid, "wood")
        add_m(anc_back, T_top, "cable")

        # Hydraulic from A1/A4 to road[2] (with n_leaf=6, dx=1.983, road[2] is at x=3.967, L=4.44m!)
        anc_low = "A1" if x0 == 0.0 else "A4"
        add_m(anc_low, road[2], "hydraulic", hyd_group)
        # Cable stays from T_top to top[-1] and top[1]
        add_m(T_top, top[-1], "cable")
        add_m(T_top, top[1], "cable")

    # Left: A0=(0,0), A2=(-4,0), A8=(-8,0)
    build_leaf(0.0, 1.0, "A0", "A2", "A8", "L")
    # Right: A3=(24,0), A5=(28,0), A13=(32,0)
    build_leaf(24.0, -1.0, "A3", "A5", "A13", "R")

    sensors = [{"id": "h", "type": "horn"}]
    lights = [
        {"id": "L1", "x": -1.0, "dir": "right", "init": "green"},
        {"id": "L2", "x": 25.0, "dir": "left", "init": "green"},
    ]
    rules = [
        {"on": "h", "delay": 0.0, "do": "light", "light": "L1", "state": "red"},
        {"on": "h", "delay": 0.0, "do": "light", "light": "L2", "state": "red"},
        {"on": "h", "delay": 4.5, "do": "hyd", "group": "L", "ratio": ratio, "speed": 2.0, "accel": 1.5},
        {"on": "h", "delay": 4.5, "do": "hyd", "group": "R", "ratio": ratio, "speed": 2.0, "accel": 1.5},
        {"on": "h", "delay": 16.5, "do": "hyd", "group": "L", "ratio": 1.0, "speed": 2.0, "accel": 1.5},
        {"on": "h", "delay": 16.5, "do": "hyd", "group": "R", "ratio": 1.0, "speed": 2.0, "accel": 1.5},
        {"on": "h", "delay": 18.5, "do": "light", "light": "L1", "state": "green"},
        {"on": "h", "delay": 18.5, "do": "light", "light": "L2", "state": "green"},
    ]
    return {"nodes": nodes, "members": members, "sensors": sensors, "lights": lights, "rules": rules}


if __name__ == "__main__":
    for ratio in [1.21, 1.22, 1.23, 1.24]:
        d = make_drawbridge(n_leaf=6, truss_h=2.0, tower_h=5.5, ratio=ratio)
        ok, cost, msg = eval_design(d)
        print(f"ratio={ratio} ok={ok} cost={cost:.1f} {msg}")
        if ok:
            with open("submission/level4.json", "w") as f:
                json.dump(d, f, indent=2)
            break
