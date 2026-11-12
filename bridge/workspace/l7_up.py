"""Level 7: warren, steel chords, upgrade web until the convoy passes with margin."""
import math, json, os, bridge
from kit import B, save, SUB

def warren(n=14, depth=3.0, bot='steel', web='wood'):
    b = B()
    x0, x1 = 0.0, 28.0
    dx = (x1 - x0) / n
    top = ['A0'] + [b.add(x0 + i * dx, 0.0) for i in range(1, n)] + ['A3']
    bots = []
    for i in range(n):
        bx = x0 + (i + 0.5) * dx
        bots.append(b.add(round(bx, 4), round(-depth, 4)))
    for a, c in zip(top, top[1:]):
        b.mem(a, c, 'road')
    b.mem('A1', bots[0], web)
    b.mem(bots[-1], 'A4', web)
    b.mem('A0', bots[0], web)
    b.mem('A3', bots[-1], web)
    for i in range(n - 1):
        b.mem(bots[i], bots[i + 1], bot)
    for i in range(n):
        b.mem(top[i], bots[i], web)
        b.mem(bots[i], top[i + 1], web)
    return b.design()

def run(d):
    lv = bridge.load_level('final')
    P = bridge.parse_design(lv, d)
    sc = bridge.load_json(bridge.sample_paths(lv)[0])
    res, _ = bridge.simulate(lv, P, sc)
    return P, sc, res

if __name__ == '__main__':
    # start strong: steel bottom, wood web if lengths allow
    n, depth = 14, 2.6
    dx = 28 / n
    diag = math.hypot(dx / 2, depth)
    print('diag', round(diag, 2), 'dx', round(dx, 2))
    web = 'wood' if diag <= 2.98 and depth <= 2.98 else 'steel'
    d = warren(n, depth, 'steel', web)
    try:
        P, sc, res = run(d)
    except bridge.DesignError as e:
        print('INV', e)
        raise SystemExit
    print('start', web, P['cost'], 'ok', res.get('ok'), 'peak', round(max(res.get('peak_members') or [0]), 3))
    if not res.get('ok'):
        print(bridge.summarize(res, P, sc)['text'])
        # upgrade broken wood to steel
        for step in range(12):
            breaks = []
            for e in res['events']:
                parts = e.split()
                if len(parts) >= 3 and parts[1] == 'BREAK':
                    breaks.append(int(parts[2]))
            up = 0
            for bi in breaks:
                if bi < len(d['members']) and d['members'][bi][2] == 'wood':
                    d['members'][bi][2] = 'steel'
                    up += 1
            print(' step', step, 'up', up, 'breaks', breaks[:6])
            if up == 0:
                break
            try:
                P, sc, res = run(d)
            except bridge.DesignError as e:
                print('INV', str(e)[:200])
                break
            print('  cost', P['cost'], 'ok', res.get('ok'))
            if res.get('ok'):
                break
    if res.get('ok'):
        peak = max(res.get('peak_members') or [0])
        print('PASS', P['cost'], 'peak', round(peak, 3))
        save(d, 'final_bridge.json')
        with open(os.path.join(SUB, 'final_bridge.json'), 'w') as f:
            json.dump(d, f)
            f.write('\n')
        print('saved')
    else:
        print('FAILED')
        print(bridge.summarize(res, P, sc)['text'])
        print(bridge.peak_report(res, P, 6))
