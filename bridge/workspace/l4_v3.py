"""Level 4: deck on posts outside the channel, hydraulic drop span over the channel,
foundation truss entirely below y=-2.6."""
import math, os, sys, json, copy
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bridge
from kit import B, save, SUB

def hits(p, q, x0=9, x1=15, y0=-2, y1=6):
    ax, ay = p; bx, by = q
    # Liang-Barsky
    dx, dy = bx - ax, by - ay
    t0, t1 = 0.0, 1.0
    for p_, q_ in ((-dx, ax - x0), (dx, x1 - ax), (-dy, ay - y0), (dy, y1 - ay)):
        if abs(p_) < 1e-12:
            if q_ < 0:
                return False
        else:
            r = q_ / p_
            if p_ < 0:
                if r > t1:
                    return False
                if r > t0:
                    t0 = r
            else:
                if r < t0:
                    return False
                if r < t1:
                    t1 = r
    return True

def build():
    b = B()
    # Deck nodes every 2.0 m from 0 to 24, but center moving nodes are separate.
    # Fixed deck: 0,2,4,6,8.0 and 16,18,20,22,24
    # Moving deck: 9.4, 11.6, 13.8, 15.05?  Channel 9-15. Moving span covers 9.15 to 14.85
    fixed_x = [0, 2, 4, 6, 8.0]
    fixed_r = [16.0, 18, 20, 22, 24]
    move_x = [9.2, 11.2, 13.2, 14.8]
    # gap 8.0 to 9.2 = 1.2m TOO BIG. Need gap ~0.2.
    # So fixed deck must extend to 8.95 and moving starts at 9.15? 
    # Post at x=8.7 is outside channel and can support the fixed deck end.
    fixed_x = [0, 2.2, 4.4, 6.6, 8.82]
    fixed_r = [15.18, 17.4, 19.6, 21.8, 24]
    move_x = [8.94, 10.5, 12.0, 13.55, 15.06]
    hyd_x = {8.94, 15.06}
    # gaps: 8.75-8.95=0.20, 15.05-15.25=0.20

    def add_deck(xs, left_anchor=None, right_anchor=None):
        ids = []
        for i, x in enumerate(xs):
            if i == 0 and left_anchor:
                ids.append(left_anchor)
            elif i == len(xs) - 1 and right_anchor:
                ids.append(right_anchor)
            else:
                ids.append(b.add(x, 0.0))
        for a, c in zip(ids, ids[1:]):
            b.mem(a, c, 'road')
        return ids

    left = add_deck(fixed_x, 'A0', None)
    right = add_deck(fixed_r, None, 'A3')
    moving = [b.add(x, 0.0) for x in move_x]
    for a, c in zip(moving, moving[1:]):
        b.mem(a, c, 'road')
    # moving-span truss below the deck so intermediate nodes don't each need a hydraulic
    mb = [b.add(x, -1.7) for x in move_x]
    for a, c in zip(mb, mb[1:]):
        b.mem(a, c, 'steel')
    for a, c in zip(moving, mb):
        b.mem(a, c, 'steel')
    for i in range(len(move_x) - 1):
        b.mem(moving[i], mb[i + 1], 'steel')

    # foundation truss y=-3.1 (upper) and y=-5.7 (lower), x from 1.0 to 23.0 step 2.0
    fx = [i * 2.0 for i in range(0, 13)]  # 0..24
    # don't place free nodes on cliff x=0 or x=24; use anchors for ends
    u = []
    low = []
    for x in fx:
        if x == 0:
            u.append('A1')  # (0,-2) not exactly on chord; handle separately
            low.append(None)
        elif x == 24:
            u.append('A4')
            low.append(None)
        else:
            u.append(b.add(x, -3.15))
            low.append(b.add(x, -5.2))
    def _xy(r):
        if isinstance(r, str):
            return (0.0, -2.0) if r == 'A1' else (24.0, -2.0)
        return b.nodes[r]
    def _chord_steel(a, c):
        xa, xc = _xy(a)[0], _xy(c)[0]
        return min(xa, xc) < 18 and max(xa, xc) > 6
    # upper chord, skip if both anchors
    for a, c in zip(u, u[1:]):
        if a is None or c is None:
            continue
        if isinstance(a, str) and isinstance(c, str):
            continue
        # A1 is at y=-2, next upper at (2,-3.1): length sqrt(4+1.21)=2.28 wood OK
        b.mem(a, c, 'steel' if _chord_steel(a, c) else 'wood')
    for a, c in zip(low, low[1:]):
        if a is None or c is None:
            continue
        b.mem(a, c, 'steel' if _chord_steel(a, c) else 'wood')
    for uu, ll in zip(u, low):
        if ll is None or isinstance(uu, str):
            continue
        b.mem(uu, ll, 'wood')
    for i in range(len(fx) - 1):
        if low[i] is None or u[i + 1] is None or isinstance(u[i + 1], str):
            continue
        if low[i + 1] is None:
            continue
        # diagonal upper i to lower i+1, and lower i to upper i+1
        # one short-wood diagonal per bay, split so buckling length stays under 1.6 m
        if (i % 2 == 0) and u[i] is not None and low[i + 1] is not None and not (isinstance(u[i], str) and isinstance(low[i + 1], str)):
            a, c = u[i], low[i + 1]
        elif low[i] is not None and u[i + 1] is not None and not isinstance(u[i + 1], str):
            a, c = low[i], u[i + 1]
        else:
            a = c = None
        if a is not None:
            def _xy(r):
                if isinstance(r, str):
                    return (0.0, -2.0) if r == 'A1' else (24.0, -2.0)
                return b.nodes[r]
            p, q = _xy(a), _xy(c)
            mx, my = (p[0] + q[0]) / 2, (p[1] + q[1]) / 2
            # keep the midpoint out of the ship rectangle
            if my > -2.7:
                my = -2.7
            mid = b.add(mx, my)
            b.mem(a, mid, 'wood')
            b.mem(mid, c, 'wood')
            brace = low[i] if a == u[i] else u[i]
            if brace is not None and not (isinstance(brace, str) and False):
                b.mem(mid, brace, 'wood')
    # tie low ends to A1/A4 via short steel if needed
    # low[1] is x=2, y=-5.7. A1 (0,-2) to (2,-5.7): sqrt(4+13.69)=4.20 steel
    b.mem('A1', low[1], 'steel')
    b.mem('A4', low[-2], 'steel')

    # posts from fixed deck nodes (not anchors) down to upper chord, x<9 or x>15
    def nearest_u(x):
        best = None
        bestd = 1e9
        for uu in u:
            if isinstance(uu, str) or uu is None:
                xx = 0 if uu == 'A1' else 24 if uu == 'A4' else None
                if xx is None:
                    continue
            else:
                xx = b.nodes[uu][0]
            if abs(xx - x) < bestd:
                bestd = abs(xx - x)
                best = uu
        return best

    for nid in left + right:
        if isinstance(nid, str):
            continue
        x, y = b.nodes[nid]
        if 8.9 <= x <= 15.1:
            continue
        uu = nearest_u(x)
        if uu is None:
            continue
        ux = 0 if uu == 'A1' else 24 if uu == 'A4' else b.nodes[uu][0]
        uy = -2 if isinstance(uu, str) else b.nodes[uu][1]
        dist = math.hypot(ux - x, uy - y)
        if dist <= 2.95:
            b.mem(nid, uu, 'wood')
        elif dist <= 6.0:
            b.mem(nid, uu, 'steel')

    # hydraulics from feet at y=-4.9 under each moving node
    for nid, x in zip(moving, move_x):
        if x not in hyd_x:
            continue
        foot = b.add(x, -4.85)
        b.mem(foot, nid, 'hydraulic', 'D')
        # brace foot into foundation
        uu = nearest_u(x)
        ll = None
        # nearest low node
        best = None
        bestd = 1e9
        for ll_ in low:
            if ll_ is None:
                continue
            xx = b.nodes[ll_][0]
            if abs(xx - x) < bestd:
                bestd = abs(xx - x)
                best = ll_
        if uu is not None and not isinstance(uu, str):
            if math.hypot(b.nodes[uu][0] - x, b.nodes[uu][1] + 4.9) <= 2.95:
                b.mem(foot, uu, 'wood')
        if best is not None and math.hypot(b.nodes[best][0] - x, b.nodes[best][1] + 4.9) <= 2.95:
            b.mem(foot, best, 'wood')

    b.sensors.append({'id': 'h', 'type': 'horn'})
    b.lights += [
        {'id': 'LL', 'x': -1.0, 'dir': 'right', 'init': 'green'},
        {'id': 'RL', 'x': 25.0, 'dir': 'left', 'init': 'green'},
    ]
    b.rules += [
        {'on': 'h', 'delay': 4.5, 'do': 'light', 'light': 'LL', 'state': 'red'},
        {'on': 'h', 'delay': 5.5, 'do': 'light', 'light': 'RL', 'state': 'red'},
        {'on': 'h', 'delay': 7.8, 'do': 'hyd', 'group': 'D', 'ratio': 0.5, 'speed': 8.0},
        {'on': 'h', 'delay': 16.2, 'do': 'hyd', 'group': 'D', 'ratio': 1.0, 'speed': 8.0},
        {'on': 'h', 'delay': 18.3, 'do': 'light', 'light': 'LL', 'state': 'green'},
        {'on': 'h', 'delay': 18.3, 'do': 'light', 'light': 'RL', 'state': 'green'},
    ]
    return b.design()

def offenders(d):
    lv = bridge.load_level(4)
    anchors = lv['anchors']
    def xy(r):
        return anchors[int(r[1:])] if isinstance(r, str) else d['nodes'][r]
    bad = []
    for i, m in enumerate(d['members']):
        if m[2] in ('hydraulic',):
            continue
        # road on the moving span is allowed to be in the channel when closed;
        # fixed road outside is ok. Flag non-hydraulic members that intersect.
        p, q = xy(m[0]), xy(m[1])
        if hits(p, q):
            bad.append((i, m[2], [round(p[0], 2), round(p[1], 2)], [round(q[0], 2), round(q[1], 2)]))
    return bad

if __name__ == '__main__':
    d = build()
    bad = offenders(d)
    print('channel hits (closed, non-hyd):', len(bad))
    for item in bad[:10]:
        print(' ', item)
    lv = bridge.load_level(4)
    try:
        P = bridge.parse_design(lv, d)
    except bridge.DesignError as e:
        print('INV', e)
        raise SystemExit
    print('cost', P['cost'], P['cost_detail'])
    for pth in bridge.sample_paths(lv):
        sc = bridge.load_json(pth)
        res, _ = bridge.simulate(lv, P, sc)
        print('----', sc['name'], 'OK' if res.get('ok') else 'FAIL')
        print(bridge.summarize(res, P, sc)['text'])
        if not res.get('ok'):
            print(bridge.peak_report(res, P, 5))
            print([e for e in res['events'] if any(k in e for k in ('SHIP', 'VFAIL', 'BREAK', 'ACT'))][:12])
