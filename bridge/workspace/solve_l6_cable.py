import copy
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bridge
from opt_helper import eval_design, save_submission


def make_l6_cable(open_delay=5.0, close_delay=17.0, green_delay=18.5):
    # Level 6 anchors:
    # A0=(0,0), A1=(0,-2), A2=(0,-4), A3=(-5,0), A4=(12,-2)
    # A5=(24,-2), A6=(36,0), A7=(36,-2), A8=(36,-4), A9=(41,0)
    nodes = []
    members = []

    for side in (0, 1):
        sign = 1 if side == 0 else -1
        x0 = 0.0 if side == 0 else 36.0
        a_deck = "A0" if side == 0 else "A6"
        a_mid = "A1" if side == 0 else "A7"
        a_bot = "A2" if side == 0 else "A8"
        a_pier = "A4" if side == 0 else "A5"

        # Road nodes: 2.4m segments from 0 to 14.4 (only 6 segments!)
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

        # Bank support from A1=(0,-2) and A2=(0,-4) to x=2.4 and x=4.8
        # A1=(0,-2) -> (2.4,0) is L=3.12m (steel)
        # A2=(0,-4) -> (2.4,-2.0) -> (4.8,0) is a 2-segment braced arch strut!
        b1 = len(nodes); nodes.append([round(x0 + sign * 2.4, 3), -2.0])
        members.append([a_mid, b1, "wood"])
        members.append([a_bot, b1, "steel"])
        members.append([b1, s_deck[0], "steel"])
        members.append([b1, s_deck[1], "steel"])

        # Pier tower at x=12 above A4=(12,-2): p1=(12, 2.2), p2=(12, 4.4)
        p1 = len(nodes); nodes.append([round(x0 + sign * 12.0, 3), 2.2])
        p2 = len(nodes); nodes.append([round(x0 + sign * 12.0, 3), 4.4])
        members.append([a_pier, s_deck[4], "steel"])
        members.append([s_deck[4], p1, "steel"])
        members.append([p1, p2, "steel"])
        # Brace p1 to x=9.6 (L=3.25m -> cable or steel) and a_pier to x=14.4
        members.append([a_pier, s_deck[3], "steel"])  # (12,-2)-(9.6,0) L=3.12m
        members.append([a_pier, s_deck[5], "steel"])  # (12,-2)-(14.4,0) L=3.12m
        members.append([p2, s_deck[5], "cable"])      # (12,4.4)-(14.4,0)
        # Stay cables from p2 to x=4.8, 7.2
        members.append([p2, s_deck[1], "cable"])
        members.append([p2, s_deck[2], "cable"])

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

        # Hydraulic from p1 (12.0, 2.2) to l1 (16.175, 0.0) -> L = 4.72m <= 5.0m
        members.append([p1, l1, "hydraulic", "A"])

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
    d = make_l6_cable()
    ok, cost, det, _ = eval_design(6, d)
    print(f"L6 Cable: ok={ok} cost={cost:.1f}")
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
