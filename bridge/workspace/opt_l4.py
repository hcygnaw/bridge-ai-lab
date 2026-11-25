import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bridge

lv = bridge.load_level("4")
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


def make_high_bridge(y_mid=6.3, arch_rise=1.5):
    # Ramp from A6=(-12, 0) up to (9, y_mid) .. (15, y_mid) .. down to A15=(36, 0)
    # Total x from -12 to 36 is 48m.
    # Let's place road nodes every 2.4m (20 segments -> 48/20 = 2.4m <= 2.5m!)
    # Anchors on ground:
    # A6=(-12,0), A7=(-10,0), A8=(-8,0), A9=(-6,0), A2=(-4,0), A10=(-2,0), A0=(0,0), A1=(0,-2)
    # A3=(24,0), A4=(24,-2), A11=(26,0), A5=(28,0), A12=(30,0), A13=(32,0), A14=(34,0), A15=(36,0)
    # Wait: if we start the ramp at A6=(-12,0) and end at A15=(36,0), we can support the ramps directly from the ground anchors!
    # And for the 24m span (0..24), we have an arch/truss above the road, or below the road (as long as x in [9,15] has all members y > 6.05)!
    # Wait: if the road in [9, 15] is at y = 6.3, and the truss is ABOVE the road (y = 6.3 to 9.0), then NOTHING is below y = 6.3 in [9, 15]!
    # Let's make road nodes from x=-12 to x=36:
    # -12 to 8.4: 9 segments of ~2.27m? Let's just do 20 segments of 2.4m: x = -12 + 2.4*i for i=0..20 (ends at 36)
    # Wait: i=8 is x=7.2, i=9 is x=9.6, i=10 is x=12.0, i=11 is x=14.4, i=12 is x=16.8.
    # At x=7.2 and x=16.8, y needs to be >= 6.05 so the segment 7.2->9.6 doesn't dip below 6.0 at x=9!
    # Actually if y(x) = y_mid * (1 - ((x-12)/24)^2) or piecewise linear:
    # -12..8: linear from 0 to y_mid (slope = y_mid/20 = 6.3/20 = 0.315 -> 17.5 deg)
    # 8..16: flat at y_mid
    # 16..36: linear from y_mid to 0
    # Let's smooth the corners at x=8 and x=16 slightly so cars don't bounce!
    n_seg = 22
    dx = 48.0 / n_seg  # 2.1818m
    nodes = []
    members = []

    def road_y(x):
        if x <= 8.0:
            t = (x - (-12.0)) / 20.0
            return y_mid * t
        elif x >= 16.0:
            t = (36.0 - x) / 20.0
            return y_mid * t
        else:
            t = (x - 12.0) / 4.0
            return y_mid + 0.2 * (1.0 - t * t)

    for i in range(1, n_seg):
        x = -12.0 + i * dx
        nodes.append([round(x, 4), round(road_y(x), 4)])

    def top(i):
        if i == 0:
            return "A6"
        if i == n_seg:
            return "A15"
        return i - 1

    for i in range(n_seg):
        members.append([top(i), top(i + 1), "road"])

    def pt(u):
        if isinstance(u, str):
            return lv["anchors"][int(u[1:])]
        return nodes[u]

    def dist(u, v):
        p1, p2 = pt(u), pt(v)
        return math.hypot(p2[0] - p1[0], p2[1] - p1[1])

    def add_m(u, v, mat="wood"):
        L = dist(u, v)
        if L < 0.3:
            return
        if mat == "wood" and L > 2.99:
            mat = "steel"
        members.append([u, v, mat])

    # Support left ramp (-12 to 0) using ground anchors
    left_anchors = ["A6", "A7", "A8", "A9", "A2", "A10", "A0"]
    for i in range(1, 6):
        # connect to 2 closest anchors
        ancs = sorted(left_anchors, key=lambda a: dist(top(i), a))
        add_m(top(i), ancs[0], "wood")
        add_m(top(i), ancs[1], "wood")

    # Right ramp (24 to 36)
    right_anchors = ["A3", "A11", "A5", "A12", "A13", "A14", "A15"]
    for i in range(n_seg - 5, n_seg):
        ancs = sorted(right_anchors, key=lambda a: dist(top(i), a))
        add_m(top(i), ancs[0], "wood")
        add_m(top(i), ancs[1], "wood")

    # Over-truss from i=5 to i=n_seg-5 (x ~ -1.1 to 25.1)
    i0 = 5
    i1 = n_seg - 5
    uc_start = len(nodes)
    for i in range(i0, i1 + 1):
        x = -12.0 + i * dx
        ry = road_y(x)
        nodes.append([round(x, 4), round(ry + arch_rise, 4)])

    def uc(i):
        return uc_start + (i - i0)

    for i in range(i0, i1):
        add_m(uc(i), uc(i + 1), "wood")
    for i in range(i0, i1 + 1):
        add_m(top(i), uc(i), "wood")
    mid = (i0 + i1) // 2
    for i in range(i0, i1):
        if i < mid:
            add_m(top(i), uc(i + 1), "wood")
        else:
            add_m(uc(i), top(i + 1), "wood")

    add_m(top(i0 - 1), uc(i0), "wood")
    add_m(top(i1 + 1), uc(i1), "wood")

    return {"nodes": nodes, "members": members}


best = (float("inf"), None, "")
for y_mid in [6.2, 6.4, 6.6]:
    for arch_rise in [2.0, 2.5, 3.0]:
        d = make_high_bridge(y_mid=y_mid, arch_rise=arch_rise)
        ok, cost, msg = eval_design(d)
        print(f"y_mid={y_mid} rise={arch_rise} ok={ok} cost={cost:.1f} {msg[:120]}")
        if ok and cost < best[0]:
            best = (cost, d, msg)

if best[1]:
    with open("submission/level4.json", "w") as f:
        json.dump(best[1], f, indent=2)
    print("Saved submission/level4.json, cost =", best[0])
