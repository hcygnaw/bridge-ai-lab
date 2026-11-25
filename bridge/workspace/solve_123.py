import json, math, sys
from pathlib import Path

WS = Path(__file__).resolve().parent
sys.path.insert(0, str(WS))
import bridge
from opt_util import eval_design, save_if_better

SUB = WS / "submission"
SUB.mkdir(exist_ok=True)

def make_catenary_road(span, n_seg, sag, anchor_l="A0", anchor_r="A2", end_dx=0.0):
    # Parabolic curve y(x) = -4 * sag * (x/span) * (1 - x/span)
    # If sag < 0, it's an upward arch!
    nodes = []
    members = []
    for i in range(1, n_seg):
        t = i / n_seg
        x = span * t
        y = -4.0 * sag * t * (1.0 - t)
        nodes.append([round(x, 4), round(y, 4)])
    for i in range(n_seg):
        u = anchor_l if i == 0 else i - 1
        v = anchor_r if i == n_seg - 1 else i
        members.append([u, v, "road"])
    return {"nodes": nodes, "members": members}

def make_gap_catenary(span, n_seg, sag, gap_idx, anchor_l="A0", anchor_r="A2"):
    # Remove one road segment? No, that breaks tension!
    pass

print("=== LEVEL 1: Pure Catenary / Arch Road Sweep ===")
best1 = None
for n_seg in [6, 7, 8]:
    for sag in [round(-1.5 + 0.1 * k, 2) for k in range(36)]:
        if abs(sag) < 0.05:
            continue
        d = make_catenary_road(15.0, n_seg, sag, "A0", "A2")
        ok, cost, pk, _ = eval_design(1, d)
        if ok:
            if best1 is None or cost < best1[0]:
                best1 = (cost, n_seg, sag, pk, d)
                print(f"  L1 PASS: cost={cost:.1f}, n={n_seg}, sag={sag}, peak={pk*100:.1f}%")
if best1:
    save_if_better(1, best1[4], SUB / "level1.json")
    eval_design(1, best1[4], verbose=True)

print("\n=== LEVEL 2: Pure Catenary / Arch Road Sweep ===")
best2 = None
for n_seg in [12, 13, 14, 15]:
    for sag in [round(-4.0 + 0.25 * k, 2) for k in range(37)]:
        if abs(sag) < 0.2:
            continue
        d = make_catenary_road(30.0, n_seg, sag, "A0", "A4")
        ok, cost, pk, _ = eval_design(2, d)
        if ok:
            if best2 is None or cost < best2[0]:
                best2 = (cost, n_seg, sag, pk, d)
                print(f"  L2 PASS: cost={cost:.1f}, n={n_seg}, sag={sag}, peak={pk*100:.1f}%")
if best2:
    save_if_better(2, best2[4], SUB / "level2.json")
    eval_design(2, best2[4], verbose=True)

print("\n=== LEVEL 3: Dual-Span Catenary with Center Pier ===")
# Anchors: A0=(0,0), A1=(0,-2), A2=(14,-4), A3=(28,0), A4=(28,-2)
best3 = None
for n_half in [6, 7]:
    for mid_y in [-2.0, -1.5, -1.0, -0.5, 0.0, 0.5]:
        for sag in [round(-1.0 + 0.25 * k, 2) for k in range(15)]:
            nodes = []
            members = []
            # Mid node at (14, mid_y)
            mid_idx = 0
            nodes.append([14.0, mid_y])
            # Left span: A0=(0,0) to mid=(14, mid_y)
            prev = "A0"
            for i in range(1, n_half):
                t = i / n_half
                x = 14.0 * t
                y = mid_y * t - 4.0 * sag * t * (1.0 - t)
                idx = len(nodes)
                nodes.append([round(x, 4), round(y, 4)])
                members.append([prev, idx, "road"])
                prev = idx
            members.append([prev, mid_idx, "road"])
            # Right span: mid=(14, mid_y) to A3=(28,0)
            prev = mid_idx
            for i in range(1, n_half):
                t = i / n_half
                x = 14.0 + 14.0 * t
                y = mid_y * (1.0 - t) - 4.0 * sag * t * (1.0 - t)
                idx = len(nodes)
                nodes.append([round(x, 4), round(y, 4)])
                members.append([prev, idx, "road"])
                prev = idx
            members.append([prev, "A3", "road"])
            # Connect mid_idx to A2=(14,-4) using wood/steel
            dist_pier = mid_y - (-4.0)
            if dist_pier <= 3.0:
                members.append(["A2", mid_idx, "wood"])
            elif dist_pier <= 6.0:
                members.append(["A2", mid_idx, "steel"])
            else:
                continue
            d = {"nodes": nodes, "members": members}
            ok, cost, pk, _ = eval_design(3, d)
            if ok:
                if best3 is None or cost < best3[0]:
                    best3 = (cost, n_half, mid_y, sag, pk, d)
                    print(f"  L3 PASS: cost={cost:.1f}, n_half={n_half}, mid_y={mid_y}, sag={sag}, peak={pk*100:.1f}%")
if best3:
    save_if_better(3, best3[5], SUB / "level3.json")
    eval_design(3, best3[5], verbose=True)
