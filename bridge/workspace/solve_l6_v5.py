import os, sys, copy, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bridge
from opt_helper import eval_design, save_submission

def make_l6_warren3m(top_y=2.4, l_top_y=0.95, open_delay=5.0, close_delay=13.5, green_delay=16.5):
    nodes = []
    members = []

    for side in [0, 1]:
        if side == 0:
            x0, sign = 0.0, 1.0
            a_deck, a_pier = "A0", "A4"
        else:
            x0, sign = 36.0, -1.0
            a_deck, a_pier = "A6", "A5"

        # Deck nodes: x = 0, 2.4, 4.8, 7.2, 9.6, 12.0, 14.0 (5x 2.4m + 1x 2.0m)
        xs = [0.0, 2.4, 4.8, 7.2, 9.6, 12.0, 14.0]
        s_deck = [a_deck]
        for x in xs[1:]:
            s_deck.append(len(nodes))
            nodes.append([round(x0 + sign * x, 3), 0.0])

        for k in range(len(s_deck) - 1):
            members.append([s_deck[k], s_deck[k + 1], "road"])

        # Pier support at x=12, y=-2 -> supports (12,0) and (14,0)
        members.append([a_pier, s_deck[5], "steel"])   # (12,-2)-(12,0) L=2.0
        members.append([a_pier, s_deck[6], "steel"])   # (12,-2)-(14,0) L=2.83

        # Above-deck Warren truss top nodes at x = 1.2, 3.6, 6.0, 8.4, 10.8, 12.0 (y = top_y)
        top_xs = [1.2, 3.6, 6.0, 8.4, 10.8, 12.0]
        s_top = []
        for x in top_xs:
            s_top.append(len(nodes))
            nodes.append([round(x0 + sign * x, 3), top_y])

        # Top chords
        for k in range(len(s_top) - 1):
            members.append([s_top[k], s_top[k + 1], "steel"])

        # Diagonals for the 5 Warren panels (0..2.4..4.8..7.2..9.6..12)
        for k in range(5):
            members.append([s_deck[k], s_top[k], "wood"])
            members.append([s_deck[k + 1], s_top[k], "wood"])

        # Vertical post at x=12: (12,0) -> (12, top_y)
        members.append([s_deck[5], s_top[5], "steel"])

        # h_anc is s_top[5] = (12, top_y)
        h_anc = s_top[5]

        # Bascule leaf: pivots at s_deck[6] (x=14.0) to x=17.95
        piv = s_deck[6]
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
        earliest = None
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
                        mat = d["members"][m_idx][2]
                        if mat == "wood" or (mat == "cable" and f > 0):
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
    for ty in [2.3, 2.5]:
        print(f"=== Testing 3m above-deck Warren top_y={ty} ===")
        d = make_l6_warren3m(top_y=ty)
        ok, cost, d_out, msg = smart_upgrade(d, max_iters=45)
        print(f"L6 Warren3m top_y={ty}: ok={ok} cost={cost:.1f} {msg}")
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
