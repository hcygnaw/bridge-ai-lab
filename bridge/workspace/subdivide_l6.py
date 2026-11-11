#!/usr/bin/env python3
"""Replace expensive 2m-3m steel compression struts in /tmp/l6_pruned.json with midpoint-braced wood pairs!"""
import copy
import json
import math
import random
import bridge as B
import opt_utils as U


def all_pass(lv, d):
    try:
        P = B.parse_design(lv, d)
    except Exception:
        return False, float('inf')
    for sp in B.sample_paths(lv):
        res, _ = B.simulate(lv, P, B.load_json(sp))
        if not res['ok']:
            return False, P['cost']
    return True, P['cost']


def coord_of(lv, d, ref):
    if isinstance(ref, str):
        return lv['anchors'][int(ref[1:])]
    return d['nodes'][ref]


if __name__ == '__main__':
    lv_real = B.load_level(6)
    lv = dict(lv_real, budget=100000)
    d = json.load(open('/tmp/l6_pruned.json'))
    ok, cost = all_pass(lv, d)
    print(f'Start cost = {cost:.2f} (ok={ok})')

    # Step 1: Greedy midpoint-braced wood replacement for every steel bar!
    # A 2.3m steel bar costs 368; replacing with 2x1.15m wood (92) + 1 node (20) + 1x1.2m wood brace (48) = 160 -> saves ~208 PER BAR!
    changed = True
    while changed:
        changed = False
        for mi in range(len(d['members'])):
            if d['members'][mi][2] != 'steel':
                continue
            u, v = d['members'][mi][0], d['members'][mi][1]
            pu, pv = coord_of(lv, d, u), coord_of(lv, d, v)
            mx, my = round(0.5 * (pu[0] + pv[0]), 4), round(0.5 * (pu[1] + pv[1]), 4)
            # Do not put a new node inside the ship box [15, 21] x [-2, 6] unless it's part of the moving elevator!
            # Actually simulation checks shiphit directly, so all_pass() automatically verifies ship clearance!
            # Find the 4 closest existing nodes/anchors (not u, v) within 2.95m to brace (mx, my)
            all_refs = [f'A{i}' for i in range(len(lv['anchors']))] + list(range(len(d['nodes'])))
            neighbors = []
            for w in all_refs:
                if w == u or w == v:
                    continue
                pw = coord_of(lv, d, w)
                dist = math.hypot(pw[0] - mx, pw[1] - my)
                if 0.32 <= dist <= 2.95:
                    # Check non-collinearity with u->v
                    area = abs((pv[0] - pu[0]) * (pw[1] - pu[1]) - (pv[1] - pu[1]) * (pw[0] - pu[0]))
                    if area > 0.25:
                        neighbors.append((dist, w))
            neighbors.sort()
            best_cand = None
            best_c = cost
            for _, w in neighbors[:5]:
                cand = copy.deepcopy(d)
                mid_idx = len(cand['nodes'])
                cand['nodes'].append([mx, my])
                cand['members'][mi] = [u, mid_idx, 'wood']
                cand['members'].append([mid_idx, v, 'wood'])
                cand['members'].append([mid_idx, w, 'wood'])
                ok_c, c_c = all_pass(lv, cand)
                if ok_c and c_c < best_c - 1.0:
                    best_cand, best_c = cand, c_c
            if best_cand is not None:
                d, cost = best_cand, best_c
                print(f'  SUBDIVIDED steel bar {mi} -> wood! New cost = {cost:.2f}')
                changed = True
                if cost <= 20000:
                    U.save_if_best(6, d, verbose=True)
                break

    # Step 2: Another round of stochastic coordinate + downgrade + prune polish!
    rng = random.Random(101)
    for step in range(400):
        cand = copy.deepcopy(d)
        r = rng.random()
        if r < 0.55:
            for _ in range(rng.choice([1, 2])):
                ni = rng.randrange(len(cand['nodes']))
                cand['nodes'][ni][0] = round(cand['nodes'][ni][0] + rng.uniform(-0.30, 0.30), 4)
                cand['nodes'][ni][1] = round(cand['nodes'][ni][1] + rng.uniform(-0.30, 0.30), 4)
        elif r < 0.85:
            steels = [i for i, m in enumerate(cand['members']) if m[2] in ('steel', 'cable')]
            if not steels:
                continue
            mi = rng.choice(steels)
            cand['members'][mi][2] = 'wood' if cand['members'][mi][2] == 'cable' or rng.random() < 0.7 else 'cable'
        else:
            rem = [i for i, m in enumerate(cand['members']) if m[2] not in ('road', 'hydraulic')]
            mi = rng.choice(rem)
            cand['members'].pop(mi)
            used = {x for m in cand['members'] for x in m[:2] if isinstance(x, int)}
            remap, nn = {}, []
            for oi, pt in enumerate(cand['nodes']):
                if oi in used:
                    remap[oi] = len(nn); nn.append(pt)
            cand['nodes'] = nn
            for m in cand['members']:
                if isinstance(m[0], int): m[0] = remap[m[0]]
                if isinstance(m[1], int): m[1] = remap[m[1]]
        ok_c, c_c = all_pass(lv, cand)
        if ok_c and c_c < cost - 0.5:
            d, cost = cand, c_c
            print(f'  [polish {step}] cost = {cost:.2f}')
            if cost <= 20000:
                U.save_if_best(6, d, verbose=True)

    with open('/tmp/l6_pruned.json', 'w') as f:
        json.dump(d, f)
    print(f'Final L6 cost = {cost:.2f}')
    if cost <= 20000:
        U.save_if_best(6, d, verbose=True)
