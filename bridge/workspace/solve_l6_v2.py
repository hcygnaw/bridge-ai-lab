import copy
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bridge
from opt_helper import eval_design, save_submission


def make_l6_above(H=1.65, h_anc_y=2.2, open_delay=5.0, close_delay=17.0, green_delay=18.5):
    # Level 6 anchors:
    # A0=(0,0), A1=(0,-4), A2=(36,0), A3=(36,-4), A4=(12,-2), A5=(24,-2)
    # Ship channel: x in [15, 21], y in [-2, 6]
    nodes = []
    members = []

    for side in (0, 1):
        sign = 1 if side == 0 else -1
        x0 = 0.0 if side == 0 else 36.0
        a_deck = "A0" if side == 0 else "A6"
        a_pier = "A4" if side == 0 else "A5"

        # Road segments from 0 to 14.4: 2.4m up to 9.6, then 1.2m (9.6..10.8..12.0), then 2.4m (12.0..14.4)
        s_deck = []
        xs = [2.4, 4.8, 7.2, 9.6, 10.8, 12.0, 14.4]
        for x in xs:
            idx = len(nodes)
            nodes.append([round(x0 + sign * x, 3), 0.0])
            s_deck.append(idx)
        for i in range(len(s_deck)):
            u = a_deck if i == 0 else s_deck[i - 1]
            v = s_deck[i]
            members.append([u, v, "road"])

        # Above-deck Warren truss from 0 to 12: top nodes at x=1.2, 3.6, 6.0, 8.4, 10.8, y=H
        s_top = []
        for i in range(5):
            idx = len(nodes)
            nodes.append([round(x0 + sign * (2.4 * i + 1.2), 3), H])
            s_top.append(idx)
            dl = a_deck if i == 0 else s_deck[i - 1]
            dr = s_deck[i] if i < 4 else s_deck[5]  # s_deck[5] is x=12.0
            members.append([idx, dl, "wood"])
            members.append([idx, dr, "wood"])
        # Vertical wood tie at x=10.8 to brace the 10.8 road node
        members.append([s_top[4], s_deck[4], "wood"])
        for i in range(4):
            members.append([s_top[i], s_top[i + 1], "steel"])

        # Pier support at x=12, y=-2
        members.append([a_pier, s_deck[5], "steel"])
        members.append([a_pier, s_deck[6], "steel"])

        # Hydraulic anchor post at x=12.0, y=h_anc_y
        h_anc = len(nodes)
        nodes.append([round(x0 + sign * 12.0, 3), h_anc_y])
        members.append([s_deck[5], h_anc, "steel"])
        members.append([s_top[4], h_anc, "steel"])
        members.append([s_deck[6], h_anc, "cable"])

        # Bascule leaf: pivots at s_deck[6] (x=14.4) to x=17.95 (length 3.55m -> 2 road segments of 1.775m)
        piv = s_deck[6]
        l1 = len(nodes); nodes.append([round(x0 + sign * 16.175, 3), 0.0])
        l2 = len(nodes); nodes.append([round(x0 + sign * 17.95, 3), 0.0])
        members.append([piv, l1, "road"])
        members.append([l1, l2, "road"])

        l_top = len(nodes); nodes.append([round(x0 + sign * 16.175, 3), 0.8])
        members.append([piv, l_top, "wood"])
        members.append([l1, l_top, "wood"])
        members.append([l2, l_top, "wood"])

        # Hydraulic from h_anc (12.0, H) to l1 (16.175, 0.0) -> L = sqrt(4.175^2 + 2.2^2) = 4.72m <= 5.0m
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


def smart_upgrade(d, max_iters=15):
    lv = bridge.load_level("6")
    d = copy.deepcopy(d)
    for it in range(max_iters):
        try:
            P = bridge.parse_design(lv, d)
        except bridge.DesignError as e:
            return False, 999999.0, d, str(e)
        all_ok = True
        earliest = None
        for sp in bridge.sample_paths(lv):
            sc = bridge.load_json(sp)
            res, _ = bridge.simulate(lv, P, sc)
            if not res["ok"]:
                all_ok = False
                for ev in res["events"]:
                    parts = ev.split()
                    if len(parts) >= 4 and parts[1] == "BREAK":
                        t = float(parts[0])
                        idx = int(parts[2])
                        f = float(parts[3])
                        if d["members"][idx][2] == "wood":
                            if earliest is None or t < earliest[0]:
                                earliest = (t, idx, f, os.path.basename(sp))
                            break
        if all_ok:
            return True, P["cost"], d, "PASS"
        if earliest is None:
            return False, P["cost"], d, "No wood break found"
        t, idx, f, sname = earliest
        print(f"  iter {it}: cost={P['cost']:.1f}, earliest wood break m[{idx}] (f={f:.0f}) at t={t:.2f}s in {sname}")
        d["members"][idx][2] = "cable" if f > 0 else "steel"
    return False, P["cost"], d, "Max iters"


if __name__ == "__main__":
    d = make_l6_above(H=1.5)
    ok, cost, d_out, msg = smart_upgrade(d, max_iters=12)
    print(f"L6 Above H=1.5: ok={ok} cost={cost:.1f} {msg}")
    if ok:
        save_submission("level6.json", d_out)
    else:
        lv = bridge.load_level("6")
        P = bridge.parse_design(lv, d_out)
        for sp in bridge.sample_paths(lv):
            sc = bridge.load_json(sp)
            res, _ = bridge.simulate(lv, P, sc)
            print(os.path.basename(sp), bridge.summarize(res, P, sc)["text"])
            print("  Events:", res["events"][:15])
