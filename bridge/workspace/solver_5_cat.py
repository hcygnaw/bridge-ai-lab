import math
import bridge as B
from opt_utils import eval_design, save_if_best


def make_l5_cat_catch(tip_x=4.4, tip_y=0.6, ratio=1.25, speed=8.0, accel=30.0, gate_x=3.0, catch_x=18.2, catch_y=-0.6):
    nodes = [[-8.6, 0.0], [-6.2, 0.0], [-3.8, 0.0], [-1.75, 0.0], [-5.2, -1.8]]
    members = [
        ["A2", 0, "road"], [0, 1, "road"], [1, 2, "road"], [2, 3, "road"], [3, "A0", "road"],
        ["A5", 4, "steel"], ["A4", 4, "steel"], [4, 0, "steel"], [4, 1, "steel"], [4, 2, "steel"], [4, 3, "steel"],
    ]
    l1 = len(nodes); nodes.append([round(tip_x * 0.5, 4), round(tip_y * 0.4, 4)])
    l2 = len(nodes); nodes.append([tip_x, tip_y])
    members += [["A0", l1, "road"], [l1, l2, "road"]]
    lu = len(nodes); nodes.append([round(tip_x * 0.5, 4), -0.65])
    members += [["A0", lu, "steel"], [l1, lu, "steel"], [l2, lu, "steel"], ["A1", lu, "hydraulic", "C"]]

    c0 = len(nodes); nodes.append([catch_x, catch_y])
    c1 = len(nodes); nodes.append([round(catch_x + (24.0 - catch_x) / 3, 4), round(catch_y * 0.65, 4)])
    c2 = len(nodes); nodes.append([round(catch_x + 2 * (24.0 - catch_x) / 3, 4), round(catch_y * 0.3, 4)])
    members += [[c0, c1, "road"], [c1, c2, "road"], [c2, "A7", "road"]]
    members += [["A8", c1, "steel"], ["A8", c2, "steel"], [c0, "A7", "cable"]]

    sensors = [{"id": "g", "type": "gate", "x": gate_x, "dir": "right"}]
    rules = [
        {"on": "g", "delay": 0.0, "do": "hyd", "group": "C", "ratio": ratio, "speed": speed, "accel": accel},
        {"on": "g", "delay": delay + 0.65 if False else 0.65, "do": "hyd", "group": "C", "ratio": 1.0, "speed": 10.0, "accel": 40.0},
    ]
    return {"nodes": nodes, "members": members, "sensors": sensors, "rules": rules}


if __name__ == "__main__":
    for cx in [18.5, 19.5]:
        for r in [1.18, 1.25, 1.32]:
            for sp in [7.0, 9.0, 11.0]:
                for gx in [2.6, 3.1, 3.6]:
                    d = make_l5_cat_catch(4.4, 0.6, r, sp, 35.0, gx, cx, -0.8)
                    ok, cost, pk, det = eval_design(5, d, quiet=True)
                    if ok:
                        print(f"L5 PASS! cx={cx} r={r} sp={sp} gx={gx} cost={cost:.0f} pk={pk*100:.1f}%")
                        save_if_best(5, d)
    d = make_l5_cat_catch(4.4, 0.6, 1.25, 9.0, 35.0, 3.1, 18.5, -0.8)
    ok, cost, pk, det = eval_design(5, d, quiet=False)
    print(f"Sample cost={cost:.0f}")
