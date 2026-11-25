import math
from opt_utils import eval_design, save_if_best


def make_l1_bowstring_above(n_seg=8, h_mid=3.0, top_mat="wood", hang_mat="cable", diag_mat="wood"):
    nodes = []
    members = []
    for i in range(1, n_seg):
        nodes.append([round(15.0 * i / n_seg, 4), 0.0])
    top_ids = ["A0"] + list(range(0, n_seg - 1)) + ["A2"]
    for i in range(n_seg):
        members.append([top_ids[i], top_ids[i + 1], "road"])

    a0 = len(nodes)
    for i in range(1, n_seg):
        t = i / n_seg
        x = 15.0 * t
        y = h_mid * 4.0 * t * (1.0 - t)
        nodes.append([round(x, 4), round(y, 4)])
    arch_ids = ["A0"] + list(range(a0, a0 + n_seg - 1)) + ["A2"]
    for i in range(n_seg):
        members.append([arch_ids[i], arch_ids[i + 1], top_mat])
    for i in range(1, n_seg):
        members.append([top_ids[i], arch_ids[i], hang_mat])
    mid = n_seg // 2
    for i in range(1, n_seg - 1):
        if i < mid:
            members.append([top_ids[i], arch_ids[i + 1], diag_mat])
        else:
            members.append([arch_ids[i], top_ids[i + 1], diag_mat])
    return {"nodes": nodes, "members": members}


def make_l1_fishbelly(n_seg=7, sag=-3.5, bot_mat="cable", strut_mat="wood", diag_mat="wood"):
    nodes = []
    members = []
    for i in range(1, n_seg):
        nodes.append([round(15.0 * i / n_seg, 4), 0.0])
    top_ids = ["A0"] + list(range(0, n_seg - 1)) + ["A2"]
    for i in range(n_seg):
        members.append([top_ids[i], top_ids[i + 1], "road"])

    b0 = len(nodes)
    for i in range(1, n_seg):
        t = i / n_seg
        x = 15.0 * t
        y = sag * 4.0 * t * (1.0 - t)
        nodes.append([round(x, 4), round(y, 4)])
    bot_ids = ["A0"] + list(range(b0, b0 + n_seg - 1)) + ["A2"]
    for i in range(n_seg):
        members.append([bot_ids[i], bot_ids[i + 1], bot_mat])
    for i in range(1, n_seg):
        members.append([top_ids[i], bot_ids[i], strut_mat])
    mid = n_seg // 2
    for i in range(1, n_seg - 1):
        if i < mid:
            members.append([top_ids[i], bot_ids[i + 1], diag_mat])
        else:
            members.append([bot_ids[i], top_ids[i + 1], diag_mat])
    return {"nodes": nodes, "members": members}


def make_l2_bowstring(n_seg=14, h_mid=6.0, top_mat="steel", hang_mat="cable", diag_mat="wood"):
    nodes = []
    members = []
    for i in range(1, n_seg):
        nodes.append([round(30.0 * i / n_seg, 4), 0.0])
    top_ids = ["A0"] + list(range(0, n_seg - 1)) + ["A4"]
    for i in range(n_seg):
        members.append([top_ids[i], top_ids[i + 1], "road"])

    a0 = len(nodes)
    for i in range(1, n_seg):
        t = i / n_seg
        x = 30.0 * t
        y = h_mid * 4.0 * t * (1.0 - t)
        nodes.append([round(x, 4), round(y, 4)])
    arch_ids = ["A0"] + list(range(a0, a0 + n_seg - 1)) + ["A4"]
    for i in range(n_seg):
        members.append([arch_ids[i], arch_ids[i + 1], top_mat])
    for i in range(1, n_seg):
        members.append([top_ids[i], arch_ids[i], hang_mat])
    mid = n_seg // 2
    for i in range(1, n_seg - 1):
        if i < mid:
            members.append([top_ids[i], arch_ids[i + 1], diag_mat])
        else:
            members.append([arch_ids[i], top_ids[i + 1], diag_mat])
    return {"nodes": nodes, "members": members}


def make_l2_deck_arch(n_seg=14, arch_top=-0.6):
    nodes = []
    members = []
    for i in range(1, n_seg):
        nodes.append([round(30.0 * i / n_seg, 4), 0.0])
    top_ids = ["A0"] + list(range(0, n_seg - 1)) + ["A4"]
    for i in range(n_seg):
        members.append([top_ids[i], top_ids[i + 1], "road"])

    a0 = len(nodes)
    for i in range(1, n_seg):
        t = i / n_seg
        x = 30.0 * t
        y = -8.0 + (arch_top + 8.0) * 4.0 * t * (1.0 - t)
        nodes.append([round(x, 4), round(y, 4)])
    arch_ids = ["A2"] + list(range(a0, a0 + n_seg - 1)) + ["A6"]
    for i in range(n_seg):
        members.append([arch_ids[i], arch_ids[i + 1], "steel"])
    for i in range(1, n_seg):
        dy = abs(nodes[arch_ids[i]][1] - 0.0)
        mat = "wood" if dy <= 2.9 else "steel"
        members.append([top_ids[i], arch_ids[i], mat])
    mid = n_seg // 2
    for i in range(n_seg):
        u, v = (arch_ids[i], top_ids[i + 1]) if i < mid else (top_ids[i], arch_ids[i + 1])
        x1, y1 = (0.0, -8.0) if u == "A2" else ((30.0, -8.0) if u == "A6" else ((0.0, 0.0) if u == "A0" else ((30.0, 0.0) if u == "A4" else nodes[u])))
        x2, y2 = (0.0, -8.0) if v == "A2" else ((30.0, -8.0) if v == "A6" else ((0.0, 0.0) if v == "A0" else ((30.0, 0.0) if v == "A4" else nodes[v])))
        L = math.hypot(x2 - x1, y2 - y1)
        if L <= 5.9:
            members.append([u, v, "wood" if L <= 2.9 else "steel"])
    return {"nodes": nodes, "members": members}


def make_l3_bowstring(n_seg_half=6, h_mid=3.2):
    nodes = []
    members = []
    n_seg = 2 * n_seg_half
    for i in range(1, n_seg):
        nodes.append([round(28.0 * i / n_seg, 4), 0.0])
    top_ids = ["A0"] + list(range(0, n_seg - 1)) + ["A3"]
    for i in range(n_seg):
        members.append([top_ids[i], top_ids[i + 1], "road"])

    mid_pier = len(nodes)
    nodes.append([14.0, -2.0])
    members.append(["A2", mid_pier, "steel"])
    members.append([mid_pier, top_ids[n_seg_half], "steel"])
    members.append(["A2", top_ids[n_seg_half - 1], "steel"])
    members.append(["A2", top_ids[n_seg_half + 1], "steel"])

    def add_arch(t_start, x0, x1):
        a0 = len(nodes)
        for i in range(1, n_seg_half):
            t = i / n_seg_half
            x = x0 + (x1 - x0) * t
            y = h_mid * 4.0 * t * (1.0 - t)
            nodes.append([round(x, 4), round(y, 4)])
        a_ids = [top_ids[t_start]] + list(range(a0, a0 + n_seg_half - 1)) + [top_ids[t_start + n_seg_half]]
        for i in range(n_seg_half):
            members.append([a_ids[i], a_ids[i + 1], "steel" if i in (0, n_seg_half - 1) else "wood"])
        for i in range(1, n_seg_half):
            members.append([top_ids[t_start + i], a_ids[i], "cable"])
        mid = n_seg_half // 2
        for i in range(1, n_seg_half - 1):
            u, v = (top_ids[t_start + i], a_ids[i + 1]) if i < mid else (a_ids[i], top_ids[t_start + i + 1])
            L = math.hypot(nodes[u][0] - nodes[v][0], nodes[u][1] - nodes[v][1])
            members.append([u, v, "wood" if L <= 2.95 else "steel"])

    add_arch(0, 0.0, 14.0)
    add_arch(n_seg_half, 14.0, 28.0)
    return {"nodes": nodes, "members": members}


if __name__ == "__main__":
    tests = [
        ("L1 bowstring(8,3.0,wood,cable,cable)", 1, make_l1_bowstring_above(8, 3.0, "wood", "cable", "cable")),
        ("L1 bowstring(8,3.0,steel,cable,wood)", 1, make_l1_bowstring_above(8, 3.0, "steel", "cable", "wood")),
        ("L1 fishbelly(7,-3.5,cable,wood,cable)", 1, make_l1_fishbelly(7, -3.5, "cable", "wood", "cable")),
        ("L1 fishbelly(7,-3.5,cable,wood,wood)", 1, make_l1_fishbelly(7, -3.5, "cable", "wood", "wood")),
        ("L2 bowstring(14,6.0)", 2, make_l2_bowstring(14, 6.0, "steel", "cable", "wood")),
        ("L2 deck_arch(14,-0.6)", 2, make_l2_deck_arch(14, -0.6)),
        ("L3 bowstring(6,3.2)", 3, make_l3_bowstring(6, 3.2)),
    ]
    for name, lv, d in tests:
        print(f"=== {name} ===")
        ok, cost, pk, _ = eval_design(lv, d, quiet=False)
        print(f"  -> ok={ok}, cost={cost:.2f}, max_peak={pk*100:.1f}%")
        if ok:
            save_if_best(lv, d)
