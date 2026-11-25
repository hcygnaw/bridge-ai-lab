import os, sys, copy, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bridge
from opt_helper import eval_design, save_submission

def make_l6_above_pratt(top_y=2.2, l_top_y=0.95, open_delay=5.0, close_delay=13.5, green_delay=16.5):
    nodes = []
    members = []

    for side in [0, 1]:
        if side == 0:
            x0, sign = 0.0, 1.0
            a_deck, a_pier = "A0", "A4"
        else:
            x0, sign = 36.0, -1.0
            a_deck, a_pier = "A6", "A5"

        # Deck nodes: x = 0, 2, 4, 6, 8, 10, 12, 14
        s_deck = [a_deck]
        for k in range(1, 8):
            s_deck.append(len(nodes))
            nodes.append([round(x0 + sign * (2.0 * k), 3), 0.0])

        for k in range(7):
            members.append([s_deck[k], s_deck[k + 1], "road"])

        # Pier support at x=12, y=-2 -> supports s_deck[5]=(10,0), s_deck[6]=(12,0), s_deck[7]=(14,0)
        members.append([a_pier, s_deck[6], "steel"])   # (12,-2)-(12,0) L=2.0
        members.append([a_pier, s_deck[7], "steel"])   # (12,-2)-(14,0) L=2.83
        members.append([a_pier, s_deck[5], "wood"])    # (12,-2)-(10,0) L=2.83

        # Above-deck Pratt truss top nodes at x = 2, 4, 6, 8, 10, 12 (y = top_y)
        s_top = []
        for k in range(1, 7):
            s_top.append(len(nodes))
            nodes.append([round(x0 + sign * (2.0 * k), 3), top_y])

        # End diagonal (0,0) -> (2, top_y) in compression
        members.append([s_deck[0], s_top[0], "steel"])

        # Top chord (2..12) in compression
        for k in range(5):
            members.append([s_top[k], s_top[k + 1], "wood"])

        # Verticals at x = 2, 4, 6, 8, 10, 12
        for k in range(6):
            members.append([s_deck[k + 1], s_top[k], "wood"])

        # Pratt diagonals (slope down toward midspan x=6 -> tension under gravity!)
        # Left half (x=2..6): (2, top)->(4,0), (4, top)->(6,0)
        members.append([s_top[0], s_deck[2], "wood"])
        members.append([s_top[1], s_deck[3], "wood"])
        # Right half (x=6..12): (8, top)->(6,0), (10, top)->(8,0), (12, top)->(10,0)
        members.append([s_top[3], s_deck[3], "wood"])
        members.append([s_top[4], s_deck[4], "wood"])
        members.append([s_top[5], s_deck[5], "wood"])

        # h_anc is s_top[5] = (12, top_y)!
        h_anc = s_top[5]

        # Bascule leaf: pivots at s_deck[7] (x=14.0) to x=17.95
        piv = s_deck[7]
        l1 = len(nodes); nodes.append([round(x0 + sign * 15.975, 3), 0.0])
        l2 = len(nodes); nodes.append([round(x0 + sign * 17.95, 3), 0.0])
        members.append([piv, l1, "road"])
        members.append([l1, l2, "road"])

        l_top = len(nodes); nodes.append([round(x0 + sign * 15.975, 3), l_top_y])
        members.append([piv, l_top, "cable"])
        members.append([l1, l_top, "wood"])
        members.append([l2, l_top, "cable"])

        # Hydraulic from h_anc (12, top_y) to l1 (15.975, 0)
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


def smart_upgrade(d, max_iters=45):
    lv = bridge.load_level("6")
    d = copy.deepcopy(d)
    for it in range(max_iters):
        try:
            P = bridge.parse_design(lv, d)
        except Exception as e:
            return False, 999999.0, d, str(e)
        all_ok = True
        earliest = None  # (t, m_idx, force, sample_name)
        for sp in bridge.sample_paths(lv):
            sc = bridge.load_json(sp)
            res, _ = bridge.simulate(lv, P, sc)
            s = bridge.summarize(res, P, sc)
            if not s["ok"]:
                all_ok = False
                for ev in res["events"]:
                    if "BREAK " in ev:
                        parts = ev.split()
                        t = float(parts[0])
                        m_idx = int(parts[2])
                        f = float(parts[3])
                        if d["members"][m_idx][2] == "wood":
                            if earliest is None or t < earliest[0]:
                                earliest = (t, m_idx, f, os.path.basename(sp))
                        elif d["members"][m_idx][2] == "cable" and f > 0:
                            if earliest is None or t < earliest[0]:
                                earliest = (t, m_idx, f, os.path.basename(sp))
        if all_ok:
            return True, P["cost"], d, "PASS"
        if earliest is None:
            return False, P["cost"], d, "No wood/cable break found"
        t, idx, f, sname = earliest
        mat = d["members"][idx][2]
        print(f"  iter {it}: cost={P['cost']:.1f}, earliest {mat} break m[{idx}] (f={f:.0f}) at t={t:.2f}s in {sname}")
        if mat == "wood":
            d["members"][idx][2] = "cable" if f > 0 else "steel"
        else:
            d["members"][idx][2] = "steel"
    return False, P["cost"], d, "Max iters"


if __name__ == "__main__":
    for ty in [2.2, 2.4, 2.6]:
        print(f"=== Testing above-deck Pratt top_y={ty} ===")
        d = make_l6_above_pratt(top_y=ty)
        ok, cost, d_out, msg = smart_upgrade(d, max_iters=45)
        print(f"L6 Pratt top_y={ty}: ok={ok} cost={cost:.1f} {msg}")
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
