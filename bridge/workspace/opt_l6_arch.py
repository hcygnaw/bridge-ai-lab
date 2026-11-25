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


def make_l6_arch(ratio=1.38, speed=2.0, accel=1.5, arch_mid_y=-0.6, use_a2=False):
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

    def build_side_span(x0, x1, anc_top, anc_bot, anc_pier):
        n_seg = 5
        dx = (x1 - x0) / n_seg
        road = [anc_top]
        for i in range(1, n_seg + 1):
            nodes.append([round(x0 + i * dx, 4), 0.0])
            road.append(len(nodes) - 1)
        for i in range(n_seg):
            members.append([road[i], road[i + 1], "road"])

        y0 = -4.0 if use_a2 else -2.0
        bot = [anc_bot]
        for i in range(1, n_seg):
            t = i / n_seg
            y_base = y0 * (1.0 - t) + (-2.0) * t
            y = y_base + (arch_mid_y - (-2.0 if not use_a2 else -3.0)) * 4.0 * t * (1.0 - t)
            if y < -1.75:
                y = -1.75
            nodes.append([round(x0 + i * dx, 4), round(y, 4)])
            bot.append(len(nodes) - 1)
        bot.append(anc_pier)

        for i in range(n_seg):
            add_m(bot[i], bot[i + 1], "steel")
        for i in range(1, n_seg + 1):
            add_m(road[i], bot[i], "steel" if i == n_seg else "wood")
        for i in range(n_seg):
            if i == 0:
                add_m(road[i], bot[i + 1], "wood")
            elif i in (1, 2):
                add_m(road[i], bot[i + 1], "steel")
            else:
                add_m(bot[i], road[i + 1], "steel" if i == 4 else "wood")
        return road[-1], road[-2]

    P_L, P_L_prev = build_side_span(0.0, 12.0, "A0", "A2" if use_a2 else "A1", "A4")
    P_R, P_R_prev = build_side_span(36.0, 24.0, "A6", "A8" if use_a2 else "A7", "A5")

    def build_leaf(x0, sign, P_hinge, P_prev, anc_pier, hyd_group):
        xs = [0.0, 1.5, 3.7, 5.95]
        road = [P_hinge]
        for x_off in xs[1:]:
            nodes.append([round(x0 + sign * x_off, 4), 0.0])
            road.append(len(nodes) - 1)
        for i in range(3):
            members.append([road[i], road[i + 1], "road"])

        top = []
        for i, y_t in [(1, 2.0), (2, 1.4)]:
            nodes.append([round(x0 + sign * xs[i], 4), y_t])
            top.append(len(nodes) - 1)

        add_m(P_hinge, top[0], "cable")
        add_m(P_prev, top[0], "cable")
        add_m(top[0], top[1], "cable")
        add_m(road[1], top[0], "steel")
        add_m(road[2], top[1], "wood")
        add_m(top[0], road[2], "steel")
        add_m(top[1], road[3], "wood")
        add_m(anc_pier, road[1], "hydraulic", hyd_group)

    build_leaf(12.0, 1.0, P_L, P_L_prev, "A4", "L")
    build_leaf(24.0, -1.0, P_R, P_R_prev, "A5", "R")

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


best = (float("inf"), None, "")
for use_a2 in [False]:
    for arch_mid_y in [-0.5, -0.6, -0.7]:
        for ratio in [1.38, 1.40, 1.42]:
            d = make_l6_arch(ratio=ratio, arch_mid_y=arch_mid_y, use_a2=use_a2)
            ok, cost, msg = eval_design(d)
            print(f"a2={use_a2} ym={arch_mid_y} r={ratio} ok={ok} cost={cost:.1f} {msg.splitlines()[0]}")
            if ok and cost < best[0]:
                best = (cost, d, msg)

if best[1]:
    with open("submission/level6.json", "w") as f:
        json.dump(best[1], f, indent=2)
    print("Saved submission/level6.json, cost =", best[0])
