import json, copy, math, time, bridge as B, opt_lib as O
from opt_fast import optimize_design

# 1. Try ultra-cheap L1 templates (span=12, anchors A0=(0,0), A1=(12,0), wood+road+cable/steel?)
lv1 = B.load_level(1)
print('L1 anchors:', lv1['anchors'], 'mats:', lv1.get('allowed_materials', lv1.get('materials')))
# Road min cost for 12m is 12*200 = 2400! So theoretical lower bound with flat road is ~2400 + structure!
# Try N=5 (dx=2.4m) and N=6 (dx=2.0m) minimal arch/truss/under-truss with wood!
for N in [5, 6]:
    dx = 12.0 / N
    for h in [-1.8, -1.4, -1.0, 1.4, 1.8, 2.2, 2.6]:
        # Minimal Warren (only N-1 apexes or 1/2/3 kingposts)
        nodes = [[round(i*dx, 3), 0.0] for i in range(1, N)]
        deck = ['A0'] + list(range(N-1)) + ['A1']
        members = [[deck[i], deck[i+1], 'road'] for i in range(N)]
        # Under-deck inverted kingpost / queenpost / minimal arch
        if abs(h) > 0:
            # 2-post queenpost at 1/3 and 2/3
            p1 = len(nodes); nodes.append([4.0, h])
            p2 = len(nodes); nodes.append([8.0, h])
            members += [['A0', p1, 'wood'], [p1, p2, 'wood'], [p2, 'A1', 'wood']]
            for i in range(1, N):
                x = i * dx
                if x <= 6.0: members.append([deck[i], p1, 'wood'])
                if x >= 6.0: members.append([deck[i], p2, 'wood'])
                if 4.0 < x < 8.0 and N == 5:
                    pass
            O.save_if_best(1, {'nodes': nodes, 'members': members})

            # 1-post kingpost at center (6, h)
            nodes2 = [[round(i*dx, 3), 0.0] for i in range(1, N)]
            p0 = len(nodes2); nodes2.append([6.0, h])
            mem2 = [[deck[i], deck[i+1], 'road'] for i in range(N)]
            mem2 += [['A0', p0, 'wood'], ['A1', p0, 'wood']]
            for i in range(1, N):
                mem2.append([deck[i], p0, 'wood'])
            O.save_if_best(1, {'nodes': nodes2, 'members': mem2})

            # Arched road deck (cambered road arch - ZERO support bars? or tiny ties!)
            for cam in [0.4, 0.7, 1.0, 1.3, 1.6]:
                nodes3 = []
                for i in range(1, N):
                    x = i * dx; s = (x - 6.0) / 6.0
                    nodes3.append([round(x, 3), round(cam * (1.0 - s*s), 3)])
                mem3 = [[deck[i], deck[i+1], 'road'] for i in range(N)]
                # Pure arch road!
                O.save_if_best(1, {'nodes': nodes3, 'members': mem3})
                # Arch road + 1 wood tie bar under it
                mem4 = mem3 + [[0, N-2, 'wood']]
                O.save_if_best(1, {'nodes': nodes3, 'members': mem4})

# Optimize L1 best found
d1 = json.load(open('submission/level1.json'))
_, c1, _ = optimize_design(1, d1, max_sec=15.0)
print(f'L1 after round2: {c1:.2f}', flush=True)

# 2. Continue optimizing L4, L2, L3, L5 with symmetric pair pruning + material downgrading + geometry descent
for lid, budget_sec in [(4, 35.0), (5, 30.0), (2, 25.0), (3, 25.0)]:
    d = json.load(open(f'submission/level{lid}.json'))
    ok0, c0, pk0, _ = O.eval_level(lid, d)
    ok1, c1, _ = optimize_design(lid, d, max_sec=budget_sec)
    print(f'L{lid}: {c0:8.2f} -> {c1:8.2f} (saved {c0-c1:7.2f})', flush=True)
