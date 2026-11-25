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


def make_cat(sag_pit=0.55, sag_riv=1.2, n_pit=5, n_riv=10):
    nodes = []
    members = []

    pit_nodes = ["A2"]
    for i in range(1, n_pit):
        t = i / n_pit
        nodes.append([round(-11.0 + 11.0 * t, 4), round(-sag_pit * 4.0 * t * (1.0 - t), 4)])
        pit_nodes.append(len(nodes) - 1)
    pit_nodes.append("A0")
    for i in range(n_pit):
        members.append([pit_nodes[i], pit_nodes[i + 1], "road"])
    # Pit reinforcing cable skipping every other node
    members.append(["A2", pit_nodes[2], "cable"])
    members.append([pit_nodes[2], pit_nodes[4], "cable"])
    if n_pit > 5:
        members.append([pit_nodes[4], "A0", "cable"])
    else:
        members.append([pit_nodes[3], "A0", "cable"])

    riv_nodes = ["A0"]
    for i in range(1, n_riv):
        t = i / n_riv
        nodes.append([round(24.0 * t, 4), round(-sag_riv * 4.0 * t * (1.0 - t), 4)])
        riv_nodes.append(len(nodes) - 1)
    riv_nodes.append("A7")
    for i in range(n_riv):
        members.append([riv_nodes[i], riv_nodes[i + 1], "road"])

    # River reinforcing cable from A1=(0,-2) -> riv[2] -> riv[4] -> ... -> A8=(24,-2)
    # Wait: A1=(0,-2) is below A0=(0,0), so A1->riv[2] pulls DOWN?
    # Better: A0 -> riv[2] -> riv[4] -> riv[6] -> riv[8] -> A7!
    # Check no duplicate pairs: A0->riv[2] is not a road member (road is A0->riv[1]->riv[2])!
    cab_pts = ["A0"] + [riv_nodes[i] for i in range(2, n_riv, 2)] + ["A7"]
    for i in range(len(cab_pts) - 1):
        if cab_pts[i] != cab_pts[i + 1]:
            members.append([cab_pts[i], cab_pts[i + 1], "cable"])

    return {"nodes": nodes, "members": members}


best = (float("inf"), None, "")
for sag_pit in [0.45, 0.55]:
    for sag_riv in [0.8, 1.0, 1.2, 1.4, 1.6]:
        for n_riv in [10, 11, 12]:
            d = make_cat(sag_pit=sag_pit, sag_riv=sag_riv, n_pit=5, n_riv=n_riv)
            ok, cost, msg = eval_design(d)
            print(f"sp={sag_pit} sr={sag_riv} nr={n_riv} ok={ok} cost={cost:.1f} {msg.splitlines()[0]}")
            if ok and cost < best[0]:
                best = (cost, d, msg)

if best[1]:
    with open("submission/level5.json", "w") as f:
        json.dump(best[1], f, indent=2)
    print("Saved submission/level5.json, cost =", best[0])
