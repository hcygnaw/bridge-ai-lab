import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bridge
from opt_helper import eval_design, save_submission


def make_l4_drawbridge(n_leaf=5, truss_h=1.8, hyd_x=2.4, hyd_ratio=0.52,
                       open_delay=5.0, close_delay=16.2, green_delay=19.5):
    """Twin-leaf bascule drawbridge for Level 4 (0..24, ship channel x in [9,15], y in [-2,6]).
    Left leaf pivots on A0=(0,0), pulled up by hydraulic from (-4,0) or tower to top chord.
    Right leaf pivots on A3=(24,0).
    """
    nodes = []
    members = []

    # Left leaf: 5 road segments from A0=(0,0) to (11.95, 0)
    dx = 11.95 / n_leaf
    l_deck = []
    for i in range(1, n_leaf + 1):
        idx = len(nodes)
        nodes.append([round(i * dx, 3), 0.0])
        l_deck.append(idx)
    for i in range(n_leaf):
        u = "A0" if i == 0 else l_deck[i - 1]
        v = l_deck[i]
        members.append([u, v, "road"])

    # Left leaf over-deck Warren truss (above road so it doesn't dip into water when closed)
    l_top = []
    for i in range(n_leaf):
        x = (i + 0.5) * dx
        # Taper height slightly toward tip to save weight
        h = truss_h * (1.0 - 0.35 * (i / n_leaf))
        idx = len(nodes)
        nodes.append([round(x, 3), round(h, 3)])
        l_top.append(idx)
        dl = "A0" if i == 0 else l_deck[i - 1]
        dr = l_deck[i]
        mat = "steel" if i == 0 else "wood"
        members.append([idx, dl, mat])
        members.append([idx, dr, "wood"])
    for i in range(n_leaf - 1):
        mat = "steel" if i == 0 else "wood"
        members.append([l_top[i], l_top[i + 1], mat])

    # Hydraulic actuator for left leaf:
    # From A2=(-4,0) to l_top[0] (around x=1.2, y=1.8 -> distance = sqrt(5.2^2 + 1.8^2) = 5.5m > 5.0m!).
    # Use A10=(-2,0) to l_top[0]: x1=-2, y1=0; x2=1.2, y2=1.8 -> dist = sqrt(3.2^2 + 1.8^2) = 3.67m <= 5.0m!
    # When hydraulic shrinks to ratio ~0.52 (length ~1.91m), l_top[0] swings back over A10, lifting the 11.95m leaf to ~55 deg!
    # At 55 deg, tip x = 11.95 * cos(55°) = 6.85 < 9.0! Completely clear of [9, 15]!
    members.append(["A10", l_top[0], "hydraulic", "A"])

    # Right leaf: symmetric from A3=(24,0) to (12.05, 0)
    r_deck = []
    for i in range(1, n_leaf + 1):
        idx = len(nodes)
        nodes.append([round(24.0 - i * dx, 3), 0.0])
        r_deck.append(idx)
    for i in range(n_leaf):
        u = "A3" if i == 0 else r_deck[i - 1]
        v = r_deck[i]
        members.append([u, v, "road"])

    r_top = []
    for i in range(n_leaf):
        x = 24.0 - (i + 0.5) * dx
        h = truss_h * (1.0 - 0.35 * (i / n_leaf))
        idx = len(nodes)
        nodes.append([round(x, 3), round(h, 3)])
        r_top.append(idx)
        dl = "A3" if i == 0 else r_deck[i - 1]
        dr = r_deck[i]
        mat = "steel" if i == 0 else "wood"
        members.append([idx, dl, mat])
        members.append([idx, dr, "wood"])
    for i in range(n_leaf - 1):
        mat = "steel" if i == 0 else "wood"
        members.append([r_top[i], r_top[i + 1], mat])

    # Hydraulic from A11=(26,0) to r_top[0]
    members.append(["A11", r_top[0], "hydraulic", "A"])

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
    d = make_l4_drawbridge()
    ok, cost, stress, msg = eval_design(4, d)
    print(f"L4 Drawbridge: {'PASS' if ok else 'FAIL'} cost={cost:.1f} stress={stress:.2f} {msg}")
    if ok:
        save_submission("level4.json", d)
    else:
        # Print details
        lv = bridge.load_level("4")
        P = bridge.parse_design(lv, d)
        for sp in bridge.sample_paths(lv):
            sc = bridge.load_json(sp)
            res, _ = bridge.simulate(lv, P, sc)
            print(os.path.basename(sp), bridge.summarize(res, P, sc)["text"])
            print("  Events:", res["events"][:10])
