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


def make_cable_stayed(sag_pit=0.5, tower_h=3.0, jump_gap=0.0, arch_river=0.2):
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

    # River: A0=(0,0) to x_end = 24.0 - jump_gap
    x_end = 24.0 - jump_gap
    n_riv = math.ceil(x_end / 2.45)
    riv_nodes = ["A0"]
    for i in range(1, n_riv):
        t = i / n_riv
        x = x_end * t
        y = arch_river * 4.0 * t * (1.0 - t)
        nodes.append([round(x, 4), round(y, 4)])
        riv_nodes.append(len(nodes) - 1)
    if jump_gap == 0.0:
        riv_nodes.append("A7")
    else:
        # Ramp tip slightly up
        nodes.append([round(x_end, 4), 0.35])
        riv_nodes.append(len(nodes) - 1)

    for i in range(n_riv):
        members.append([riv_nodes[i], riv_nodes[i + 1], "road"])

    # Towers at (0, tower_h) and (24, tower_h)
    nodes.append([0.0, tower_h])
    T_L = len(nodes) - 1
    members.append(["A0", T_L, "steel"])
    members.append(["A2", T_L, "cable"])

    nodes.append([24.0, tower_h])
    T_R = len(nodes) - 1
    members.append(["A7", T_R, "steel"])
    members.append(["A9", T_R, "cable"])

    # Forestays from T_L to riv_nodes[2], riv_nodes[4] (or evenly spaced)
    # and from T_R to riv_nodes[-3], riv_nodes[-5]
    # Let's stay every 2nd node!
    mid = n_riv // 2
    for idx in range(2, mid + 1, 2):
        members.append([T_L, riv_nodes[idx], "cable"])
    for idx in range(mid + 1, n_riv - (1 if jump_gap == 0.0 else 0), 2):
        members.append([T_R, riv_nodes[idx], "cable"])
    if jump_gap > 0.0:
        members.append([T_R, riv_nodes[-1], "cable"])

    return {"nodes": nodes, "members": members}


best = (float("inf"), None, "")
for sag_pit in [0.4, 0.55]:
    for tower_h in [2.5, 3.0, 3.5]:
        for jump_gap in [0.0, 2.0, 3.0]:
            d = make_cable_stayed(sag_pit=sag_pit, tower_h=tower_h, jump_gap=jump_gap)
            ok, cost, msg = eval_design(d)
            print(f"pit={sag_pit} h={tower_h} gap={jump_gap} ok={ok} cost={cost:.1f} {msg.splitlines()[0]}")
            if ok and cost < best[0]:
                best = (cost, d, msg)

if best[1]:
    with open("submission/level5.json", "w") as f:
        json.dump(best[1], f, indent=2)
    print("Saved submission/level5.json, cost =", best[0])
