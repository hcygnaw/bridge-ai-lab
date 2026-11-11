#!/usr/bin/env python3
"""Level 7 ('决赛·攻防') solver v2: Proven Underslung Cable-Truss Fortress + Internal-Anvil Saboteur."""
import copy
import json
import math
import os
import bridge as B
import saboteur as S
import opt_utils as U


def make_fortress_v2():
    # Proven architecture from our passing Level 2 design, scaled to 28m and reinforced up to ~25,600 budget!
    n_seg = 14  # dx = 2.0m exact! road buckling = min(90, 300/4.0) = 75 kN!
    uw_depth = 1.75
    cab_sag = 4.9
    nodes = []
    m = []

    d_pts = ['A0']
    for i in range(1, n_seg):
        idx = len(nodes); nodes.append([round(28.0 * i / n_seg, 5), 0.0]); d_pts.append(idx)
    d_pts.append('A3')
    for a, b in zip(d_pts, d_pts[1:]):
        m.append([a, b, 'road'])

    # Stiffening Warren lower chord at y = -1.75 (all diagonals L = hypot(1.0, 1.75) = 2.015m! Wood buckle = 29.5kN, Steel = 140kN!)
    b_pts = []
    for i in range(n_seg):
        b_pts.append(len(nodes))
        nodes.append([round(28.0 * (i + 0.5) / n_seg, 4), -uw_depth])

    m += [
        ['A1', d_pts[1], 'steel'], ['A4', d_pts[-2], 'steel'],
        ['A1', b_pts[0], 'steel'], ['A4', b_pts[-1], 'steel'],
    ]
    for i in range(n_seg):
        # Reinforce ALL web diagonals and chords up to ~25,500 fortress budget!
        wmat = 'steel' if i in (0, 1, 2, 5, 6, 7, 8, 11, 12, 13) else 'wood'
        m.append([b_pts[i], d_pts[i], wmat])
        m.append([b_pts[i], d_pts[i + 1], wmat])
    for i in range(n_seg - 1):
        m.append([b_pts[i], b_pts[i + 1], 'steel'])

    # Parabolic primary 90kN suspension cable system underneath + secondary stay cables from A0/A3!
    c_indices = [1, 3, 5, 8, 10, 12]
    c_pts = []
    for idx in c_indices:
        x = nodes[b_pts[idx]][0]
        t = x / 28.0
        yc = min(-cab_sag * 4.0 * t * (1.0 - t), -uw_depth - 0.45)
        cn = len(nodes); nodes.append([round(x, 4), round(yc, 4)])
        c_pts.append((idx, cn))

    c_chain = ['A0'] + [cn for _, cn in c_pts] + ['A3']
    for a, b in zip(c_chain, c_chain[1:]):
        m.append([a, b, 'cable'])
    # Secondary stay cables anchored at A1=(0,-2) and A4=(28,-2) for redundancy (distinct node pairs!)
    m += [
        ['A1', c_pts[1][1], 'cable'], ['A1', c_pts[2][1], 'cable'],
        [c_pts[3][1], 'A4', 'cable'], [c_pts[4][1], 'A4', 'cable'],
    ]

    for idx, cn in c_pts:
        L = abs(nodes[b_pts[idx]][1] - nodes[cn][1])
        m.append([cn, b_pts[idx], 'steel' if L > 2.95 else 'wood'])
        if idx - 1 >= 0:
            L1 = math.hypot(nodes[b_pts[idx - 1]][0] - nodes[cn][0], nodes[b_pts[idx - 1]][1] - nodes[cn][1])
            if L1 <= 2.99:
                m.append([cn, b_pts[idx - 1], 'wood'])
        if idx + 1 < n_seg:
            L2 = math.hypot(nodes[b_pts[idx + 1]][0] - nodes[cn][0], nodes[b_pts[idx + 1]][1] - nodes[cn][1])
            if L2 <= 2.99:
                m.append([cn, b_pts[idx + 1], 'wood'])

    return {'nodes': nodes, 'members': m}


def make_anvil_saboteur(ballast_kg=1900):
    # 4-wheel indestructible steel tank + 1,900kg hinged steel hammer arm driven by hydraulic (NO springs to break!)
    nodes = [
        [0.0, 0.22],     # 0: front wheel
        [-1.0, 0.22],    # 1: mid-front wheel
        [-2.0, 0.22],    # 2: mid-rear wheel
        [-3.0, 0.22],    # 3: rear wheel
        [-0.5, 0.78],    # 4: chassis upper front
        [-1.5, 0.78],    # 5: chassis upper mid
        [-2.5, 0.78],    # 6: chassis upper rear
        [-1.85, 1.38],   # 7: 1900kg hinged steel hammer anvil (hinged to node 4 by 140kN steel, driven from node 2 by hydraulic!)
    ]
    wheels = [0, 1, 2, 3]
    members = [
        [0, 1, 'steel'], [1, 2, 'steel'], [2, 3, 'steel'],
        [4, 5, 'steel'], [5, 6, 'steel'],
        [0, 4, 'steel'], [1, 4, 'steel'], [1, 5, 'steel'],
        [2, 5, 'steel'], [2, 6, 'steel'], [3, 6, 'steel'],
        [0, 5, 'steel'], [3, 5, 'steel'],
        # Hinged hammer arm (140 kN steel!) + indestructible 250 kN hydraulic!
        [4, 7, 'steel'],
        [2, 7, 'hydraulic', 'A'],
    ]
    sensors = [
        {'id': 'g1', 'type': 'mygate', 'x': 3.5},
        {'id': 'g2', 'type': 'mygate', 'x': 9.5},
        {'id': 'g3', 'type': 'mygate', 'x': 15.0},
        {'id': 'g4', 'type': 'mygate', 'x': 20.5},
        {'id': 'g5', 'type': 'mygate', 'x': 25.5},
    ]
    rules = []
    for gid in ('g1', 'g2', 'g3', 'g4'):
        rules.append({'on': gid, 'delay': 0.0,  'do': 'hyd', 'group': 'A', 'ratio': 0.68, 'speed': 3.0, 'accel': 5.0})
        rules.append({'on': gid, 'delay': 0.18, 'do': 'hyd', 'group': 'A', 'ratio': 1.25, 'speed': 3.0, 'accel': 5.0})
        rules.append({'on': gid, 'delay': 0.36, 'do': 'hyd', 'group': 'A', 'ratio': 0.68, 'speed': 3.0, 'accel': 5.0})
    rules.append({'on': 'g5', 'delay': 0.0, 'do': 'hyd', 'group': 'A', 'ratio': 1.0, 'speed': 2.5, 'accel': 4.0})

    return {
        'nodes': nodes,
        'members': members,
        'wheels': wheels,
        'ballast': [[7, ballast_kg]],
        'motor': {'speed': 10.0, 'accel': 4.0},
        'sensors': sensors,
        'rules': rules,
    }


if __name__ == '__main__':
    lv = B.load_level('final')
    fb = make_fortress_v2()
    P_fb = B.parse_design(lv, fb)
    print(f"Fortress v2 Cost = {P_fb['cost']:.2f} / {lv['budget']}")
    ok_fb, _, pk_fb, _ = U.eval_bridge('final', fb, verbose=True)

    sab = make_anvil_saboteur(100)
    S0 = S.parse_sab(lv, sab)
    max_extra = int(min(2498 - (S0['mass'] - 100), 5990 - (S0['cost'] - 100)))
    sab = make_anvil_saboteur(max_extra)
    S_parsed = S.parse_sab(lv, sab)
    print(f"Anvil Saboteur valid! Mass = {S_parsed['mass']:.1f}/2500 kg, Cost = {S_parsed['cost']:.1f}/6000")

    r_self, _ = S.duel(lv, P_fb, S_parsed)
    print("=== Self-Duel (Fortress v2 vs Anvil Saboteur) ===")
    print(r_self['text'])

    if ok_fb and r_self['bridge_win']:
        U.save_if_best('final', fb, verbose=False)
        print("*** SAVED submission/final_bridge.json ***")
    if r_self['sab_arrived']:
        with open('submission/saboteur.json', 'w', encoding='utf-8') as f:
            json.dump(sab, f, ensure_ascii=False, indent=1)
        print("*** SAVED submission/saboteur.json ***")
