import copy
import json
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bridge
import opt_l5_v3

lv = bridge.load_level("5")
scenarios = [bridge.load_json(p) for p in bridge.sample_paths(lv)]


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
                # Reward survival time before failing
                score += v["t"] * 5.0
        # Penalize broken members
        score -= res.get("broken", 0) * 15.0
        # Penalize high peak stress
        max_pk = max([m for m in res.get("peak_members", [0.0]) if m < 8.0] or [1.0])
        if max_pk > 0.95:
            score -= (max_pk - 0.95) * 100.0
    if all_ok:
        score += (10000.0 - P["cost"]) * 0.1
    return score, all_ok, P["cost"]


best_d = opt_l5_v3.make_susp_jump(sag_pit=0.55, sag_riv=0.0, tower_h=2.8, cable_mid_y=0.2, jump_gap=2.0, tip_y=0.2)
best_s, best_ok, best_cost = score_design(best_d)
print(f"Start: score={best_s:.2f}, ok={best_ok}, cost={best_cost:.1f}")

rng = random.Random(42)
n_nodes = len(best_d["nodes"])

for it in range(250):
    cand = copy.deepcopy(best_d)
    # Perturb 1 to 3 nodes' y (and occasionally x)
    k = rng.choice([1, 1, 2])
    for _ in range(k):
        ni = rng.randrange(n_nodes)
        step_y = rng.gauss(0, 0.08 if it < 150 else 0.04)
        cand["nodes"][ni][1] = round(cand["nodes"][ni][1] + step_y, 4)
        if ni in (4 + 9, 4 + 9 + 1, 4 + 9 + 2):  # tip or towers
            cand["nodes"][ni][0] = round(cand["nodes"][ni][0] + rng.gauss(0, 0.05), 4)
    s, ok, cost = score_design(cand)
    if s > best_s:
        best_s, best_ok, best_cost = s, ok, cost
        best_d = cand
        print(f"Iter {it}: score={best_s:.2f}, ok={best_ok}, cost={best_cost:.1f}")
        if best_ok:
            with open("submission/level5.json", "w") as f:
                json.dump(best_d, f, indent=2)
            if it > 100:
                break
