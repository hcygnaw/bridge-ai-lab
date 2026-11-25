import json, math, sys
from pathlib import Path

WS = Path(__file__).resolve().parent
sys.path.insert(0, str(WS))
import bridge
from opt_util import eval_design, save_if_better

SUB = WS / "submission"
SUB.mkdir(exist_ok=True)

def make_l5_underslung(
    pit_mode="one_v",
    n_riv=10,
    n_posts=3,
    post_depth=3.0,
    arch_rise=0.0,
    add_diags="cable_x",
    anchor_bottom="A1",
):
    nodes = []
    members = []
    def add(x, y):
        nodes.append([round(x, 4), round(y, 4)])
        return len(nodes) - 1

    # Pit: A2=(-11,0) to A0=(0,0)
    if pit_mode == "one_v":
        # 5 road segs (2.2m each)
        pit_r = ["A2"] + [add(-11.0 + 11.0*i/5, 0.0) for i in range(1, 5)] + ["A0"]
        for i in range(5):
            members.append([pit_r[i], pit_r[i+1], "road"])
        # Underslung cable from A2 -> b -> A0, or steel struts from A5=(-6,-4), A4=(-4,-4)
        # Wait: 2 steel struts from A5 to pit_r[2] (-6.6,0) and A4 to pit_r[3] (-4.4,0)?
        # Better: underslung on pit too! One strut at (-5.5, -2.5) supported by A5=(-6,-4)!
        members.append(["A6", pit_r[1], "steel"])
        members.append(["A5", pit_r[2], "steel"])
        members.append(["A4", pit_r[3], "steel"])
        members.append(["A3", pit_r[4], "steel"])
    elif pit_mode == "underslung":
        # 5 road segs (2.2m each) + 1 steel strut at x=-5.5? Or 4 road segs? 11/4=2.75>2.5, so 5 segs
        pit_r = ["A2"] + [add(-11.0 + 11.0*i/5, 0.0) for i in range(1, 5)] + ["A0"]
        for i in range(5):
            members.append([pit_r[i], pit_r[i+1], "road"])
        # 2 short struts from A5=(-6,-4) and A4=(-4,-4)? Wait: length is 4.0m -> $640 each!
        # Instead, hang a queen-post of depth 1.8m from A2 and A0!
        pb1 = add(-6.6, -1.8)
        pb2 = add(-4.4, -1.8)
        members.append([pit_r[2], pb1, "steel"])
        members.append([pit_r[3], pb2, "steel"])
        members.append(["A2", pb1, "cable"])
        members.append([pb1, pb2, "cable"])
        members.append([pb2, "A0", "cable"])
        # Also tie pit_r[1] and pit_r[4] with short cables to pb1, pb2?
        members.append([pit_r[1], pb1, "cable"])
        members.append([pit_r[4], pb2, "cable"])
    elif pit_mode == "kingpost_mid":
        # 5 road segs, 1 node at (-5.5, -2.0) connected to pit_r[2] and pit_r[3] by steel V,
        # and cable to A2, A0!
        pit_r = ["A2"] + [add(-11.0 + 11.0*i/5, 0.0) for i in range(1, 5)] + ["A0"]
        for i in range(5):
            members.append([pit_r[i], pit_r[i+1], "road"])
        pb = add(-5.5, -1.8)
        members.append([pit_r[2], pb, "steel"])
        members.append([pit_r[3], pb, "steel"])
        members.append(["A2", pb, "cable"])
        members.append(["A0", pb, "cable"])
        members.append([pit_r[1], pb, "cable"])
        members.append([pit_r[4], pb, "cable"])

    # River: A0=(0,0) to A7=(24,0), n_riv segments
    riv_r = ["A0"]
    for i in range(1, n_riv):
        t = i / n_riv
        x = 24.0 * t
        y = 4.0 * arch_rise * t * (1.0 - t)
        riv_r.append(add(x, y))
    riv_r.append("A7")
    for i in range(n_riv):
        members.append([riv_r[i], riv_r[i+1], "road"])

    # Underslung posts at evenly spaced road nodes
    # For n_riv=10, n_posts=4 -> indices 2, 4, 6, 8 (spacing 4.8m, 2 road segs per bay!)
    # For n_riv=10, n_posts=3 -> indices 2, 5, 8 (or n_riv=12, indices 3, 6, 9 -> 6m bays)
    if n_riv == 10 and n_posts == 4:
        p_idxs = [2, 4, 6, 8]
    elif n_riv == 10 and n_posts == 3:
        p_idxs = [3, 5, 7]
    elif n_riv == 12 and n_posts == 3:
        p_idxs = [3, 6, 9]
    elif n_riv == 12 and n_posts == 5:
        p_idxs = [2, 4, 6, 8, 10]
    else:
        p_idxs = [int(round(n_riv * (k + 1) / (n_posts + 1))) for k in range(n_posts)]

    bot_nodes = []
    for idx in p_idxs:
        t = idx / n_riv
        x = 24.0 * t
        y_top = 4.0 * arch_rise * t * (1.0 - t)
        y_bot = y_top - post_depth * (0.65 + 0.35 * 4.0 * t * (1.0 - t))
        b = add(x, y_bot)
        bot_nodes.append((idx, b))
        # Steel post from road node down to bottom node
        members.append([riv_r[idx], b, "steel"])

    # Bottom cable chord
    bl_anchor = "A1" if anchor_bottom == "A1" else "A0"
    br_anchor = "A8" if anchor_bottom == "A1" else "A7"
    members.append([bl_anchor, bot_nodes[0][1], "cable"])
    for k in range(len(bot_nodes) - 1):
        members.append([bot_nodes[k][1], bot_nodes[k+1][1], "cable"])
    members.append([bot_nodes[-1][1], br_anchor, "cable"])

    # Also support intermediate road nodes (between posts) with V-struts or cables!
    # Every road node not directly on a post needs support!
    # If we connect adjacent road nodes to the bottom nodes with diagonal cables or steel:
    if add_diags == "cable_v":
        # Connect each bottom node to adjacent road nodes (idx-1, idx+1) with cable?
        # Wait: road node idx-1 is ABOVE bot_node, so cable goes UP-LEFT (tension when road pushes down? NO, road pushing down compresses a diagonal going down!)
        # Wait: a cable from riv_r[idx-1] to bot_node is in TENSION if riv_r[idx-1] tries to move UP, or in COMPRESSION if it moves DOWN!
        # Whereas a cable from A0 to bot_node is in TENSION when bot_node moves DOWN!
        # And for intermediate road node riv_r[idx-1], a diagonal STEEL strut from riv_r[idx-1] to bot_node is in COMPRESSION (supports riv_r[idx-1])!
        pass
    elif add_diags == "steel_v":
        # Each bottom node supports riv_r[idx] AND riv_r[idx-1] AND riv_r[idx+1]?
        # Better: remove vertical post, put V-struts to midpoints!
        pass
    elif add_diags == "x_cable":
        # Cross-bracing cables in each bay to prevent shear deformation!
        # Bay 0: A0 -> bot_nodes[0] and riv_r[p_idxs[0]] -> A1
        members.append(["A0", bot_nodes[0][1], "cable"])
        members.append(["A7", bot_nodes[-1][1], "cable"])
        for k in range(len(bot_nodes) - 1):
            members.append([riv_r[bot_nodes[k][0]], bot_nodes[k+1][1], "cable"])
            members.append([riv_r[bot_nodes[k+1][0]], bot_nodes[k][1], "cable"])
        # Also support mid-bay road nodes with short cables? No, mid-bay road nodes hang from... wait!
        # If road is 10 segs (2.4m each) and posts are at 2,4,6,8, then nodes 1,3,5,7,9 are unsupported!
        # If we make road nodes 1,3,5,7,9 slightly arched or add short steel struts from bot_nodes to them?
        for idx, b in bot_nodes:
            if idx - 1 > 0:
                members.append([riv_r[idx - 1], b, "cable"])
            if idx + 1 < n_riv:
                members.append([riv_r[idx + 1], b, "cable"])

    return {"nodes": nodes, "members": members}

# Even cleaner: INVERTED WARREN TRUSS with ROAD top chord, CABLE bottom chord, STEEL diagonals!
def make_l5_cable_warren(
    pit_mode="kingpost_mid",
    n_riv=10,
    depth=2.4,
    arch_rise=0.0,
    diag_mat="steel",
    tie_ends="A0",
):
    nodes = []
    members = []
    def add(x, y):
        nodes.append([round(x, 4), round(y, 4)])
        return len(nodes) - 1

    # Pit: 5 road segs (2.2m each)
    pit_r = ["A2"] + [add(-11.0 + 11.0*i/5, 0.0) for i in range(1, 5)] + ["A0"]
    for i in range(5):
        members.append([pit_r[i], pit_r[i+1], "road"])
    if pit_mode == "kingpost_mid":
        # 2 bottom nodes under pit: inverted warren with cable bottom chord!
        pb = [add(-11.0 + 11.0*(i+0.5)/5, -1.6) for i in range(5)]
        # Wait: 5 bottom nodes is too many steel diags. Use 2 bottom nodes at -7.7, -3.3!
        pb1 = add(-7.7, -1.8)
        pb2 = add(-3.3, -1.8)
        members += [["A2", pb1, "cable"], [pb1, pb2, "cable"], [pb2, "A0", "cable"]]
        members += [[pit_r[1], pb1, "steel"], [pit_r[2], pb1, "steel"],
                    [pit_r[3], pb2, "steel"], [pit_r[4], pb2, "steel"]]
    elif pit_mode == "props2":
        # 2 steel props from A5=(-6,-4) and A4=(-4,-4) + cables
        members += [["A6", pit_r[1], "steel"], ["A5", pit_r[2], "steel"],
                    ["A4", pit_r[3], "steel"], ["A3", pit_r[4], "steel"]]
    elif pit_mode == "props_v":
        # A5=(-6,-4) to pit_r[2], A4=(-4,-4) to pit_r[3], plus 2 short steel struts to pit_r[1], pit_r[4]?
        # No, A6=(-8,-4) -> pit_r[1] (-8.8,0) is 4.08m ($652).
        # Wait: what about 2 nodes at (-8.2,-2.2) and (-2.8,-2.2)?
        # Simplest cheap pit: A5=(-6,-4) to (-5.5,-1.5) -> V to pit_r[2], pit_r[3]!
        m = add(-5.5, -1.8)
        members += [["A5", m, "steel"], [m, pit_r[2], "steel"], [m, pit_r[3], "steel"],
                    ["A2", m, "cable"], ["A0", m, "cable"]]
        # And support pit_r[1] and pit_r[4] with 1m arch? Let's arch pit_r slightly!

    # River: n_riv road segments from A0=(0,0) to A7=(24,0)
    riv_r = ["A0"]
    for i in range(1, n_riv):
        t = i / n_riv
        x = 24.0 * t
        y = 4.0 * arch_rise * t * (1.0 - t)
        riv_r.append(add(x, y))
    riv_r.append("A7")
    for i in range(n_riv):
        members.append([riv_r[i], riv_r[i+1], "road"])

    # Bottom cable nodes: only at EVERY 2ND road node (so n_riv/2 bottom nodes!)
    # Wait: if n_riv=10, bottom nodes at x = 3.6, 8.4, 12.0, 15.6, 20.4 (5 nodes) or 4.8, 9.6, 14.4, 19.2 (4 nodes)
    # Better: n_riv=10 -> road nodes 0..10. Bottom nodes at midpoints of (1,2), (3,4), (5,6), (7,8), (9)?
    # Even simpler: 5 bottom nodes at x = 2.4, 7.2, 12.0, 16.8, 21.6!
    # Node b[0] at x=2.4 supports riv_r[1] and riv_r[2] (V-strut!) -> ONLY 2 steel struts per bottom node!
    # Wait: 5 bottom nodes -> 10 road nodes (1..9)?
    # Let's place bottom nodes at x_b = 24 * (k + 0.5) / n_b, connecting to the road nodes in that group!
    # For n_riv=10: groups of 2 road nodes:
    # b0 at x=3.6 supports riv_r[1], riv_r[2]
    # b1 at x=8.4 supports riv_r[3], riv_r[4]
    # b2 at x=12.0 supports riv_r[5]
    # b3 at x=15.6 supports riv_r[6], riv_r[7]
    # b4 at x=20.4 supports riv_r[8], riv_r[9]
    # Wait: that's 9 steel struts of length ~2.2m = 20m steel = $3200 + 25m cable = $1750 -> $4950 + $3600 = $8550!
    b_specs = [(1, 2), (3, 4), (5,), (6, 7), (8, 9)] if n_riv == 10 else [(1, 2), (3, 4), (5, 6), (7, 8), (9, 10)]
    b_nodes = []
    for grp in b_specs:
        xm = sum(24.0 * idx / n_riv for idx in grp) / len(grp)
        t = xm / 24.0
        ym = 4.0 * arch_rise * t * (1.0 - t) - depth * (0.55 + 0.45 * 4.0 * t * (1.0 - t))
        bn = add(xm, ym)
        b_nodes.append(bn)
        for idx in grp:
            members.append([riv_r[idx], bn, diag_mat])

    # Connect bottom chord with CABLE
    a_l = "A0" if tie_ends == "A0" else "A1"
    a_r = "A7" if tie_ends == "A0" else "A8"
    members.append([a_l, b_nodes[0], "cable"])
    for k in range(len(b_nodes) - 1):
        members.append([b_nodes[k], b_nodes[k+1], "cable"])
    members.append([b_nodes[-1], a_r, "cable"])

    return {"nodes": nodes, "members": members}

print("=== LEVEL 5 INVERTED CABLE-WARREN SWEEP ===", flush=True)
best5 = None
for pit_mode in ["kingpost_mid", "props_v"]:
    for n_riv in [10, 11]:
        for depth in [1.6, 2.0, 2.5, 3.0]:
            for arch in [0.0, 0.5, 1.0, 1.5]:
                for tie in ["A0", "A1"]:
                    d = make_l5_cable_warren(pit_mode, n_riv, depth, arch, "steel", tie)
                    ok, cost, pk, msgs = eval_design(5, d)
                    if cost is not None:
                        if ok:
                            if best5 is None or cost < best5[0]:
                                best5 = (cost, d)
                                print(f"PASS L5!! cost={cost:.1f} pit={pit_mode} n={n_riv} d={depth} arch={arch} tie={tie} pk={pk*100:.1f}%", flush=True)
                                save_if_better(5, d, SUB / "level5.json")
                        elif pk < 1.3:
                            print(f"  close: cost={cost:.1f} pk={pk*100:.1f}% pit={pit_mode} n={n_riv} d={depth} arch={arch} tie={tie}", flush=True)

if best5:
    print("\n=== BEST L5 ===")
    eval_design(5, best5[1], verbose=True)
else:
    print("No pass yet, printing diagnostic:")
    d = make_l5_cable_warren("kingpost_mid", 10, 2.2, 0.5, "steel", "A0")
    eval_design(5, d, verbose=True)
