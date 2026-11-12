"""Start from a cheap wood truss and upgrade failing members to steel until it passes."""
import math, os, sys, json, copy
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bridge
from kit import B, save, SUB

def make_warren(x0, x1, n, depth, left, right, lowL=None, lowR=None, web='wood', bot='wood', y=0.0):
    b = B()
    dx = (x1 - x0) / n
    top = [left] + [b.add(x0 + i * dx, y) for i in range(1, n)] + [right]
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
        b.mem(bots[i], bots[i + 1], bot)
    for i in range(n):
        b.mem(top[i], bots[i], web)
        b.mem(bots[i], top[i + 1], web)
    return b.design()

def eval_design(lv, scs, design, names=None):
    try:
        P = bridge.parse_design(lv, design)
    except bridge.DesignError as e:
        return {'ok': False, 'err': str(e).split('\n')[0]}
    peak = 0
    worst = None
    for name, sc in scs:
        if names and name not in names:
            continue
        res, _ = bridge.simulate(lv, P, sc)
        if not res.get('ok'):
            breaks = []
            for e in res['events']:
                parts = e.split()
                if len(parts) >= 3 and parts[1] == 'BREAK':
                    breaks.append(int(parts[2]))
            return {'ok': False, 'cost': P['cost'], 'fail': name, 'breaks': breaks,
                    'why': bridge.summarize(res, P, sc)['text'].split('\n')[0],
                    'top': bridge.peak_report(res, P, 6), 'P': P}
        peak = max(peak, max(res.get('peak_members') or [0]))
    return {'ok': True, 'cost': P['cost'], 'peak': peak, 'detail': P['cost_detail']}

def upgrade_until(level, design, screen, max_up=80):
    lv = bridge.load_level(level)
    scs = [(os.path.basename(p), bridge.load_json(p)) for p in bridge.sample_paths(lv)]
    d = copy.deepcopy(design)
    for step in range(max_up):
        r = eval_design(lv, scs, d, {screen})
        if r.get('err'):
            print('INV', r['err'])
            return None
        if r['ok']:
            full = eval_design(lv, scs, d)
            print(f'PASS step={step} cost={full["cost"]:.0f} peak={full.get("peak")} full={full["ok"]}', flush=True)
            if full['ok']:
                return d, full
            # failed another sample; continue upgrading against that sample
            screen_fail = full['fail']
            print('  other sample failed', screen_fail, full.get('why'))
            r = eval_design(lv, scs, d, {screen_fail})
        breaks = r.get('breaks') or []
        # unique, skip already-steel and road
        upgraded = 0
        for bi in breaks:
            if bi >= len(d['members']):
                continue
            m = d['members'][bi]
            if m[2] == 'road':
                continue
            if m[2] == 'steel':
                continue
            # length check for steel (always ok if wood was ok, steel max 6)
            m[2] = 'steel'
            upgraded += 1
            if upgraded >= 4:
                break
        if upgraded == 0:
            print(f'stuck step={step} cost={r.get("cost")} {r.get("why")} breaks={breaks[:6]} top={r.get("top")}')
            return None
        print(f'  step {step} upgraded {upgraded} cost~ {r.get("cost")} first {breaks[:3]}', flush=True)
    print('gave up')
    return None

if __name__ == '__main__':
    print('L2 upgrade wood warren', flush=True)
    # n=12 dx=2.5 depth=3 diagonals ~3.2 > 3 wood, so start with steel web? 
    # Use n=15 dx=2.0 depth=2.2 so wood diagonals fit: half=1.0, diag=sqrt(1+4.84)=2.42
    for n, depth in [(15, 2.4), (15, 3.0), (12, 2.2)]:
        dx = 30 / n
        diag = math.hypot(dx / 2, depth)
        botlen = dx
        print(f'try n={n} d={depth} diag={diag:.2f} bot={botlen:.2f}')
        if diag > 2.98 or botlen > 2.98 or dx > 2.5:
            print('  lengths no')
            continue
        d0 = make_warren(0, 30, n, depth, 'A0', 'A4', 'A1', 'A5', 'wood', 'wood')
        out = upgrade_until(2, d0, 'sample2.json')
        if out:
            d, full = out
            save(d, 'level2_up.json')
            with open(os.path.join(SUB, 'level2.json'), 'w') as f:
                json.dump(d, f); f.write('\n')
            print('SAVED', full['cost'], full['detail'])
            break
