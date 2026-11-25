import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bridge

lv = bridge.load_level("5")
scenarios = [bridge.load_json(p) for p in bridge.sample_paths(lv)]


def make_catapult(ratio=1.22, speed=11.0, accel=60.0, gate_x=1.5, delay=0.1):
    nodes, members = [], []

    # Rigid 2-span pit: -11, -8.8, -6.6, -4.4, -2.2, 0 supported by A6, A5, A4, A3
    pit_xs = [-8.8, -6.6, -4.4, -2.2]
    pit_nodes = ["A2"]
    for x in pit_xs:
        nodes.append([x, 0.0])
        pit_nodes.append(len(nodes) - 1)
    pit_nodes.append("A0")
    for i in range(5):
        members.append([pit_nodes[i], pit_nodes[i + 1], "road"])
    # Mid-height nodes at y=-2.0 so steel struts are ~2m (140 kN buckling!)
    nodes.append([-7.7, -2.0])
    m1 = len(nodes) - 1
    nodes.append([-3.3, -2.0])
    m2 = len(nodes) - 1
    members.append(["A6", m1, "steel"])
    members.append(["A5", m1, "steel"])
    members.append([m1, pit_nodes[1], "steel"])
    members.append([m1, pit_nodes[2], "steel"])
    members.append(["A4", m2, "steel"])
    members.append(["A3", m2, "steel"])
    members.append([m2, pit_nodes[3], "steel"])
    members.append([m2, pit_nodes[4], "steel"])

    # Catapult ramp: A0=(0,0) -> R1=(2.2, 0) -> R2=(4.4, 0)
    nodes.append([2.2, 0.0])
    R1 = len(nodes) - 1
    nodes.append([4.4, 0.0])
    R2 = len(nodes) - 1
    # Rigidify ramp with a top node T=(2.2, 1.0)
    nodes.append([2.2, 1.0])
    T = len(nodes) - 1
    members.append(["A0", R1, "road"])
    members.append([R1, R2, "road"])
    members.append(["A0", T, "steel"])
    members.append([R1, T, "steel"])
    members.append([T, R2, "steel"])

    # Hydraulic from A1=(0,-2) to R1=(2.2, 0)
    members.append(["A1", R1, "hydraulic", "C"])

    sensors = [{"id": "g", "type": "gate", "x": gate_x, "dir": "right"}]
    rules = [
        {"on": "g", "delay": delay, "do": "hyd", "group": "C", "ratio": ratio, "speed": speed, "accel": accel},
        {"on": "g", "delay": delay + 1.5, "do": "hyd", "group": "C", "ratio": 1.0, "speed": 4.0, "accel": 20.0},
    ]
    return {"nodes": nodes, "members": members, "sensors": sensors, "rules": rules}


for speed in [9.0, 11.0, 13.0]:
    for ratio in [1.18, 1.24, 1.30]:
        for delay in [0.05, 0.15]:
            d = make_catapult(ratio=ratio, speed=speed, accel=60.0, gate_x=1.5, delay=delay)
            P = bridge.parse_design(lv, d)
            ok = True
            msgs = []
            for sc in scenarios:
                res, _ = bridge.simulate(lv, P, sc)
                if not res["ok"]:
                    ok = False
                    msgs.append(bridge.summarize(res, P, sc)["text"].splitlines()[0])
            print(f"spd={speed} r={ratio} del={delay} ok={ok} cost={P['cost']:.1f} {msgs}")
            if ok:
                with open("submission/level5.json", "w") as f:
                    json.dump(d, f, indent=2)
                raise SystemExit(0)
