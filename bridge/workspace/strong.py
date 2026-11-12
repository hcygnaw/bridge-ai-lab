"""Stronger level 2/3 designs: steel bowstring, steel warren, short-wood multistory."""
import math, os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bridge
from kit import B, save, SUB

def test(level, design, names=None):
    lv = bridge.load_level(level)
    scs = [(os.path.basename(p), bridge.load_json(p)) for p in bridge.sample_paths(lv)]
    try:
        P = bridge.parse_design(lv, design)
    except bridge.DesignError as e:
        return {'ok': False, 'err': str(e).split('\n')[0], 'cost': None}
    peak = 0
    for name, sc in scs:
        if names and name not in names:
            continue
        res, _ = bridge.simulate(lv, P, sc)
        if not res.get('ok'):
            br = [e for e in res['events'] if 'BREAK' in e][:3]
            return {'ok': False, 'cost': P['cost'], 'fail': name,
                    'why': bridge.summarize(res, P, sc)['text'].split('\n')[0],
                    'top': bridge.peak_report(res, P, 4), 'br': br}
        peak = max(peak, max(res.get('peak_members') or [0]))
    return {'ok': True, 'cost': P['cost'], 'peak': peak, 'detail': P['cost_detail']}

def steel_bow(span=30, rise=6.0, n_deck=12, seg=3.2, arch_mat='steel', hang='cable',
              left='A0', right='A4', x0=0.0, deck_y=0.0, brace=True):
    b = B()
    x1 = x0 + span
    def ya(x):
        t = (x - x0) / span
        return deck_y + rise * 4 * t * (1 - t)
    xs = [x0]
    x = x0
    while x < x1 - 1e-6:
        nx = min(x1, x + seg)
        for _ in range(8):
            ch = math.hypot(nx - x, ya(nx) - ya(x))
            if ch <= seg + 0.01 or nx >= x1 - 1e-9:
                break
            nx = x + (nx - x) * (seg / max(ch, 0.1))
        xs.append(round(nx, 4))
        x = nx
    arch = [left]
    for x in xs[1:-1]:
        arch.append(b.add(x, ya(x)))
    arch.append(right)
    for a, c in zip(arch, arch[1:]):
        b.mem(a, c, arch_mat)
    dx = span / n_deck
    deck = [left] + [b.add(x0 + i * dx, deck_y) for i in range(1, n_deck)] + [right]
    for a, c in zip(deck, deck[1:]):
        b.mem(a, c, 'road')
    axy = []
    for a in arch:
        if isinstance(a, str):
            # anchors: left at x0, right at x1, y = deck_y (A0/A4 are deck level)
            if a == left:
                axy.append((x0, deck_y, a))
            else:
                axy.append((x1, deck_y, a))
        else:
            axy.append((b.nodes[a][0], b.nodes[a][1], a))
    hang_ids = []
    for d in deck[1:-1]:
        x, y = b.nodes[d]
        best = min(axy, key=lambda t: abs(t[0] - x))
        dist = math.hypot(best[0] - x, best[1] - y)
        if dist < 0.35:
            hang_ids.append(None)
            continue
        mat = hang
        if mat == 'wood' and dist > 2.95:
            mat = 'cable'
        if mat == 'cable' and dist > 29:
            mat = 'steel'
        b.mem(d, best[2], mat)
        hang_ids.append(best[2])
    if brace:
        # diagonal cable from deck node i to arch node of deck i+1
        for i, d in enumerate(deck[1:-2]):
            x = b.nodes[d][0]
            # target arch near next deck node
            nx = x + dx
            best = min(axy, key=lambda t: abs(t[0] - nx))
            if isinstance(d, str) and isinstance(best[2], str):
                continue
            dist = math.hypot(best[0] - b.nodes[d][0], best[1] - b.nodes[d][1])
            if dist < 0.4 or dist > 29:
                continue
            b.mem(d, best[2], 'cable')
    return b.design()

def steel_warren(span, n, depth, x0=0.0, left='A0', right='A4', lowL='A1', lowR='A5',
                 web='steel', bot='steel', y=0.0, low_y=-4.0):
    b = B()
    dx = span / n
    top = [left] + [b.add(x0 + i * dx, y) for i in range(1, n)] + [right]
    bots = []
    for i in range(n):
        bx = x0 + (i + 0.5) * dx
        # keep off cliff faces
        if bx <= x0:
            bx = x0 + 0.2
        if bx >= x0 + span:
            bx = x0 + span - 0.2
        bots.append(b.add(bx, y - depth))
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

def show(tag, r):
    if r.get('err'):
        print(f'INV {tag}: {r["err"]}')
    elif r['ok']:
        print(f'PASS {tag} cost={r["cost"]:.0f} peak={r["peak"]:.2f} {r.get("detail")}', flush=True)
    else:
        print(f'fail {tag} cost={r.get("cost")} {r.get("why")} {r.get("br")}', flush=True)

print('=== L2 bow ===', flush=True)
for rise in (5, 7, 9):
    for seg in (3.0, 4.0):
        for nd in (12, 15):
            d = steel_bow(30, rise, nd, seg)
            r = test(2, d, {'sample2.json'})
            show(f'bow rise={rise} seg={seg} nd={nd}', r)
            if r['ok']:
                r2 = test(2, d)
                print('  FULL', r2['ok'], r2.get('cost'), r2.get('peak'), r2.get('fail'))
                if r2['ok']:
                    save(d, 'level2_best.json')
                    with open(os.path.join(SUB, 'level2.json'), 'w') as f:
                        json.dump(d, f); f.write('\n')
                    print('  SAVED')

print('=== L2 warren steel ===', flush=True)
for n, depth, web, bot in [
    (12, 3.0, 'steel', 'steel'),
    (12, 3.5, 'steel', 'steel'),
    (12, 2.5, 'steel', 'cable'),
    (15, 3.0, 'steel', 'steel'),
    (10, 3.5, 'steel', 'steel'),
    (12, 4.0, 'steel', 'cable'),
]:
    dx = 30 / n
    if dx > 2.5:
        print('skip road', n)
        continue
    d = steel_warren(30, n, depth, web=web, bot=bot)
    r = test(2, d, {'sample2.json'})
    show(f'war n={n} d={depth} {web}/{bot}', r)
    if r['ok']:
        r2 = test(2, d)
        print('  FULL', r2['ok'], r2.get('peak'))
        if r2['ok']:
            save(d, 'level2_warren.json')
            print('  candidate', r2['cost'])
