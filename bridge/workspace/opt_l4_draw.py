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


def make_drawbridge(n_leaf=5, truss_h=2.0, tower_h=2.5, ratio=0.55):
    # Left leaf: A0=(0,0) to (11.9, 0) in n_leaf segments
    # Right leaf: A3=(24,0) to (12.1, 0) in n_leaf segments
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

    # Left leaf road nodes: 1..n_leaf
    dx_L = 11.9 / n_leaf
    L_road = ["A0"]
    for i in range(1, n_leaf + 1):
        nodes.append([round(i * dx_L, 4), 0.0])
        L_road.append(len(nodes) - 1)
    for i in range(n_leaf):
        members.append([L_road[i], L_road[i + 1], "road"])

    # Left leaf upper truss nodes above i=1..n_leaf-1
    L_top = []
    for i in range(1, n_leaf):
        x = i * dx_L
        y = truss_h * (1.0 - 0.3 * (i / n_leaf))
        nodes.append([round(x, 4), round(y, 4)])
        L_top.append(len(nodes) - 1)

    # Connect L_top
    for i in range(len(L_top) - 1):
        add_m(L_top[i], L_top[i + 1], "wood")
    # Verticals & diagonals on left leaf (connect A0 to L_top[0] so leaf is a rigid truss pivoting around A0!)
    add_m("A0", L_top[0], "wood")
    for i in range(len(L_top)):
        add_m(L_road[i + 1], L_top[i], "wood")
        if i < len(L_top) - 1:
            add_m(L_top[i], L_road[i + 2], "wood")
    # Tip diagonal
    add_m(L_top[-1], L_road[-1], "wood")

    # Left tower (fixed): T_L = (0, tower_h), braced to A0=(0,0) and A2=(-4,0) or A10=(-2,0)
    nodes.append([0.0, tower_h])
    T_L = len(nodes) - 1
    add_m("A0", T_L, "wood")
    add_m("A10", T_L, "wood")
    add_m("A2", T_L, "steel")

    # Hydraulic from T_L to L_top[0] (or L_road[1])
    # Wait: T_L=(0, 2.5), L_road[1]=(2.38, 0) -> L=3.45m; L_top[0]=(2.38, 1.88) -> L=2.46m
    # If we connect hydraulic from T_L to L_top[0], at ratio=0.55 it's 2.46*0.55=1.35m!
    # Let's check angle: T_L=(0, 2.5), L_top[0]=(2.38, 1.88), dist from A0 to L_top[0] is hypot(2.38, 1.88)=3.03m.
    # Let's connect hydraulic from T_L to L_road[1] (dist=3.45m) AND a cable from T_L to L_top[-2] (or L_road[-1])?
    # Wait: if hydraulic is T_L -> L_road[1], when L_road[1] lifts, the whole leaf rotates around A0!
    add_m(T_L, L_road[1], "hydraulic", "L")
    # Cable stay from T_L to L_top[-1] for stiffness when closed (goes slack when lifted!)
    add_m(T_L, L_top[-1], "cable")

    # Right leaf road nodes: A3=(24,0) to (12.1, 0)
    R_road = ["A3"]
    for i in range(1, n_leaf + 1):
        nodes.append([round(24.0 - i * dx_L, 4), 0.0])
        R_road.append(len(nodes) - 1)
    for i in range(n_leaf):
        members.append([R_road[i], R_road[i + 1], "road"])

    R_top = []
    for i in range(1, n_leaf):
        x = 24.0 - i * dx_L
        y = truss_h * (1.0 - 0.3 * (i / n_leaf))
        nodes.append([round(x, 4), round(y, 4)])
        R_top.append(len(nodes) - 1)

    add_m("A3", R_top[0], "wood")
    for i in range(len(R_top) - 1):
        add_m(R_top[i], R_top[i + 1], "wood")
    for i in range(len(R_top)):
        add_m(R_road[i + 1], R_top[i], "wood")
        if i < len(R_top) - 1:
            add_m(R_top[i], R_road[i + 2], "wood")
    add_m(R_top[-1], R_road[-1], "wood")

    nodes.append([24.0, tower_h])
    T_R = len(nodes) - 1
    add_m("A3", T_R, "wood")
    add_m("A11", T_R, "wood")
    add_m("A5", T_R, "steel")

    add_m(T_R, R_road[1], "hydraulic", "R")
    add_m(T_R, R_top[-1], "cable")

    sensors = [{"id": "h", "type": "horn"}]
    lights = [
        {"id": "L1", "x": -1.0, "dir": "right", "init": "green"},
        {"id": "L2", "x": 25.0, "dir": "left", "init": "green"},
    ]
    rules = [
        {"on": "h", "delay": 0.0, "do": "light", "light": "L1", "state": "red"},
        {"on": "h", "delay": 0.0, "do": "light", "light": "L2", "state": "red"},
        {"on": "h", "delay": 4.5, "do": "hyd", "group": "L", "ratio": ratio, "speed": 2.5},
        {"on": "h", "delay": 4.5, "do": "hyd", "group": "R", "ratio": ratio, "speed": 2.5},
        {"on": "h", "delay": 16.5, "do": "hyd", "group": "L", "ratio": 1.0, "speed": 2.5},
        {"on": "h", "delay": 16.5, "do": "hyd", "group": "R", "ratio": 1.0, "speed": 2.5},
        {"on": "h", "delay": 18.5, "do": "light", "light": "L1", "state": "green"},
        {"on": "h", "delay": 18.5, "do": "light", "light": "L2", "state": "green"},
    ]
    return {"nodes": nodes, "members": members, "sensors": sensors, "lights": lights, "rules": rules}


for ratio in [0.55, 0.50, 0.60]:
    d = make_drawbridge(n_leaf=5, truss_h=2.0, tower_h=2.5, ratio=ratio)
    ok, cost, msg = eval_design(d)
    print(f"ratio={ratio} ok={ok} cost={cost:.1f} {msg}")
    if ok:
        with open("submission/level4.json", "w") as f:
            json.dump(d, f, indent=2)
        break
