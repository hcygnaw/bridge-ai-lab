#!/usr/bin/env python3
"""Coordinate + Material + Subdivision optimizer to push /tmp/l6_pruned.json below 20,000."""
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


if __name__ == '__main__':
    lv_real = B.load_level(6)
    lv = dict(lv_real, budget=100000)
    d = json.load(open('/tmp/l6_pruned.json'))
    ok, cost = all_pass(lv, d)
    print(f'Loaded L6 pruned: ok={ok}, cost={cost:.2f}')

    # Trick 1: Check every STEEL member — can we downgrade it to WOOD if we move one of its endpoints slightly to shorten L and reduce buckling stress?
    P = B.parse_design(lv, d)
    for i, (u, v, mat, g, L) in enumerate(P['members']):
        if mat == 'steel':
            print(f'  STEEL m[{i}] {B.name_of(u, P["n_anchor"])}->{B.name_of(v, P["n_anchor"])} L={L:.2f} cost={160*L:.0f}')

    # Trick 2: Stochastic coordinate descent + material downgrade + edge pruning!
    rng = random.Random(42)
    for step in range(450):
        cand = copy.deepcopy(d)
        r = rng.random()
        if r < 0.45:
            # Perturb 1 or 2 node coordinates toward shorter bars / higher wood capacity
            for _ in range(rng.choice([1, 2])):
                ni = rng.randrange(len(cand['nodes']))
                # If it's a road node (y == 0), allow tiny camber or x shift; otherwise shift x, y
                cand['nodes'][ni][0] = round(cand['nodes'][ni][0] + rng.uniform(-0.35, 0.35), 4)
                cand['nodes'][ni][1] = round(cand['nodes'][ni][1] + rng.uniform(-0.35, 0.35), 4)
        elif r < 0.80:
            # Pick a steel or cable bar, try downgrading to wood or cable + optionally nudging its endpoints closer!
            steels = [i for i, m in enumerate(cand['members']) if m[2] in ('steel', 'cable')]
            if not steels:
                continue
            mi = rng.choice(steels)
            u, v, cur_m = cand['members'][mi][:3]
            cand['members'][mi][2] = 'wood' if (cur_m == 'cable' or rng.random() < 0.75) else 'cable'
            for end in (u, v):
                if isinstance(end, int) and rng.random() < 0.6:
                    cand['nodes'][end][0] = round(cand['nodes'][end][0] + rng.uniform(-0.3, 0.3), 4)
                    cand['nodes'][end][1] = round(cand['nodes'][end][1] + rng.uniform(-0.3, 0.3), 4)
        else:
            # Try removing a non-road, non-hydraulic member!
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

        ok_c, cost_c = all_pass(lv, cand)
        if ok_c and cost_c < cost - 0.5:
            d, cost = cand, cost_c
            print(f'  [step {step}] NEW BEST L6 = {cost:.2f}')
            if cost <= 20000:
                U.save_if_best(6, d, verbose=True)

    print(f'Done L6 opt: final cost = {cost:.2f}')
    with open('/tmp/l6_pruned.json', 'w') as f:
        json.dump(d, f)
    if cost <= 20000:
        U.save_if_best(6, d, verbose=True)
