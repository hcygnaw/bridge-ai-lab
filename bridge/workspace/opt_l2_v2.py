import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bridge

lv = bridge.load_level("2")
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
            return False, P["cost"], f"fail {sc.get('name','')}"
        for mr in res.get("peak_members", []):
            if mr > max_ratio:
                max_ratio = mr
    return True, P["cost"], f"max_ratio={max_ratio:.3f}"


def make_l2_suspension(n_seg=12, tower_h=4.0, cable_mid_y=0.4, road_arch=0.3, under_truss=False):
    dx = 30.0 / n_seg
    nodes, members = [], []
    for i in range(1, n_seg):
        t = i / n_seg
        x = i * dx
        y = road_arch * 4.0 * t * (1.0 - t)
        nodes.append([round(x, 4), round(y, 4)])

    def top(i):
        return "A0" if i == 0 else ("A4" if i == n_seg else i - 1)

    for i in range(n_seg):
        members.append([top(i), top(i + 1), "road"])

    # Towers: mid node at y=tower_h/2 braced to A3/A7? No, cable backstay from T_top to A3/A7!
    nodes.append([0.0, tower_h * 0.5])
    T_Lm = len(nodes) - 1
    nodes.append([0.0, tower_h])
    T_L = len(nodes) - 1
    members.append(["A0", T_Lm, "steel"])
    members.append([T_Lm, T_L, "steel"])
    members.append(["A3", T_L, "cable"])
    members.append(["A3", T_Lm, "wood" if math.hypot(6, tower_h * 0.5) <= 2.99 else "cable"])

    nodes.append([30.0, tower_h * 0.5])
    T_Rm = len(nodes) - 1
    nodes.append([30.0, tower_h])
    T_R = len(nodes) - 1
    members.append(["A4", T_Rm, "steel"])
    members.append([T_Rm, T_R, "steel"])
    members.append(["A7", T_R, "cable"])
    members.append(["A7", T_Rm, "wood" if math.hypot(6, tower_h * 0.5) <= 2.99 else "cable"])

    cab = [T_L]
    for i in range(1, n_seg):
        t = i / n_seg
        u = (t - 0.5) * 2.0
        y = max(nodes[top(i)][1] + 0.35, cable_mid_y + (tower_h - cable_mid_y) * u * u)
        nodes.append([round(i * dx, 4), round(y, 4)])
        cab.append(len(nodes) - 1)
    cab.append(T_R)

    for i in range(len(cab) - 1):
        members.append([cab[i], cab[i + 1], "cable"])
    for i in range(1, n_seg):
        members.append([cab[i], top(i), "cable"])

    return {"nodes": nodes, "members": members}


def make_l2_wood_arch(n_seg=13, y_arch_mid=-0.8, y_road_mid=0.8):
    # All-wood arch from A1=(0,-4) to A5=(30,-4), upgrading only >2.99m or >100% members!
    dx = 30.0 / n_seg
    nodes, members = [], []
    for i in range(1, n_seg):
        t = i / n_seg
        nodes.append([round(i * dx, 4), round(y_road_mid * 4 * t * (1 - t), 4)])

    def top(i):
        return "A0" if i == 0 else ("A4" if i == n_seg else i - 1)

    for i in range(n_seg):
        members.append([top(i), top(i + 1), "road"])

    bot_s = len(nodes)
    for i in range(1, n_seg):
        t = i / n_seg
        y = -4.0 + (y_arch_mid - (-4.0)) * 4 * t * (1 - t)
        nodes.append([round(i * dx, 4), round(y, 4)])

    def bot(i):
        return "A1" if i == 0 else ("A5" if i == n_seg else bot_s + i - 1)

    def pt(u):
        return lv["anchors"][int(u[1:])] if isinstance(u, str) else nodes[u]

    def add_m(u, v, mat="wood"):
        L = math.hypot(pt(v)[0] - pt(u)[0], pt(v)[1] - pt(u)[1])
        if mat == "wood" and L > 2.99:
            mat = "steel"
        members.append([u, v, mat])

    for i in range(n_seg):
        add_m(bot(i), bot(i + 1), "wood")
    for i in range(1, n_seg):
        add_m(top(i), bot(i), "wood")
    for i in range(n_seg):
        if i < n_seg // 2:
            add_m(top(i), bot(i + 1), "wood")
        else:
            add_m(bot(i), top(i + 1), "wood")
    return {"nodes": nodes, "members": members}


best = (24124.2, None, "")
for th in [3.5, 4.5, 5.5]:
    for ra in [0.2, 0.5, 0.8]:
        d = make_l2_suspension(n_seg=12, tower_h=th, cable_mid_y=ra + 0.35, road_arch=ra)
        ok, cost, msg = eval_design(d)
        if ok:
            print(f"SUSP PASS: th={th} ra={ra} cost={cost:.1f} {msg}")
            if cost < best[0]:
                best = (cost, d, msg)

# Also greedy wood->steel arch
d_arch = make_l2_wood_arch(n_seg=13, y_arch_mid=-0.8, y_road_mid=0.8)
for step in range(20):
    P = bridge.parse_design(lv, d_arch)
    all_ok = True
    fb = None
    for sc in scenarios:
        res, _ = bridge.simulate(lv, P, sc)
        if not res["ok"]:
            all_ok = False
            for ev in res["events"]:
                parts = ev.split()
                if parts[1] == "BREAK":
                    idx = int(parts[2])
                    if d_arch["members"][idx][2] == "wood":
                        fb = (idx, float(parts[3]))
                        break
            if fb:
                break
    if all_ok:
        print(f"ARCH PASS: step={step} cost={P['cost']:.1f}")
        if P["cost"] < best[0]:
            best = (P["cost"], d_arch, f"arch step {step}")
        break
    if not fb:
        break
    idx, fval = fb
    d_arch["members"][idx][2] = "cable" if fval > 0 else "steel"

if best[1]:
    with open("submission/level2.json", "w") as f:
        json.dump(best[1], f, indent=2)
    print("NEW BEST SAVED for Level 2! cost =", best[0])
