"""Static level-4 bridge entirely clear of the ship rectangle."""
import math, os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bridge
from kit import B, save, SUB

def hits(p, q):
    ax, ay = p; bx, by = q
    dx, dy = bx-ax, by-ay
    t0, t1 = 0.0, 1.0
    x0, x1, y0, y1 = 9, 15, -2, 6
    for p_, q_ in ((-dx, ax-x0), (dx, x1-ax), (-dy, ay-y0), (dy, y1-ay)):
        if abs(p_) < 1e-12:
            if q_ < -1e-9:
                return False
        else:
            r = q_ / p_
            if p_ < 0:
                if r > t1: return False
                if r > t0: t0 = r
            else:
                if r < t0: return False
                if r < t1: t1 = r
    return True

def build(yc=6.2):
    b = B()
    # polyline of the road: (-12,0) -> (8.6, y at 8.6) -> (9.0, yc) -> (15, yc) -> (15.4, yc) -> (36, 0)
    # slope from x=-12 to x=9
    def yl(x):
        return yc * (x - (-12)) / (9 - (-12))
    def yr(x):
        return yc * (36 - x) / (36 - 15)
    # left ramp nodes every ~2.1 m
    xs = []
    x = -12.0
    while x < 9 - 1e-6:
        xs.append(round(x, 3))
        x += 2.1
    xs.append(9.0)
    anchors = {-12:'A6', -10:'A7', -8:'A8', -6:'A9', -4:'A2', -2:'A10', 0:'A0',
               24:'A3', 26:'A11', 28:'A5', 30:'A12', 32:'A13', 34:'A14', 36:'A15'}
    def N(x, y):
        if abs(y) < 1e-6 and round(x) in anchors and abs(x-round(x))<1e-6:
            return anchors[round(x)]
        return b.add(x, y)
    left = [N(x, yl(x) if x < 9 else yc) for x in xs]
    # fix last
    left[-1] = b.add(9.0, yc)
    mid = [left[-1], b.add(12.0, yc), b.add(15.0, yc)]
    xs2 = [15.0]
    x = 15.0
    while x < 36 - 1e-6:
        x += 2.1
        xs2.append(min(36.0, round(x, 3)))
    if xs2[-1] != 36:
        xs2.append(36.0)
    right = [mid[-1]] + [N(x, yr(x) if x > 15 else yc) for x in xs2[1:]]
    road = left + mid[1:] + right[1:]
    # unique consecutive
    for a, c in zip(road, road[1:]):
        b.mem(a, c, 'road')
    # posts to bank anchors under the ramp, split if needed, stay out of channel
    for x, aid in anchors.items():
        if x <= 0:
            yy = yl(x)
            if yy < 0.4:
                continue
            top = None
            # nearest left node
            best, bd = None, 1e9
            for nid in left:
                if isinstance(nid, str):
                    continue
                if abs(b.nodes[nid][0] - x) < bd:
                    bd = abs(b.nodes[nid][0]-x)
                    best = nid
            if best and bd < 1.3 and 0.35 < b.nodes[best][1] <= 2.9:
                b.mem(best, aid, 'wood')
            elif best and bd < 1.3 and b.nodes[best][1] > 2.9:
                m = b.add(b.nodes[best][0], b.nodes[best][1]/2)
                b.mem(best, m, 'wood')
                if math.hypot(b.nodes[best][0]-x, b.nodes[best][1]/2) <= 2.95:
                    b.mem(m, aid, 'wood')
        elif x >= 24:
            yy = yr(x)
            if yy < 0.4:
                continue
            best, bd = None, 1e9
            for nid in right:
                if isinstance(nid, str):
                    continue
                if abs(b.nodes[nid][0]-x) < bd:
                    bd = abs(b.nodes[nid][0]-x)
                    best = nid
            if best and bd < 1.3 and 0.35 < b.nodes[best][1] <= 2.9:
                b.mem(best, aid, 'wood')
            elif best and bd < 1.3 and b.nodes[best][1] > 2.9:
                m = b.add(b.nodes[best][0], b.nodes[best][1]/2)
                b.mem(best, m, 'wood')
                if math.hypot(b.nodes[best][0]-x, b.nodes[best][1]/2) <= 2.95:
                    b.mem(m, aid, 'wood')
    # towers at x=7.5 and x=16.5, outside channel, supporting the high deck
    # left tower: nodes at (7.5, yc), (7.5, yc/2), (7.5, 0.4), braced to A0 and to deck at x=9
    for tx, side in ((7.2, 'L'), (16.8, 'R')):
        top = b.add(tx, yc)
        midn = b.add(tx, yc/2)
        bot = b.add(tx, 0.4)
        b.mem(top, midn, 'steel')
        b.mem(midn, bot, 'steel')
        deck_pt = mid[0] if side=='L' else mid[2]
        # connect tower top to deck — must not enter channel below yc
        b.mem(top, deck_pt, 'road')
        if side=='L':
            b.mem(bot, 'A0', 'steel')
            b.mem(midn, 'A1', 'steel')
        else:
            b.mem(bot, 'A3', 'steel')
            b.mem(midn, 'A4', 'steel')
    # small truss above the channel deck so the 6m span holds: arch above yc
    arch = [b.add(9.0, yc+1.6), b.add(12.0, yc+2.2), b.add(15.0, yc+1.6)]
    b.mem(mid[0], arch[0], 'wood')
    b.mem(arch[0], arch[1], 'wood')
    b.mem(arch[1], arch[2], 'wood')
    b.mem(arch[2], mid[2], 'wood')
    b.mem(arch[0], mid[1], 'wood')
    b.mem(arch[1], mid[1], 'wood')
    b.mem(arch[2], mid[1], 'wood')
    b.mem(arch[0], mid[0], 'wood')
    return b.design()

if __name__ == '__main__':
    d = build()
    lv = bridge.load_level(4)
    anchors = lv['anchors']
    def xy(r):
        return anchors[int(r[1:])] if isinstance(r, str) else d['nodes'][r]
    bad=[]
    for i,m in enumerate(d['members']):
        if hits(xy(m[0]), xy(m[1])):
            bad.append((i, m[2], xy(m[0]), xy(m[1])))
    print('channel hits', len(bad))
    for item in bad[:8]:
        print(' ', item[0], item[1], [round(item[2][0],2), round(item[2][1],2)], [round(item[3][0],2), round(item[3][1],2)])
    try:
        P = bridge.parse_design(lv, d)
    except bridge.DesignError as e:
        print('INV', e)
        raise SystemExit
    print('cost', P['cost'], P['cost_detail'])
    for pth in bridge.sample_paths(lv):
        sc = bridge.load_json(pth)
        res,_ = bridge.simulate(lv, P, sc)
        print('----', sc['name'], 'OK' if res.get('ok') else 'FAIL')
        print(bridge.summarize(res, P, sc)['text'])
        if not res.get('ok'):
            print(bridge.peak_report(res, P, 4))
            print([e for e in res['events'] if any(k in e for k in ('SHIP','VFAIL','BREAK'))][:8])
