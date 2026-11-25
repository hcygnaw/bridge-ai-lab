import json, math, sys
from pathlib import Path

WS = Path(__file__).resolve().parent
sys.path.insert(0, str(WS))
import bridge
from opt_util import eval_design, save_if_better

SUB = WS / "submission"
SUB.mkdir(exist_ok=True)

def dist(a, b):
    return math.hypot(a[0]-b[0], a[1]-b[1])

# ================= LEVEL 2 =================
# Anchors: A0=(0,0), A1=(0,-4), A2=(0,-8), A3=(-6,0), A4=(30,0), A5=(30,-4), A6=(30,-8), A7=(36,0)
def l2_arch_truss(n_seg, y_bot_end, y_bot_mid, use_a2=False, bot_mat="wood", diag_mat="wood", road_camber=0.0):
    # Parabolic inverted Warren / arch truss
    nodes = []
    members = []
    for i in range(1, n_seg):
        t = i / n_seg
        x = 30.0 * t
        y = 4.0 * road_camber * t * (1.0 - t)
        nodes.append([round(x, 4), round(y, 4)])
    for i in range(n_seg):
        u = "A0" if i == 0 else i - 1
        v = "A4" if i == n_seg - 1 else i
        members.append([u, v, "road"])
    bot_start = len(nodes)
    for i in range(n_seg):
        t = (i + 0.5) / n_seg
        x = 30.0 * t
        y = y_bot_end + (y_bot_mid - y_bot_end) * 4.0 * t * (1.0 - t)
        nodes.append([round(x, 4), round(y, 4)])
    for i in range(n_seg):
        u = "A0" if i == 0 else i - 1
        v = "A4" if i == n_seg - 1 else i
        b = bot_start + i
        # choose wood or steel if > 3m
        p_u = (0, 0) if u == "A0" else nodes[u]
        p_v = (30, 0) if v == "A4" else nodes[v]
        p_b = nodes[b]
        m1 = diag_mat if dist(p_u, p_b) <= (3.0 if diag_mat=="wood" else 6.0) else "steel"
        m2 = diag_mat if dist(p_v, p_b) <= (3.0 if diag_mat=="wood" else 6.0) else "steel"
        members.append([u, b, m1])
        members.append([v, b, m2])
        if i + 1 < n_seg:
            mb = bot_mat if dist(nodes[b], nodes[b+1]) <= (3.0 if bot_mat=="wood" else 6.0) else "steel"
            members.append([b, b + 1, mb])
    # Tie ends to A1=(0,-4) and A5=(30,-4)
    p_b0 = nodes[bot_start]
    p_bn = nodes[bot_start + n_seg - 1]
    m_e = "wood" if dist((0,-4), p_b0) <= 3.0 else "steel"
    members.append(["A1", bot_start, m_e])
    members.append(["A5", bot_start + n_seg - 1, m_e])
    if use_a2:
        # Also tie A2=(0,-8) to bot_start and bot_start+1
        if dist((0,-8), p_b0) <= 6.0:
            members.append(["A2", bot_start, "wood" if dist((0,-8), p_b0) <= 3.0 else "steel"])
            members.append(["A6", bot_start + n_seg - 1, "wood" if dist((30,-8), p_bn) <= 3.0 else "steel"])
    return {"nodes": nodes, "members": members}

def l2_cable_stayed(n_seg, tower_h, stay_indices, backstay_a=True):
    # Two towers at x=0 (above A0) and x=30 (above A4), cables to road nodes!
    # Tower height can be built in 1 or 2 segments (wood or steel)
    nodes = []
    members = []
    for i in range(1, n_seg):
        t = i / n_seg
        nodes.append([round(30.0 * t, 4), 0.0])
    for i in range(n_seg):
        u = "A0" if i == 0 else i - 1
        v = "A4" if i == n_seg - 1 else i
        members.append([u, v, "road"])
    # Left tower: (0, tower_h) supported by A0=(0,0) and A3=(-6,0)
    # Use steel for tower mast if <= 6m, else 2 segments
    tl = len(nodes)
    nodes.append([0.0, tower_h])
    tr = len(nodes)
    nodes.append([30.0, tower_h])
    if tower_h <= 3.0:
        members.append(["A0", tl, "wood"])
        members.append(["A4", tr, "wood"])
    else:
        members.append(["A0", tl, "steel"])
        members.append(["A4", tr, "steel"])
    # Backstays to A3=(-6,0) and A7=(36,0)
    members.append(["A3", tl, "cable"])
    members.append(["A7", tr, "cable"])
    # Stays to road nodes
    for idx in stay_indices:
        members.append([tl, idx, "cable"])
        members.append([tr, (n_seg - 2) - idx, "cable"])
    return {"nodes": nodes, "members": members}

print("=== LEVEL 2 SWEEP ===", flush=True)
best2 = None
def try2(label, d):
    global best2
    ok, cost, pk, _ = eval_design(2, d)
    if ok:
        if best2 is None or cost < best2[0]:
            best2 = (cost, label, pk, d)
            print(f"NEW BEST L2: {cost:.1f} ({label}) peak={pk*100:.1f}%", flush=True)
            save_if_better(2, d, SUB / "level2.json")

# Test arch/inverted Warren
for n_seg in [12, 13, 14]:
    for y_end in [-3.5, -2.5, -2.0]:
        for y_mid in [-2.5, -2.0, -1.5, -1.0, -0.5]:
            for bm in ["wood", "steel"]:
                try2(f"arch_n{n_seg}_ye{y_end}_ym{y_mid}_{bm}", l2_arch_truss(n_seg, y_end, y_mid, False, bm, "wood"))

# Test cable-stayed!
for n_seg in [12, 13, 14]:
    for th in [4.5, 5.5, 6.0]:
        # stay every node or every 2nd node
        all_half = list(range(0, (n_seg - 1 + 1) // 2))
        try2(f"cs_all_n{n_seg}_th{th}", l2_cable_stayed(n_seg, th, all_half))
        even_half = [i for i in all_half if i % 2 == 1 or i == all_half[-1]]
        try2(f"cs_even_n{n_seg}_th{th}", l2_cable_stayed(n_seg, th, even_half))

if best2:
    eval_design(2, best2[3], verbose=True)

# ================= LEVEL 3 =================
# Anchors: A0=(0,0), A1=(0,-2), A2=(14,-4), A3=(28,0), A4=(28,-2)
def l3_dual_inv_warren(n_half, y_bot_end, y_bot_mid, pier_y=-2.0, road_camber=0.0, bot_mat="wood", pier_mat="wood"):
    # Road: 2*n_half segments from A0=(0,0) to A3=(28,0). Center road node is at (14, 0)
    nodes = []
    members = []
    n_tot = 2 * n_half
    for i in range(1, n_tot):
        x = 28.0 * i / n_tot
        # local t in each half
        if i <= n_half:
            tl = i / n_half
        else:
            tl = (n_tot - i) / n_half
        y = 4.0 * road_camber * tl * (1.0 - tl)
        nodes.append([round(x, 4), round(y, 4)])
    for i in range(n_tot):
        u = "A0" if i == 0 else i - 1
        v = "A3" if i == n_tot - 1 else i
        members.append([u, v, "road"])
    mid_road = n_half - 1 # node at x=14
    # Pier node at (14, pier_y) connected to A2=(14,-4) and mid_road=(14,0)
    pier_node = len(nodes)
    nodes.append([14.0, pier_y])
    members.append(["A2", pier_node, pier_mat if abs(pier_y - (-4.0)) <= 3.0 else "steel"])
    members.append([pier_node, mid_road, pier_mat if abs(0.0 - pier_y) <= 3.0 else "steel"])

    # Bottom chord for left half (n_half nodes) and right half (n_half nodes)
    bot_l = len(nodes)
    for i in range(n_half):
        t = (i + 0.5) / n_half
        x = 14.0 * t
        y = y_bot_end + (y_bot_mid - y_bot_end) * 4.0 * t * (1.0 - t)
        nodes.append([round(x, 4), round(y, 4)])
    for i in range(n_half):
        u = "A0" if i == 0 else i - 1
        v = i
        b = bot_l + i
        members.append([u, b, "wood"])
        members.append([v, b, "wood"])
        if i + 1 < n_half:
            members.append([b, b + 1, bot_mat])
    # Tie left end to A1=(0,-2) and inner end to pier_node & A2
    members.append(["A1", bot_l, bot_mat])
    members.append([bot_l + n_half - 1, pier_node, bot_mat])
    if dist(nodes[bot_l + n_half - 1], (14.0, -4.0)) <= 3.0:
        members.append([bot_l + n_half - 1, "A2", "wood"])

    bot_r = len(nodes)
    for i in range(n_half):
        t = (i + 0.5) / n_half
        x = 14.0 + 14.0 * t
        y = y_bot_end + (y_bot_mid - y_bot_end) * 4.0 * t * (1.0 - t)
        nodes.append([round(x, 4), round(y, 4)])
    for i in range(n_half):
        u = n_half - 1 + i
        v = "A3" if i == n_half - 1 else n_half + i
        b = bot_r + i
        members.append([u, b, "wood"])
        members.append([v, b, "wood"])
        if i + 1 < n_half:
            members.append([b, b + 1, bot_mat])
    members.append([pier_node, bot_r, bot_mat])
    members.append([bot_r + n_half - 1, "A4", bot_mat])
    if dist(nodes[bot_r], (14.0, -4.0)) <= 3.0:
        members.append([bot_r, "A2", "wood"])

    return {"nodes": nodes, "members": members}

print("\n=== LEVEL 3 SWEEP ===", flush=True)
best3 = None
def try3(label, d):
    global best3
    ok, cost, pk, _ = eval_design(3, d)
    if ok:
        if best3 is None or cost < best3[0]:
            best3 = (cost, label, pk, d)
            print(f"NEW BEST L3: {cost:.1f} ({label}) peak={pk*100:.1f}%", flush=True)
            save_if_better(3, d, SUB / "level3.json")

for n_half in [6, 7]:
    for y_end in [-2.0, -1.6, -1.3]:
        for y_mid in [-2.0, -1.5, -1.2, -1.0]:
            for py in [-2.0, -1.7]:
                for bm in ["wood", "cable"]:
                    try3(f"dualW_nh{n_half}_ye{y_end}_ym{y_mid}_py{py}_{bm}",
                         l3_dual_inv_warren(n_half, y_end, y_mid, py, 0.0, bm, "wood"))

if best3:
    eval_design(3, best3[3], verbose=True)
