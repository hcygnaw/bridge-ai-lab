"""Test whether a van/car can climb a static high bridge over the level-4 channel."""
import math, os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bridge
from kit import B

def high(y_clear=6.15, x_start=-12.0, x_end=36.0, n_ramp=12):
    b = B()
    # left ramp x_start -> 9, right ramp 15 -> x_end, deck 9->15 at y_clear
    def y_left(x):
        return y_clear * (x - x_start) / (9.0 - x_start)
    def y_right(x):
        return y_clear * (x_end - x) / (x_end - 15.0)
    # deck nodes
    xs_left = [x_start + (9.0 - x_start) * i / n_ramp for i in range(n_ramp + 1)]
    xs_right = [15.0 + (x_end - 15.0) * i / n_ramp for i in range(n_ramp + 1)]
    # map x to anchor if we have one exactly on y=0
    anchors = {
        -12: 'A6', -10: 'A7', -8: 'A8', -6: 'A9', -4: 'A2', -2: 'A10',
        0: 'A0', 24: 'A3', 26: 'A11', 28: 'A5', 30: 'A12', 32: 'A13', 34: 'A14', 36: 'A15'
    }
    def nid(x, y):
        if abs(y) < 1e-6 and round(x) in anchors and abs(x - round(x)) < 1e-6:
            return anchors[round(x)]
        return b.add(x, y)
    left_ids = [nid(x, y_left(x)) for x in xs_left]
    # force channel edges
    left_ids[-1] = b.add(9.0, y_clear) if not isinstance(left_ids[-1], str) else left_ids[-1]
    # rebuild last properly
    mid = [b.add(9.0, y_clear), b.add(12.0, y_clear), b.add(15.0, y_clear)]
    right_ids = [nid(x, y_right(x)) for x in xs_right]
    # connect road along left, mid, right — avoid duplicate 9 and 15
    road = left_ids[:-1] + mid + right_ids[1:]
    for a, c in zip(road, road[1:]):
        b.mem(a, c, 'road')
    # posts down to bank anchors where x matches and post is short enough, else a truss stub
    bank = [(-12,'A6'),(-10,'A7'),(-8,'A8'),(-6,'A9'),(-4,'A2'),(-2,'A10'),(0,'A0'),
            (24,'A3'),(26,'A11'),(28,'A5'),(30,'A12'),(32,'A13'),(34,'A14'),(36,'A15')]
    for x, aid in bank:
        if x <= 9:
            yy = y_left(x)
        elif x >= 15:
            yy = y_right(x)
        else:
            continue
        if yy < 0.35:
            continue
        # find nearest road node
        # create a post node on the ramp if needed
        # connect aid to a ramp node near this x
        best = None
        bestd = 1e9
        for nid_ in road:
            if isinstance(nid_, str):
                continue
            xx, y2 = b.nodes[nid_]
            if abs(xx - x) < bestd:
                bestd = abs(xx - x)
                best = nid_
        if best is None or bestd > 1.2:
            continue
        xx, y2 = b.nodes[best]
        dist = math.hypot(xx - x, y2 - 0)
        if dist < 0.35 or dist > 2.95:
            if dist > 2.95:
                # split
                m = b.add(xx, y2 / 2)
                b.mem(best, m, 'wood')
                if math.hypot(xx - x, y2/2) <= 2.95:
                    b.mem(m, aid, 'wood')
            continue
        b.mem(best, aid, 'wood')
    # towers outside channel: x=8.2 and x=15.8 from y_clear down, braced
    for tx, anchor in ((8.2, None), (15.8, None)):
        top = b.add(tx, y_clear)
        # connect into deck
        deck_pt = mid[0] if tx < 12 else mid[2]
        b.mem(top, deck_pt, 'road')
        # leg down in two wood segments, staying x<9 or x>15
        m = b.add(tx, y_clear / 2)
        bot = b.add(tx, 0.3)
        b.mem(top, m, 'steel')
        b.mem(m, bot, 'steel')
        # brace bot toward bank anchor
        if tx < 9:
            b.mem(bot, 'A0', 'steel')
            b.mem(m, 'A1', 'steel')
        else:
            b.mem(bot, 'A3', 'steel')
            b.mem(m, 'A4', 'steel')
    return b.design()

if __name__ == '__main__':
    d = high()
    lv = bridge.load_level(4)
    try:
        P = bridge.parse_design(lv, d)
        print('cost', P['cost'], P['cost_detail'])
    except bridge.DesignError as e:
        print('INV', e)
        raise SystemExit
    for p in bridge.sample_paths(lv):
        sc = bridge.load_json(p)
        res, _ = bridge.simulate(lv, P, sc)
        print(sc['name'], bridge.summarize(res, P, sc)['text'])
        if not res.get('ok'):
            print(' ', bridge.peak_report(res, P, 4))
            br = [e for e in res['events'] if 'SHIP' in e or 'BREAK' in e or 'VFAIL' in e][:8]
            print(' ', br)
