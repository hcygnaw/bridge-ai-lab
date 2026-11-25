import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bridge

lv = bridge.load_level("5")
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


def make_suspension(sag_pit=0.55, sag_riv=0.3, tower_h=2.0, cable_mid_y=0.35, n_riv=10):
    nodes = []
    members = []

    # Pit: A2=(-11,0) to A0=(0,0) in 5 segments
    n_pit = 5
    pit_nodes = ["A2"]
    for i in range(1, n_pit):
        t = i / n_pit
        x = -11.0 + 11.0 * t
        y = -sag_pit * 4.0 * t * (1.0 - t)
        nodes.append([round(x, 4), round(y, 4)])
        pit_nodes.append(len(nodes) - 1)
    pit_nodes.append("A0")
    for i in range(n_pit):
        members.append([pit_nodes[i], pit_nodes[i + 1], "road"])

    # River: A0=(0,0) to A7=(24,0) in n_riv segments
    riv_nodes = ["A0"]
    for i in range(1, n_riv):
        t = i / n_riv
        x = 24.0 * t
        y = -sag_riv * 4.0 * t * (1.0 - t)
        nodes.append([round(x, 4), round(y, 4)])
        riv_nodes.append(len(nodes) - 1)
    riv_nodes.append("A7")
    for i in range(n_riv):
        members.append([riv_nodes[i], riv_nodes[i + 1], "road"])

    # Towers at (0, tower_h) and (24, tower_h)
    nodes.append([0.0, tower_h])
    T_L = len(nodes) - 1
    members.append(["A0", T_L, "steel"])
    members.append(["A3", T_L, "cable"])

    nodes.append([24.0, tower_h])
    T_R = len(nodes) - 1
    members.append(["A7", T_R, "steel"])
    members.append(["A9", T_R, "cable"])

    # Main suspension cable nodes above riv_nodes[1..n_riv-1]
    cab_nodes = [T_L]
    for i in range(1, n_riv):
        t = i / n_riv
        x = 24.0 * t
        # parabola from tower_h at t=0,1 to cable_mid_y at t=0.5
        u = (t - 0.5) * 2.0
        y = cable_mid_y + (tower_h - cable_mid_y) * (u * u)
        nodes.append([round(x, 4), round(y, 4)])
        cab_nodes.append(len(nodes) - 1)
    cab_nodes.append(T_R)

    for i in range(n_riv):
        members.append([cab_nodes[i], cab_nodes[i + 1], "cable"])
    for i in range(1, n_riv):
        members.append([cab_nodes[i], riv_nodes[i], "cable"])

    return {"nodes": nodes, "members": members}


best = (float("inf"), None, "")
for tower_h in [2.6, 2.8, 3.0]:
    for sag_riv in [-0.2, -0.4, -0.6, -0.8]:
        for cable_mid_y in [0.6, 0.9, 1.2]:
            if cable_mid_y <= -sag_riv + 0.35:
                continue
            d = make_suspension(sag_pit=0.55, sag_riv=sag_riv, tower_h=tower_h, cable_mid_y=cable_mid_y)
            ok, cost, msg = eval_design(d)
            print(f"th={tower_h} sr={sag_riv} cm={cable_mid_y} ok={ok} cost={cost:.1f} {msg.splitlines()[0]}")
            if ok and cost < best[0]:
                best = (cost, d, msg)

if best[1]:
    with open("submission/level5.json", "w") as f:
        json.dump(best[1], f, indent=2)
    print("Saved submission/level5.json, cost =", best[0])
