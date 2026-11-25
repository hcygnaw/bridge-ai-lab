import copy
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bridge
from opt_helper import eval_design, save_submission


def make_l6_pratt(H=2.1, h_anc_y=2.2, open_delay=5.0, close_delay=17.0, green_delay=18.5):
    # Level 6 anchors:
    # A0=(0,0), A1=(0,-2), A2=(0,-4), A3=(-5,0), A4=(12,-2)
    # A5=(24,-2), A6=(36,0), A7=(36,-2), A8=(36,-4), A9=(41,0)
    nodes = []
    members = []

    for side in (0, 1):
        sign = 1 if side == 0 else -1
        x0 = 0.0 if side == 0 else 36.0
        a_deck = "A0" if side == 0 else "A6"
        a_pier = "A4" if side == 0 else "A5"

        # Road: 2.4m segments from 0 to 14.4
        xs = [2.4, 4.8, 7.2, 9.6, 12.0, 14.4]
        s_deck = []
        for x in xs:
            idx = len(nodes)
            nodes.append([round(x0 + sign * x, 3), 0.0])
            s_deck.append(idx)
        for i in range(len(s_deck)):
            u = a_deck if i == 0 else s_deck[i - 1]
            v = s_deck[i]
            members.append([u, v, "road"])

        # Above-deck Pratt truss from 0 to 12:
        # Top nodes at x=2.4, 4.8, 7.2, 9.6, y=H (steel top chord = 7.2m total!)
        s_top = []
        for i in range(4):
            idx = len(nodes)
            nodes.append([round(x0 + sign * (2.4 * (i + 1)), 3), H])
            s_top.append(idx)
        # End inclined steel posts: A0 -> s_top[0] and s_deck[4](12,0) -> s_top[3](9.6,H)
        members.append([a_deck, s_top[0], "steel"])
        members.append([s_deck[4], s_top[3], "steel"])
        # Top chord (steel, 2.4m segments)
        for i in range(3):
            members.append([s_top[i], s_top[i + 1], "steel"])
        # Vertical wood posts (L=2.1m -> buckling limit 27.2 kN, or tension!)
        for i in range(4):
            members.append([s_deck[i], s_top[i], "wood"])
        # Tension diagonals (cables! 150 kN limit!)
        members.append([s_top[0], s_deck[1], "cable"])
        members.append([s_top[1], s_deck[2], "cable"])
        members.append([s_top[2], s_deck[1], "cable"])
        members.append([s_top[3], s_deck[2], "cable"])

        # Pier support at x=12, y=-2
        members.append([a_pier, s_deck[4], "steel"])
        members.append([a_pier, s_deck[5], "steel"])

        # Hydraulic anchor post at x=12.0, y=h_anc_y
        h_anc = len(nodes)
        nodes.append([round(x0 + sign * 12.0, 3), h_anc_y])
        members.append([s_deck[4], h_anc, "steel"])
        members.append([s_top[3], h_anc, "cable"])
        members.append([s_deck[5], h_anc, "cable"])

        # Bascule leaf: pivots at s_deck[5] (x=14.4) to x=17.95 (length 3.55m -> 2 road segments of 1.775m)
        piv = s_deck[5]
        l1 = len(nodes); nodes.append([round(x0 + sign * 16.175, 3), 0.0])
        l2 = len(nodes); nodes.append([round(x0 + sign * 17.95, 3), 0.0])
        members.append([piv, l1, "road"])
        members.append([l1, l2, "road"])

        l_top = len(nodes); nodes.append([round(x0 + sign * 16.175, 3), 0.8])
        members.append([piv, l_top, "cable"])
        members.append([l1, l_top, "wood"])
        members.append([l2, l_top, "cable"])

        # Hydraulic from h_anc (12.0, h_anc_y) to l1 (16.175, 0.0) -> L = 4.72m <= 5.0m
        members.append([h_anc, l1, "hydraulic", "A"])

    sensors = [
        {"id": "h", "type": "horn", "cooldown": 25.0},
    ]
    lights = [
        {"id": "L1", "x": -1.0, "dir": "right", "init": "green"},
        {"id": "L2", "x": 37.0, "dir": "left", "init": "green"},
    ]
    rules = [
        {"on": "h", "delay": 0.0, "do": "light", "light": "L1", "state": "red"},
        {"on": "h", "delay": 0.0, "do": "light", "light": "L2", "state": "red"},
        {"on": "h", "delay": open_delay, "do": "hyd", "group": "A", "ratio": 0.50, "speed": 2.5},
        {"on": "h", "delay": close_delay, "do": "hyd", "group": "A", "ratio": 1.0, "speed": 2.5},
        {"on": "h", "delay": green_delay, "do": "light", "light": "L1", "state": "green"},
        {"on": "h", "delay": green_delay + 4.0, "do": "light", "light": "L2", "state": "green"},
    ]
    return {"nodes": nodes, "members": members, "sensors": sensors, "lights": lights, "rules": rules}


if __name__ == "__main__":
    d = make_l6_pratt()
    ok, cost, det, _ = eval_design(6, d)
    print(f"L6 Pratt: ok={ok} cost={cost:.1f}")
    if ok:
        save_submission("level6.json", d)
    else:
        lv = bridge.load_level("6")
        P = bridge.parse_design(lv, d)
        for sp in bridge.sample_paths(lv):
            sc = bridge.load_json(sp)
            res, _ = bridge.simulate(lv, P, sc)
            print(os.path.basename(sp), bridge.summarize(res, P, sc)["text"])
            print("  Events:", res["events"][:10])
