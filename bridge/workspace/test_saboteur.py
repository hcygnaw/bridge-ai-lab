import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bridge
import saboteur

lv = bridge.load_level("final")
convoy_sc = bridge.load_json("levels/final/sample1.json")


def make_enemy_wood_truss():
    # A typical budget wood truss (~11k) that easily passes the standard convoy
    n_seg = 14
    dx = 28.0 / n_seg
    nodes, members = [], []
    for i in range(1, n_seg):
        nodes.append([round(i * dx, 4), 0.0])
    def top(i): return "A0" if i == 0 else ("A3" if i == n_seg else i - 1)
    for i in range(n_seg):
        members.append([top(i), top(i + 1), "road"])
    bot_s = len(nodes)
    for i in range(1, n_seg):
        nodes.append([round(i * dx, 4), -2.0])
    def bot(i): return "A1" if i == 0 else ("A4" if i == n_seg else bot_s + i - 1)
    for i in range(n_seg):
        members.append([bot(i), bot(i + 1), "cable" if 3 <= i <= 10 else "wood"])
    for i in range(1, n_seg):
        members.append([top(i), bot(i), "wood"])
    for i in range(n_seg):
        if i < n_seg // 2:
            members.append([top(i), bot(i + 1), "wood"])
        else:
            members.append([bot(i), top(i + 1), "wood"])
    return {"nodes": nodes, "members": members}


def make_saboteur_hammer():
    # 3-node triangle: 0=(0, 0.22) wheel, 1=(-2.5, 0.22) wheel, 2=(-1.25, 1.1) hammer
    # 0->1 is steel, 0->2 and 1->2 are hydraulics in group H (kinematically free!)
    nodes = [
        [0.0, 0.22],
        [-2.5, 0.22],
        [-1.25, 1.10],
    ]
    members = [
        [0, 1, "steel"],
        [0, 2, "hydraulic", "H"],
        [1, 2, "hydraulic", "H"],
    ]
    wheels = [0, 1]
    # Mass: 2*80 + 5 + 2.5*35 + 2*1.53*40 = ~375 kg -> ballast 2050 kg on node 2!
    ballast = [[2, 2050]]
    motor = {"speed": 9.5, "accel": 4.0}
    sensors = [
        {"id": "g1", "type": "mygate", "x": 6.0},
        {"id": "g2", "type": "mygate", "x": 13.0},
        {"id": "g3", "type": "mygate", "x": 20.0},
    ]
    rules = [
        {"on": "g1", "delay": 0.0, "do": "hyd", "group": "H", "ratio": 1.9, "speed": 3.0, "accel": 5.0},
        {"on": "g1", "delay": 0.5, "do": "hyd", "group": "H", "ratio": 0.6, "speed": 3.0, "accel": 5.0},
        {"on": "g2", "delay": 0.0, "do": "hyd", "group": "H", "ratio": 1.9, "speed": 3.0, "accel": 5.0},
        {"on": "g2", "delay": 0.5, "do": "hyd", "group": "H", "ratio": 0.6, "speed": 3.0, "accel": 5.0},
        {"on": "g3", "delay": 0.0, "do": "hyd", "group": "H", "ratio": 1.9, "speed": 3.0, "accel": 5.0},
        {"on": "g3", "delay": 0.5, "do": "hyd", "group": "H", "ratio": 0.7, "speed": 3.0, "accel": 5.0},
    ]
    return {
        "nodes": nodes,
        "members": members,
        "wheels": wheels,
        "ballast": ballast,
        "motor": motor,
        "sensors": sensors,
        "rules": rules,
    }


sab_d = make_saboteur_hammer()
S = saboteur.parse_sab(lv, sab_d)
print(f"Saboteur valid! mass={S['mass']:.1f} kg, cost={S['cost']:.1f}")

# Test against our final_bridge.json
fb = bridge.load_json("submission/final_bridge.json")
P_fb = bridge.parse_design(lv, fb)
out_fb = saboteur.duel(lv, P_fb, S)
print("Duel vs final_bridge:", out_fb)

# Test against enemy wood truss
ew = make_enemy_wood_truss()
P_ew = bridge.parse_design(lv, ew)
res_ew_clean, _ = bridge.simulate(lv, P_ew, convoy_sc)
print("Enemy wood truss (no sab) ok=", res_ew_clean["ok"], "cost=", P_ew["cost"])
out_ew = saboteur.duel(lv, P_ew, S)
print("Duel vs enemy wood truss:", out_ew)

with open("submission/saboteur.json", "w") as f:
    json.dump(sab_d, f, indent=2)
print("Saved submission/saboteur.json")
