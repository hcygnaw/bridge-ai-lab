import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bridge

lv = bridge.load_level("6")
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


def make_l6(ratio=1.38, speed=2.0, accel=1.5):
    nodes = []
    members = []

    def pt(u):
        if isinstance(u, str):
            return lv["anchors"][int(u[1:])]
        return nodes[u]

    def dist(u, v):
        p1, p2 = pt(u), pt(v)
        return math.hypot(p2[0] - p1[0], p2[1] - p1[1])

    def add_m(u, v, mat="wood", group=None):
        L = dist(u, v)
        if mat == "wood" and L > 2.99:
            mat = "steel"
        if group is not None:
            members.append([u, v, mat, group])
        else:
            members.append([u, v, mat])

    # Helper to build static 12m side span (x0 to x1) with 6 segments of 2.0m
    # Anchors: top_end (A0 or A6), bot_end (A1 or A7), pier_bot (A4 or A5)
    def build_side_span(x0, x1, anc_top, anc_bot, anc_pier):
        n_seg = 6
        dx = (x1 - x0) / n_seg
        road = [anc_top]
        for i in range(1, n_seg + 1):
            nodes.append([round(x0 + i * dx, 4), 0.0])
            road.append(len(nodes) - 1)
        for i in range(n_seg):
            members.append([road[i], road[i + 1], "road"])

        bot = [anc_bot]
        for i in range(1, n_seg):
            t = i / n_seg
            y = -2.0 - 0.2 * 4.0 * t * (1.0 - t)
            nodes.append([round(x0 + i * dx, 4), round(y, 4)])
            bot.append(len(nodes) - 1)
        bot.append(anc_pier)

        for i in range(n_seg):
            add_m(bot[i], bot[i + 1], "steel" if i in (2, 3) else "cable")
        for i in range(1, n_seg + 1):
            add_m(road[i], bot[i], "steel" if i in (2, 3, 4) else "wood")
        # Diagonals: Pratt truss
        for i in range(n_seg):
            if i < n_seg // 2:
                add_m(road[i], bot[i + 1], "steel" if i == 2 else "wood")
            else:
                add_m(bot[i], road[i + 1], "steel" if i == 3 else "wood")
        return road[-1]  # pier top node at (x1, 0)

    # Left side span: 0 -> 12
    P_L = build_side_span(0.0, 12.0, "A0", "A1", "A4")
    # Right side span: 36 -> 24
    P_R = build_side_span(36.0, 24.0, "A6", "A7", "A5")

    # Center drawbridge: 2 leaves of 5.95m (3 segments of 1.983m each)
    def build_leaf(x0, sign, P_hinge, anc_pier, hyd_group):
        n_leaf = 3
        dx = 5.95 / n_leaf
        road = [P_hinge]
        for i in range(1, n_leaf + 1):
            nodes.append([round(x0 + sign * i * dx, 4), 0.0])
            road.append(len(nodes) - 1)
        for i in range(n_leaf):
            members.append([road[i], road[i + 1], "road"])

        # Upper truss on leaf (2 nodes above road[1], road[2])
        top = []
        for i in range(1, n_leaf):
            nodes.append([round(x0 + sign * i * dx, 4), 1.8 if i == 1 else 1.4])
            top.append(len(nodes) - 1)

        add_m(P_hinge, top[0], "steel")
        add_m(top[0], top[1], "wood")
        add_m(road[1], top[0], "steel")
        add_m(road[2], top[1], "wood")
        add_m(top[0], road[2], "steel")
        add_m(top[1], road[3], "wood")

        # Hydraulic from anc_pier (y=-2) to road[1] (length = hypot(1.983, 2.0) = 2.817m)
        add_m(anc_pier, road[1], "hydraulic", hyd_group)

    build_leaf(12.0, 1.0, P_L, "A4", "L")
    build_leaf(24.0, -1.0, P_R, "A5", "R")

    sensors = [{"id": "h", "type": "horn"}]
    lights = [
        {"id": "L1", "x": 11.0, "dir": "right", "init": "green"},
        {"id": "L2", "x": 25.0, "dir": "left", "init": "green"},
    ]
    rules = [
        {"on": "h", "delay": 0.0, "do": "light", "light": "L1", "state": "red"},
        {"on": "h", "delay": 0.0, "do": "light", "light": "L2", "state": "red"},
        {"on": "h", "delay": 3.5, "do": "hyd", "group": "L", "ratio": ratio, "speed": speed, "accel": accel},
        {"on": "h", "delay": 3.5, "do": "hyd", "group": "R", "ratio": ratio, "speed": speed, "accel": accel},
        {"on": "h", "delay": 16.5, "do": "hyd", "group": "L", "ratio": 1.0, "speed": speed, "accel": accel},
        {"on": "h", "delay": 16.5, "do": "hyd", "group": "R", "ratio": 1.0, "speed": speed, "accel": accel},
        {"on": "h", "delay": 18.5, "do": "light", "light": "L1", "state": "green"},
        {"on": "h", "delay": 18.5, "do": "light", "light": "L2", "state": "green"},
    ]
    return {"nodes": nodes, "members": members, "sensors": sensors, "lights": lights, "rules": rules}


for ratio in [1.35, 1.38, 1.40, 1.32]:
    d = make_l6(ratio=ratio)
    ok, cost, msg = eval_design(d)
    print(f"ratio={ratio} ok={ok} cost={cost:.1f} {msg}")
    if ok:
        with open("submission/level6.json", "w") as f:
            json.dump(d, f, indent=2)
        break
