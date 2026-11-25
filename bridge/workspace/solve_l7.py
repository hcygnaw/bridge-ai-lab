import os, sys, math, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bridge
from opt_helper import save_submission

def make_fortress_bridge(n_seg=12, depth=2.95):
    # 28m river, anchors: A0=(0,0), A1=(0,-2), A2=(-5,0), A3=(28,0), A4=(28,-2), A5=(33,0)
    # Budget: 26,000. Static only.
    nodes = []
    members = []
    dx = 28.0 / n_seg  # 2.0m

    # Deck nodes: A0, 0..n_seg-2, A3
    deck = ["A0"]
    for i in range(1, n_seg):
        deck.append(len(nodes))
        nodes.append([round(i * dx, 3), 0.0])
    deck.append("A3")

    for i in range(n_seg):
        members.append([deck[i], deck[i + 1], "road"])

    # Above-deck steel Warren truss (depth = 3.2m)
    top = []
    for i in range(n_seg):
        top.append(len(nodes))
        nodes.append([round((i + 0.5) * dx, 3), depth])

    for i in range(n_seg - 1):
        members.append([top[i], top[i + 1], "steel"])
    for i in range(n_seg):
        members.append([deck[i], top[i], "steel"])
        members.append([deck[i + 1], top[i], "steel"])

    # Tie top ends to A2=(-5,0) and A5=(33,0) with cables? No, top[0]=(1,3.2) to A2=(-5,0) is 6.8m cable
    members.append(["A2", top[0], "cable"])
    members.append(["A2", top[1], "cable"])
    members.append(["A5", top[-1], "cable"])
    members.append(["A5", top[-2], "cable"])

    # Under-deck steel end braces from A1=(0,-2) and A4=(28,-2)
    members.append(["A1", deck[1], "steel"])
    members.append(["A1", deck[2], "steel"])
    members.append(["A4", deck[-2], "steel"])
    members.append(["A4", deck[-3], "steel"])

    return {"nodes": nodes, "members": members}


def make_saboteur(speed=9.5, accel=4.0, ballast_mass=1530):
    # Max mass 2500 kg, max cost 6000, len <= 3.0m, height <= 1.5m
    # 2 wheels at x = 0.0, -2.8, y = 0.22 (2 * 80 = 160 kg)
    nodes = [
        [0.0, 0.22],
        [-2.8, 0.22],
        [-1.05, 0.65],
        [-1.4, 0.65],
        [-1.75, 0.65],
        [-1.4, 1.45],
    ]
    members = [
        # Rigid steel chassis
        [0, 1, "steel"],
        [2, 3, "steel"],
        [3, 4, "steel"],
        [0, 2, "steel"],
        [1, 4, "steel"],
        [0, 3, "steel"],
        [1, 3, "steel"],
        # Hammer hydraulics from 2 and 4 to 5 (symmetric 2-bar linkage -> zero binding!)
        [2, 5, "hydraulic", "H"],
        [4, 5, "hydraulic", "H"],
    ]
    ballast = [
        [5, ballast_mass],
    ]
    sensors = [
        {"id": "g1", "type": "mygate", "x": 6.0},
        {"id": "g2", "type": "mygate", "x": 12.0},
        {"id": "g3", "type": "mygate", "x": 18.0},
    ]
    rules = [
        {"on": "g1", "delay": 0.0, "do": "hyd", "group": "H", "ratio": 1.5, "speed": 3.0, "accel": 5.0},
        {"on": "g1", "delay": 0.25, "do": "hyd", "group": "H", "ratio": 0.5, "speed": 3.0, "accel": 5.0},
        {"on": "g2", "delay": 0.0, "do": "hyd", "group": "H", "ratio": 1.5, "speed": 3.0, "accel": 5.0},
        {"on": "g2", "delay": 0.25, "do": "hyd", "group": "H", "ratio": 0.5, "speed": 3.0, "accel": 5.0},
        {"on": "g3", "delay": 0.0, "do": "hyd", "group": "H", "ratio": 1.5, "speed": 3.0, "accel": 5.0},
        {"on": "g3", "delay": 0.25, "do": "hyd", "group": "H", "ratio": 0.5, "speed": 3.0, "accel": 5.0},
    ]
    return {
        "nodes": nodes,
        "members": members,
        "wheels": [0, 1],
        "ballast": ballast,
        "motor": {"speed": speed, "accel": accel},
        "sensors": sensors,
        "rules": rules,
    }


if __name__ == "__main__":
    lv = bridge.load_level("final")
    fb = make_fortress_bridge()
    P = bridge.parse_design(lv, fb)
    print(f"Fortress bridge cost: {P['cost']:.1f} / {lv['budget']}")
    sc = bridge.load_json(bridge.sample_paths(lv)[0])
    res, _ = bridge.simulate(lv, P, sc)
    s = bridge.summarize(res, P, sc)
    print("Fortress solo:", s["ok"], s["text"])
    if s["ok"]:
        save_submission("final_bridge.json", fb)

    sab = make_saboteur()
    save_submission("saboteur.json", sab)
