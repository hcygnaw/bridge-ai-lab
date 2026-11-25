import copy
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bridge
from opt_helper import eval_design, save_submission
from solve_l2_l3_v3 import auto_upgrade_to_pass


def make_l6_bascule(open_delay=6.0, close_delay=16.2, green_delay=18.5):
    """Level 6 (0..36, piers A4=(12,-2) & A5=(24,-2), ship channel x in [15,21], y in [-2,6]).
    Static spans 0..14.4 and 21.6..36 + twin short bascule leaves 14.4..17.95 and 18.05..21.6.
    """
    nodes = []
    members = []

    def build_half(sign):
        # sign = +1: left (0..18), anchors A0=(0,0), A1=(0,-2), A4=(12,-2)
        # sign = -1: right (36..18), anchors A6=(36,0), A7=(36,-2), A5=(24,-2)
        x0 = 0.0 if sign == 1 else 36.0
        a_deck = "A0" if sign == 1 else "A6"
        a_bot = "A1" if sign == 1 else "A7"
        a_pier = "A4" if sign == 1 else "A5"

        # 5 road segments of 2.4m from x0 to x=12 (or 24), plus 1 segment of 2.4m to x=14.4 (or 21.6)
        s_deck = []
        xs = [2.4, 4.8, 7.2, 9.6, 12.0, 14.4]
        for x in xs:
            idx = len(nodes)
            nodes.append([round(x0 + sign * x, 3), 0.0])
            s_deck.append(idx)
        for i in range(len(s_deck)):
            u = a_deck if i == 0 else s_deck[i - 1]
            v = s_deck[i]
            members.append([u, v, "road"])

        # Under-deck Warren truss from 0 to 12 (5 bottom nodes at x=1.2, 3.6, 6.0, 8.4, 10.8, y=-1.35)
        s_bot = []
        for i in range(5):
            idx = len(nodes)
            nodes.append([round(x0 + sign * (2.4 * i + 1.2), 3), -1.35])
            s_bot.append(idx)
            dl = a_deck if i == 0 else s_deck[i - 1]
            dr = s_deck[i]
            members.append([idx, dl, "wood"])
            members.append([idx, dr, "wood"])
        members.append([a_bot, s_bot[0], "wood"])
        for i in range(4):
            members.append([s_bot[i], s_bot[i + 1], "cable"])
        # Connect pier A4=(12,-2) / A5=(24,-2) to s_bot[4] (x=10.8), s_deck[4] (x=12), and s_deck[5] (x=14.4)
        members.append([a_pier, s_bot[4], "wood"])
        members.append([a_pier, s_deck[4], "steel"])
        members.append([a_pier, s_deck[5], "steel"])

        # Hydraulic anchor post above s_deck[4] (x=12.0, y=2.2)
        h_anc = len(nodes)
        nodes.append([round(x0 + sign * 12.0, 3), 2.2])
        members.append([s_deck[4], h_anc, "steel"])
        members.append([s_deck[3], h_anc, "cable"])
        members.append([s_deck[5], h_anc, "cable"])

        # Bascule leaf: pivots at s_deck[5] (x=14.4) to x=17.95 (length 3.55m -> 2 road segments of 1.775m)
        piv = s_deck[5]
        l1 = len(nodes); nodes.append([round(x0 + sign * 16.175, 3), 0.0])
        l2 = len(nodes); nodes.append([round(x0 + sign * 17.95, 3), 0.0])
        members.append([piv, l1, "road"])
        members.append([l1, l2, "road"])

        l_top = len(nodes); nodes.append([round(x0 + sign * 16.175, 3), 0.8])
        members.append([piv, l_top, "wood"])
        members.append([l1, l_top, "wood"])
        members.append([l2, l_top, "wood"])

        # Hydraulic from h_anc (12.0, 2.2) to l1 (16.175, 0.0) -> L = 4.72m <= 5.0m!
        members.append([h_anc, l1, "hydraulic", "A"])

    build_half(+1)
    build_half(-1)

    sensors = [{"id": "h", "type": "horn"}]
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


def smart_upgrade_l6(d, max_iters=15):
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
        # Upgrade idx and its symmetric twin if wood
        half = len(d["members"]) // 2
        twin = idx + half if idx < half else idx - half
        print(f"  iter {it}: cost={P['cost']:.1f}, earliest wood break m[{idx}] (f={f:.0f}) at t={t:.2f}s in {sname}")
        d["members"][idx][2] = "cable" if f > 0 else "steel"
        if d["members"][twin][2] == "wood":
            d["members"][twin][2] = "cable" if f > 0 else "steel"
    return False, P["cost"], d, "Max iters"

if __name__ == "__main__":
    d = make_l6_bascule()
    ok, cost, d_out, msg = smart_upgrade_l6(d, max_iters=15)
    print(f"Smart L6: ok={ok} cost={cost:.1f} {msg}")
    if ok:
        save_submission("level6.json", d_out)
    else:
        lv = bridge.load_level("6")
        try:
            P = bridge.parse_design(lv, d_out)
            for sp in bridge.sample_paths(lv):
                sc = bridge.load_json(sp)
                res, _ = bridge.simulate(lv, P, sc)
                print(os.path.basename(sp), bridge.summarize(res, P, sc)["text"])
                print("  Events:", res["events"][:8])
        except Exception as e:
            print("Parse error:", e)
