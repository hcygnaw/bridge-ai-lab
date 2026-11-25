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


def make_ribbon(sag_pit=1.0, sag_river=2.5, n_pit=5, n_river=11, reinforce_cable=False):
    nodes = []
    members = []

    # Pit: A2=(-11, 0) to A0=(0, 0)
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

    # River: A0=(0, 0) to A7=(24, 0)
    riv_nodes = ["A0"]
    for i in range(1, n_river):
        t = i / n_river
        x = 24.0 * t
        y = -sag_river * 4.0 * t * (1.0 - t)
        nodes.append([round(x, 4), round(y, 4)])
        riv_nodes.append(len(nodes) - 1)
    riv_nodes.append("A7")
    for i in range(n_river):
        members.append([riv_nodes[i], riv_nodes[i + 1], "road"])

    if reinforce_cable:
        # Single cable under the river from A1=(0,-2) to A8=(24,-2)? Or A0 to mid to A7
        members.append(["A0", riv_nodes[n_river // 2], "cable"])
        members.append([riv_nodes[n_river // 2], "A7", "cable"])

    return {"nodes": nodes, "members": members}


best = (float("inf"), None, "")
for sag_pit in [0.8, 1.2, 1.6]:
    for sag_river in [1.8, 2.2, 2.6, 3.0, 3.5]:
        for rc in [False, True]:
            d = make_ribbon(sag_pit=sag_pit, sag_river=sag_river, reinforce_cable=rc)
            ok, cost, msg = eval_design(d)
            if ok:
                print(f"PASS: pit={sag_pit} riv={sag_river} rc={rc} cost={cost:.1f} {msg}")
                if cost < best[0]:
                    best = (cost, d, msg)
            else:
                print(f"FAIL: pit={sag_pit} riv={sag_river} rc={rc} cost={cost:.1f} {msg.splitlines()[0]}")

if best[1]:
    with open("submission/level5.json", "w") as f:
        json.dump(best[1], f, indent=2)
    print("Saved submission/level5.json, cost =", best[0])
