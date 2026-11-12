"""Level 7 static bridge: deep redundant truss, spend budget on strength."""
import math, json, os, bridge
from kit import B, save, SUB

def build(n=14, depth=4.0, stories=2):
    b = B()
    x0, x1 = 0.0, 28.0
    dx = (x1 - x0) / n
    ys = [0.0 - depth * s / stories for s in range(stories + 1)]
    rows = []
    for s, y in enumerate(ys):
        row = []
        for i in range(n + 1):
            x = x0 + i * dx
            if s == 0 and i == 0:
                row.append('A0')
            elif s == 0 and i == n:
                row.append('A3')
            elif s == stories and i == 0 and abs(y - (-2)) < 0.15:
                row.append('A1')
            elif s == stories and i == n and abs(y - (-2)) < 0.15:
                row.append('A4')
            else:
                xx = x
                if xx <= 0.01:
                    xx = 0.25
                if xx >= 27.99:
                    xx = 27.75
                row.append(b.add(round(xx, 4), round(y, 4)))
        rows.append(row)
    for s, row in enumerate(rows):
        mat = 'road' if s == 0 else 'steel'
        for i in range(n):
            b.mem(row[i], row[i + 1], mat)
    for s in range(stories):
        for i in range(n + 1):
            a, c = rows[s][i], rows[s + 1][i]
            if isinstance(a, str) and isinstance(c, str):
                continue
            b.mem(a, c, 'steel')
        for i in range(n):
            b.mem(rows[s][i], rows[s + 1][i + 1], 'steel')
            b.mem(rows[s][i + 1], rows[s + 1][i], 'steel')
    # backstays to rear anchors for extra stiffness
    # A2=(-5,0), A5=(33,0)
    if rows[0][1] not in ('A0',):
        pass
    # tie first interior bottom toward A2 via a node if useful
    return b.design()

if __name__ == '__main__':
    best = None
    for n, depth, stories in [(14, 4, 2), (14, 3, 1), (16, 4, 2), (10, 4, 2)]:
        dx = 28 / n
        h = depth / stories
        diag = math.hypot(dx, h)
        print(f'n={n} d={depth} st={stories} dx={dx:.2f} diag={diag:.2f}', flush=True)
        if dx > 2.5 or diag > 6:
            print('  skip')
            continue
        d = build(n, depth, stories)
        lv = bridge.load_level('final')
        try:
            P = bridge.parse_design(lv, d)
        except bridge.DesignError as e:
            print('  INV', str(e).split('\n')[0])
            continue
        print('  cost', P['cost'])
        sc = bridge.load_json(bridge.sample_paths(lv)[0])
        res, _ = bridge.simulate(lv, P, sc)
        print('  ', 'OK' if res.get('ok') else 'FAIL', bridge.summarize(res, P, sc)['text'].split('\n')[0])
        if res.get('ok'):
            peak = max(res.get('peak_members') or [0])
            print('  peak', round(peak, 3))
            if best is None or P['cost'] < best[0]:
                best = (P['cost'], d, peak)
    if best:
        save(best[1], 'final_bridge.json')
        with open(os.path.join(SUB, 'final_bridge.json'), 'w') as f:
            json.dump(best[1], f)
            f.write('\n')
        print('SAVED', best[0], 'peak', best[2])
