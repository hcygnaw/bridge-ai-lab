import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bridge
import saboteur

lv = bridge.load_level("final")
convoy_sc = bridge.load_json("levels/final/sample1.json")


def make_enemy_valid_bridge():
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
        members.append([bot(i), bot(i + 1), "steel" if 4 <= i <= 9 else "cable"])
    for i in range(1, n_seg):
        members.append([top(i), bot(i), "wood"])
    for i in range(n_seg):
        if i < n_seg // 2:
            members.append([top(i), bot(i + 1), "steel" if i in (0, 1, 2) else "wood"])
        else:
            members.append([bot(i), top(i + 1), "steel" if i in (11, 12, 13) else "wood"])
    return {"nodes": nodes, "members": members}


def make_saboteur_hammer():
    nodes = [
        [0.0, 0.22],
        [-2.0, 0.22],
        [-1.0, 1.45],
    ]
    members = [
        [0, 1, "steel"],
        [0, 2, "hydraulic", "H"],
        [1, 2, "hydraulic", "H"],
    ]
    wheels = [0, 1]
    ballast = [[2, 2050]]
    motor = {"speed": 10.0, "accel": 4.0}
    sensors = [
        {"id": "g1", "type": "mygate", "x": 14.0},
        {"id": "g2", "type": "mygate", "x": 22.0},
    ]
    rules = [
        {"on": "g1", "delay": 0.0, "do": "hyd", "group": "H", "ratio": 1.6, "speed": 3.0, "accel": 5.0},
        {"on": "g1", "delay": 0.35, "do": "hyd", "group": "H", "ratio": 0.80, "speed": 3.0, "accel": 5.0},
        {"on": "g2", "delay": 0.0, "do": "hyd", "group": "H", "ratio": 1.6, "speed": 3.0, "accel": 5.0},
        {"on": "g2", "delay": 0.35, "do": "hyd", "group": "H", "ratio": 0.85, "speed": 3.0, "accel": 5.0},
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

fb = bridge.load_json("submission/final_bridge.json")
P_fb = bridge.parse_design(lv, fb)
out_fb, _ = saboteur.duel(lv, P_fb, S)
print("Duel vs final_bridge:", out_fb["verdict"], "| sab:", out_fb["res"]["sab"])

ev = make_enemy_valid_bridge()
P_ev = bridge.parse_design(lv, ev)
res_ev_clean, _ = bridge.simulate(lv, P_ev, convoy_sc)
print("Enemy valid bridge (no sab) ok=", res_ev_clean["ok"], "cost=", P_ev["cost"])
if res_ev_clean["ok"]:
    out_ev, _ = saboteur.duel(lv, P_ev, S)
    print("Duel vs enemy valid bridge:", out_ev["verdict"], "| sab:", out_ev["res"]["sab"])

with open("submission/saboteur.json", "w") as f:
    json.dump(sab_d, f, indent=2)
print("Saved submission/saboteur.json")
