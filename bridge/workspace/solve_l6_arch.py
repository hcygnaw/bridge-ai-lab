import copy
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bridge
from opt_helper import save_submission


def make_l6_arch(arch_y=-2.0, open_delay=5.0, close_delay=17.0, green_delay=18.5):
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

        # 5 road segments of 2.4m (0..12) + 1 cantilever to 13.5
        xs = [2.4, 4.8, 7.2, 9.6, 12.0, 13.5]
        s_deck = []
        for x in xs:
            idx = len(nodes)
            nodes.append([round(x0 + sign * x, 3), 0.0])
            s_deck.append(idx)
        for i in range(len(s_deck)):
            u = a_deck if i == 0 else s_deck[i - 1]
            v = s_deck[i]
            members.append([u, v, "road"])

        # 3-node steel arch from A1=(0,-2) to A4=(12,-2): every segment <= 3.03m (buckling ~100 kN!)
        b1 = len(nodes); nodes.append([round(x0 + sign * 3.0, 3), arch_y])
        b2 = len(nodes); nodes.append([round(x0 + sign * 6.0, 3), arch_y])
        b3 = len(nodes); nodes.append([round(x0 + sign * 9.0, 3), arch_y])
        members.append([a_mid, b1, "steel"])
        members.append([b1, b2, "steel"])
        members.append([b2, b3, "steel"])
        members.append([b3, a_pier, "steel"])

        # Short web struts from arch to deck (every strut <= 2.2m!)
        members.append([b1, s_deck[0], "wood"])      # (3,-1.6)->(2.4,0) L=1.71m
        members.append([b1, s_deck[1], "wood"])      # (3,-1.6)->(4.8,0) L=2.41m
        members.append([b2, s_deck[1], "wood"])      # (6,-1.6)->(4.8,0) L=2.00m
        members.append([b2, s_deck[2], "wood"])      # (6,-1.6)->(7.2,0) L=2.00m
        members.append([b3, s_deck[2], "wood"])      # (9,-1.6)->(7.2,0) L=2.41m
        members.append([b3, s_deck[3], "wood"])      # (9,-1.6)->(9.6,0) L=1.71m
        members.append([a_pier, s_deck[4], "steel"]) # (12,-2)->(12,0) L=2.00m
        members.append([a_pier, s_deck[5], "steel"]) # (12,-2)->(13.5,0) L=2.50m

        # Hydraulic anchor post at x=13.0, y=2.5
        h_anc = len(nodes)
        nodes.append([round(x0 + sign * 13.0, 3), 2.5])
        members.append([s_deck[5], h_anc, "steel"])
        members.append([s_deck[4], h_anc, "cable"])

        # Bascule leaf: pivots at s_deck[5] (x=13.5) to x=17.9
        piv = s_deck[5]
        l1 = len(nodes); nodes.append([round(x0 + sign * 15.6, 3), 0.0])
        l2 = len(nodes); nodes.append([round(x0 + sign * 17.9, 3), 0.0])
        members.append([piv, l1, "road"])
        members.append([l1, l2, "road"])

        l_top = len(nodes); nodes.append([round(x0 + sign * 15.6, 3), 0.9])
        members.append([piv, l_top, "cable"])
        members.append([l1, l_top, "wood"])
        members.append([l2, l_top, "cable"])

        # Hydraulic from h_anc (13.0, 2.5) to l1 (15.6, 0.0) -> L=3.61m
        members.append([h_anc, l1, "hydraulic", "A"])

    sensors = [{"id": "h", "type": "horn", "cooldown": 25.0}]
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
    lv = bridge.load_level("6")
    d = make_l6_arch(arch_y=-2.0)
    for it in range(25):
        P = bridge.parse_design(lv, d)
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
                        t, idx, f = float(parts[0]), int(parts[2]), float(parts[3])
                        if d["members"][idx][2] in ("wood", "cable"):
                            if earliest is None or t < earliest[0]:
                                earliest = (t, idx, f, os.path.basename(sp))
                            break
        if all_ok:
            print(f"PASS! cost={P['cost']:.1f}")
            save_submission("level6.json", d)
            break
        if earliest is None:
            print(f"Stopped at iter {it}, cost={P['cost']:.1f}")
            for sp in bridge.sample_paths(lv):
                sc = bridge.load_json(sp)
                res, _ = bridge.simulate(lv, P, sc)
                print(os.path.basename(sp), bridge.summarize(res, P, sc)["text"].strip())
                print("  Events:", res["events"][:10])
            break
        t, idx, f, sname = earliest
        cur = d["members"][idx][2]
        nxt = "cable" if (cur == "wood" and f > 0) else "steel"
        print(f"iter {it}: cost={P['cost']:.1f}, {cur} m[{idx}] (f={f:.0f}) -> {nxt} at t={t:.2f}s in {sname}")
        d["members"][idx][2] = nxt
