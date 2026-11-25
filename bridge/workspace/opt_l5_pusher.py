import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bridge

lv = bridge.load_level("5")
scenarios = [bridge.load_json(p) for p in bridge.sample_paths(lv)]


def make_pusher(ramp_angle=22.0, ramp_len=4.5, speed=15.0, accel=100.0, delay=0.15):
    nodes, members = [], []

    # Rigid 2-span pit: -11, -8.8, -6.6, -5.0, -2.5, 0 supported by 1 braced pier at (-5.0, 0)
    pit_pts = [(-9.17, -0.2), (-7.33, -0.2), (-5.0, 0.0), (-3.33, -0.2), (-1.67, -0.2)]
    pit_nodes = ["A2"]
    for x, y in pit_pts:
        nodes.append([x, y])
        pit_nodes.append(len(nodes) - 1)
    pit_nodes.append("A0")
    for i in range(6):
        members.append([pit_nodes[i], pit_nodes[i + 1], "road"])
    # Pier mid-node at (-5.0, -2.0) braced to A5=(-6,-4), A4=(-4,-4) -> 2m steel = 140 kN!
    nodes.append([-5.0, -2.0])
    mp = len(nodes) - 1
    members.append(["A5", mp, "steel"])
    members.append(["A4", mp, "steel"])
    members.append([mp, pit_nodes[3], "steel"])
    members.append([mp, pit_nodes[2], "steel"])
    members.append([mp, pit_nodes[4], "steel"])

    # Fixed launch ramp from A0=(0,0) up at ramp_angle (2 segments)
    rad = math.radians(ramp_angle)
    r1x, r1y = round(0.5 * ramp_len * math.cos(rad), 4), round(0.5 * ramp_len * math.sin(rad), 4)
    r2x, r2y = round(ramp_len * math.cos(rad), 4), round(ramp_len * math.sin(rad), 4)
    nodes.append([r1x, r1y])
    R1 = len(nodes) - 1
    nodes.append([r2x, r2y])
    R2 = len(nodes) - 1
    members.append(["A0", R1, "road"])
    members.append([R1, R2, "road"])
    # Support ramp from A1=(0,-2)
    members.append(["A1", R1, "steel"])
    members.append(["A1", R2, "steel"])

    # Pusher: a vertical road bar (P_bot -> P_top) sitting above pit_nodes[4]=(-2.2, 0)
    # Wait: if P_bot starts at (-3.5, 0.35) and P_top at (-3.5, 0.95),
    # Wait: road->road collision might block the car if P_bot is in the way!
    # So P_bot starts at (-3.5, 1.3) (ABOVE the car!) and drops/swings? No, even simpler:
    # Start P_bot at (-4.0, 0.35) -> when car passes x=-1.0, gate triggers hydraulic from A0=(0,0) or (-4.4, 0)
    # Actually: if P_bot starts at (-4.0, 1.2) and P_top at (-4.0, 1.8), car drives UNDER it?
    # No, car height is 0.55m! So (-4.0, 1.2) is above the car, and a 2nd hydraulic drops it?
    # Simpler: car passes x = 0.0 -> gate at x = 0.2 triggers hydraulic from A2/pit_nodes[3]=(-4.4, 0) to P_bot=(-1.5, 0.35)
    # Wait: P_bot=(-1.5, 0.35) is BEHIND the car (car front is at x=0.2, rear is at x=-1.0)!
    # Let's put P_bot at (-1.8, 0.30) and P_top at (-1.8, 0.70), connected by 'road' (length 0.40m).
    # Held by hydraulic from pit_nodes[3]=(-4.4, 0.0) -> P_bot (L=2.62m) and pit_nodes[3] -> P_top (L=2.69m)!
    # Wait: when car is at x=-1.8, P_bot is at x=-1.8? No, trigger when car front is at x=0.2 -> rear is at x=-1.0!
    # So P_bot can't be at -1.8 before the car passes -1.8!
    # Solution: P_bot starts at (-1.8, 1.2), P_top at (-1.8, 1.6) (above the car, y=1.2 > 0.7!),
    # or just put P_bot at y = 0.30 at x = -1.8, and have it ALREADY be behind the car? No, car drives from x=-24!
    # So put P_bot at (-1.8, 1.2) -> drop it? No, put a 'gate' at x=0.5, and push from (-1.8, 1.2)? Still needs to drop to y=0.3.
    # Use 2 hydraulics:
    # 1) Drop/push arm: A0=(0, 0.0) -> ... no, pit_nodes[3]=(-4.4, 0) -> P_bot(-1.8, 0.35) would block car!
    # Wait: cars ONLY collide with 'road'! They pass through 'steel' and 'hydraulic'!
    # So if P_bot=(-1.8, 1.1) and P_top=(-1.8, 1.6) is 'road', car drives right UNDER it at y<=0.7!
    # Then when gate at x=0.2 fires:
    # - Group 'D' (drop): hyd from pit_nodes[4]=(-2.2, 0) to P_bot=(-1.8, 1.1) contracts (ratio=0.5 -> P_bot drops to y=0.35)!
    # - Group 'P' (push): hyd from pit_nodes[3]=(-4.4, 0) to P_bot extends (ratio=1.95, speed=15.0, accel=120.0)!
    nodes.append([-1.8, 1.15])
    Pb = len(nodes) - 1
    nodes.append([-1.8, 1.60])
    Pt = len(nodes) - 1
    members.append([Pb, Pt, "road"])
    members.append([pit_nodes[5], Pb, "hydraulic", "D"])
    members.append([pit_nodes[3], Pb, "hydraulic", "P"])
    members.append([pit_nodes[3], Pt, "hydraulic", "P"])

    sensors = [{"id": "g", "type": "gate", "x": 0.2, "dir": "right"}]
    rules = [
        {"on": "g", "delay": 0.0, "do": "hyd", "group": "D", "ratio": 0.5, "speed": 10.0, "accel": 80.0},
        {"on": "g", "delay": 0.08, "do": "hyd", "group": "P", "ratio": 1.95, "speed": speed, "accel": accel},
        {"on": "g", "delay": 1.5, "do": "hyd", "group": "D", "ratio": 1.0, "speed": 4.0, "accel": 20.0},
        {"on": "g", "delay": 1.5, "do": "hyd", "group": "P", "ratio": 1.0, "speed": 4.0, "accel": 20.0},
    ]
    return {"nodes": nodes, "members": members, "sensors": sensors, "rules": rules}


d = make_pusher()
P = bridge.parse_design(lv, d)
print("Cost:", P["cost"])
for sc in scenarios:
    res, _ = bridge.simulate(lv, P, sc)
    print(sc["name"], "ok=", res["ok"], bridge.summarize(res, P, sc)["text"].replace("\n", " | "))
