import json, math, sys
from pathlib import Path

WS = Path(__file__).resolve().parent
sys.path.insert(0, str(WS))
import bridge
from opt_util import eval_design, save_if_better

SUB = WS / "submission"
SUB.mkdir(exist_ok=True)

# ================= LEVEL 4: Static High Bridge over y=6 =================
# Anchors: A0=(0,0), A1=(0,-2), A2=(-4,0), A3=(24,0), A4=(24,-2), A5=(28,0),
# A6=(-12,0), A7=(-10,0), A8=(-8,0), A9=(-6,0), A10=(-2,0),
# A11=(26,0), A12=(30,0), A13=(32,0), A14=(34,0), A15=(36,0)
ANCHORS_4 = {
    -12: "A6", -10: "A7", -8: "A8", -6: "A9", -4: "A2", -2: "A10", 0: "A0",
    24: "A3", 26: "A11", 28: "A5", 30: "A12", 32: "A13", 34: "A14", 36: "A15"
}

def dist(a, b):
    return math.hypot(a[0]-b[0], a[1]-b[1])

def mat_for(p1, p2, pref="wood"):
    L = dist(p1, p2)
    if pref == "wood" and L <= 3.0:
        return "wood"
    if L <= 6.0:
        return "steel"
    return "cable"

def l4_high_bridge(start_x=-12, crest_y=6.25, arch_drop=1.5, curve_exp=0.85, mat="wood"):
    # Symmetric bridge from x=start_x to x=24-start_x (e.g. -12 to 36, total 48m)
    # Channel is x in [9, 15], y in [-2, 6].
    # Road points every ~2.0m (from start_x to 24-start_x)
    end_x = 24 - start_x
    span = end_x - start_x # e.g. 48
    n_seg = int(round(span / 2.0))
    # Use exact x = start_x + 2*i
    xs = [start_x + 2.0 * i for i in range(n_seg + 1)]
    def road_y(x):
        # distance from nearest start/end
        d = min(x - start_x, end_x - x)
        ramp_len = 9.0 - start_x # 21.0
        if d <= 0:
            return 0.0
        if d >= ramp_len:
            # slight arch over channel [9, 15]
            u = (x - 12.0) / 3.0 # -1..1
            return crest_y + 0.15 * (1.0 - u*u)
        t = d / ramp_len
        # Concave curve (steeper at bottom where vehicle has speed, gentler at top)
        return crest_y * (1.0 - (1.0 - t) ** (1.0 / curve_exp)) if curve_exp < 1.0 else crest_y * (t ** curve_exp)

    nodes = []
    members = []
    road_ids = []
    for i, x in enumerate(xs):
        if i == 0:
            road_ids.append(ANCHORS_4[int(round(x))])
        elif i == len(xs) - 1:
            road_ids.append(ANCHORS_4[int(round(x))])
        else:
            rid = len(nodes)
            nodes.append([round(x, 4), round(road_y(x), 4)])
            road_ids.append(rid)

    def pos(ref):
        if isinstance(ref, str):
            # lookup anchor
            lv = bridge.load_level("4")
            idx = int(ref[1:])
            return tuple(lv["anchors"][idx])
        return tuple(nodes[ref])

    # Road members
    for i in range(n_seg):
        members.append([road_ids[i], road_ids[i+1], "road"])

    # Support structure:
    # 1. On left ramp (x <= 0) and right ramp (x >= 24), vertical + diagonal struts directly to ground anchors!
    # 2. Over water (0 < x < 24):
    #    - Outside channel (x in [2, 8] and [16, 22]), build an arch/truss down to A0/A1 and A3/A4!
    #    - Inside channel (x in [9, 15]), ALL members must stay ABOVE y = 6.05!
    #      So use an UPPER Warren truss over the middle [6, 18] (above the road!) and under-support on the ramps!
    # Wait: even simpler! Build an UPPER truss from x=0 to x=24 (all above road, so over [9,15] it's at y >= 6.25 > 6.0!),
    # plus vertical/diagonal piers down to ground anchors on x <= 0 and x >= 24!
    top_ids = []
    for i in range(n_seg):
        xm = 0.5 * (xs[i] + xs[i+1])
        ym = 0.5 * (pos(road_ids[i])[1] + pos(road_ids[i+1])[1]) + arch_drop
        if 0 <= xm <= 24:
            tid = len(nodes)
            nodes.append([round(xm, 4), round(ym, 4)])
            top_ids.append((i, tid))
            members.append([road_ids[i], tid, mat_for(pos(road_ids[i]), nodes[tid], mat)])
            members.append([road_ids[i+1], tid, mat_for(pos(road_ids[i+1]), nodes[tid], mat)])
    for j in range(len(top_ids) - 1):
        t1 = top_ids[j][1]
        t2 = top_ids[j+1][1]
        members.append([t1, t2, mat_for(nodes[t1], nodes[t2], "steel" if mat=="steel" else mat)])

    # Support ramps x <= 0 and x >= 24 directly from ground anchors!
    for i, x in enumerate(xs):
        if i == 0 or i == len(xs) - 1:
            continue
        xi = int(round(x))
        if xi in ANCHORS_4:
            anc = ANCHORS_4[xi]
            p_anc = pos(anc)
            p_rd = pos(road_ids[i])
            L = dist(p_anc, p_rd)
            if L <= 3.0:
                members.append([anc, road_ids[i], "wood"])
            elif L <= 6.0:
                # 2 wood pieces or 1 steel
                mid = len(nodes)
                nodes.append([p_anc[0], round(0.5*(p_anc[1]+p_rd[1]), 4)])
                members.append([anc, mid, "wood"])
                members.append([mid, road_ids[i], "wood"])
                # brace mid to adjacent anchor if exists
                if xi - 2 in ANCHORS_4 and dist(pos(ANCHORS_4[xi-2]), nodes[mid]) <= 3.0:
                    members.append([ANCHORS_4[xi-2], mid, "wood"])
                if xi + 2 in ANCHORS_4 and dist(pos(ANCHORS_4[xi+2]), nodes[mid]) <= 3.0:
                    members.append([ANCHORS_4[xi+2], mid, "wood"])
            else:
                members.append([anc, road_ids[i], "steel"])
            # diagonal to prev road node
            if i > 1 and dist(p_anc, pos(road_ids[i-1])) <= 3.0:
                members.append([anc, road_ids[i-1], "wood"])
            if i < len(xs) - 2 and dist(p_anc, pos(road_ids[i+1])) <= 3.0:
                members.append([anc, road_ids[i+1], "wood"])

    # Also brace x=2,4,6 down to A0=(0,0) and A1=(0,-2) (staying outside x>=9!)
    # And x=22,20,18 down to A3=(24,0) and A4=(24,-2) (staying outside x<=15!)
    # Add diagonal knee braces from A0=(0,0) to road(x=2,4) and A3=(24,0) to road(x=22,20)
    idx_0 = xs.index(0.0)
    idx_24 = xs.index(24.0)
    # Knee brace from A0 to mid-node on x=2..4
    for dx, anc_a, anc_b, sgn in [(0, "A0", "A1", 1), (0, "A3", "A4", -1)]:
        base_i = idx_0 if sgn == 1 else idx_24
        # road node at x=2 (or 22)
        r2 = road_ids[base_i + sgn]
        r4 = road_ids[base_i + 2*sgn]
        r6 = road_ids[base_i + 3*sgn]
        # Intermediate arch node at x=4 (or 20), y=2.5
        k1 = len(nodes)
        nodes.append([0.0 + 4.0*sgn if sgn==1 else 24.0 + 4.0*sgn, 2.5])
        members.append([anc_a, k1, mat_for(pos(anc_a), nodes[k1], "steel")])
        members.append([k1, r4, mat_for(nodes[k1], pos(r4), "steel")])
        members.append([k1, r6, mat_for(nodes[k1], pos(r6), "steel")])
        members.append([k1, r2, mat_for(nodes[k1], pos(r2), "wood")])

    return {"nodes": nodes, "members": members}

print("=== LEVEL 4 HIGH BRIDGE TEST ===", flush=True)
best4 = None
for ce in [0.7, 0.85, 1.0]:
    for ad in [1.8, 2.2]:
        for mat in ["wood", "steel"]:
            d = l4_high_bridge(-12, 6.25, ad, ce, mat)
            ok, cost, pk, msgs = eval_design(4, d)
            print(f"  ce={ce} ad={ad} {mat}: ok={ok} cost={cost} pk={pk*100:.1f}% | {msgs[0][:60]}", flush=True)
            if ok and (best4 is None or cost < best4[0]):
                best4 = (cost, d)
                save_if_better(4, d, SUB / "level4.json")

if best4:
    print("\n=== BEST L4 ===")
    eval_design(4, best4[1], verbose=True)
