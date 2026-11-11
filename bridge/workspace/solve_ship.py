#!/usr/bin/env python3
"""Submersible Elevator Bridge solver for Level 4 ('过船') and Level 6 ('地狱关')."""
import copy
import math
import os
import opt_utils as U
import bridge as B


def make_l4_submersible(open_ratio=0.50):
    # River 0..24, channel x in [9, 15], y in [-2, 6], build_area y in [-6, 14].
    # Permanent continuous truss across 0..24:
    #   Left deck: A0(0,0) -> (2.23,0) -> (4.46,0) -> (6.69,0) -> (8.92,0)  (all x < 9.0!)
    #   Right deck: (15.08,0) -> (17.31,0) -> (19.54,0) -> (21.77,0) -> A3(24,0)  (all x > 15.0!)
    #   Submerged continuous truss below y = -2.2 across the ENTIRE 24m span!
    nodes = []
    m = []

    l_deck = ['A0']
    for i in range(1, 6):
        idx = len(nodes); nodes.append([round(8.92 * i / 5.0, 4), 0.0]); l_deck.append(idx)
    for a, b in zip(l_deck, l_deck[1:]):
        m.append([a, b, 'road'])

    r_deck = []
    for i in range(5):
        idx = len(nodes); nodes.append([round(15.08 + 8.92 * i / 5.0, 4), 0.0]); r_deck.append(idx)
    r_deck.append('A3')
    for a, b in zip(r_deck, r_deck[1:]):
        m.append([a, b, 'road'])

    # Submerged main truss: keep panel dx <= 1.98m so ALL diagonals are <= 2.95m WOOD (40/m)!!
    sub_top_xs = [round(8.92 * i / 5.0, 4) for i in range(1, 6)] + [11.02, 12.98] + [round(15.08 + 8.92 * i / 5.0, 4) for i in range(5)]
    sub_top = ['A1']
    for x in sub_top_xs:
        y = -2.25 if 8.5 <= x <= 15.5 else -2.05
        idx = len(nodes); nodes.append([x, y]); sub_top.append(idx)
    sub_top.append('A4')

    # Lower submerged chord at midpoints, y in [-3.6, -4.35] so diagonals <= 2.85m WOOD!
    all_st_x = [0.0] + sub_top_xs + [24.0]
    sub_bot = []
    for i in range(len(all_st_x) - 1):
        x = 0.5 * (all_st_x[i] + all_st_x[i + 1])
        t = x / 24.0
        y = -3.55 - 0.85 * 4.0 * t * (1.0 - t)
        idx = len(nodes); nodes.append([round(x, 4), round(y, 4)]); sub_bot.append(idx)

    # Connect left & right fixed decks down to sub_top (all outside x in [9, 15], all L <= 2.90m WOOD!)
    for i in range(1, 6):
        m.append([l_deck[i], sub_top[i], 'wood'])
        m.append([l_deck[i - 1], sub_top[i], 'wood'])
    m.append([l_deck[5], sub_top[4], 'wood'])

    for i in range(5):
        st_i = 8 + i
        m.append([r_deck[i], sub_top[st_i], 'wood'])
        m.append([r_deck[i + 1], sub_top[st_i], 'wood'])
    m.append([r_deck[0], sub_top[9], 'wood'])

    # Start ALL submerged truss bars as cheap WOOD (auto_upgrade_ship upgrades ONLY the exact bars that need steel!)
    for a, b in zip(sub_top, sub_top[1:]):
        m.append([a, b, 'wood'])
    for a, b in zip(sub_bot, sub_bot[1:]):
        m.append([a, b, 'wood'])
    m.append(['A1', sub_bot[0], 'wood'])
    m.append([sub_bot[-1], 'A4', 'wood'])
    for i in range(len(sub_bot)):
        m.append([sub_bot[i], sub_top[i], 'wood'])
        m.append([sub_bot[i], sub_top[i + 1], 'wood'])

    # --- Elevator Deck (9.06 -> 11.02 -> 12.98 -> 14.94, y = 0.0) ---
    # When lowered by 2.35m, road is at y = -2.35m < -2.0m!
    e_xs = [9.06, 11.02, 12.98, 14.94]
    e_deck = []
    for x in e_xs:
        idx = len(nodes); nodes.append([x, 0.0]); e_deck.append(idx)
    for a, b in zip(e_deck, e_deck[1:]):
        m.append([a, b, 'road'])

    # Stiffen elevator deck with an under-chord at y = -1.15 (drops to -3.50 >= -6.0 when lowered!)
    eb0 = len(nodes); nodes.append([10.04, -1.15])
    eb1 = len(nodes); nodes.append([12.00, -1.15])
    eb2 = len(nodes); nodes.append([13.96, -1.15])
    m += [
        [eb0, e_deck[0], 'wood'], [eb0, e_deck[1], 'wood'],
        [eb1, e_deck[1], 'wood'], [eb1, e_deck[2], 'wood'],
        [eb2, e_deck[2], 'wood'], [eb2, e_deck[3], 'wood'],
        [eb0, eb1, 'wood'], [eb1, eb2, 'wood'],
    ]

    # Two vertical hydraulics of length 4.80m from submerged base nodes at y = -4.80 up to e_deck[1] and e_deck[2]!
    # At ratio = 0.50 -> length = 2.40m -> e_deck drops from 0.0 to -4.80 + 2.40 = -2.40m < -2.0m!!
    nodes[sub_bot[5]] = [11.02, -4.40]
    nodes[sub_bot[7]] = [12.98, -4.40]
    m += [
        [sub_bot[5], e_deck[1], 'hydraulic', 'A'],
        [sub_bot[7], e_deck[2], 'hydraulic', 'A'],
    ]
    nodes[sub_top[4]] = [7.136, -2.25]
    m.append([sub_top[4], eb0, 'steel'])

    lights = [
        {'id': 'LL', 'x': -1.0, 'dir': 'right', 'init': 'green'},
        {'id': 'LR', 'x': 25.0, 'dir': 'left', 'init': 'green'},
    ]
    sensors = [{'id': 'h', 'type': 'horn'}]
    rules = [
        {'on': 'h', 'delay': 6.4, 'do': 'light', 'light': 'LL', 'state': 'red'},
        {'on': 'h', 'delay': 6.4, 'do': 'light', 'light': 'LR', 'state': 'red'},
        {'on': 'h', 'delay': 7.2, 'do': 'hyd', 'group': 'A', 'ratio': open_ratio, 'speed': 1.8, 'accel': 3.5},
        {'on': 'h', 'delay': 16.1, 'do': 'hyd', 'group': 'A', 'ratio': 1.0, 'speed': 1.8, 'accel': 3.5},
        {'on': 'h', 'delay': 18.8, 'do': 'light', 'light': 'LL', 'state': 'green'},
        {'on': 'h', 'delay': 18.8, 'do': 'light', 'light': 'LR', 'state': 'green'},
    ]
    return {'nodes': nodes, 'members': m, 'lights': lights, 'sensors': sensors, 'rules': rules}


def make_l6_submersible(open_ratio=0.50):
    # River 0..36, reefs at A4=(12,-2) and A5=(24,-2), channel x in [15, 21], y in [-2, 6]!
    # Note solid reefs: [11,-8]->[11.6,-2]->[12.4,-2]->[13,-8] and [23,-8]->[23.6,-2]->[24.4,-2]->[25,-8]!
    # So near x=12 and x=24, nodes must NOT be inside those trapezoids!
    # Look how clean Level 6 is with reefs at A4=(12,-2) and A5=(24,-2):
    #   Span 1 (0..12): 12m static span from A0/A1 to A4=(12,-2)!
    #   Span 3 (24..36): 12m static span from A5=(24,-2) to A6/A7!
    #   Span 2 (12..24):
    #     Fixed stubs: 12..14.92 (all x < 15.0!) and 21.08..24.0 (all x > 21.0!)
    #     Submerged truss between A4=(12,-2) -> (14.92,-2.25) -> (17.02,-2.25) -> (18.98,-2.25) -> (21.08,-2.25) -> A5=(24,-2)
    #     and lower chord at y = -4.80 across 14..22 (completely between x=13 and x=23, OUTSIDE both reef polygons!!)!
    # Deep 2-tier / short-panel wood truss on Span 1 (0..12) using FREE DEEP ANCHOR A2=(0,-4) and A4=(12,-2)!
    #Wait: keep panel dx = 2.0m (6 road segs of 2.0m on 0..12 instead of 5 of 2.4m!) so wood buckling jumps by +44%!!
    nodes = []
    m = []

    l_xs = [2.4, 4.8, 7.2, 9.6, 12.0, 13.46, 14.92]
    l_deck = ['A0']
    for x in l_xs:
        idx = len(nodes); nodes.append([x, 0.0]); l_deck.append(idx)
    for a, b in zip(l_deck, l_deck[1:]):
        m.append([a, b, 'road'])

    r_xs = [21.08, 22.54, 24.0, 26.4, 28.8, 31.2, 33.6]
    r_deck = []
    for x in r_xs:
        idx = len(nodes); nodes.append([x, 0.0]); r_deck.append(idx)
    r_deck.append('A6')
    for a, b in zip(r_deck, r_deck[1:]):
        m.append([a, b, 'road'])

    # Span 1 & Span 3: shallow Warren stiffening (y=-1.75 so L=2.12m -> wood buckle = 26.7 kN, NO steel web needed!!)
    # PLUS ONE parabolic under-cable A2(0,-4)->c1(6.0,-3.5)->A4(12,-2) carrying truck moment at 70/m!!
    b1_xs = [1.2, 3.6, 6.0, 8.4, 10.6]
    b1 = []
    for x in b1_xs:
        idx = len(nodes); nodes.append([x, -1.75]); b1.append(idx)
    c1 = len(nodes); nodes.append([6.0, -3.55])
    m += [
        ['A1', b1[0], 'wood'], [b1[-1], 'A4', 'wood'],
        ['A2', c1, 'cable'], [c1, 'A4', 'cable'],
        [c1, b1[1], 'wood'], [c1, b1[2], 'wood'], [c1, b1[3], 'wood'],
    ]
    for a, b in zip(b1, b1[1:]):
        m.append([a, b, 'wood'])
    for i in range(5):
        m.append([b1[i], l_deck[i], 'wood'])
        m.append([b1[i], l_deck[i + 1], 'wood'])
    m.append(['A4', l_deck[5], 'wood'])

    b3_xs = [25.4, 27.6, 30.0, 32.4, 34.8]
    b3 = []
    for x in b3_xs:
        idx = len(nodes); nodes.append([x, -1.75]); b3.append(idx)
    c3 = len(nodes); nodes.append([30.0, -3.55])
    m += [
        ['A5', b3[0], 'wood'], [b3[-1], 'A7', 'wood'],
        ['A5', c3, 'cable'], [c3, 'A8', 'cable'],
        [c3, b3[1], 'wood'], [c3, b3[2], 'wood'], [c3, b3[3], 'wood'],
    ]
    for a, b in zip(b3, b3[1:]):
        m.append([a, b, 'wood'])
    for i in range(5):
        m.append([b3[i], r_deck[2 + i], 'wood'])
        m.append([b3[i], r_deck[3 + i], 'wood'])
    m.append(['A5', r_deck[2], 'wood'])

    # Center Span 2 (12..24) submerged truss + Single-Hydraulic Submerged Parallelogram Elevator!
    st_xs = [13.35, 14.92, 16.53, 18.00, 19.47, 21.08]
    st = ['A4']
    for x in st_xs:
        idx = len(nodes); nodes.append([x, -2.28]); st.append(idx)
    st.append('A5')
    for a, b in zip(st, st[1:]):
        m.append([a, b, 'wood'])

    # Connect fixed deck stubs (12..14.92 and 21.08..24) down to st!
    m += [
        [l_deck[6], st[1], 'wood'], [l_deck[5], st[1], 'wood'],
        [l_deck[6], st[2], 'wood'], [l_deck[7], st[2], 'wood'],
        [r_deck[1], 'A5', 'wood'], [r_deck[1], st[6], 'wood'], [r_deck[0], st[6], 'wood'],
    ]

    # G_bot at (13.35, -3.48) directly below G_top = st[1] = (13.35, -2.28) (dy = 1.20m)
    G_top = st[1]
    G_bot = len(nodes); nodes.append([13.35, -3.48])
    m += [['A4', G_bot, 'wood'], [G_top, G_bot, 'wood'], [G_bot, st[2], 'wood']]

    # Lower submerged chord in 15.2..20.8, with sb_mid = (18.00, -4.55) for ONE vertical 4.55m hydraulic!
    sb0 = len(nodes); nodes.append([15.6, -4.35])
    sb_mid = len(nodes); nodes.append([18.00, -4.55])
    sb1 = len(nodes); nodes.append([20.4, -4.35])
    m += [
        [G_bot, sb0, 'cable'], [sb0, sb_mid, 'wood'], [sb_mid, sb1, 'wood'], [sb1, 'A5', 'cable'],
        [sb0, st[2], 'wood'], [sb0, st[3], 'wood'],
        [sb_mid, st[3], 'wood'], [sb_mid, st[4], 'wood'], [sb_mid, st[5], 'wood'],
        [sb1, st[5], 'wood'], [sb1, st[6], 'wood'],
    ]

    # Elevator Deck: 4 road segments (15.06 -> 16.53 -> 18.00 -> 19.47 -> 20.94, y = 0.0)
    e_xs = [15.06, 16.53, 18.00, 19.47, 20.94]
    e_deck = []
    for x in e_xs:
        idx = len(nodes); nodes.append([x, 0.0]); e_deck.append(idx)
    for a, b in zip(e_deck, e_deck[1:]):
        m.append([a, b, 'road'])

    # Elevator rigid under-truss + parallelogram post (E_top=(16.05,-1.10), E_bot=(16.05,-2.30), dy=1.20m!)
    E_top = len(nodes); nodes.append([16.05, -1.10])
    E_bot = len(nodes); nodes.append([16.05, -2.30])
    eb_mid = len(nodes); nodes.append([18.00, -1.15])
    eb_r = len(nodes); nodes.append([19.95, -1.10])
    m += [
        [E_top, e_deck[0], 'wood'], [E_top, e_deck[1], 'wood'], [E_top, e_deck[2], 'wood'],
        [E_top, E_bot, 'wood'], [E_bot, e_deck[1], 'wood'], [E_bot, eb_mid, 'wood'],
        [eb_mid, e_deck[1], 'wood'], [eb_mid, e_deck[2], 'wood'], [eb_mid, e_deck[3], 'wood'],
        [eb_r, e_deck[2], 'wood'], [eb_r, e_deck[3], 'wood'], [eb_r, e_deck[4], 'wood'],
        [E_top, eb_mid, 'wood'], [eb_mid, eb_r, 'wood'],
        # Exact Parallelogram Guide Links (both L = hypot(2.70, 1.18) = 2.947m <= 3.0m!)
        [G_top, E_top, 'wood'],
        [G_bot, E_bot, 'wood'],
        # ONE SINGLE VERTICAL 4.55m HYDRAULIC! (at ratio=0.50 -> L=2.275m -> drops e_deck to -2.275m < -2.0m!)
        [sb_mid, e_deck[2], 'hydraulic', 'A'],
    ]

    lights = [
        {'id': 'LL', 'x': -1.0, 'dir': 'right', 'init': 'green'},
        {'id': 'LR', 'x': 37.0, 'dir': 'left', 'init': 'green'},
    ]
    sensors = [{'id': 'h', 'type': 'horn'}]
    rules = [
        {'on': 'h', 'delay': 2.5, 'do': 'light', 'light': 'LL', 'state': 'red'},
        {'on': 'h', 'delay': 2.5, 'do': 'light', 'light': 'LR', 'state': 'red'},
        {'on': 'h', 'delay': 6.8, 'do': 'hyd', 'group': 'A', 'ratio': open_ratio, 'speed': 1.8, 'accel': 3.5},
        {'on': 'h', 'delay': 16.1, 'do': 'hyd', 'group': 'A', 'ratio': 1.0, 'speed': 1.8, 'accel': 3.5},
        {'on': 'h', 'delay': 19.0, 'do': 'light', 'light': 'LL', 'state': 'green'},
        {'on': 'h', 'delay': 19.0, 'do': 'light', 'light': 'LR', 'state': 'green'},
    ]
    return {'nodes': nodes, 'members': m, 'lights': lights, 'sensors': sensors, 'rules': rules}


def sanitize_design(lv_id, d):
    lv = B.load_level(lv_id)
    anc = lv['anchors']
    nodes = d['nodes']
    seen = set()
    clean_m = []
    for entry in d['members']:
        u, v, mat = entry[0], entry[1], entry[2]
        pu = anc[int(u[1:])] if isinstance(u, str) else nodes[u]
        pv = anc[int(v[1:])] if isinstance(v, str) else nodes[v]
        iu = ('A', int(u[1:])) if isinstance(u, str) else ('N', u)
        iv = ('A', int(v[1:])) if isinstance(v, str) else ('N', v)
        if iu == iv:
            continue
        key = tuple(sorted([iu, iv]))
        if key in seen:
            continue
        seen.add(key)
        L = math.hypot(pu[0] - pv[0], pu[1] - pv[1])
        if mat == 'wood' and L > 2.999:
            mat = 'cable'  # try cable (70/m) before steel (160/m)!
        if mat == 'hydraulic':
            clean_m.append([u, v, 'hydraulic', entry[3]])
        else:
            clean_m.append([u, v, mat])
    out = dict(d)
    out['members'] = clean_m
    return out


def auto_upgrade_ship(lv_id, design, max_iter=60):
    lv = B.load_level(lv_id)
    lv_wide = dict(lv, budget=100000)
    d = sanitize_design(lv_id, copy.deepcopy(design))
    for _ in range(max_iter):
        P = B.parse_design(lv_wide, d)
        earliest = None  # (time, bi, force)
        all_ok = True
        for sp in B.sample_paths(lv):
            sc = B.load_json(sp)
            res, _ = B.simulate(lv_wide, P, sc)
            if not res['ok']:
                all_ok = False
                for e in res['events']:
                    f = e.split()
                    if f[1] == 'BREAK' and int(f[2]) < len(d['members']):
                        bi = int(f[2])
                        if d['members'][bi][2] in ('wood', 'cable'):
                            cand_t = float(f[0])
                            if earliest is None or cand_t < earliest[0]:
                                earliest = (cand_t, bi, float(f[3]))
                            break
        if all_ok:
            print(f'  [L{lv_id}] Passed before downgrade at cost={P["cost"]:.1f}, running greedy downgrade...')
            improved = True
            while improved:
                improved = False
                # Sort expensive steel bars first!
                P_cur = B.parse_design(lv_wide, d)
                order = sorted(range(len(d['members'])), key=lambda i: -P_cur['members'][i][4])
                for idx in order:
                    cur_mat = d['members'][idx][2]
                    L = P_cur['members'][idx][4]
                    for try_mat in (['wood', 'cable'] if cur_mat == 'steel' else (['wood'] if cur_mat == 'cable' else [])):
                        if L <= B.MATERIALS[try_mat]['max_len'] - 1e-4:
                            cand = copy.deepcopy(d)
                            cand['members'][idx][2] = try_mat
                            P2 = B.parse_design(lv_wide, cand)
                            if all(B.simulate(lv_wide, P2, B.load_json(sp))[0]['ok'] for sp in B.sample_paths(lv)):
                                d = cand
                                improved = True
                                break
            return True, d
        if earliest is None:
            break
        _, bi, force = earliest
        mat = d['members'][bi][2]
        L = P['members'][bi][4]
        if mat == 'wood':
            d['members'][bi][2] = 'cable' if (force > 0 and force < 82000) else 'steel'
        elif mat == 'cable' and L <= 6.0:
            d['members'][bi][2] = 'steel'
        else:
            break
    ok, _, _, _ = U.eval_bridge(lv_id, d, verbose=False)
    return ok, d


if __name__ == '__main__':
    print('=== Testing Level 4 Submersible ===')
    d4 = make_l4_submersible()
    try:
        ok4, d4_up = auto_upgrade_ship(4, d4)
        U.save_if_best(4, d4_up, verbose=True)
    except Exception as e:
        print('L4 err:', e)
        U.eval_bridge(4, d4, verbose=True)

    print('=== Testing Level 6 Submersible ===')
    d6 = make_l6_submersible()
    try:
        ok6, d6_up = auto_upgrade_ship(6, d6)
        U.save_if_best(6, d6_up, verbose=True)
    except Exception as e:
        print('L6 err:', e)
        U.eval_bridge(6, d6, verbose=True)
