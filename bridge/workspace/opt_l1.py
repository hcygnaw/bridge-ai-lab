"""Tighten level 1: shallower warren, drop bottom chord, greedy member deletion."""
import math, os, sys, json, copy
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bridge
from kit import B, save, SUB

LV = bridge.load_level(1)
SC = {os.path.basename(p): bridge.load_json(p) for p in bridge.sample_paths(LV)}

def run(design, samples=('sample2.json',)):
    try:
        P = bridge.parse_design(LV, design)
    except bridge.DesignError as e:
        return {'ok': False, 'cost': None, 'err': str(e).split('\n')[0]}
    peaks = []
    for name in samples:
        res, _ = bridge.simulate(LV, P, SC[name])
        if not res.get('ok'):
            return {'ok': False, 'cost': P['cost'], 'fail': name}
        peaks.append(max(res.get('peak_members') or [0]))
    return {'ok': True, 'cost': P['cost'], 'peak': max(peaks) if peaks else 0}

def warren(n, depth, bottom=True, y=0.0, x0=0.0, x1=15.0, left='A0', right='A2', lowL='A1', lowR='A3'):
    b = B()
    dx = (x1 - x0) / n
    top = [left] + [b.add(x0 + i * dx, y) for i in range(1, n)] + [right]
    bots = [b.add(x0 + (i + 0.5) * dx, y - depth) for i in range(n)]
    for a, c in zip(top, top[1:]):
        b.mem(a, c, 'road')
    if lowL:
        b.mem(lowL, bots[0], 'wood')
    if lowR:
        b.mem(bots[-1], lowR, 'wood')
    b.mem(left, bots[0], 'wood')
    b.mem(right, bots[-1], 'wood')
    if bottom:
        for i in range(n - 1):
            b.mem(bots[i], bots[i + 1], 'wood')
    for i in range(n):
        b.mem(top[i], bots[i], 'wood')
        b.mem(bots[i], top[i + 1], 'wood')
    return b.design()

def prune(design, samples=('sample2.json',)):
    """Greedy: drop any member whose removal still passes. Repeat."""
    d = copy.deepcopy(design)
    improved = True
    while improved:
        improved = False
        # rank members by approximate cost (longer wood first)
        idxs = list(range(len(d['members'])))
        def mcost(i):
            m = d['members'][i]
            if m[2] == 'road':
                return -1  # never drop road first; try last
            return 0
        # try non-road first, longest first
        def length(i):
            m = d['members'][i]
            def xy(r):
                if isinstance(r, str):
                    ai = int(r[1:])
                    return LV['anchors'][ai]
                return d['nodes'][r]
            a, c = xy(m[0]), xy(m[1])
            return math.hypot(a[0] - c[0], a[1] - c[1])
        order = sorted(idxs, key=lambda i: (d['members'][i][2] == 'road', -length(i)))
        for i in order:
            trial = copy.deepcopy(d)
            trial['members'].pop(i)
            # drop orphan nodes
            used = set()
            for m in trial['members']:
                for e in m[:2]:
                    if isinstance(e, int):
                        used.add(e)
            if len(used) != len(trial['nodes']):
                remap = {}
                new_nodes = []
                for k in range(len(trial['nodes'])):
                    if k in used:
                        remap[k] = len(new_nodes)
                        new_nodes.append(trial['nodes'][k])
                trial['nodes'] = new_nodes
                nm = []
                for m in trial['members']:
                    mm = []
                    for e in m[:2]:
                        mm.append(remap[e] if isinstance(e, int) else e)
                    mm.append(m[2])
                    if len(m) > 3:
                        mm.append(m[3])
                    nm.append(mm)
                trial['members'] = nm
            r = run(trial, samples)
            if r['ok'] and r['cost'] < run(d, samples)['cost'] - 0.5:
                print(f'  drop member -> {r["cost"]:.0f} peak={r["peak"]:.2f}', flush=True)
                d = trial
                improved = True
                break
    return d

best = None
print('depth sweep', flush=True)
for bottom in (True, False):
    for depth in (0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.4):
        d = warren(6, depth, bottom=bottom)
        r = run(d)
        flag = 'PASS' if r['ok'] else 'fail'
        extra = f'cost={r["cost"]:.0f} peak={r["peak"]:.2f}' if r.get('cost') and r['ok'] else r.get('err') or r.get('fail') or ''
        print(f'{flag} warren d={depth} bottom={bottom} {extra}', flush=True)
        if r['ok'] and (best is None or r['cost'] < best[0]):
            best = (r['cost'], r['peak'], depth, bottom, d)

print('BEST screen', best[0], 'd', best[2], 'bottom', best[3], 'peak', best[1])
d = best[4]
print('prune...', flush=True)
d2 = prune(d)
r = run(d2, ('sample1.json', 'sample2.json', 'sample3.json'))
print('FULL', r)
if r['ok']:
    save(d2, 'level1_best.json')
    with open(os.path.join(SUB, 'level1.json'), 'w', encoding='utf-8') as f:
        json.dump(d2, f)
        f.write('\n')
    print('saved', r['cost'])
else:
    print('pruned failed full, verify unpruned')
    r0 = run(best[4], ('sample1.json', 'sample2.json', 'sample3.json'))
    print(r0)
    if r0['ok']:
        save(best[4], 'level1_best.json')
        with open(os.path.join(SUB, 'level1.json'), 'w', encoding='utf-8') as f:
            json.dump(best[4], f)
            f.write('\n')
