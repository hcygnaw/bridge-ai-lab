"""Fast level-1 search: wood trusses, warren, underslung arch. Screen on van."""
import math, os, sys, json
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
            return {'ok': False, 'cost': P['cost'], 'fail': name, 'text': bridge.summarize(res, P, SC[name])['text'],
                    'top': bridge.peak_report(res, P, 4), 'peak': max(res.get('peak_members') or [0])}
        peaks.append(max(res.get('peak_members') or [0]))
    return {'ok': True, 'cost': P['cost'], 'peak': max(peaks) if peaks else 0, 'P': P}

def pratt(n, depth, web='wood', botmat='wood', y=0.0):
    b = B()
    x0, x1 = 0.0, 15.0
    dx = (x1 - x0) / n
    top = ['A0']
    for i in range(1, n):
        top.append(b.add(x0 + i * dx, y))
    top.append('A2')
    bot = []
    for i in range(n + 1):
        x = x0 + i * dx
        if i == 0:
            bot.append('A1')
        elif i == n:
            bot.append('A3')
        else:
            bot.append(b.add(x, y - depth))
    for a, c in zip(top, top[1:]):
        b.mem(a, c, 'road')
    for a, c in zip(bot, bot[1:]):
        b.mem(a, c, botmat)
    for i in range(n + 1):
        if isinstance(top[i], str) and isinstance(bot[i], str):
            continue
        b.mem(top[i], bot[i], web)
    mid = n / 2
    for i in range(n):
        if i < mid:
            b.mem(top[i], bot[i + 1], web)
        else:
            b.mem(top[i + 1], bot[i], web)
    return b.design()

def warren(n, depth, web='wood', botmat='wood', y=0.0):
    """Top nodes at panel points, bottom nodes offset by half panel. No verticals."""
    b = B()
    x0, x1 = 0.0, 15.0
    dx = (x1 - x0) / n
    top = ['A0'] + [b.add(x0 + i * dx, y) for i in range(1, n)] + ['A2']
    # bottom nodes at half-panels, plus connect ends to A1/A3
    bots = []
    for i in range(n):
        x = x0 + (i + 0.5) * dx
        bots.append(b.add(x, y - depth))
    for a, c in zip(top, top[1:]):
        b.mem(a, c, 'road')
    # end struts to lower anchors
    b.mem('A1', bots[0], botmat)
    b.mem(bots[-1], 'A3', botmat)
    b.mem('A0', bots[0], web)
    b.mem('A2', bots[-1], web)
    for i in range(n - 1):
        b.mem(bots[i], bots[i + 1], botmat)
    for i in range(n):
        b.mem(top[i], bots[i], web)
        b.mem(bots[i], top[i + 1], web)
    return b.design()

def underslung(n_deck, rise, seg=1.4):
    """Deck tie in tension, wood arch below from A1 to A3, posts up to deck."""
    b = B()
    x0, x1 = 0.0, 15.0
    # arch springs at A1 (0,-2) and A3 (15,-2). Crown at mid, y = -2 + rise (rise negative to go down)
    # rise here is downward sag magnitude, crown y = -2 - rise
    y_spring = -2.0
    def yarch(x):
        t = (x - x0) / (x1 - x0)
        return y_spring - rise * 4 * t * (1 - t)
    # sample arch at spacing ~seg
    length_est = 0
    # build x list
    xs = [x0]
    x = x0
    while x < x1 - 1e-6:
        # step so chord ~ seg
        step = seg
        nx = min(x1, x + step)
        # shrink if chord too long
        for _ in range(8):
            chord = math.hypot(nx - x, yarch(nx) - yarch(x))
            if chord <= seg + 0.02 or nx >= x1 - 1e-9:
                break
            nx = x + (nx - x) * (seg / chord)
        if nx <= x + 0.2:
            nx = min(x1, x + 0.3)
        xs.append(round(nx, 4))
        x = nx
    if abs(xs[-1] - x1) > 1e-6:
        xs.append(x1)
    arch = ['A1']
    for x in xs[1:-1]:
        arch.append(b.add(x, yarch(x)))
    arch.append('A3')
    for a, c in zip(arch, arch[1:]):
        b.mem(a, c, 'wood')
    # deck
    dx = (x1 - x0) / n_deck
    deck = ['A0']
    for i in range(1, n_deck):
        deck.append(b.add(x0 + i * dx, 0.0))
    deck.append('A2')
    for a, c in zip(deck, deck[1:]):
        b.mem(a, c, 'road')
    # posts: each deck node to nearest arch node (wood if <=2.95 else split)
    arch_xy = []
    for a in arch:
        if a == 'A1':
            arch_xy.append((0.0, -2.0, a))
        elif a == 'A3':
            arch_xy.append((15.0, -2.0, a))
        else:
            arch_xy.append((b.nodes[a][0], b.nodes[a][1], a))
    for i, d in enumerate(deck):
        if isinstance(d, str):
            x = 0.0 if d == 'A0' else 15.0
            yy = 0.0
        else:
            x, yy = b.nodes[d]
        # nearest arch
        best = min(arch_xy, key=lambda t: abs(t[0] - x))
        if isinstance(d, str) and isinstance(best[2], str):
            continue
        dist = math.hypot(best[0] - x, best[1] - yy)
        if dist < 0.35:
            continue
        if dist <= 2.95:
            b.mem(d, best[2], 'wood')
        else:
            # one intermediate
            mx = (best[0] + x) / 2
            my = (best[1] + yy) / 2
            m = b.add(mx, my)
            b.mem(d, m, 'wood')
            b.mem(m, best[2], 'wood')
    # diagonals between consecutive posts for stability: deck[i] to arch near deck[i+1]
    for i in range(len(deck) - 1):
        d0, d1 = deck[i], deck[i + 1]
        x1d = 0.0 if d1 == 'A2' else (15.0 if isinstance(d1, str) else b.nodes[d1][0])
        best = min(arch_xy, key=lambda t: abs(t[0] - x1d))
        if isinstance(d0, str) and isinstance(best[2], str):
            continue
        x0d = 0.0 if d0 == 'A0' else b.nodes[d0][0]
        y0d = 0.0 if isinstance(d0, str) else b.nodes[d0][1]
        dist = math.hypot(best[0] - x0d, best[1] - y0d)
        if dist < 0.35 or dist > 2.95:
            continue
        b.mem(d0, best[2], 'wood')
    return b.design()

best = None
trials = []
for n in range(6, 12):
    for depth in (1.2, 1.4, 1.5, 1.6, 1.8, 2.0, 2.2, 2.5):
        dx = 15 / n
        diag = math.hypot(dx, depth)
        if diag > 2.98 or depth > 2.98 or dx > 2.98:
            continue
        trials.append((f'pratt n={n} d={depth}', pratt(n, depth)))
for n in range(5, 10):
    for depth in (1.2, 1.5, 1.8, 2.2, 2.6):
        dx = 15 / n
        diag = math.hypot(dx / 2, depth)  # not exact for end members
        # end member from A1 (0,-2) to first bot (dx/2, -depth)
        end = math.hypot(dx / 2, abs(-depth - (-2)))
        half = math.hypot(dx / 2, depth)
        if max(end, half, dx) > 2.98:
            continue
        trials.append((f'warren n={n} d={depth}', warren(n, depth)))
for n in (4, 5, 6, 8):
    for rise in (1.5, 2.0, 2.5, 3.0):
        trials.append((f'under n={n} r={rise}', underslung(n, rise)))

print(f'{len(trials)} trials', flush=True)
passed = []
for i, (label, d) in enumerate(trials):
    r = run(d)
    if r.get('err'):
        print(f'INV {label}: {r["err"]}')
        continue
    if r['ok']:
        print(f'PASS {label} cost={r["cost"]:.0f} peak={r["peak"]:.2f}', flush=True)
        passed.append((r['cost'], r['peak'], label, d))
        if best is None or r['cost'] < best[0]:
            best = (r['cost'], label, d)
            save(d, 'level1_best.json')
    # else silent

print('--- screen best', best[0] if best else None, best[1] if best else None)
# verify top 5 on all samples
passed.sort()
for cost, peak, label, d in passed[:6]:
    r = run(d, samples=('sample1.json', 'sample2.json', 'sample3.json'))
    print(f'FULL {"PASS" if r["ok"] else "FAIL"} {label} cost={cost:.0f} peak={r.get("peak")}')
    if r['ok']:
        save(d, 'level1_best.json')
        with open(os.path.join(SUB, 'level1.json'), 'w', encoding='utf-8') as f:
            json.dump(d, f)
            f.write('\n')
        print('  saved submission')
        break
    else:
        print(r.get('text'))
