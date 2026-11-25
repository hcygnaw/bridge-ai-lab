import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bridge
from opt_helper import eval_design, save_submission
from solve_l2_l3_v3 import auto_upgrade_to_pass


def make_l4_short_bascule(truss_h=1.8, hyd_ratio=0.52,
                          open_delay=5.5, close_delay=16.2, green_delay=19.0):
    """Static approaches (0..8.8 and 15.2..24) + twin short bascule leaves (8.8..11.95 and 12.05..15.2).
    Ship channel: x in [9, 15], y in [-2, 6].
    """
    nodes = []
    members = []

    # --- LEFT STATIC APPROACH: A0=(0,0) to x=8.8 (4 road segments of 2.2m) ---
    l_stat_deck = []
    for i in range(1, 5):
        idx = len(nodes)
        nodes.append([round(i * 2.2, 3), 0.0])
        l_stat_deck.append(idx)
    for i in range(4):
        u = "A0" if i == 0 else l_stat_deck[i - 1]
        v = l_stat_deck[i]
        members.append([u, v, "road"])

    # Under-deck truss for left static approach (all x <= 8.8, outside channel [9,15])
    l_stat_bot = []
    for i in range(4):
        x = (i + 0.5) * 2.2
        idx = len(nodes)
        nodes.append([round(x, 3), -1.8])
        l_stat_bot.append(idx)
        dl = "A0" if i == 0 else l_stat_deck[i - 1]
        dr = l_stat_deck[i]
        members.append([idx, dl, "wood"])
        members.append([idx, dr, "wood"])
    members.append(["A1", l_stat_bot[0], "wood"])
    for i in range(3):
        members.append([l_stat_bot[i], l_stat_bot[i + 1], "wood"])

    # Backstay / top brace on left static approach to support cantilever + leaf
    l_top_anc = len(nodes)
    nodes.append([6.6, 1.9])
    members.append([l_stat_deck[2], l_top_anc, "wood"])
    members.append([l_stat_deck[3], l_top_anc, "wood"])
    members.append([l_stat_deck[1], l_top_anc, "wood"])
    members.append(["A2", l_top_anc, "cable"])  # cable to A2=(-4,0) holds the whole left cantilever!

    # --- LEFT LEAF: pivots at l_stat_deck[3]=(8.8, 0) to (11.95, 0) (2 road segments of 1.575m) ---
    lpiv = l_stat_deck[3]
    ll1 = len(nodes); nodes.append([10.375, 0.0])
    ll2 = len(nodes); nodes.append([11.95, 0.0])
    members.append([lpiv, ll1, "road"])
    members.append([ll1, ll2, "road"])

    # Leaf triangle above deck
    ll_top = len(nodes); nodes.append([10.375, 1.5])
    members.append([lpiv, ll_top, "wood"])
    members.append([ll1, ll_top, "wood"])
    members.append([ll2, ll_top, "wood"])

    # Hydraulic from l_top_anc=(6.6, 2.2) to ll_top=(10.375, 1.5) -> L = sqrt(3.775^2 + 0.7^2) = 3.84m <= 5.0m!
    # When shrunk to ratio 0.52 (L=2.0m), ll_top swings up and left so the entire leaf is x < 8.9!
    members.append([l_top_anc, ll_top, "hydraulic", "A"])

    # --- RIGHT STATIC APPROACH: A3=(24,0) to x=15.2 (4 road segments of 2.2m) ---
    r_stat_deck = []
    for i in range(1, 5):
        idx = len(nodes)
        nodes.append([round(24.0 - i * 2.2, 3), 0.0])
        r_stat_deck.append(idx)
    for i in range(4):
        u = "A3" if i == 0 else r_stat_deck[i - 1]
        v = r_stat_deck[i]
        members.append([u, v, "road"])

    r_stat_bot = []
    for i in range(4):
        x = 24.0 - (i + 0.5) * 2.2
        idx = len(nodes)
        nodes.append([round(x, 3), -1.8])
        r_stat_bot.append(idx)
        dl = "A3" if i == 0 else r_stat_deck[i - 1]
        dr = r_stat_deck[i]
        members.append([idx, dl, "wood"])
        members.append([idx, dr, "wood"])
    members.append(["A4", r_stat_bot[0], "wood"])
    for i in range(3):
        members.append([r_stat_bot[i], r_stat_bot[i + 1], "wood"])

    r_top_anc = len(nodes)
    nodes.append([17.4, 1.9])
    members.append([r_stat_deck[2], r_top_anc, "wood"])
    members.append([r_stat_deck[3], r_top_anc, "wood"])
    members.append([r_stat_deck[1], r_top_anc, "wood"])
    members.append(["A5", r_top_anc, "cable"])  # cable to A5=(28,0)

    # --- RIGHT LEAF: pivots at r_stat_deck[3]=(15.2, 0) to (12.05, 0) ---
    rpiv = r_stat_deck[3]
    rl1 = len(nodes); nodes.append([13.625, 0.0])
    rl2 = len(nodes); nodes.append([12.05, 0.0])
    members.append([rpiv, rl1, "road"])
    members.append([rl1, rl2, "road"])

    rl_top = len(nodes); nodes.append([13.625, 1.5])
    members.append([rpiv, rl_top, "wood"])
    members.append([rl1, rl_top, "wood"])
    members.append([rl2, rl_top, "wood"])

    members.append([r_top_anc, rl_top, "hydraulic", "A"])

    sensors = [{"id": "h", "type": "horn"}]
    lights = [
        {"id": "L1", "x": -1.0, "dir": "right", "init": "green"},
        {"id": "L2", "x": 25.0, "dir": "left", "init": "green"},
    ]
    rules = [
        {"on": "h", "delay": 0.0, "do": "light", "light": "L1", "state": "red"},
        {"on": "h", "delay": 0.0, "do": "light", "light": "L2", "state": "red"},
        {"on": "h", "delay": open_delay, "do": "hyd", "group": "A", "ratio": hyd_ratio, "speed": 2.0},
        {"on": "h", "delay": close_delay, "do": "hyd", "group": "A", "ratio": 1.0, "speed": 2.0},
        {"on": "h", "delay": green_delay, "do": "light", "light": "L1", "state": "green"},
        {"on": "h", "delay": green_delay, "do": "light", "light": "L2", "state": "green"},
    ]
    return {"nodes": nodes, "members": members, "sensors": sensors, "lights": lights, "rules": rules}


if __name__ == "__main__":
    d = make_l4_short_bascule()
    ok, cost, d_out, msg = auto_upgrade_to_pass(4, d, max_iters=15)
    print(f"L4 ShortBascule: {ok} cost={cost:.1f} {msg}")
    if ok:
        save_submission("level4.json", d_out)
    else:
        lv = bridge.load_level("4")
        P = bridge.parse_design(lv, d_out)
        for sp in bridge.sample_paths(lv):
            sc = bridge.load_json(sp)
            res, _ = bridge.simulate(lv, P, sc)
            print(os.path.basename(sp), bridge.summarize(res, P, sc)["text"])
            print("  Events:", res["events"][:15])
