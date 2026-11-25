import math
from opt_utils import eval_design, save_if_best


def make_l1_truss(n_seg=7, depth=-1.5, road_arch=0.0, bot_mat="wood", diag_mat="wood", vert_mat="wood"):
    # Anchors: A0=(0,0), A1=(0,-2), A2=(15,0), A3=(15,-2)
    nodes = []
    members = []
    for i in range(1, n_seg):
        t = i / n_seg
        x = 15.0 * t
        y = road_arch * 4.0 * t * (1.0 - t)
        nodes.append([round(x, 4), round(y, 4)])
    top_ids = ["A0"] + list(range(0, n_seg - 1)) + ["A2"]
    for i in range(n_seg):
        members.append([top_ids[i], top_ids[i + 1], "road"])

    b0 = len(nodes)
    for i in range(1, n_seg):
        t = i / n_seg
        x = 15.0 * t
        y = depth
        nodes.append([round(x, 4), round(y, 4)])
    bot_ids = ["A1"] + list(range(b0, b0 + n_seg - 1)) + ["A3"]
    for i in range(n_seg):
        members.append([bot_ids[i], bot_ids[i + 1], bot_mat])
    for i in range(1, n_seg):
        members.append([top_ids[i], bot_ids[i], vert_mat])
    mid = n_seg // 2
    for i in range(n_seg):
        if i < mid:
            members.append([bot_ids[i], top_ids[i + 1], diag_mat])
        else:
            members.append([top_ids[i], bot_ids[i + 1], diag_mat])
    return {"nodes": nodes, "members": members}


def make_l1_arch(n_seg=7, arch_y=1.4, tie_y=-1.2):
    # Parabolic/catenary arch from A1=(0,-2) and A3=(15,-2) or road arch itself!
    # Wait: let's try a standard Warren-like truss above OR below, or road arch + hangers to A1/A3
    nodes = []
    members = []
    for i in range(1, n_seg):
        t = i / n_seg
        x = 15.0 * t
        y = arch_y * 4.0 * t * (1.0 - t)
        nodes.append([round(x, 4), round(y, 4)])
    top_ids = ["A0"] + list(range(0, n_seg - 1)) + ["A2"]
    for i in range(n_seg):
        members.append([top_ids[i], top_ids[i + 1], "road"])
    # Bottom arch/chord from A1 to A3 peaking at tie_y
    b0 = len(nodes)
    for i in range(1, n_seg):
        t = i / n_seg
        x = 15.0 * t
        y = -2.0 + (tie_y + 2.0) * 4.0 * t * (1.0 - t)
        nodes.append([round(x, 4), round(y, 4)])
    bot_ids = ["A1"] + list(range(b0, b0 + n_seg - 1)) + ["A3"]
    for i in range(n_seg):
        members.append([bot_ids[i], bot_ids[i + 1], "wood"])
    for i in range(1, n_seg):
        members.append([top_ids[i], bot_ids[i], "wood"])
    mid = n_seg // 2
    for i in range(n_seg):
        if i < mid:
            members.append([bot_ids[i], top_ids[i + 1], "wood"])
        else:
            members.append([top_ids[i], bot_ids[i + 1], "wood"])
    return {"nodes": nodes, "members": members}


def make_l2_arch_truss(n_seg=14, arch_rise=5.0, deck_arch=0.0):
    # A0=(0,0), A1=(0,-4), A2=(0,-8), A3=(-6,0), A4=(30,0), A5=(30,-4), A6=(30,-8), A7=(36,0)
    # Two-chord arch from A1=(0,-4)..A5=(30,-4) or A2=(0,-8)..A6=(30,-8) rising up to near deck!
    nodes = []
    members = []
    for i in range(1, n_seg):
        t = i / n_seg
        x = 30.0 * t
        y = deck_arch * 4.0 * t * (1.0 - t)
        nodes.append([round(x, 4), round(y, 4)])
    top_ids = ["A0"] + list(range(0, n_seg - 1)) + ["A4"]
    for i in range(n_seg):
        members.append([top_ids[i], top_ids[i + 1], "road"])

    # Lower parabolic arch from A1=(0,-4) to A5=(30,-4) rising by arch_rise (peaking at -4 + arch_rise = -1.2)
    b0 = len(nodes)
    for i in range(1, n_seg):
        t = i / n_seg
        x = 30.0 * t
        y = -4.0 + arch_rise * 4.0 * t * (1.0 - t)
        nodes.append([round(x, 4), round(y, 4)])
    bot_ids = ["A1"] + list(range(b0, b0 + n_seg - 1)) + ["A5"]
    for i in range(n_seg):
        dx = 30.0 / n_seg
        members.append([bot_ids[i], bot_ids[i + 1], "steel" if i in (0, 1, n_seg - 2, n_seg - 1) else "wood"])
    for i in range(1, n_seg):
        members.append([top_ids[i], bot_ids[i], "wood"])
    mid = n_seg // 2
    for i in range(n_seg):
        if i < mid:
            members.append([bot_ids[i], top_ids[i + 1], "wood"])
        else:
            members.append([top_ids[i], bot_ids[i + 1], "wood"])
    return {"nodes": nodes, "members": members}


def make_l3_two_span(n_seg_half=7, depth=-1.8):
    # A0=(0,0), A1=(0,-2), A2=(14,-4), A3=(28,0), A4=(28,-2)
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
    members.append([mid_pier, top_ids[n_seg_half], "wood"])

    def span_truss(t_start, b_left, b_right, x0, x1):
        b_nodes = [b_left]
        for i in range(1, n_seg_half):
            t = i / n_seg_half
            x = x0 + (x1 - x0) * t
            y = depth
            idx = len(nodes)
            nodes.append([round(x, 4), round(y, 4)])
            b_nodes.append(idx)
        b_nodes.append(b_right)
        for i in range(n_seg_half):
            members.append([b_nodes[i], b_nodes[i + 1], "wood"])
        for i in range(1, n_seg_half):
            members.append([top_ids[t_start + i], b_nodes[i], "wood"])
        mid = n_seg_half // 2
        for i in range(n_seg_half):
            if i < mid:
                members.append([b_nodes[i], top_ids[t_start + i + 1], "wood"])
            else:
                members.append([top_ids[t_start + i], b_nodes[i + 1], "wood"])

    span_truss(0, "A1", mid_pier, 0.0, 14.0)
    span_truss(n_seg_half, mid_pier, "A4", 14.0, 28.0)
    return {"nodes": nodes, "members": members}


if __name__ == "__main__":
    for name, lv, fn in [
        ("L1 truss7", 1, make_l1_truss(7, -1.5, 0.0)),
        ("L1 arch7", 1, make_l1_arch(7, 1.0, -0.5)),
        ("L2 arch_truss", 2, make_l2_arch_truss(14, 2.8, 0.0)),
        ("L2 arch_truss2", 2, make_l2_arch_truss(14, 3.0, 1.0)),
        ("L3 two_span", 3, make_l3_two_span(7, -1.7)),
    ]:
        print(f"=== {name} ===")
        ok, cost, pk, _ = eval_design(lv, fn, quiet=False)
        print(f"  -> ok={ok}, cost={cost:.2f}, max_peak={pk*100:.1f}%")
        if ok:
            save_if_best(lv, fn)
