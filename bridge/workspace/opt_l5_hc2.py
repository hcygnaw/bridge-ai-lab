import copy
import json
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bridge

lv = bridge.load_level("5")
scenarios = [bridge.load_json(p) for p in bridge.sample_paths(lv)]


def make_l5_v4(sp=0.58, th=2.55, tx_L=1.4, gap=2.3, ty=0.25, cm=0.15):
    nodes, members = [], []
    pit_xs = [-8.8, -6.6, -4.4, -2.2]
    pit_ys = [-sp * 0.667, -sp, -sp, -sp * 0.667]
    pit_nodes = ["A2"]
    for x, y in zip(pit_xs, pit_ys):
        nodes.append([x, round(y, 4)])
        pit_nodes.append(len(nodes) - 1)
    pit_nodes.append("A0")
    for i in range(5):
        members.append([pit_nodes[i], pit_nodes[i + 1], "road"])
    members.append(["A2", pit_nodes[2], "cable"])
    members.append([pit_nodes[3], "A0", "cable"])

    x_end = 24.0 - gap
    n_riv = math.ceil(x_end / 2.45)
    riv_nodes = ["A0"]
    for i in range(1, n_riv):
        t = i / n_riv
        nodes.append([round(x_end * t, 4), round(ty * t, 4)])
        riv_nodes.append(len(nodes) - 1)
    nodes.append([round(x_end, 4), ty])
    riv_nodes.append(len(nodes) - 1)
    for i in range(n_riv):
        members.append([riv_nodes[i], riv_nodes[i + 1], "road"])

    nodes.append([tx_L, th])
    T_L = len(nodes) - 1
    members.append(["A0", T_L, "steel"])
    members.append(["A3", T_L, "cable"])
    nodes.append([24.0, th])
    T_R = len(nodes) - 1
    members.append(["A7", T_R, "steel"])
    members.append(["A9", T_R, "cable"])

    cab = [T_L]
    for i in range(1, n_riv + 1):
        x = nodes[riv_nodes[i]][0]
        u = ((x - tx_L) / (24.0 - tx_L) - 0.5) * 2.0
        y = max(nodes[riv_nodes[i]][1] + 0.35, cm + (th - cm) * u * u)
        nodes.append([round(x, 4), round(y, 4)])
        cab.append(len(nodes) - 1)
    cab.append(T_R)
    for i in range(len(cab) - 1):
        members.append([cab[i], cab[i + 1], "cable"])
    for i in range(1, n_riv + 1):
        members.append([cab[i], riv_nodes[i], "cable"])
    return {"nodes": nodes, "members": members}


def score_design(d):
    try:
        P = bridge.parse_design(lv, d)
    except bridge.DesignError:
        return -1e9, False, float("inf")
    score = 0.0
    all_ok = True
    for sc in scenarios:
        res, _ = bridge.simulate(lv, P, sc, replay=False)
        if res["ok"]:
            score += 1000.0
        else:
            all_ok = False
        for v in res["vehicles"]:
            if v["status"] == 2:
                score += 200.0
            else:
                score += v["t"] * 5.0
        score -= res.get("broken", 0) * 15.0
        max_pk = max([m for m in res.get("peak_members", [0.0]) if m < 8.0] or [1.0])
        if max_pk > 0.95:
            score -= (max_pk - 0.95) * 100.0
    if all_ok:
        score += (10000.0 - P["cost"]) * 0.1
    return score, all_ok, P["cost"]


best_d = make_l5_v4(sp=0.58, th=2.50, tx_L=1.4, gap=2.4)
best_s, best_ok, best_cost = score_design(best_d)
print(f"Start: score={best_s:.2f}, ok={best_ok}, cost={best_cost:.1f}")

rng = random.Random(123)
n_nodes = len(best_d["nodes"])
for it in range(200):
    cand = copy.deepcopy(best_d)
    for _ in range(rng.choice([1, 1, 2])):
        ni = rng.randrange(n_nodes)
        cand["nodes"][ni][1] = round(cand["nodes"][ni][1] + rng.gauss(0, 0.07), 4)
        if ni in (0, 1, 2, 3, 12, 13, 14):
            cand["nodes"][ni][0] = round(cand["nodes"][ni][0] + rng.gauss(0, 0.05), 4)
    s, ok, cost = score_design(cand)
    if s > best_s:
        best_s, best_ok, best_cost = s, ok, cost
        best_d = cand
        print(f"Iter {it}: score={best_s:.2f}, ok={best_ok}, cost={best_cost:.1f}")
        if best_ok:
            with open("submission/level5.json", "w") as f:
                json.dump(best_d, f, indent=2)
            break
