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


def make_arch_l5(arch_h=1.2, n_riv=14):
    nodes = []
    members = []

    # Pit: flat with V-pier at (-5.5, 0) from A5=(-6,-4) and A4=(-4,-4)
    # 5 segments of 2.2m: -11, -8.8, -6.6, -4.4, -2.2, 0
    # Put pit_nodes[2] at (-5.5, 0) -> segments: 2.75? No, max_len=2.5!
    # -11, -8.8, -6.6, -5.0, -2.5, 0 -> 2.2, 2.2, 1.6, 2.5, 2.5!
    pit_xs = [-8.8, -6.6, -5.0, -2.5]
    pit_nodes = ["A2"]
    for x in pit_xs:
        nodes.append([x, 0.0])
        pit_nodes.append(len(nodes) - 1)
    pit_nodes.append("A0")
    for i in range(len(pit_nodes) - 1):
        members.append([pit_nodes[i], pit_nodes[i + 1], "road"])
    # V-pier to pit_nodes[3] (-5.0, 0)
    members.append(["A5", pit_nodes[3], "steel"])
    members.append(["A4", pit_nodes[3], "steel"])
    # Also brace pit_nodes[1] (-8.8, 0) to A6=(-8,-4)? No, let's test with/without
    # Actually, (-11,0)->(-8.8,0)->(-6.6,0)->(-5.0,0) has 2 free hinges unless braced!
    # Wait: if pit_nodes[1..2] are slightly sagged (-0.2) or supported by cable from A2 to pit_nodes[3]?
    # Let's check!

    # River: road arch from A0=(0,0) to A7=(24,0)
    riv_nodes = ["A0"]
    for i in range(1, n_riv):
        t = i / n_riv
        x = 24.0 * t
        y = arch_h * 4.0 * t * (1.0 - t)
        nodes.append([round(x, 4), round(y, 4)])
        riv_nodes.append(len(nodes) - 1)
    riv_nodes.append("A7")
    for i in range(n_riv):
        members.append([riv_nodes[i], riv_nodes[i + 1], "road"])

    # Cable ties from A1=(0,-2) and A8=(24,-2) to prevent arch buckling/snap-through
    for idx in [3, 6, 9]:
        if idx < n_riv:
            if idx <= n_riv // 2:
                members.append(["A1", riv_nodes[idx], "cable"])
            if idx >= n_riv // 2:
                members.append(["A8", riv_nodes[idx], "cable"])

    return {"nodes": nodes, "members": members}


for arch_h in [1.0, 1.4, 1.8]:
    d = make_arch_l5(arch_h=arch_h, n_riv=12)
    ok, cost, msg = eval_design(d)
    print(f"arch_h={arch_h} ok={ok} cost={cost:.1f} {msg.splitlines()[0]}")
    if ok:
        with open("submission/level5.json", "w") as f:
            json.dump(d, f, indent=2)
        break
