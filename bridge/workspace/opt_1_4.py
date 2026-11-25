import json
import math
import bridge as B
from opt_utils import eval_design, save_if_best


def opt_l1():
    print("--- Optimizing L1 ---")
    # Test Pratt trusses with varying n_seg, depth, parabolic sag, and cable/wood bottom chord!
    for n_seg in [6, 7, 8]:
        for d_end in [-1.4, -1.7, -2.0]:
            for d_mid in [-1.4, -1.8, -2.2, -2.6]:
                for bot_mat in ["wood", "cable"]:
                    for diag_mat in ["wood", "cable"]:
                        nodes, members = [], []
                        for i in range(1, n_seg):
                            nodes.append([round(15.0 * i / n_seg, 4), 0.0])
                        top_ids = ["A0"] + list(range(0, n_seg - 1)) + ["A2"]
                        for i in range(n_seg):
                            members.append([top_ids[i], top_ids[i + 1], "road"])
                        b0 = len(nodes)
                        for i in range(1, n_seg):
                            t = i / n_seg
                            y = d_end + (d_mid - d_end) * 4 * t * (1 - t)
                            nodes.append([round(15.0 * t, 4), round(y, 4)])
                        bot_ids = ["A1"] + list(range(b0, b0 + n_seg - 1)) + ["A3"]
                        # Check if A1->bot[1] etc are valid
                        for i in range(n_seg):
                            members.append([bot_ids[i], bot_ids[i + 1], bot_mat])
                        for i in range(1, n_seg):
                            members.append([top_ids[i], bot_ids[i], "wood"])
                        mid = n_seg // 2
                        for i in range(n_seg):
                            u, v = (top_ids[i], bot_ids[i + 1]) if i < mid else (bot_ids[i], top_ids[i + 1])
                            members.append([u, v, diag_mat])
                        d = {"nodes": nodes, "members": members}
                        ok, cost, pk, _ = eval_design(1, d, quiet=True)
                        if ok:
                            save_if_best(1, d)

    # Also test sparse underslung wood/cable truss (fewer bottom nodes!)
    # E.g. 6 road segs (2.5m each), only 3 bottom nodes at x=3.75, 7.5, 11.25!
    for n_seg in [6, 7]:
        for dy in [-1.8, -2.2, -2.6]:
            nodes, members = [], []
            for i in range(1, n_seg):
                nodes.append([round(15.0 * i / n_seg, 4), 0.0])
            top = ["A0"] + list(range(0, n_seg - 1)) + ["A2"]
            for i in range(n_seg):
                members.append([top[i], top[i + 1], "road"])
            # 2 or 3 bottom nodes:
            if n_seg == 6:
                b0 = len(nodes)
                nodes += [[3.75, dy], [7.5, dy - 0.3], [11.25, dy]]
                # A1=(0,-2)->b0 is >3m (3.75m -> cable!), b0->b1->b2 (cable!), b2->A3 (cable!)
                members += [["A1", b0, "cable"], [b0, b0 + 1, "cable"], [b0 + 1, b0 + 2, "cable"], [b0 + 2, "A3", "cable"]]
                # Struts from b0 to top[1](2.5), top[2](5.0); b0+1 to top[3](7.5); b0+2 to top[4](10.0), top[5](12.5)
                members += [[b0, top[1], "wood"], [b0, top[2], "wood"],
                            [b0 + 1, top[2], "wood"], [b0 + 1, top[3], "wood"], [b0 + 1, top[4], "wood"],
                            [b0 + 2, top[4], "wood"], [b0 + 2, top[5], "wood"]]
                d = {"nodes": nodes, "members": members}
                ok, cost, pk, _ = eval_design(1, d, quiet=True)
                if ok:
                    save_if_best(1, d)


def opt_l3():
    print("--- Optimizing L3 ---")
    # Level 3: 28m with A2=(14,-4). Currently cost=9975 with n_seg_half=7, all wood except 2 steel at pier.
    for n_h in [6, 7]:
        for depth in [-1.5, -1.8, -2.1]:
            for bot_mat in ["wood", "cable"]:
                for diag_mat in ["wood", "cable"]:
                    for pier_mat in ["wood", "steel"]:
                        nodes, members = [], []
                        n_seg = 2 * n_h
                        for i in range(1, n_seg):
                            nodes.append([round(28.0 * i / n_seg, 4), 0.0])
                        top_ids = ["A0"] + list(range(0, n_seg - 1)) + ["A3"]
                        for i in range(n_seg):
                            members.append([top_ids[i], top_ids[i + 1], "road"])
                        mid_pier = len(nodes)
                        nodes.append([14.0, depth])
                        members.append(["A2", mid_pier, pier_mat])
                        members.append([mid_pier, top_ids[n_h], "wood"])
                        # Brace A2=(14,-4) to top[n_h-1] and top[n_h+1]? Wait: length ~4.5m -> steel, or only if needed!
                        # Actually brace mid_pier=(14, depth) to b_nodes adjacent!
                        def add_span(t_start, b_left, b_right, x0, x1):
                            b_nodes = [b_left]
                            for i in range(1, n_h):
                                t = i / n_h
                                idx = len(nodes)
                                nodes.append([round(x0 + (x1 - x0) * t, 4), depth])
                                b_nodes.append(idx)
                            b_nodes.append(b_right)
                            for i in range(n_h):
                                members.append([b_nodes[i], b_nodes[i + 1], bot_mat])
                            for i in range(1, n_h):
                                members.append([top_ids[t_start + i], b_nodes[i], "wood"])
                            mid = n_h // 2
                            for i in range(n_h):
                                u, v = (top_ids[t_start + i], b_nodes[i + 1]) if i < mid else (b_nodes[i], top_ids[t_start + i + 1])
                                members.append([u, v, diag_mat])

                        add_span(0, "A1", mid_pier, 0.0, 14.0)
                        add_span(n_h, mid_pier, "A4", 14.0, 28.0)
                        d = {"nodes": nodes, "members": members}
                        ok, cost, pk, _ = eval_design(3, d, quiet=True)
                        if ok:
                            save_if_best(3, d)


def opt_l2():
    print("--- Optimizing L2 ---")
    # Level 2: 30m canyon, currently cost=18,310 with A1->A5 steel arch + steel verticals/diags!
    # Replace steel verticals/diags with wood (<= 3.0m!) and wood/cable where tension!
    for n_seg in [12, 13, 14]:
        for arch_top in [-0.6, -1.0, -1.4]:
            for arch_mat in ["steel", "wood"]:
                for diag_mode in ["wood_if_fit", "cable_tension"]:
                    nodes, members = [], []
                    for i in range(1, n_seg):
                        nodes.append([round(30.0 * i / n_seg, 4), 0.0])
                    top_ids = ["A0"] + list(range(0, n_seg - 1)) + ["A4"]
                    for i in range(n_seg):
                        members.append([top_ids[i], top_ids[i + 1], "road"])
                    a0 = len(nodes)
                    for i in range(1, n_seg):
                        t = i / n_seg
                        y = -4.0 + (arch_top + 4.0) * 4 * t * (1 - t)
                        nodes.append([round(30.0 * t, 4), round(y, 4)])
                    arch_ids = ["A1"] + list(range(a0, a0 + n_seg - 1)) + ["A5"]
                    def pos(u):
                        if u == "A0": return (0.0, 0.0)
                        if u == "A1": return (0.0, -4.0)
                        if u == "A4": return (30.0, 0.0)
                        if u == "A5": return (30.0, -4.0)
                        return nodes[u]
                    for i in range(n_seg):
                        L = math.hypot(pos(arch_ids[i])[0]-pos(arch_ids[i+1])[0], pos(arch_ids[i])[1]-pos(arch_ids[i+1])[1])
                        mat = arch_mat if (arch_mat == "steel" or L <= 2.98) else "steel"
                        members.append([arch_ids[i], arch_ids[i + 1], mat])
                    for i in range(1, n_seg):
                        dy = abs(pos(arch_ids[i])[1])
                        members.append([top_ids[i], arch_ids[i], "wood" if dy <= 2.95 else "steel"])
                    mid = n_seg // 2
                    for i in range(n_seg):
                        # Only add diagonals in outer panels or all panels
                        u, v = (arch_ids[i], top_ids[i + 1]) if i < mid else (top_ids[i], arch_ids[i + 1])
                        L = math.hypot(pos(u)[0]-pos(v)[0], pos(u)[1]-pos(v)[1])
                        if L <= 5.95:
                            members.append([u, v, "wood" if L <= 2.95 else "steel"])
                        if diag_mode == "cable_tension" and 1 <= i <= n_seg - 2:
                            u2, v2 = (top_ids[i], arch_ids[i + 1]) if i < mid else (arch_ids[i], top_ids[i + 1])
                            members.append([u2, v2, "cable"])
                    d = {"nodes": nodes, "members": members}
                    ok, cost, pk, _ = eval_design(2, d, quiet=True)
                    if ok:
                        save_if_best(2, d)


def opt_l4():
    print("--- Optimizing L4 ---")
    # Level 4: currently 23,938! Can easily drop below 15,000 by replacing steel with wood/cable on [0, 7.5]!
    for app_mat in ["wood", "cable"]:
        for bot_mat in ["wood", "steel"]:
            for leaf_steel in [(0,), ()]:
                for use_t0 in [False, True]:
                    nodes, members = [], []
                    def add_n(x, y):
                        nodes.append([round(x, 4), round(y, 4)])
                        return len(nodes) - 1
                    def add_side(x0, xd, a_top, a_bot, a_back, hgrp):
                        xs = [2.5, 5.0, 7.5]  # 3 segs of 2.5m instead of 4 segs of 1.875m!!
                        top = [a_top] + [add_n(x0 + xd * x, 0.0) for x in xs]
                        for i in range(3): members.append([top[i], top[i + 1], "road"])
                        bot = [a_bot] + [add_n(x0 + xd * x, -1.8) for x in xs]
                        for i in range(3):
                            members.append([bot[i], bot[i + 1], bot_mat])
                            members.append([top[i + 1], bot[i + 1], "wood"])
                            # Pratt tension diagonal top[i]->bot[i+1] (or bot[i]->top[i+1] for cantilever!)
                            # Wait: [0, 7.5] is a CANTILEVER when leaf is loaded, so top[i]->bot[i+1] is comp, bot[i]->top[i+1] is TENSION?
                            # No: load at tip pulls top[3] down -> top[0..3] is TENSION, bot[0..3] is COMPRESSION, top[i]->bot[i+1] is COMPRESSION, bot[i]->top[i+1] is TENSION!
                            members.append([bot[i], top[i + 1], app_mat])
                        # Tower at (4.5, 2.8) supported by top[1]=(2.5,0), top[2]=(5.0,0), top[3]=(7.5,0) and backstay to a_back!
                        tow = add_n(x0 + xd * 4.5, 2.8)
                        members.extend([[top[1], tow, "wood"], [top[2], tow, "wood"], [top[3], tow, "steel"], [tow, a_back, "cable"]])
                        if use_t0:
                            members.append([tow, a_top, "cable"])
                        # Leaf [7.5, 11.93]
                        piv = top[3]
                        l1 = add_n(x0 + xd * 9.7, 0.0); tip = add_n(x0 + xd * 11.93, 0.0)
                        members.extend([[piv, l1, "road"], [l1, tip, "road"]])
                        lu1 = add_n(x0 + xd * 8.8, 1.3); lu2 = add_n(x0 + xd * 10.5, 0.9)
                        members.extend([
                            [piv, lu1, "steel" if 0 in leaf_steel else "wood"],
                            [lu1, lu2, "wood"], [lu2, tip, "cable"],
                            [lu1, l1, "wood"], [lu2, l1, "wood"],
                        ])
                        members.append([tow, lu1, "hydraulic", hgrp])
                    add_side(0.0, 1.0, "A0", "A1", "A2", "L")
                    add_side(24.0, -1.0, "A3", "A4", "A5", "R")
                    d = {
                        "nodes": nodes, "members": members,
                        "sensors": [{"id": "h", "type": "horn"}],
                        "lights": [{"id": "LL", "x": -1.0, "dir": "right", "init": "green"}, {"id": "LR", "x": 25.0, "dir": "left", "init": "green"}],
                        "rules": [
                            {"on": "h", "delay": 6.5, "do": "light", "light": "LL", "state": "red"},
                            {"on": "h", "delay": 6.5, "do": "light", "light": "LR", "state": "red"},
                            {"on": "h", "delay": 7.5, "do": "hyd", "group": "L", "ratio": 0.50, "speed": 2.5},
                            {"on": "h", "delay": 7.5, "do": "hyd", "group": "R", "ratio": 0.50, "speed": 2.5},
                            {"on": "h", "delay": 16.2, "do": "hyd", "group": "L", "ratio": 1.0, "speed": 2.5},
                            {"on": "h", "delay": 16.2, "do": "hyd", "group": "R", "ratio": 1.0, "speed": 2.5},
                            {"on": "h", "delay": 18.5, "do": "light", "light": "LL", "state": "green"},
                            {"on": "h", "delay": 18.5, "do": "light", "light": "LR", "state": "green"},
                        ]
                    }
                    ok, cost, pk, _ = eval_design(4, d, quiet=True)
                    if ok:
                        save_if_best(4, d)


if __name__ == "__main__":
    opt_l1()
    opt_l3()
    opt_l2()
    opt_l4()
