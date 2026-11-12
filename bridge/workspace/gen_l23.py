"""Warren bridges for level 2 and 3."""
import math, os, sys, json, copy
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bridge
from kit import B, save, SUB

def load(level):
    lv = bridge.load_level(level)
    sc = [(os.path.basename(p), bridge.load_json(p)) for p in bridge.sample_paths(lv)]
    return lv, sc

def run(lv, scs, design, names=None):
    try:
        P = bridge.parse_design(lv, design)
    except bridge.DesignError as e:
        return {'ok': False, 'cost': None, 'err': str(e).split('\n')[0]}
    peak = 0
    for name, sc in scs:
        if names and name not in names:
            continue
        res, _ = bridge.simulate(lv, P, sc)
        if not res.get('ok'):
            return {'ok': False, 'cost': P['cost'], 'fail': name,
                    'text': bridge.summarize(res, P, sc)['text'],
                    'top': bridge.peak_report(res, P, 5)}
        peak = max(peak, max(res.get('peak_members') or [0]))
    return {'ok': True, 'cost': P['cost'], 'peak': peak}

def warren_span(b, x0, x1, n, depth, y, left, right, lowL=None, lowR=None, web='wood'):
    """Add a warren between x0 and x1. Returns (top_ids, bot_ids). left/right may be anchor strings."""
    dx = (x1 - x0) / n
    # length checks happen at parse time
    top = [left]
    for i in range(1, n):
        top.append(b.add(x0 + i * dx, y))
    top.append(right)
    bots = [b.add(x0 + (i + 0.5) * dx, y - depth) for i in range(n)]
    for a, c in zip(top, top[1:]):
        b.mem(a, c, 'road')
    if lowL:
        b.mem(lowL, bots[0], web)
    if lowR:
        b.mem(bots[-1], lowR, web)
    b.mem(left, bots[0], web)
    b.mem(right, bots[-1], web)
    for i in range(n - 1):
        b.mem(bots[i], bots[i + 1], web)
    for i in range(n):
        b.mem(top[i], bots[i], web)
        b.mem(bots[i], top[i + 1], web)
    return top, bots

def level2(n, depth, extra_low=False):
    b = B()
    # 0 to 30
    warren_span(b, 0, 30, n, depth, 0.0, 'A0', 'A4', lowL='A1', lowR='A5')
    if extra_low:
        # brace first/last bottom nodes toward deeper anchors via an intermediate if needed
        # A2=(0,-8), A6=(30,-8). Add a node at (0.8, -5) if useful — skip if lengths illegal.
        pass
    return b.design()

def level3(n_half, depth, pier_brace=True):
    """Two spans 0-14 and 14-28. Center deck node supported down to A2."""
    b = B()
    # build left span ending at a shared center node
    dx = 14.0 / n_half
    left_top = ['A0']
    for i in range(1, n_half):
        left_top.append(b.add(i * dx, 0.0))
    center = b.add(14.0, 0.0)
    left_top.append(center)
    right_top = [center]
    for i in range(1, n_half):
        right_top.append(b.add(14.0 + i * dx, 0.0))
    right_top.append('A3')
    def bots_for(x0, n):
        return [b.add(x0 + (i + 0.5) * dx, -depth) for i in range(n)]
    lb = bots_for(0.0, n_half)
    rb = bots_for(14.0, n_half)
    def connect(top, bots, lowL=None, lowR=None):
        for a, c in zip(top, top[1:]):
            b.mem(a, c, 'road')
        if lowL:
            b.mem(lowL, bots[0], 'wood')
        if lowR:
            b.mem(bots[-1], lowR, 'wood')
        # end diagonals to top ends if not both anchors
        b.mem(top[0], bots[0], 'wood')
        b.mem(top[-1], bots[-1], 'wood')
        for i in range(len(bots) - 1):
            b.mem(bots[i], bots[i + 1], 'wood')
        for i in range(len(bots)):
            b.mem(top[i], bots[i], 'wood')
            b.mem(bots[i], top[i + 1], 'wood')
    connect(left_top, lb, lowL='A1')
    connect(right_top, rb, lowR='A4')
    # pier: center (14,0) down to A2 (14,-4). Split at (14,-2) if depth allows.
    mid = b.add(14.0, -2.0)
    b.mem(center, mid, 'wood')
    b.mem(mid, 'A2', 'wood')
    if pier_brace:
        # brace mid to nearest bottom nodes
        b.mem(mid, lb[-1], 'wood')
        b.mem(mid, rb[0], 'wood')
        b.mem(center, lb[-1], 'wood')
        b.mem(center, rb[0], 'wood')
    return b.design()

def search_l2():
    lv, scs = load(2)
    print('LEVEL 2', flush=True)
    best = None
    for n in (12, 14, 15):
        dx = 30 / n
        if dx > 2.5 + 1e-9:
            continue
        for depth in (1.6, 1.9, 2.2, 2.5, 2.7):
            half = dx / 2
            diag = math.hypot(half, depth)
            bot = dx
            end = math.hypot(half, abs(depth - 4))  # A1 is at y=-4
            if max(diag, bot, end) > 2.98:
                print(f'skip n={n} d={depth} diag={diag:.2f} end={end:.2f}')
                continue
            d = level2(n, depth)
            r = run(lv, scs, d, names={'sample2.json'})
            if r.get('err'):
                print(f'INV n={n} d={depth}: {r["err"]}')
                continue
            if r['ok']:
                print(f'PASS n={n} d={depth} cost={r["cost"]:.0f} peak={r["peak"]:.2f}', flush=True)
                if best is None or r['cost'] < best[0]:
                    best = (r['cost'], n, depth, d, r['peak'])
            else:
                print(f'fail n={n} d={depth} cost={r["cost"]:.0f} {r["fail"]}', flush=True)
    if not best:
        print('no pass')
        return
    print('best screen', best[0], 'n', best[1], 'd', best[2])
    r = run(lv, scs, best[3])
    print('FULL', r['ok'], r.get('cost'), r.get('peak'), r.get('fail'))
    if not r['ok']:
        print(r.get('text'))
        print(r.get('top'))
        return
    save(best[3], 'level2_best.json')
    with open(os.path.join(SUB, 'level2.json'), 'w', encoding='utf-8') as f:
        json.dump(best[3], f)
        f.write('\n')
    print('saved level2', r['cost'])

def search_l3():
    lv, scs = load(3)
    print('LEVEL 3', flush=True)
    best = None
    for n_half in (6, 7, 8):
        dx = 14 / n_half
        if dx > 2.5 + 1e-9:
            continue
        for depth in (1.2, 1.5, 1.8, 2.2, 2.6):
            half = dx / 2
            diag = math.hypot(half, depth)
            # brace from mid (14,-2) to last left bot (14-half, -depth)
            brace = math.hypot(half, abs(-2 - (-depth)))
            if max(diag, dx, brace) > 2.98:
                print(f'skip nh={n_half} d={depth} diag={diag:.2f} brace={brace:.2f}')
                continue
            d = level3(n_half, depth)
            r = run(lv, scs, d, names={'sample2.json'})
            if r.get('err'):
                print(f'INV nh={n_half} d={depth}: {r["err"]}')
                continue
            if r['ok']:
                print(f'PASS nh={n_half} d={depth} cost={r["cost"]:.0f} peak={r["peak"]:.2f}', flush=True)
                if best is None or r['cost'] < best[0]:
                    best = (r['cost'], n_half, depth, d)
            else:
                print(f'fail nh={n_half} d={depth} cost={r.get("cost")} {r.get("fail")}', flush=True)
                if r.get('top'):
                    print('   ', r['top'][0])
    if not best:
        print('no pass')
        return
    r = run(lv, scs, best[3])
    print('FULL', r['ok'], r.get('cost'), r.get('peak'), r.get('fail'))
    if not r['ok']:
        print(r.get('text'))
        print(r.get('top'))
        return
    save(best[3], 'level3_best.json')
    with open(os.path.join(SUB, 'level3.json'), 'w', encoding='utf-8') as f:
        json.dump(best[3], f)
        f.write('\n')
    print('saved level3', r['cost'])

if __name__ == '__main__':
    search_l2()
    search_l3()
