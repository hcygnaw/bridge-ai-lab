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

def mat_for(p1, p2, pref="wood"):
    L = dist(p1, p2)
    if pref == "wood" and L <= 3.0:
        return "wood"
    if pref == "cable" and L <= 30.0:
        return "cable"
    if L <= 6.0:
        return "steel"
    return "cable"

# ================= LEVEL 2: True Parabolic Arch from A2=(0,-8) to A6=(30,-8) =================
def l2_true_arch(n_seg, y_anchor_start=-8.0, y_mid=-1.5, arch_mat="wood", diag_mat="wood", tie_a1=True):
    # Road: n_seg segments from A0=(0,0) to A4=(30,0)
    # Arch: n_seg+1 points from A2=(0,-8) (or A1=(0,-4)) to A6=(30,-8) (or A5=(30,-4)),
    # with interior nodes aligned with road nodes (x = 30*i/n_seg)
    nodes = []
    members = []
    for i in range(1, n_seg):
        nodes.append([round(30.0 * i / n_seg, 4), 0.0])
    for i in range(n_seg):
        u = "A0" if i == 0 else i - 1
        v = "A4" if i == n_seg - 1 else i
        members.append([u, v, "road"])

    aL = "A2" if y_anchor_start == -8.0 else "A1"
    aR = "A6" if y_anchor_start == -8.0 else "A5"
    pL = (0.0, y_anchor_start)
    pR = (30.0, y_anchor_start)

    arch_ids = []
    for i in range(1, n_seg):
        t = i / n_seg
        x = 30.0 * t
        y = y_anchor_start + (y_mid - y_anchor_start) * 4.0 * t * (1.0 - t)
        aid = len(nodes)
        nodes.append([round(x, 4), round(y, 4)])
        arch_ids.append(aid)

    # Arch rib
    for i in range(n_seg):
        u = aL if i == 0 else arch_ids[i - 1]
        v = aR if i == n_seg - 1 else arch_ids[i]
        pu = pL if u == aL else nodes[u]
        pv = pR if v == aR else nodes[v]
        members.append([u, v, mat_for(pu, pv, arch_mat)])

    # Verticals + diagonals between road and arch
    # If vertical > 3m, subdivide it with a mid-node!
    vert_mids = {}
    for i in range(n_seg - 1):
        r_id = i
        a_id = arch_ids[i]
        pr = nodes[r_id]
        pa = nodes[a_id]
        L = dist(pr, pa)
        if L <= 3.0:
            members.append([r_id, a_id, "wood"])
        elif L <= 6.0:
            if diag_mat == "wood":
                # subdivide vertical in 2 wood pieces
                mid_id = len(nodes)
                nodes.append([pr[0], round(0.5*(pr[1]+pa[1]), 4)])
                vert_mids[i] = mid_id
                members.append([r_id, mid_id, "wood"])
                members.append([mid_id, a_id, "wood"])
            else:
                members.append([r_id, a_id, "steel"])
        else:
            # 3 pieces
            m1 = len(nodes); nodes.append([pr[0], round(pr[1] + (pa[1]-pr[1])/3, 4)])
            m2 = len(nodes); nodes.append([pr[0], round(pr[1] + 2*(pa[1]-pr[1])/3, 4)])
            vert_mids[i] = m1
            members.append([r_id, m1, "wood"])
            members.append([m1, m2, "wood"])
            members.append([m2, a_id, "wood"])

    # Diagonals in each panel
    for i in range(n_seg):
        u_r = "A0" if i == 0 else i - 1
        v_r = "A4" if i == n_seg - 1 else i
        u_a = aL if i == 0 else arch_ids[i - 1]
        v_a = aR if i == n_seg - 1 else arch_ids[i]
        pu_r = (0,0) if u_r == "A0" else nodes[u_r]
        pv_r = (30,0) if v_r == "A4" else nodes[v_r]
        pu_a = pL if u_a == aL else nodes[u_a]
        pv_a = pR if v_a == aR else nodes[v_a]

        if i < n_seg // 2:
            # Diagonal from u_a (or A1) to v_r, or u_r to v_a
            if i == 0 and tie_a1 and y_anchor_start == -8.0:
                members.append(["A1", v_r, mat_for((0,-4), pv_r, diag_mat)])
                members.append(["A1", v_a, mat_for((0,-4), pv_a, diag_mat)])
                if 0 in vert_mids:
                    members.append(["A1", vert_mids[0], mat_for((0,-4), nodes[vert_mids[0]], diag_mat)])
            else:
                if dist(pu_a, pv_r) <= (3.0 if diag_mat=="wood" else 6.0):
                    members.append([u_a, v_r, mat_for(pu_a, pv_r, diag_mat)])
                else:
                    members.append([u_r, v_a, mat_for(pu_r, pv_a, "cable" if dist(pu_r, pv_a) > 6.0 else diag_mat)])
        else:
            if i == n_seg - 1 and tie_a1 and y_anchor_start == -8.0:
                members.append(["A5", u_r, mat_for((30,-4), pu_r, diag_mat)])
                members.append(["A5", u_a, mat_for((30,-4), pu_a, diag_mat)])
                if (n_seg - 2) in vert_mids:
                    members.append(["A5", vert_mids[n_seg - 2], mat_for((30,-4), nodes[vert_mids[n_seg - 2]], diag_mat)])
            else:
                if dist(pv_a, pu_r) <= (3.0 if diag_mat=="wood" else 6.0):
                    members.append([v_a, u_r, mat_for(pv_a, pu_r, diag_mat)])
                else:
                    members.append([v_r, u_a, mat_for(pv_r, pu_a, "cable" if dist(pv_r, pu_a) > 6.0 else diag_mat)])

    return {"nodes": nodes, "members": members}

# ================= LEVEL 2: Cable-Stayed with Braced A-Frame Towers =================
def l2_cable_stayed_v2(n_seg, tower_h, tower_mat="steel"):
    # Road: n_seg segments from A0=(0,0) to A4=(30,0)
    # Left tower: A0=(0,0) -> (0, tower_h/2) -> (0, tower_h), braced by A3=(-6,0) and a mid-brace!
    nodes = []
    members = []
    for i in range(1, n_seg):
        nodes.append([round(30.0 * i / n_seg, 4), 0.0])
    for i in range(n_seg):
        u = "A0" if i == 0 else i - 1
        v = "A4" if i == n_seg - 1 else i
        members.append([u, v, "road"])

    # Left A-frame tower: base A0=(0,0) and A3=(-6,0), apex at (-1.5, tower_h) or (0, tower_h) with mid-bracing
    # Better: 2-tier mast on x=0 with mid-node at (0, h/2) and back-brace node at (-3, h/2)!
    h = tower_h
    lm1 = len(nodes); nodes.append([0.0, round(h/2, 4)])
    lm2 = len(nodes); nodes.append([0.0, round(h, 4)])
    lb1 = len(nodes); nodes.append([-3.0, round(h/2, 4)])
    members.append(["A0", lm1, mat_for((0,0), nodes[lm1], tower_mat)])
    members.append([lm1, lm2, mat_for(nodes[lm1], nodes[lm2], tower_mat)])
    members.append(["A3", lb1, mat_for((-6,0), nodes[lb1], tower_mat)])
    members.append([lb1, lm2, mat_for(nodes[lb1], nodes[lm2], tower_mat)])
    members.append([lb1, lm1, mat_for(nodes[lb1], nodes[lm1], "wood")])
    members.append(["A0", lb1, mat_for((0,0), nodes[lb1], "wood")])

    rm1 = len(nodes); nodes.append([30.0, round(h/2, 4)])
    rm2 = len(nodes); nodes.append([30.0, round(h, 4)])
    rb1 = len(nodes); nodes.append([33.0, round(h/2, 4)])
    members.append(["A4", rm1, mat_for((30,0), nodes[rm1], tower_mat)])
    members.append([rm1, rm2, mat_for(nodes[rm1], nodes[rm2], tower_mat)])
    members.append(["A7", rb1, mat_for((36,0), nodes[rb1], tower_mat)])
    members.append([rb1, rm2, mat_for(nodes[rb1], nodes[rm2], tower_mat)])
    members.append([rb1, rm1, mat_for(nodes[rb1], nodes[rm1], "wood")])
    members.append(["A4", rb1, mat_for((30,0), nodes[rb1], "wood")])

    # Cables from tower tops to every road node in their half
    half = (n_seg - 1) // 2
    for i in range(half):
        members.append([lm2, i, "cable"])
        members.append([rm2, (n_seg - 2) - i, "cable"])
    if (n_seg - 1) % 2 == 1:
        mid = half
        members.append([lm2, mid, "cable"])
        members.append([rm2, mid, "cable"])
    return {"nodes": nodes, "members": members}

print("=== LEVEL 2 V2 SWEEP ===", flush=True)
best2 = None
def try2(label, d):
    global best2
    ok, cost, pk, _ = eval_design(2, d)
    if ok:
        if best2 is None or cost < best2[0]:
            best2 = (cost, label, pk, d)
            print(f"NEW BEST L2: {cost:.1f} ({label}) peak={pk*100:.1f}%", flush=True)
            save_if_better(2, d, SUB / "level2.json")

for n_seg in [12, 13, 14]:
    for th in [6.0, 8.0, 10.0]:
        for tm in ["wood", "steel"]:
            try2(f"cs2_n{n_seg}_th{th}_{tm}", l2_cable_stayed_v2(n_seg, th, tm))

for n_seg in [12, 14]:
    for y_anc in [-8.0, -4.0]:
        for y_mid in [-2.5, -1.5, -1.0]:
            for am in ["wood", "steel"]:
                for dm in ["wood", "steel"]:
                    try2(f"arch2_n{n_seg}_ya{y_anc}_ym{y_mid}_{am}_{dm}",
                         l2_true_arch(n_seg, y_anc, y_mid, am, dm))

if best2:
    eval_design(2, best2[3], verbose=True)

# ================= LEVEL 3: Dual Inverted Warren with Steel/V-Pier =================
def l3_dual_v2(n_half, y_bot_end, y_bot_mid, pier_y=-2.0, bot_mat="wood", pier_mat="steel", extra_v=True):
    nodes = []
    members = []
    n_tot = 2 * n_half
    for i in range(1, n_tot):
        x = 28.0 * i / n_tot
        nodes.append([round(x, 4), 0.0])
    for i in range(n_tot):
        u = "A0" if i == 0 else i - 1
        v = "A3" if i == n_tot - 1 else i
        members.append([u, v, "road"])
    mid_road = n_half - 1 # at x=14, y=0
    pier_node = len(nodes)
    nodes.append([14.0, pier_y])
    members.append(["A2", pier_node, pier_mat])
    members.append([pier_node, mid_road, pier_mat])

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
    members.append(["A1", bot_l, bot_mat])
    members.append([bot_l + n_half - 1, pier_node, bot_mat])

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

    if extra_v:
        # V-braces from A2=(14,-4) to bot_l[-1] and bot_r[0] (steel if > 3m else wood)
        members.append(["A2", bot_l + n_half - 1, mat_for((14,-4), nodes[bot_l + n_half - 1], "wood")])
        members.append(["A2", bot_r, mat_for((14,-4), nodes[bot_r], "wood")])
    return {"nodes": nodes, "members": members}

print("\n=== LEVEL 3 V2 SWEEP ===", flush=True)
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
    for y_end in [-2.0, -1.5, -1.2]:
        for y_mid in [-2.0, -1.5, -1.2]:
            for py in [-2.0, -1.5]:
                for pm in ["steel", "wood"]:
                    for bm in ["wood", "steel"]:
                        try3(f"l3_nh{n_half}_ye{y_end}_ym{y_mid}_py{py}_{pm}_{bm}",
                             l3_dual_v2(n_half, y_end, y_mid, py, bm, pm, True))

if best3:
    eval_design(3, best3[3], verbose=True)
