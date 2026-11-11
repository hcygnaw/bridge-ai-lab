#!/usr/bin/env python3
"""Automated cost-crushing optimizer across Levels 1-6 + Level 7 Red/Blue Co-Evolution."""
import copy
import json
import math
import os
import random
import time
import bridge as B
import saboteur as S
import opt_utils as U


def optimize_level(lv_id, budget_sec=18.0, seed=7):
    fpath = os.path.join(U.SUB_DIR, f'level{lv_id}.json')
    d = B.load_json(fpath)
    lv = B.load_level(lv_id)
    ok, best_cost, _, _ = U.eval_bridge(lv_id, d, verbose=False)
    if not ok:
        print(f'[L{lv_id}] Baseline did not pass?! Skipping.')
        return
    start_cost = best_cost
    t0 = time.time()
    rng = random.Random(seed + int(lv_id) * 31)

    # Identify protected members (referenced by plate sensors)
    plate_members = {s.get('member') for s in d.get('sensors', []) if s.get('type') == 'plate'}

    # Phase A: Deterministic greedy downgrade (steel -> cable/wood, cable -> wood)
    for idx in range(len(d['members'])):
        if time.time() - t0 > budget_sec * 0.4:
            break
        cur_m = d['members'][idx][2]
        opts = []
        if cur_m == 'steel':
            opts = [x for x in ('wood', 'cable', 'spring') if x not in lv.get('banned', [])]
        elif cur_m == 'cable':
            opts = [x for x in ('wood',) if x not in lv.get('banned', [])]
        for nm in opts:
            cand = copy.deepcopy(d)
            cand['members'][idx][2] = nm
            ok_c, c_c, _, _ = U.eval_bridge(lv_id, cand, verbose=False)
            if ok_c and c_c < best_cost - 0.5:
                d, best_cost = cand, c_c
                U.save_if_best(lv_id, d, verbose=False)
                break

    # Phase B: Deterministic greedy pruning (when no plate sensors)
    if not plate_members:
        improved = True
        while improved and (time.time() - t0 < budget_sec * 0.65):
            improved = False
            P_cur = B.parse_design(lv, d)
            order = sorted(range(len(d['members'])),
                           key=lambda i: -(B.MATERIALS[d['members'][i][2]]['cost_m'] * P_cur['members'][i][4]))
            for idx in order:
                if time.time() - t0 > budget_sec * 0.65:
                    break
                if d['members'][idx][2] in ('road', 'hydraulic'):
                    continue
                cand = copy.deepcopy(d)
                cand['members'].pop(idx)
                used = {x for m in cand['members'] for x in m[:2] if isinstance(x, int)}
                remap, nn = {}, []
                for oi, pt in enumerate(cand['nodes']):
                    if oi in used:
                        remap[oi] = len(nn); nn.append(pt)
                cand['nodes'] = nn
                for m in cand['members']:
                    if isinstance(m[0], int): m[0] = remap[m[0]]
                    if isinstance(m[1], int): m[1] = remap[m[1]]
                ok_c, c_c, _, _ = U.eval_bridge(lv_id, cand, verbose=False)
                if ok_c and c_c < best_cost - 0.5:
                    d, best_cost = cand, c_c
                    U.save_if_best(lv_id, d, verbose=False)
                    improved = True
                    break

    # Phase C: Stochastic coordinate descent + downgrade!
    steps = 0
    while time.time() - t0 < budget_sec:
        steps += 1
        cand = copy.deepcopy(d)
        r = rng.random()
        if r < 0.72 and cand['nodes']:
            for _ in range(rng.choice([1, 1, 2])):
                ni = rng.randrange(len(cand['nodes']))
                scale = rng.choice([0.08, 0.22, 0.45])
                cand['nodes'][ni][0] = round(cand['nodes'][ni][0] + rng.uniform(-scale, scale), 4)
                cand['nodes'][ni][1] = round(cand['nodes'][ni][1] + rng.uniform(-scale, scale), 4)
        else:
            non_rd = [i for i, m in enumerate(cand['members']) if m[2] in ('steel', 'cable', 'spring')]
            if not non_rd:
                continue
            mi = rng.choice(non_rd)
            choices = [x for x in ('wood', 'cable') if x not in lv.get('banned', []) and x != cand['members'][mi][2]]
            if not choices:
                continue
            cand['members'][mi][2] = rng.choice(choices)
            for end in cand['members'][mi][:2]:
                if isinstance(end, int) and rng.random() < 0.6:
                    cand['nodes'][end][0] = round(cand['nodes'][end][0] + rng.uniform(-0.25, 0.25), 4)
                    cand['nodes'][end][1] = round(cand['nodes'][end][1] + rng.uniform(-0.25, 0.25), 4)
        ok_c, c_c, _, _ = U.eval_bridge(lv_id, cand, verbose=False)
        if ok_c and c_c < best_cost - 0.2:
            d, best_cost = cand, c_c
            U.save_if_best(lv_id, d, verbose=False)

    print(f'[L{lv_id}] Optimized: {start_cost:.2f} -> {best_cost:.2f} (saved {start_cost - best_cost:.2f}, {steps} coord steps)')


def tune_final_duel():
    lv = B.load_level('final')
    # Build 4 realistic enemy bridges (1: underslung cable-wood, 2: overhead steel/wood Warren, 3: pure steel arch, 4: cable-stayed)
    enemies = []

    # Enemy 1: Underslung cable + steel/wood Warren (~17k)
    n1 = [[round(28.0 * i / 14, 4), 0.0] for i in range(1, 14)]
    d1 = ['A0'] + list(range(13)) + ['A3']
    m1 = [[a, b, 'road'] for a, b in zip(d1, d1[1:])]
    b1 = []
    for i in range(14):
        t = (i + 0.5) / 14
        b1.append(len(n1)); n1.append([round(28.0 * t, 4), round(-1.8 - 0.9 * 4 * t * (1 - t), 4)])
    m1 += [['A1', b1[0], 'steel'], [b1[-1], 'A4', 'steel'], ['A1', d1[1], 'steel'], ['A4', d1[-2], 'steel']]
    for i in range(13): m1.append([b1[i], b1[i+1], 'cable'])
    for i in range(14): m1 += [[b1[i], d1[i], 'steel' if i in (0, 1, 12, 13) else 'wood'], [b1[i], d1[i+1], 'steel' if i in (0, 1, 12, 13) else 'wood']]
    enemies.append(('Underslung_17k', {'nodes': n1, 'members': m1}))

    # Enemy 2: Cable-stayed bridge (~22k)
    n2 = [[round(28.0 * i / 12, 4), 0.0] for i in range(1, 12)]
    d2 = ['A0'] + list(range(11)) + ['A3']
    m2 = [[a, b, 'road'] for a, b in zip(d2, d2[1:])]
    tL = len(n2); n2.append([-1.8, 5.2])
    tR = len(n2); n2.append([29.8, 5.2])
    m2 += [['A2', tL, 'steel'], ['A0', tL, 'steel'], ['A5', tR, 'steel'], ['A3', tR, 'steel'], ['A1', d2[1], 'steel'], ['A4', d2[-2], 'steel']]
    for i in range(2, 7): m2.append([tL, d2[i], 'cable'])
    for i in range(5, 10): m2.append([tR, d2[i], 'cable'])
    b2 = []
    for i in range(12):
        b2.append(len(n2)); n2.append([round(28.0 * (i + 0.5) / 12, 4), -1.6])
    for i in range(12): m2 += [[b2[i], d2[i], 'wood'], [b2[i], d2[i+1], 'wood']]
    for i in range(11): m2.append([b2[i], b2[i+1], 'wood'])
    enemies.append(('CableStayed_22k', {'nodes': n2, 'members': m2}))

    valid_enemies = []
    for name, ed in enemies:
        try:
            Pe = B.parse_design(lv, ed)
            base, _ = B.simulate(lv, Pe, S.convoy_scenario(lv))
            print(f'  Enemy {name}: cost={Pe["cost"]:.0f}, baseline_ok={base["ok"]}')
            if base['ok']:
                valid_enemies.append((name, Pe))
        except Exception as e:
            print(f'  Enemy {name} invalid: {e}')

    # Upgrade our final_bridge.json up to ~25,850 budget for maximum armor!
    fb = B.load_json(os.path.join(U.SUB_DIR, 'final_bridge.json'))
    P_fb = B.parse_design(lv, fb)
    for idx in range(len(fb['members'])):
        if fb['members'][idx][2] == 'wood':
            cand = copy.deepcopy(fb)
            cand['members'][idx][2] = 'steel'
            try:
                Pc = B.parse_design(lv, cand)
            except Exception:
                continue
            if Pc['cost'] <= 25950:
                ok_c, _, _, _ = U.eval_bridge('final', cand, verbose=False)
                if ok_c:
                    fb, P_fb = cand, Pc
    U.save_if_best('final', fb, verbose=False)
    print(f'[L7] Upgraded Fortress Bridge cost = {P_fb["cost"]:.2f} / 26000')

    # Test saboteur variants (different hammer stroke amplitudes & frequencies) against valid_enemies AND our Fortress!
    cur_sab = B.load_json(os.path.join(U.SUB_DIR, 'saboteur.json'))
    best_sab = cur_sab
    best_kills = -1

    for r_lo, r_hi, dt1, dt2 in [(0.68, 1.25, 0.18, 0.36), (0.55, 1.38, 0.15, 0.30), (0.52, 1.45, 0.14, 0.28), (0.60, 1.35, 0.12, 0.24)]:
        cand_s = copy.deepcopy(cur_sab)
        rules = []
        for gid in ('g1', 'g2', 'g3', 'g4'):
            rules.append({'on': gid, 'delay': 0.0, 'do': 'hyd', 'group': 'A', 'ratio': r_lo, 'speed': 3.0, 'accel': 5.0})
            rules.append({'on': gid, 'delay': dt1, 'do': 'hyd', 'group': 'A', 'ratio': r_hi, 'speed': 3.0, 'accel': 5.0})
            rules.append({'on': gid, 'delay': dt2, 'do': 'hyd', 'group': 'A', 'ratio': r_lo, 'speed': 3.0, 'accel': 5.0})
        rules.append({'on': 'g5', 'delay': 0.0, 'do': 'hyd', 'group': 'A', 'ratio': 1.0, 'speed': 2.5, 'accel': 4.0})
        cand_s['rules'] = rules
        Sp = S.parse_sab(lv, cand_s)
        r_fort, _ = S.duel(lv, P_fb, Sp)
        if not r_fort['sab_arrived']:
            continue
        kills = sum(1 for _, Pe in valid_enemies if S.duel(lv, Pe, Sp)[0]['sab_win'])
        arr_ok = all(S.duel(lv, Pe, Sp)[0]['sab_arrived'] for _, Pe in valid_enemies)
        print(f'  Saboteur ({r_lo}, {r_hi}, {dt1}): sab_arr_all={arr_ok}, enemy_kills={kills}/{len(valid_enemies)}, vs_our_fort_bridge_win={r_fort["bridge_win"]}')
        if arr_ok and kills > best_kills:
            best_kills = kills
            best_sab = cand_s

    with open(os.path.join(U.SUB_DIR, 'saboteur.json'), 'w', encoding='utf-8') as f:
        json.dump(best_sab, f, ensure_ascii=False, indent=1)
    print(f'[L7] Saved best saboteur.json (kills={best_kills}/{len(valid_enemies)})')


if __name__ == '__main__':
    for lv_id, sec in [(1, 14), (2, 18), (3, 18), (4, 16), (5, 14), (6, 16)]:
        optimize_level(lv_id, budget_sec=sec)
    tune_final_duel()
