"""A few more level-1 ideas. Keep submission if nothing cheaper passes all samples."""
import math, os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bridge
from kit import B

LV = bridge.load_level(1)
SC = [bridge.load_json(p) for p in bridge.sample_paths(LV)]

def full(design):
    try:
        P = bridge.parse_design(LV, design)
    except bridge.DesignError as e:
        return False, None, str(e).split('\n')[0]
    peak = 0
    for sc in SC:
        res, _ = bridge.simulate(LV, P, sc)
        if not res.get('ok'):
            return False, P['cost'], sc['name']
        peak = max(peak, max(res.get('peak_members') or [0]))
    return True, P['cost'], peak

def warren(n, depth, use_low=True, y=0.0):
    b = B()
    x0, x1 = 0.0, 15.0
    dx = (x1 - x0) / n
    top = ['A0'] + [b.add(x0 + i * dx, y) for i in range(1, n)] + ['A2']
    bots = [b.add(x0 + (i + 0.5) * dx, y - depth) for i in range(n)]
    for a, c in zip(top, top[1:]):
        b.mem(a, c, 'road')
    if use_low:
        b.mem('A1', bots[0], 'wood')
        b.mem(bots[-1], 'A3', 'wood')
    b.mem('A0', bots[0], 'wood')
    b.mem('A2', bots[-1], 'wood')
    for i in range(n - 1):
        b.mem(bots[i], bots[i + 1], 'wood')
    for i in range(n):
        b.mem(top[i], bots[i], 'wood')
        b.mem(bots[i], top[i + 1], 'wood')
    return b.design()

def bow(rise=4.0, n_deck=6, seg=1.25):
    b = B()
    x0, x1 = 0.0, 15.0
    L = x1 - x0
    def ya(x):
        t = (x - x0) / L
        return rise * 4 * t * (1 - t)
    # arch xs
    xs = [x0]
    x = x0
    while x < x1 - 1e-6:
        nx = min(x1, x + seg)
        # fit chord
        for _ in range(6):
            ch = math.hypot(nx - x, ya(nx) - ya(x))
            if ch <= seg or nx >= x1 - 1e-9:
                break
            nx = x + (nx - x) * seg / ch
        xs.append(nx)
        x = nx
    arch = ['A0']
    for x in xs[1:-1]:
        arch.append(b.add(x, ya(x)))
    arch.append('A2')
    for a, c in zip(arch, arch[1:]):
        b.mem(a, c, 'wood')
    dx = L / n_deck
    deck = ['A0'] + [b.add(x0 + i * dx, 0.0) for i in range(1, n_deck)] + ['A2']
    for a, c in zip(deck, deck[1:]):
        b.mem(a, c, 'road')
    # hangers wood or split, from deck node up to nearest arch node
    axy = []
    for a in arch:
        if a == 'A0':
            axy.append((0.0, 0.0, a))
        elif a == 'A2':
            axy.append((15.0, 0.0, a))
        else:
            axy.append((b.nodes[a][0], b.nodes[a][1], a))
    for d in deck[1:-1]:
        x, y = b.nodes[d]
        best = min(axy, key=lambda t: abs(t[0] - x))
        dist = best[1] - y
        if dist < 0.4:
            continue
        if dist <= 2.9:
            b.mem(d, best[2], 'wood')
        else:
            steps = int(math.ceil(dist / 2.6))
            prev = d
            for k in range(1, steps):
                m = b.add(x, y + dist * k / steps)
                b.mem(prev, m, 'wood')
                prev = m
            b.mem(prev, best[2], 'wood')
    return b.design()

print('no-low warren')
for d in (1.0, 1.3, 1.6, 2.0, 2.4):
    # check lengths
    dx = 2.5
    diag = math.hypot(dx/2, d)
    if diag > 2.98:
        print('skip', d, 'diag', diag)
        continue
    ok, cost, info = full(warren(6, d, use_low=False))
    print(f'  d={d} ok={ok} cost={cost} info={info}')

print('bow')
for rise in (3.0, 4.0, 5.0):
    for seg in (1.15, 1.4):
        ok, cost, info = full(bow(rise, 6, seg))
        print(f'  rise={rise} seg={seg} ok={ok} cost={cost} info={info}')
