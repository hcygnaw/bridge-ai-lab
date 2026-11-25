import copy
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bridge
from opt_helper import eval_design, save_submission


def make_l6_under(bot_y=-1.8, open_delay=5.0, close_delay=17.0, green_delay=18.5):
    # Level 6 anchors:
    # A0=(0,0), A1=(0,-2), A2=(0,-4), A3=(-5,0), A4=(12,-2)
    # A5=(24,-2), A6=(36,0), A7=(36,-2), A8=(36,-4), A9=(41,0)
    nodes = []
    members = []

    for side in (0, 1):
        sign = 1 if side == 0 else -1
        x0 = 0.0 if side == 0 else 36.0
        a_deck = "A0" if side == 0 else "A6"
        a_bot = "A1" if side == 0 else "A7"
        a_pier = "A4" if side == 0 else "A5"

        # 5 road segments of 2.4m from 0 to 12.0 + 1 short cantilever to 13.8
        xs = [2.4, 4.8, 7.2, 9.6, 12.0, 13.8]
        s_deck = []
        for x in xs:
            idx = len(nodes)
            nodes.append([round(x0 + sign * x, 3), 0.0])
            s_deck.append(idx)
        for i in range(len(s_deck)):
            u = a_deck if i == 0 else s_deck[i - 1]
            v = s_deck[i]
            members.append([u, v, "road"])

        # Under-deck Warren truss from 0 to 12: 5 bottom nodes at x=1.2, 3.6, 6.0, 8.4, 10.8, y=bot_y
        s_bot = []
        for i in range(5):
            idx = len(nodes)
            nodes.append([round(x0 + sign * (2.4 * i + 1.2), 3), bot_y])
            s_bot.append(idx)
            dl = a_deck if i == 0 else s_deck[i - 1]
            dr = s_deck[i]
            members.append([idx, dl, "wood"])
            members.append([idx, dr, "wood"])
        members.append([a_bot, s_bot[0], "wood"])
        for i in range(4):
            members.append([s_bot[i], s_bot[i + 1], "wood"])
        # Connect pier A4=(12,-2) to s_bot[4] (x=10.8), s_deck[4] (x=12), and s_deck[5] (x=13.8)
        members.append([a_pier, s_bot[4], "wood"])
        members.append([a_pier, s_deck[4], "steel"])
        members.append([a_pier, s_deck[5], "steel"])

        # Hydraulic anchor post at x=12.0, y=2.6 + cable stay to piv=(13.8,0) to unload pier strut!
        h_anc = len(nodes)
        nodes.append([round(x0 + sign * 12.0, 3), 2.6])
        members.append([s_deck[4], h_anc, "steel"])  # (12.0,0)-(12.0,2.6) L=2.60m
        members.append([s_deck[3], h_anc, "cable"])  # (9.6,0)-(12.0,2.6) L=3.54m
        members.append([s_deck[5], h_anc, "cable"])  # (13.8,0)-(12.0,2.6) L=3.16m

        # Bascule leaf: pivots at s_deck[5] (x=13.8) to x=17.9 (2 segments of 2.05m, 0.2m gap)
        piv = s_deck[5]
        l1 = len(nodes); nodes.append([round(x0 + sign * 15.85, 3), 0.0])
        l2 = len(nodes); nodes.append([round(x0 + sign * 17.9, 3), 0.0])
        members.append([piv, l1, "road"])
        members.append([l1, l2, "road"])

        l_top = len(nodes); nodes.append([round(x0 + sign * 15.85, 3), 0.9])
        members.append([piv, l_top, "wood"])
        members.append([l1, l_top, "wood"])
        members.append([l2, l_top, "wood"])

        # Hydraulic from h_anc (12.0, 2.6) to l1 (15.85, 0.0) -> L = 4.65m <= 5.0m
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


def smart_upgrade(d, max_iters=20):
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
                        if d["members"][idx][2] in ("wood", "cable"):
                            if earliest is None or t < earliest[0]:
                                earliest = (t, idx, f, os.path.basename(sp))
                            break
        if all_ok:
            return True, P["cost"], d, "PASS"
        if earliest is None:
            return False, P["cost"], d, "No wood/cable break found"
        t, idx, f, sname = earliest
        cur = d["members"][idx][2]
        nxt = "cable" if (cur == "wood" and f > 0) else "steel"
        print(f"  iter {it}: cost={P['cost']:.1f}, earliest {cur} break m[{idx}] (f={f:.0f}) -> {nxt} at t={t:.2f}s in {sname}")
        d["members"][idx][2] = nxt
    return False, P["cost"], d, "Max iters"


if __name__ == "__main__":
    for by in [-1.6, -1.5]:
        print(f"=== Testing bot_y={by} ===")
        d = make_l6_under(bot_y=by)
        ok, cost, d_out, msg = smart_upgrade(d, max_iters=45)
        print(f"L6 Under bot_y={by}: ok={ok} cost={cost:.1f} {msg}")
        if ok:
            save_submission("level6.json", d_out)
            break
        else:
            lv = bridge.load_level("6")
            try:
                P = bridge.parse_design(lv, d_out)
                for sp in bridge.sample_paths(lv):
                    sc = bridge.load_json(sp)
                    res, _ = bridge.simulate(lv, P, sc)
                    print(os.path.basename(sp), bridge.summarize(res, P, sc)["text"])
                    print("  Events:", res["events"][:10])
            except Exception as e:
                print("Parse error:", e)
