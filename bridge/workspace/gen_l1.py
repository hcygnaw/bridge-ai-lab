"""Level 1 experiments: tied arch and underslung truss."""
import math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kit import B, report, save

def bowstring(n=8, rise=4.5, arch_mat='wood', hang_mat='cable', deck_y=0.0, x0=0.0, x1=15.0,
              left='A0', right='A2', extra_end=True):
    """Tied arch: deck on y, parabolic arch above, hangers to each deck node.
    Arch is subdivided so wood segments stay <= 2.9 m.
    """
    b = B()
    L = x1 - x0
    # deck nodes (not including anchors)
    dx = L / n
    deck = []
    for i in range(1, n):
        deck.append(b.add(x0 + i * dx, deck_y))
    # arch polyline from left anchor to right anchor, nodes above deck nodes plus extras
    def yarch(x):
        t = (x - x0) / L
        return deck_y + rise * 4 * t * (1 - t)

    # build arch points including anchors, insert extras if segment too long
    xs = [x0 + i * dx for i in range(n + 1)]
    arch_pts = []  # (x, y) or anchor id at ends
    for i, x in enumerate(xs):
        if i == 0:
            arch_pts.append(left)
        elif i == n:
            arch_pts.append(right)
        else:
            arch_pts.append((x, yarch(x)))

    def length(p, q):
        def xy(p):
            if p == left:
                return (x0, deck_y)
            if p == right:
                return (x1, deck_y)
            return p
        x, y = xy(p); u, v = xy(q)
        return math.hypot(u - x, v - y), (x, y), (u, v)

    # subdivide arch segments longer than 2.85
    refined = [arch_pts[0]]
    for q in arch_pts[1:]:
        p = refined[-1]
        ln, a, c = length(p, q)
        if ln > 2.85 and arch_mat == 'wood':
            parts = int(math.ceil(ln / 2.6))
            for k in range(1, parts):
                t = k / parts
                refined.append((a[0] + t * (c[0] - a[0]), a[1] + t * (c[1] - a[1])))
        refined.append(q)

    ids = []
    for p in refined:
        if isinstance(p, str):
            ids.append(p)
        else:
            ids.append(b.add(p[0], p[1]))
    for a, c in zip(ids, ids[1:]):
        b.mem(a, c, arch_mat)

    # deck
    deck_ids = [left] + deck + [right]
    for a, c in zip(deck_ids, deck_ids[1:]):
        b.mem(a, c, 'road')

    # hangers: each deck node to the arch node directly above it (same x), if not coincident
    # map x -> arch id
    arch_by_x = {}
    for i, p in enumerate(refined):
        if isinstance(p, str):
            continue
        arch_by_x[round(p[0], 4)] = ids[i]
    for i, nid in enumerate(deck):
        x = x0 + (i + 1) * dx
        # find closest arch node in x
        best = None
        bestd = 1e9
        for ax, ai in arch_by_x.items():
            if abs(ax - x) < bestd:
                bestd = abs(ax - x)
                best = ai
        if best is None or bestd > 0.05:
            # create hanger target? skip if no arch node
            continue
        ay = b.nodes[best][1]
        if abs(ay - deck_y) < 0.35:
            continue
        # split hanger if needed
        if hang_mat == 'wood' and abs(ay - deck_y) > 2.9:
            # intermediate
            midy = (ay + deck_y) / 2
            m = b.add(x, midy)
            b.mem(best, m, 'wood')
            b.mem(m, nid, 'wood')
        else:
            b.mem(best, nid, hang_mat)
    return b.design()


def truss(n=8, depth=2.5, x0=0.0, x1=15.0, y=0.0, left='A0', right='A2',
          bot_mat='wood', web_mat='wood', low_left='A1', low_right='A3'):
    """Pratt-like: deck, bottom chord, verticals, diagonals sloping down toward center (tension)."""
    b = B()
    L = x1 - x0
    dx = L / n
    top = [left]
    bot = []
    for i in range(1, n):
        top.append(b.add(x0 + i * dx, y))
    top.append(right)
    for i in range(0, n + 1):
        x = x0 + i * dx
        if i == 0 and low_left:
            bot.append(low_left)
        elif i == n and low_right:
            bot.append(low_right)
        else:
            bot.append(b.add(x, y - depth))
    for a, c in zip(top, top[1:]):
        b.mem(a, c, 'road')
    for a, c in zip(bot, bot[1:]):
        b.mem(a, c, bot_mat)
    for i in range(n + 1):
        if top[i] == bot[i]:
            continue
        # skip if both anchors
        if isinstance(top[i], str) and isinstance(bot[i], str):
            # connect via a short stub node? vertical between two anchors is illegal
            continue
        b.mem(top[i], bot[i], web_mat)
    # diagonals: from top[i] to bot[i+1] for left half, top[i+1] to bot[i] for right half
    mid = n // 2
    for i in range(n):
        if i < mid:
            b.mem(top[i], bot[i + 1], web_mat)
        else:
            b.mem(top[i + 1], bot[i], web_mat)
    return b.design()


if __name__ == '__main__':
    designs = []
    for n in (6, 8, 10):
        for rise in (3.5, 4.5, 5.5):
            designs.append((f'bow n={n} r={rise}', bowstring(n=n, rise=rise)))
    for n in (6, 8, 10):
        for depth in (1.6, 2.2, 3.0):
            # check diagonal length
            dx = 15 / n
            diag = math.hypot(dx, depth)
            mat = 'wood' if diag <= 2.95 and depth <= 2.95 else 'steel'
            bot = 'wood' if dx <= 2.95 else 'steel'
            designs.append((f'truss n={n} d={depth} web={mat}', truss(n=n, depth=depth, bot_mat=bot, web_mat=mat)))
    best = None
    for label, d in designs:
        r = report(1, d, label)
        if r['ok'] and (best is None or r['cost'] < best[0]):
            best = (r['cost'], label, d)
            save(d, 'level1_best.json')
            print('  ** new best', r['cost'], label)
    print('BEST', best[0] if best else None, best[1] if best else None)
