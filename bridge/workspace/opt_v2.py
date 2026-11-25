import math
from opt_utils import eval_design, save_if_best


def opt_l1_v2():
    print("--- Opt L1 v2 ---")
    # 6-seg Pratt truss with depth <= 1.65 so diag <= 3.0m!
    for n_seg in [6, 7]:
        for d_end in [-1.2, -1.4, -1.6]:
            for d_mid in [-1.4, -1.65, -1.9, -2.2]:
                for bot_mat in ["wood", "cable"]:
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
                    for i in range(n_seg):
                        members.append([bot_ids[i], bot_ids[i + 1], bot_mat])
                    for i in range(1, n_seg):
                        members.append([top_ids[i], bot_ids[i], "wood"])
                    mid = n_seg // 2
                    for i in range(n_seg):
                        u, v = (top_ids[i], bot_ids[i + 1]) if i < mid else (bot_ids[i], top_ids[i + 1])
                        members.append([u, v, "wood"])
                    d = {"nodes": nodes, "members": members}
                    ok, cost, pk, _ = eval_design(1, d, quiet=True)
                    if ok:
                        save_if_best(1, d)

    # Also test shallow upward road arch with minimal ties to A1/A3!
    # Road from A0=(0,0) -> (15,0) arching up by +1.2m, braced by wood/cable to A1/A3 or flat wood tie!
    for n_seg in [6, 7]:
        for h in [0.8, 1.2, 1.6]:
            nodes, members = [], []
            for i in range(1, n_seg):
                t = i / n_seg
                nodes.append([round(15.0 * t, 4), round(h * 4 * t * (1 - t), 4)])
            top = ["A0"] + list(range(0, n_seg - 1)) + ["A2"]
            for i in range(n_seg):
                members.append([top[i], top[i + 1], "road"])
            # 1 or 2 central wood/cable struts to A1/A3? Let's put 3 bottom nodes at y=-0.8:
            b0 = len(nodes)
            nodes += [[3.75, -0.8], [7.5, -0.8], [11.25, -0.8]]
            members += [["A1", b0, "cable"], [b0, b0 + 1, "cable"], [b0 + 1, b0 + 2, "cable"], [b0 + 2, "A3", "cable"]]
            for bi, x_b in [(b0, 3.75), (b0 + 1, 7.5), (b0 + 2, 11.25)]:
                # connect to nearest 2 top nodes
                near = sorted(range(1, n_seg), key=lambda k: abs(nodes[top[k]][0] - x_b))[:2]
                for nk in near:
                    members.append([bi, top[nk], "wood"])
            d = {"nodes": nodes, "members": members}
            ok, cost, pk, _ = eval_design(1, d, quiet=True)
            if ok:
                save_if_best(1, d)


def opt_l3_v2():
    print("--- Opt L3 v2 ---")
    for n_h in [6, 7]:
        for depth in [-1.5, -1.75, -2.0]:
            for bot_mat in ["wood", "cable"]:
                for brace_mat in ["wood", "steel"]:
                    nodes, members = [], []
                    n_seg = 2 * n_h
                    for i in range(1, n_seg):
                        nodes.append([round(28.0 * i / n_seg, 4), 0.0])
                    top_ids = ["A0"] + list(range(0, n_seg - 1)) + ["A3"]
                    for i in range(n_seg):
                        members.append([top_ids[i], top_ids[i + 1], "road"])
                    mid_pier = len(nodes)
                    nodes.append([14.0, depth])
                    members.append(["A2", mid_pier, "wood" if abs(-4.0 - depth) <= 2.95 else "steel"])
                    members.append([mid_pier, top_ids[n_h], "wood"])
                    # Brace A2 to top[n_h-1] and top[n_h+1]
                    L_br = math.hypot(14.0 / n_h, 4.0)
                    if brace_mat == "wood" and L_br > 2.98:
                        continue
                    members.append(["A2", top_ids[n_h - 1], brace_mat])
                    members.append(["A2", top_ids[n_h + 1], brace_mat])
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
                            members.append([u, v, "wood"])
                    add_span(0, "A1", mid_pier, 0.0, 14.0)
                    add_span(n_h, mid_pier, "A4", 14.0, 28.0)
                    d = {"nodes": nodes, "members": members}
                    ok, cost, pk, _ = eval_design(3, d, quiet=True)
                    if ok:
                        save_if_best(3, d)


def opt_l2_v2():
    print("--- Opt L2 v2 ---")
    # Test cheaper steel+wood arch (wood verticals/diagonals where <= 2.98m, steel only on arch + tall verts!)
    for n_seg in [12, 13, 14]:
        for arch_top in [-0.5, -0.9, -1.3]:
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
                members.append([arch_ids[i], arch_ids[i + 1], "steel"])
            for i in range(1, n_seg):
                dy = abs(pos(arch_ids[i])[1])
                members.append([top_ids[i], arch_ids[i], "wood" if dy <= 2.95 else "steel"])
            mid = n_seg // 2
            for i in range(n_seg):
                u, v = (arch_ids[i], top_ids[i + 1]) if i < mid else (top_ids[i], arch_ids[i + 1])
                L = math.hypot(pos(u)[0] - pos(v)[0], pos(u)[1] - pos(v)[1])
                if L <= 5.95:
                    members.append([u, v, "wood" if L <= 2.95 else "steel"])
            d = {"nodes": nodes, "members": members}
            ok, cost, pk, _ = eval_design(2, d, quiet=True)
            if ok:
                save_if_best(2, d)

    # Also test cable-stayed + light wood truss for L2!
    for h_tow in [4.5, 5.5]:
        n_seg = 12
        nodes, members = [], []
        for i in range(1, n_seg): nodes.append([round(30.0 * i / n_seg, 4), 0.0])
        top = ["A0"] + list(range(0, n_seg - 1)) + ["A4"]
        for i in range(n_seg): members.append([top[i], top[i + 1], "road"])
        tl = len(nodes); nodes.append([0.0, h_tow])
        tr = len(nodes); nodes.append([30.0, h_tow])
        members += [["A0", tl, "steel"], [tl, "A3", "cable"], ["A4", tr, "steel"], [tr, "A7", "cable"]]
        for i in range(1, n_seg):
            if i <= 6: members.append([tl, top[i], "cable"])
            if i >= 6: members.append([tr, top[i], "cable"])
        # Stiffen deck with light wood bottom chord at y=-1.4!
        b0 = len(nodes)
        for i in range(1, n_seg): nodes.append([round(30.0 * i / n_seg, 4), -1.4])
        bot = ["A0"] + list(range(b0, b0 + n_seg - 1)) + ["A4"]
        # Wait: A0->bot[1] is 2.87m wood, A1=(0,-4) not needed!
        for i in range(n_seg): members.append([bot[i], bot[i + 1], "wood"])
        for i in range(1, n_seg): members.append([top[i], bot[i], "wood"])
        for i in range(1, n_seg - 1):
            u, v = (top[i], bot[i + 1]) if i < 6 else (bot[i], top[i + 1])
            members.append([u, v, "wood"])
        d = {"nodes": nodes, "members": members}
        ok, cost, pk, _ = eval_design(2, d, quiet=True)
        if ok:
            save_if_best(2, d)


def opt_l4_v2():
    print("--- Opt L4 v2 ---")
    # Level 4: currently 23,938! Use 3 segs of 2.5m on [0, 7.5] + wood/cable!
    for bot_mat in ["steel", "wood"]:
        for diag_mat in ["wood", "cable"]:
            for use_t0 in [True, False]:
                nodes, members = [], []
                def add_n(x, y):
                    nodes.append([round(x, 4), round(y, 4)])
                    return len(nodes) - 1
                def add_side(x0, xd, a_top, a_bot, a_back, hgrp):
                    xs = [2.5, 5.0, 7.5]
                    top = [a_top] + [add_n(x0 + xd * x, 0.0) for x in xs]
                    for i in range(3): members.append([top[i], top[i + 1], "road"])
                    bot = [a_bot] + [add_n(x0 + xd * x, -1.65) for x in xs]
                    for i in range(3):
                        members.append([bot[i], bot[i + 1], bot_mat])
                        members.append([top[i + 1], bot[i + 1], "wood"])
                        members.append([bot[i], top[i + 1], diag_mat])
                    tow = add_n(x0 + xd * 4.2, 2.3)
                    members.extend([[top[1], tow, "wood"], [top[2], tow, "wood"], [top[3], tow, "steel"], [tow, a_back, "cable"]])
                    if use_t0:
                        members.append([a_top, tow, "steel" if False else "cable"])  # 4.78m cable
                    piv = top[3]
                    l1 = add_n(x0 + xd * 9.7, 0.0); tip = add_n(x0 + xd * 11.93, 0.0)
                    members.extend([[piv, l1, "road"], [l1, tip, "road"]])
                    lu1 = add_n(x0 + xd * 8.8, 1.3); lu2 = add_n(x0 + xd * 10.5, 0.9)
                    members.extend([[piv, lu1, "steel"], [lu1, lu2, "wood"], [lu2, tip, "cable"],
                                    [lu1, l1, "wood"], [lu2, l1, "wood"]])
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
    opt_l1_v2()
    opt_l3_v2()
    opt_l2_v2()
    opt_l4_v2()
