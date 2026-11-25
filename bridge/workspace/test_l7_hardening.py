import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bridge
import saboteur

lv = bridge.load_level("final")
convoy_sc = bridge.load_json("levels/final/sample1.json")


def make_enemy_truss_valid():
    # Valid 28m bridge (~12k) using our Level 3/2 style wood+steel+cable arch
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
        nodes.append([round(i * dx, 4), -1.9])
    def bot(i): return "A1" if i == 0 else ("A4" if i == n_seg else bot_s + i - 1)
    for i in range(n_seg):
        members.append([bot(i), bot(i + 1), "steel" if i in (0, 1, 12, 13) else "cable"])
    for i in range(1, n_seg):
        members.append([top(i), bot(i), "wood"])
    for i in range(n_seg):
        if i < n_seg // 2:
            members.append([top(i), bot(i + 1), "wood"])
        else:
            members.append([bot(i), top(i + 1), "wood"])
    d = {"nodes": nodes, "members": members}
    # Upgrade any wood member that breaks under convoy
    for _ in range(15):
        P = bridge.parse_design(lv, d)
        res, _ = bridge.simulate(lv, P, convoy_sc)
        if res["ok"]:
            return d, P["cost"]
        for ev in res["events"]:
            parts = ev.split()
            if parts[1] == "BREAK":
                idx = int(parts[2])
                if d["members"][idx][2] == "wood":
                    d["members"][idx][2] = "cable" if float(parts[3]) > 0 else "steel"
                    break
        else:
            break
    return d, bridge.parse_design(lv, d)["cost"]


enemy_d, enemy_cost = make_enemy_truss_valid()
P_en = bridge.parse_design(lv, enemy_d)
print("Valid enemy bridge cost:", enemy_cost, "convoy ok:", bridge.simulate(lv, P_en, convoy_sc)[0]["ok"])

# Test current saboteur against enemy bridge AND final_bridge
S = saboteur.parse_sab(lv, bridge.load_json("submission/saboteur.json"))
out_en, _ = saboteur.duel(lv, P_en, S)
print("Current saboteur vs enemy:", out_en["verdict"], "| sab:", out_en["res"]["sab"], "| broken:", out_en["broken"])

fb = bridge.load_json("submission/final_bridge.json")
P_fb = bridge.parse_design(lv, fb)
out_fb, _ = saboteur.duel(lv, P_fb, S)
print("Current saboteur vs final_bridge:", out_fb["verdict"], "| sab:", out_fb["res"]["sab"], "| broken:", out_fb["broken"])
