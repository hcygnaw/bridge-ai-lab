"""Level 3: pier-supported warren, upgrade weak members to steel."""
import math, os, sys, json, copy
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bridge
from kit import B, save, SUB
from upgrade import eval_design, upgrade_until, make_warren

def with_pier(n, depth, web='wood', bot='wood'):
    # 0..28, n panels, center at x=14 must be a node so n even
    assert n % 2 == 0
    d = make_warren(0, 28, n, depth, 'A0', 'A3', 'A1', 'A4', web, bot)
    b = B()
    b.nodes = d['nodes']
    b.members = d['members']
    # rebuild index
    b._idx = {tuple(p): i for i, p in enumerate(b.nodes)}
    b._idx['_pairs'] = set()
    for m in b.members:
        pair = tuple(sorted((str(m[0]), str(m[1]))))
        b._idx['_pairs'].add(pair)
    # find deck node at x=14, y=0
    center = None
    for i, (x, y) in enumerate(b.nodes):
        if abs(x - 14) < 0.05 and abs(y) < 0.05:
            center = i
            break
    if center is None:
        center = b.add(14, 0)
        # shouldn't happen
    mid = b.add(14, -2.0)
    b.mem(center, mid, 'wood')
    b.mem(mid, 'A2', 'wood')
    # brace mid to nearest bottom nodes
    bots = [(i, x, y) for i, (x, y) in enumerate(b.nodes) if y < -0.3 and abs(x - 14) < 4]
    bots.sort(key=lambda t: abs(t[1] - 14))
    for i, x, y in bots[:2]:
        if math.hypot(x - 14, y - (-2)) <= 2.98:
            b.mem(mid, i, 'wood')
    return b.design()

if __name__ == '__main__':
    best = None
    for n, depth in [(14, 1.6), (14, 2.0), (14, 2.4), (16, 1.8), (12, 2.0)]:
        dx = 28 / n
        diag = math.hypot(dx / 2, depth)
        print(f'n={n} d={depth} dx={dx:.2f} diag={diag:.2f}', flush=True)
        if dx > 2.5 or diag > 2.98 or depth > 2.98:
            print('  skip length')
            continue
        d0 = with_pier(n, depth)
        # quick validity
        r = eval_design(bridge.load_level(3),
                        [(os.path.basename(p), bridge.load_json(p)) for p in bridge.sample_paths(bridge.load_level(3))],
                        d0, {'sample2.json'})
        if r.get('err'):
            print('  INV', r['err'])
            continue
        print(f'  start cost={r.get("cost")} ok={r["ok"]}', flush=True)
        if r['ok']:
            out = (d0, eval_design(bridge.load_level(3),
                                   [(os.path.basename(p), bridge.load_json(p)) for p in bridge.sample_paths(bridge.load_level(3))],
                                   d0))
        else:
            out = upgrade_until(3, d0, 'sample2.json', max_up=40)
        if not out:
            continue
        d, full = out
        print('  RESULT', full['cost'], full.get('peak'), full.get('detail'))
        if best is None or full['cost'] < best[0]:
            best = (full['cost'], d, n, depth)
            save(d, 'level3_best.json')
            with open(os.path.join(SUB, 'level3.json'), 'w') as f:
                json.dump(d, f); f.write('\n')
            print('  saved')
    print('BEST', best[0] if best else None)
