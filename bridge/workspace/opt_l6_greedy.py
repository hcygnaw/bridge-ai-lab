import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bridge

lv = bridge.load_level("6")
scenarios = [bridge.load_json(p) for p in bridge.sample_paths(lv)]


def build_warren_base(top_h=1.8, y_t0=2.0, ratio=1.38):
    nodes, members = [], []

    def pt(u):
        return lv["anchors"][int(u[1:])] if isinstance(u, str) else nodes[u]

    def dist(u, v):
        p1, p2 = pt(u), pt(v)
        return math.hypot(p2[0] - p1[0], p2[1] - p1[1])

    def add_m(u, v, mat="wood", g=None):
        if mat == "wood" and dist(u, v) > 2.99:
            mat = "steel"
        members.append([u, v, mat, g] if g else [u, v, mat])

    def side(x0, sgn, at, ab, ap):
        n = 6
        dx = 12.0 / n
        road = [at]
        for i in range(1, n + 1):
            nodes.append([round(x0 + sgn * i * dx, 4), 0.0])
            road.append(len(nodes) - 1)
        for i in range(n):
            members.append([road[i], road[i + 1], "road"])
        top = []
        for i in range(n):
            xo = (i + 0.5) * dx
            t = xo / 12.0
            u = (t - 0.5) * 2.0
            y = top_h * (1.0 - 0.1 * u * u)
            nodes.append([round(x0 + sgn * xo, 4), round(y, 4)])
            top.append(len(nodes) - 1)
        for i in range(n - 1):
            add_m(top[i], top[i + 1], "steel")
        for i in range(n):
            add_m(road[i], top[i], "wood")
            add_m(top[i], road[i + 1], "wood")
        add_m(ap, road[-1], "steel")
        add_m(ap, road[-2], "wood")
        return road[-1], top[-1]

    PL, PL_top = side(0.0, 1.0, "A0", "A1", "A4")
    PR, PR_top = side(36.0, -1.0, "A6", "A7", "A5")

    def leaf(x0, sgn, ph, pt_prev, ap, hg):
        xs = [0.0, 1.95, 3.95, 5.95]
        road = [ph]
        for xo in xs[1:]:
            nodes.append([round(x0 + sgn * xo, 4), 0.0])
            road.append(len(nodes) - 1)
        for i in range(3):
            members.append([road[i], road[i + 1], "road"])
        top = []
        for i, yt in [(1, y_t0), (2, 1.4)]:
            nodes.append([round(x0 + sgn * xs[i], 4), yt])
            top.append(len(nodes) - 1)
        add_m(ph, top[0], "cable")
        add_m(pt_prev, top[0], "cable")
        add_m(top[0], top[1], "cable")
        add_m(road[1], top[0], "steel")
        add_m(road[2], top[1], "wood")
        add_m(top[0], road[2], "steel")
        add_m(top[1], road[3], "wood")
        add_m(ap, road[1], "hydraulic", hg)

    leaf(12.0, 1.0, PL, PL_top, "A4", "L")
    leaf(24.0, -1.0, PR, PR_top, "A5", "R")
    return {
        "nodes": nodes,
        "members": members,
        "sensors": [{"id": "h", "type": "horn"}],
        "lights": [
            {"id": "L1", "x": 11.0, "dir": "right", "init": "green"},
            {"id": "L2", "x": 25.0, "dir": "left", "init": "green"},
        ],
        "rules": [
            {"on": "h", "delay": 0.0, "do": "light", "light": "L1", "state": "red"},
            {"on": "h", "delay": 0.0, "do": "light", "light": "L2", "state": "red"},
            {"on": "h", "delay": 3.5, "do": "hyd", "group": "L", "ratio": ratio, "speed": 2.0, "accel": 1.5},
            {"on": "h", "delay": 3.5, "do": "hyd", "group": "R", "ratio": ratio, "speed": 2.0, "accel": 1.5},
            {"on": "h", "delay": 16.5, "do": "hyd", "group": "L", "ratio": 1.0, "speed": 2.0, "accel": 1.5},
            {"on": "h", "delay": 16.5, "do": "hyd", "group": "R", "ratio": 1.0, "speed": 2.0, "accel": 1.5},
            {"on": "h", "delay": 18.5, "do": "light", "light": "L1", "state": "green"},
            {"on": "h", "delay": 18.5, "do": "light", "light": "L2", "state": "green"},
        ],
    }


d = build_warren_base(top_h=1.8, y_t0=2.05)
lv_no_budget = dict(lv, budget=100000)

for step in range(25):
    P = bridge.parse_design(lv_no_budget, d)
    all_ok = True
    first_break = None
    for sc in scenarios:
        res, _ = bridge.simulate(lv_no_budget, P, sc)
        if not res["ok"]:
            all_ok = False
            for ev in res["events"]:
                parts = ev.split()
                if parts[1] == "BREAK":
                    idx = int(parts[2])
                    force = float(parts[3])
                    if d["members"][idx][2] == "wood":
                        first_break = (idx, force, sc["name"])
                        break
            if first_break:
                break
    print(f"Step {step}: cost={P['cost']:.1f}, all_ok={all_ok}, first_break={first_break}")
    if all_ok:
        if P["cost"] <= 20000:
            with open("submission/level6.json", "w") as f:
                json.dump(d, f, indent=2)
            print("SAVED submission/level6.json!")
        break
    if not first_break:
        print("Non-wood break! Stopping.")
        for sc in scenarios:
            res, _ = bridge.simulate(lv_no_budget, P, sc)
            if not res["ok"]:
                print(sc["name"], res["events"][:10])
        break
    idx, force, _ = first_break
    d["members"][idx][2] = "cable" if force > 0 else "steel"
