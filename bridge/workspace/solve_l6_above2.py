import copy, json, math, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bridge
from opt_helper import eval_design, save_submission

SAMPLES = ["levels/level6/sample1.json", "levels/level6/sample2.json", "levels/level6/sample3.json"]

def make_l6_above(top_y=2.2, piv_x=13.7, l1_x=15.4, l2_x=17.85, open_delay=5.0, close_delay=17.0, green_delay=18.5):
    nodes = []
    members = []

    for side in (0, 1):
        sign = 1 if side == 0 else -1
        x0 = 0.0 if side == 0 else 36.0
        a_deck = "A0" if side == 0 else "A6"
        a_bot = "A1" if side == 0 else "A7"
        a_pier = "A4" if side == 0 else "A5"

        # 6 road segments of 2.0m from 0 to 12.0 + 1 cantilever to piv_x (13.5)
        xs = [2.0, 4.0, 6.0, 8.0, 10.0, 12.0, piv_x]
        s_deck = []
        for x in xs:
            idx = len(nodes)
            nodes.append([round(x0 + sign * x, 3), 0.0])
            s_deck.append(idx)
        for i in range(len(s_deck)):
            u = a_deck if i == 0 else s_deck[i - 1]
            v = s_deck[i]
            members.append([u, v, "road"])

        # Above-deck Warren truss ONLY over the 8m span [2, 10]: 4 top nodes at x=3, 5, 7, 9
        s_top = []
        for i in range(1, 5):
            idx = len(nodes)
            nodes.append([round(x0 + sign * (2.0 * i + 1.0), 3), top_y])
            s_top.append(idx)
            dl = s_deck[i - 1]
            dr = s_deck[i]
            members.append([idx, dl, "wood"])
            members.append([idx, dr, "wood"])
        for i in range(3):
            members.append([s_top[i], s_top[i + 1], "wood"])

        # Knee-braces from A1=(0,-2) to (2,0) and A4=(12,-2) to (10,0) shrink 12m span to 8m!
        members.append([a_bot, s_deck[0], "steel"])
        members.append([a_pier, s_deck[4], "steel"])
        # Pier A4=(12,-2) supports s_deck[5]=(12,0) and piv=(13.5,0)
        members.append([a_pier, s_deck[5], "steel"])
        members.append([a_pier, s_deck[6], "steel"])

        # Hydraulic anchor at (13.5, 2.5) directly above piv
        h_anc = len(nodes)
        nodes.append([round(x0 + sign * 13.5, 3), 2.5])
        members.append([s_top[3], h_anc, "cable"])   # (9,top_y)-(13.5,2.5)
        members.append([s_deck[6], h_anc, "steel"])

        # Bascule leaf: pivots at s_deck[6] (13.7) to 17.85
        piv = s_deck[6]
        l1 = len(nodes); nodes.append([round(x0 + sign * l1_x, 3), 0.0])
        l2 = len(nodes); nodes.append([round(x0 + sign * l2_x, 3), 0.0])
        members.append([piv, l1, "road"])
        members.append([l1, l2, "road"])

        l_bot = len(nodes); nodes.append([round(x0 + sign * l1_x, 3), -1.0])
        members.append([piv, l_bot, "steel"])
        members.append([l1, l_bot, "steel"])
        members.append([l2, l_bot, "steel"])

        # Hydraulic from h_anc (13.2, top_y) to l1 (15.7, 0.0) -> L = 3.2m
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

def auto_upgrade(d, max_iters=25):
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
            print(f"  Stopped at iter {it}, cost={P['cost']:.1f}")
            for sp in bridge.sample_paths(lv):
                sc = bridge.load_json(sp)
                res, _ = bridge.simulate(lv, P, sc)
                print(" ", os.path.basename(sp), res["ok"], "Events:", [e for e in res["events"] if any(k in e for k in ("BREAK", "FAIL", "SHIPHIT"))][:8])
            return False, P["cost"], d, "No wood/cable break"
        t, idx, f, sname = earliest
        cur = d["members"][idx][2]
        nxt = "cable" if (cur == "wood" and f > 0 and idx in (26, 28, 56, 58)) else "steel"
        print(f"  iter {it}: cost={P['cost']:.1f}, {cur} m[{idx}] (f={f:.0f}) -> {nxt} at t={t:.2f}s in {sname}")
        d["members"][idx][2] = nxt
    return False, P["cost"], d, "Max iters"

for top_y in (2.2,):
    for close_d, green_d in [(14.2, 16.0)]:
        print(f"=== Testing top_y={top_y} close={close_d} green={green_d} ===")
        d = make_l6_above(top_y=top_y, open_delay=5.0, close_delay=close_d, green_delay=green_d)
        ok, cost, d, msg = auto_upgrade(d, max_iters=20)
        print(f"Result: ok={ok}, cost={cost:.1f}, msg={msg}")
        if ok and cost <= 20000:
            with open("submission/level6.json", "w") as f:
                json.dump(d, f)
            print("SAVED submission/level6.json!")
            sys.exit(0)
