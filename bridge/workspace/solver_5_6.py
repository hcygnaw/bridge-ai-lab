import math
import bridge as B
from opt_utils import eval_design, save_if_best


def make_l5_ramp_kick(tip_x=4.6, tip_y=0.7, ratio=1.30, speed=11.0, accel=60.0, delay=0.0, gate_x=3.2, add_catch=False):
    nodes = [[-8.6, 0.0], [-6.2, 0.0], [-3.8, 0.0], [-1.75, 0.0], [-5.2, -1.8]]
    members = [
        ["A2", 0, "road"], [0, 1, "road"], [1, 2, "road"], [2, 3, "road"], [3, "A0", "road"],
        ["A5", 4, "steel"], ["A4", 4, "steel"], [4, 0, "steel"], [4, 1, "steel"], [4, 2, "steel"], [4, 3, "steel"],
    ]
    l1 = len(nodes); nodes.append([round(tip_x * 0.5, 4), round(tip_y * 0.4, 4)])
    l2 = len(nodes); nodes.append([tip_x, tip_y])
    members += [["A0", l1, "road"], [l1, l2, "road"]]
    lu = len(nodes); nodes.append([round(tip_x * 0.5, 4), -0.6])
    members += [["A0", lu, "steel"], [l1, lu, "steel"], [l2, lu, "steel"], ["A0", l2, "steel"], ["A1", lu, "hydraulic", "C"]]

    if add_catch:
        # Catch deck from (18.5, -0.8) -> (21.25, -0.4) -> A7=(24.0, 0.0)
        # Wait: dist(18.5, 24) = 5.5m (3 road segs: 18.5 -> 20.33 -> 22.16 -> 24.0)
        # Support from A8=(24,-2): steel A8->(20.5,-1.5)->(18.5,-0.8) etc.
        c0 = len(nodes); nodes.append([19.2, -0.6])
        c1 = len(nodes); nodes.append([21.6, -0.3])
        members += [[c0, c1, "road"], [c1, "A7", "road"]]
        # Support c0 from A8=(24,-2) (L=hypot(4.8,1.4)=5.0m steel!) and cable c0->A9=(30,0)? (10.8m cable=756)
        members += [[c0, "A8", "steel"], [c1, "A8", "steel"], [c0, "A9", "cable"]]

    sensors = [{"id": "g", "type": "gate", "x": gate_x, "dir": "right"}]
    rules = [
        {"on": "g", "delay": delay, "do": "hyd", "group": "C", "ratio": ratio, "speed": speed, "accel": accel},
        {"on": "g", "delay": delay + 0.55, "do": "hyd", "group": "C", "ratio": 1.0, "speed": 10.0, "accel": 40.0},
    ]
    return {"nodes": nodes, "members": members, "sensors": sensors, "rules": rules}


if __name__ == "__main__":
    for ac in [False, True]:
        for r in [1.20, 1.28, 1.38]:
            for sp in [8.0, 10.5, 13.0]:
                for gx in [2.8, 3.4, 4.0]:
                    d = make_l5_ramp_kick(4.6, 0.7, r, sp, 60.0, 0.0, gx, ac)
                    ok, cost, pk, det = eval_design(5, d, quiet=True)
                    if ok:
                        print(f"L5 PASS! catch={ac} r={r} sp={sp} gx={gx} cost={cost:.0f} pk={pk*100:.1f}%")
                        save_if_best(5, d)
    # Inspect one!
    d = make_l5_ramp_kick(4.6, 0.7, 1.28, 10.5, 60.0, 0.0, 3.4, True)
    ok, cost, pk, det = eval_design(5, d, quiet=False)
    print(f"Sample inspect cost={cost:.0f}")
    lv = B.load_level(5)
    P = B.parse_design(lv, d)
    sc = B.load_json(B.sample_paths(lv)[0])
    res, rep = B.simulate(lv, P, sc, replay=True)
    for ev in res["events"][:15]:
        print(" ", ev)
