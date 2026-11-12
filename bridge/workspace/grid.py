"""Multi-story truss grid. All bays triangulated. Materials selectable."""
import math, os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bridge
from kit import B, save, SUB

def grid(x0, x1, y_top, y_bot, n, stories=1, left_top='A0', right_top='A2',
         left_bots=None, right_bots=None, web='wood', botmat='wood',
         diagonals=True, x_bracing=False):
    """stories>=1. y levels from y_top down to y_bot equally.
    left_bots/right_bots: list of anchor ids for intermediate and bottom levels (len stories), or None.
    """
    b = B()
    dx = (x1 - x0) / n
    ys = [y_top + (y_bot - y_top) * s / stories for s in range(stories + 1)]
    # node grid [story][i]
    nodes = []
    for s, y in enumerate(ys):
        row = []
        for i in range(n + 1):
            x = x0 + i * dx
            if s == 0 and i == 0:
                row.append(left_top)
            elif s == 0 and i == n:
                row.append(right_top)
            elif left_bots and i == 0 and s-1 < len(left_bots) and left_bots[s-1]:
                row.append(left_bots[s-1])
            elif right_bots and i == n and s-1 < len(right_bots) and right_bots[s-1]:
                row.append(right_bots[s-1])
            else:
                # cliff faces x<=0 and x>=30 are solid; keep free nodes strictly inside the gap
                xx = x
                if xx <= 0:
                    xx = 0.2
                elif xx >= 30:
                    xx = 29.8
                row.append(b.add(xx, y))
        nodes.append(row)
    # chords
    for s, row in enumerate(nodes):
        mat = 'road' if s == 0 else botmat
        for i in range(n):
            b.mem(row[i], row[i+1], mat)
    # verticals
    for s in range(stories):
        for i in range(n + 1):
            a, c = nodes[s][i], nodes[s+1][i]
            if isinstance(a, str) and isinstance(c, str):
                continue
            b.mem(a, c, web)
    # diagonals: one direction per bay, alternating, or X
    if diagonals:
        for s in range(stories):
            for i in range(n):
                if x_bracing:
                    b.mem(nodes[s][i], nodes[s+1][i+1], web)
                    b.mem(nodes[s][i+1], nodes[s+1][i], web)
                else:
                    if (i + s) % 2 == 0:
                        b.mem(nodes[s][i], nodes[s+1][i+1], web)
                    else:
                        b.mem(nodes[s][i+1], nodes[s+1][i], web)
    return b.design(), dx, abs(ys[0]-ys[1]) if stories else 0


def test(level, design, sample_names=None):
    lv = bridge.load_level(level)
    scs = [(os.path.basename(p), bridge.load_json(p)) for p in bridge.sample_paths(lv)]
    try:
        P = bridge.parse_design(lv, design)
    except bridge.DesignError as e:
        return {'ok': False, 'err': str(e).split('\n')[0]}
    peak = 0
    for name, sc in scs:
        if sample_names and name not in sample_names:
            continue
        res, _ = bridge.simulate(lv, P, sc)
        if not res.get('ok'):
            br = [e for e in res['events'] if 'BREAK' in e][:4]
            return {'ok': False, 'cost': P['cost'], 'fail': name,
                    'why': bridge.summarize(res, P, sc)['text'].split('\n')[0],
                    'top': bridge.peak_report(res, P, 3), 'br': br}
        peak = max(peak, max(res.get('peak_members') or [0]))
    return {'ok': True, 'cost': P['cost'], 'peak': peak}


if __name__ == '__main__':
    print('L2 grid search', flush=True)
    best = None
    for n, stories, depth, web, bot in [
        (15, 2, 4.0, 'wood', 'wood'),
        (15, 2, 4.0, 'steel', 'wood'),
        (15, 2, 4.0, 'steel', 'steel'),
        (20, 2, 4.0, 'wood', 'wood'),
        (12, 2, 4.0, 'steel', 'steel'),
        (15, 1, 3.0, 'steel', 'steel'),
        (20, 1, 3.5, 'wood', 'steel'),
        (20, 2, 5.0, 'wood', 'wood'),
        (24, 2, 4.0, 'wood', 'wood'),
        (20, 3, 6.0, 'wood', 'wood'),
    ]:
        # left bots: story levels. depth total, stories.
        # y of story s (1..stories) = 0 - depth*s/stories
        # anchors: A1 at -4, A2 at -8. Use if close.
        ys = [0 - depth * s / stories for s in range(1, stories+1)]
        left, right = [], []
        for y in ys:
            if abs(y - (-4)) < 0.05:
                left.append('A1'); right.append('A5')
            elif abs(y - (-8)) < 0.05:
                left.append('A2'); right.append('A6')
            else:
                left.append(None); right.append(None)
        d, dx, h = grid(0, 30, 0, -depth, n, stories, 'A0', 'A4', left, right, web, bot)
        diag = math.hypot(dx, h)
        r = test(2, d, {'sample2.json'})
        tag = f'n={n} st={stories} d={depth} web={web} bot={bot} dx={dx:.2f} h={h:.2f} diag={diag:.2f}'
        if r.get('err'):
            print('INV', tag, r['err'])
        elif r['ok']:
            print('PASS', tag, f'cost={r["cost"]:.0f} peak={r["peak"]:.2f}', flush=True)
            if best is None or r['cost'] < best[0]:
                best = (r['cost'], tag, d)
        else:
            print('fail', tag, f'cost={r.get("cost")} {r.get("why")}', r.get('br', [''])[0] if r.get('br') else '', flush=True)
    if best:
        r = test(2, best[2])
        print('L2 FULL', r)
        if r['ok']:
            save(best[2], 'level2_best.json')
            with open(os.path.join(SUB, 'level2.json'), 'w') as f:
                json.dump(best[2], f); f.write('\n')
            print('saved', best[0], best[1])
