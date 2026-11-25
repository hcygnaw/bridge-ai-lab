import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bridge
from opt_helper import eval_design, save_submission
from solve_l2_l3_v3 import auto_upgrade_to_pass


def make_l4_tower_bascule(tower_h=5.0, hyd_ratio=0.50,
                          open_delay=5.5, close_delay=16.2, green_delay=19.0):
    """Cable-stayed static approaches (0..8.4 and 15.6..24) + twin bascule leaves (8.4..11.95 and 12.05..15.6).
    Ship channel: x in [9, 15], y in [-2, 6].
    """
    nodes = []
    members = []

    def build_half(sign):
        # sign = +1 for left (A0=(0,0), A1=(0,-2), A9=(-6,0)), -1 for right (A3=(24,0), A4=(24,-2), A12=(30,0))
        x0 = 0.0 if sign == 1 else 24.0
        a_deck = "A0" if sign == 1 else "A3"
        a_bot = "A1" if sign == 1 else "A4"
        a_back = "A9" if sign == 1 else "A12"  # (-6,0) and (30,0)

        # Static approach: 4 road segments of 2.1m -> 0 to 8.4 (or 24 to 15.6)
        s_deck = []
        for i in range(1, 5):
            idx = len(nodes)
            nodes.append([round(x0 + sign * i * 2.1, 3), 0.0])
            s_deck.append(idx)
        for i in range(4):
            u = a_deck if i == 0 else s_deck[i - 1]
            v = s_deck[i]
            members.append([u, v, "road"])

        # Under-deck wood Warren truss for static approach
        s_bot = []
        for i in range(4):
            idx = len(nodes)
            nodes.append([round(x0 + sign * (i + 0.5) * 2.1, 3), -1.7])
            s_bot.append(idx)
            dl = a_deck if i == 0 else s_deck[i - 1]
            dr = s_deck[i]
            members.append([idx, dl, "wood"])
            members.append([idx, dr, "wood"])
        members.append([a_bot, s_bot[0], "wood"])
        for i in range(3):
            members.append([s_bot[i], s_bot[i + 1], "wood"])

        # 2-segment braced tower at x0
        t1 = len(nodes); nodes.append([round(x0, 3), round(tower_h * 0.5, 3)])
        t2 = len(nodes); nodes.append([round(x0, 3), round(tower_h, 3)])
        members.append([a_deck, t1, "steel"])
        members.append([t1, t2, "steel"])
        members.append([a_back, t1, "cable"])
        members.append([a_back, t2, "cable"])
        # Brace t1 to s_deck[0] to prevent tower buckling
        members.append([t1, s_deck[0], "steel"])
        # Forestay cables from t2 to s_deck[2] and s_deck[3] (pivot at 8.4)
        members.append([t2, s_deck[2], "cable"])
        members.append([t2, s_deck[3], "cable"])

        # Hydraulic anchor post above s_deck[2] (x=6.3, y=2.2)
        h_anc = len(nodes); nodes.append([round(x0 + sign * 6.3, 3), 2.2])
        members.append([s_deck[2], h_anc, "wood"])
        members.append([s_deck[3], h_anc, "steel"])
        members.append([s_deck[1], h_anc, "steel"])
        members.append([t2, h_anc, "cable"])

        # Bascule leaf: pivots at s_deck[3] (x=8.4) to x=11.95 (length 3.55m -> 2 road segments of 1.775m)
        piv = s_deck[3]
        l1 = len(nodes); nodes.append([round(x0 + sign * 10.175, 3), 0.0])
        l2 = len(nodes); nodes.append([round(x0 + sign * 11.95, 3), 0.0])
        members.append([piv, l1, "road"])
        members.append([l1, l2, "road"])

        # Leaf triangle: top node at x=10.175, y=0.7 (stiffens the 2-segment leaf)
        l_top = len(nodes); nodes.append([round(x0 + sign * 10.175, 3), 0.7])
        members.append([piv, l_top, "wood"])
        members.append([l1, l_top, "wood"])
        members.append([l2, l_top, "wood"])

        # Hydraulic directly from h_anc (6.3, 2.2) to l1 (10.175, 0.0) -> L=4.46m, shrinks to 2.23m -> swings leaf to ~90 deg!
        members.append([h_anc, l1, "hydraulic", "A"])

    build_half(+1)
    build_half(-1)

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
        {"on": "h", "delay": green_delay + 3.5, "do": "light", "light": "L2", "state": "green"},
    ]
    return {"nodes": nodes, "members": members, "sensors": sensors, "lights": lights, "rules": rules}


if __name__ == "__main__":
    d = make_l4_tower_bascule()
    ok, cost, d_out, msg = auto_upgrade_to_pass(4, d, max_iters=15)
    print(f"L4 TowerBascule: {ok} cost={cost:.1f} {msg}")
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
