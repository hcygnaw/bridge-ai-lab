#!/usr/bin/env python3
"""Level 5 ('钱不够') Statically Determinate 2-Group (A & B) 500kN Catapult (Zero Overconstraint, Independent Pitch Control!)."""
import json
import math
import os
import opt_utils as U
import bridge as B


def make_l5_det(bh=0.32, dip=-0.28, fh=0.06,
                gxc=-0.45, spA_c=14.0, rtA_c=1.52, rtB_c=1.50, ac_c=85.0,
                gxv=-0.45, spA_v=15.0, rtA_v=1.64, rtB_v=1.62, ac_v=95.0,
                with_catch=False):
    nodes = []
    m = []
    # 1. 100% Rigid Steel Pit Bridge (-11 to -2.68)
    pit_pts = ['A2']
    for i in range(1, 4):
        x = -11.0 + 8.32 * i / 4.0
        y = -0.55 * math.sin(math.pi * i / 4.0) + bh * (i / 4.0) ** 2
        idx = len(nodes); nodes.append([round(x, 4), round(y, 4)]); pit_pts.append(idx)
    p_end = len(nodes); nodes.append([-2.68, bh])
    pit_pts.append(p_end)
    for a, b in zip(pit_pts, pit_pts[1:]):
        m.append([a, b, 'road'])
    m += [
        ['A6', pit_pts[1], 'steel'],
        ['A5', pit_pts[2], 'steel'],
        ['A4', pit_pts[3], 'steel'],
        ['A3', p_end, 'steel'],
        ['A0', p_end, 'cable'],
    ]

    # 2. Statically Determinate Rigid Cradle (3 DOFs constrained by EXACTLY 3 links: A1->d0 steel + A4->d0 hyd A + A3->d1_top hyd B!)
    # Check L(A1->d0): Move d0 to -2.25 (`p_end = -2.38`) so L(A1->d0) = hypot(2.25, 2.32) = 3.23m -> buckle = 86.2 kN (unbucklable!!)!
    nodes[p_end] = [-2.38, bh]
    for i in range(1, 4):
        nodes[pit_pts[i]][0] = round(-11.0 + 8.62 * i / 4.0, 4)

    d0 = len(nodes); nodes.append([-2.25, bh])
    d1_top = len(nodes); nodes.append([-0.25, bh])
    dm = len(nodes); nodes.append([-1.30, dip])
    d1_rd = len(nodes); nodes.append([0.12, fh])

    m += [
        [d0, dm, 'road'], [dm, d1_rd, 'road'],
        [d0, d1_top, 'steel'], [dm, d1_top, 'steel'], [d1_rd, d1_top, 'steel'],
        ['A1', d0, 'steel'],              # Link 1: guides d0 on circle around A1(0,-2) (86 kN buckle!)
        ['A4', d0, 'hydraulic', 'A'],     # Link 2: drives position along circle (250 kN!)
        ['A3', d1_top, 'hydraulic', 'B'], # Link 3: independently controls pitch angle + adds 250 kN thrust = 500 kN total!!
    ]

    if with_catch:
        c1 = len(nodes); nodes.append([21.56, 0.28])
        m += [[c1, 'A7', 'road'], ['A8', c1, 'spring']]

    spB_c = round(spA_c * max(0.2, (rtB_c - 1.0) / max(0.05, rtA_c - 1.0)), 3)
    spB_v = round(spA_v * max(0.2, (rtB_v - 1.0) / max(0.05, rtA_v - 1.0)), 3)
    spB_c = min(15.0, max(0.1, spB_c))
    spB_v = min(15.0, max(0.1, spB_v))

    sensors = [
        {'id': 'gc', 'type': 'gate', 'x': -0.80, 'dir': 'right'},
        {'id': 'gv', 'type': 'gate', 'x': -0.80, 'dir': 'right', 'min_mass': 1500},
    ]
    dc_del = round(max(0.0, (gxc + 0.80) / 7.8), 4)
    dv_del = round(max(dc_del + 0.002, (gxv + 0.80) / 6.8), 4)

    rules = [
        {'on': 'gc', 'delay': dc_del, 'do': 'hyd', 'group': 'A', 'ratio': rtA_c, 'speed': spA_c, 'accel': ac_c},
        {'on': 'gc', 'delay': dc_del, 'do': 'hyd', 'group': 'B', 'ratio': rtB_c, 'speed': spB_c, 'accel': ac_c},
        {'on': 'gc', 'delay': 1.20,   'do': 'hyd', 'group': 'A', 'ratio': 1.0,   'speed': 4.5,   'accel': 16.0},
        {'on': 'gc', 'delay': 1.20,   'do': 'hyd', 'group': 'B', 'ratio': 1.0,   'speed': 4.5,   'accel': 16.0},

        {'on': 'gv', 'delay': dv_del, 'do': 'hyd', 'group': 'A', 'ratio': rtA_v, 'speed': spA_v, 'accel': ac_v},
        {'on': 'gv', 'delay': dv_del, 'do': 'hyd', 'group': 'B', 'ratio': rtB_v, 'speed': spB_v, 'accel': ac_v},
        {'on': 'gv', 'delay': 1.25,   'do': 'hyd', 'group': 'A', 'ratio': 1.0,   'speed': 4.5,   'accel': 16.0},
        {'on': 'gv', 'delay': 1.25,   'do': 'hyd', 'group': 'B', 'ratio': 1.0,   'speed': 4.5,   'accel': 16.0},
    ]
    return {'nodes': nodes, 'members': m, 'sensors': sensors, 'rules': rules}


if __name__ == '__main__':
    lv5 = B.load_level(5)
    print('Cost without catch:', B.parse_design(lv5, make_l5_det(with_catch=False))['cost'])
    print('Cost WITH catch:', B.parse_design(lv5, make_l5_det(with_catch=True))['cost'])

    sc_van = {'name': 'van_only', 'vehicles': [{'type': 'van', 'from': 'left', 't': 1.0}]}
    sc_car = {'name': 'car_only', 'vehicles': [{'type': 'car', 'from': 'left', 't': 1.0}]}

    # Step 1: Find 0-break VAN wins using independent pitch control (rtB_v - rtA_v)!
    for wc in [True, False]:
        van_wins = []
        for gx in [-0.35, -0.18, -0.05]:
            for spA in [13.8, 14.5, 15.0]:
                for rtA in [1.52, 1.58, 1.64]:
                    for d_rtB in [-0.12, -0.06, -0.02, 0.02, 0.06, 0.12]:
                        rtB = round(rtA + d_rtB, 3)
                        for ac in [65.0, 85.0, 105.0]:
                            d = make_l5_det(0.32, -0.28, 0.06, gx, spA, rtA, rtB, ac, gx, spA, rtA, rtB, ac, wc)
                            # For pure van test, fire at delay=0 directly at gx!
                            d['sensors'] = [{'id': 'gv', 'type': 'gate', 'x': gx, 'dir': 'right'}]
                            spB = min(15.0, max(0.1, round(spA * max(0.2, (rtB - 1.0) / max(0.05, rtA - 1.0)), 3)))
                            d['rules'] = [
                                {'on': 'gv', 'delay': 0.0,  'do': 'hyd', 'group': 'A', 'ratio': rtA, 'speed': spA, 'accel': ac},
                                {'on': 'gv', 'delay': 0.0,  'do': 'hyd', 'group': 'B', 'ratio': rtB, 'speed': spB, 'accel': ac},
                                {'on': 'gv', 'delay': 1.25, 'do': 'hyd', 'group': 'A', 'ratio': 1.0, 'speed': 4.5, 'accel': 16.0},
                                {'on': 'gv', 'delay': 1.25, 'do': 'hyd', 'group': 'B', 'ratio': 1.0, 'speed': 4.5, 'accel': 16.0},
                            ]
                            P = B.parse_design(lv5, d)
                            rv, _ = B.simulate(lv5, P, sc_van)
                            if rv['ok'] and rv['broken'] == 0:
                                van_wins.append((gx, spA, rtA, rtB, ac))
                                if len(van_wins) <= 5:
                                    print(f'  [wc={wc}] 0-BREAK VAN WIN:', (gx, spA, rtA, rtB, ac), 'cost=', P['cost'])
        print(f'[wc={wc}] Total 0-break van wins: {len(van_wins)}')

        if van_wins:
            # Find matching 0-break CAR wins on same wc!
            car_wins = []
            for gx in [-0.40, -0.22, -0.08]:
                for spA in [12.5, 13.5, 14.3, 15.0]:
                    for rtA in [1.44, 1.50, 1.56]:
                        for d_rtB in [-0.08, -0.03, 0.0, 0.04, 0.08]:
                            rtB = round(rtA + d_rtB, 3)
                            for ac in [65.0, 85.0]:
                                d = make_l5_det(0.32, -0.28, 0.06, gx, spA, rtA, rtB, ac, gx, spA, rtA, rtB, ac, wc)
                                d['sensors'] = [{'id': 'gc', 'type': 'gate', 'x': gx, 'dir': 'right'}]
                                spB = min(15.0, max(0.1, round(spA * max(0.2, (rtB - 1.0) / max(0.05, rtA - 1.0)), 3)))
                                d['rules'] = [
                                    {'on': 'gc', 'delay': 0.0,  'do': 'hyd', 'group': 'A', 'ratio': rtA, 'speed': spA, 'accel': ac},
                                    {'on': 'gc', 'delay': 0.0,  'do': 'hyd', 'group': 'B', 'ratio': rtB, 'speed': spB, 'accel': ac},
                                    {'on': 'gc', 'delay': 1.20, 'do': 'hyd', 'group': 'A', 'ratio': 1.0, 'speed': 4.5, 'accel': 16.0},
                                    {'on': 'gc', 'delay': 1.20, 'do': 'hyd', 'group': 'B', 'ratio': 1.0, 'speed': 4.5, 'accel': 16.0},
                                ]
                                P = B.parse_design(lv5, d)
                                rc, _ = B.simulate(lv5, P, sc_car)
                                if rc['ok'] and rc['broken'] == 0:
                                    car_wins.append((gx, spA, rtA, rtB, ac))
            print(f'[wc={wc}] Total 0-break car wins: {len(car_wins)}')
            for gxv, spAv, rtAv, rtBv, acv in van_wins[:12]:
                for gxc, spAc, rtAc, rtBc, acc in car_wins[:12]:
                    d_comb = make_l5_det(0.32, -0.28, 0.06, gxc, spAc, rtAc, rtBc, acc, gxv, spAv, rtAv, rtBv, acv, wc)
                    ok, c = U.save_if_best(5, d_comb, verbose=True)
                    if ok:
                        print(f'*** SOLVED LEVEL 5 (wc={wc}) AT COST {c} ***')
                        break
                else:
                    continue
                break
