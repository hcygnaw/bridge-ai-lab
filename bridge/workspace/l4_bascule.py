"""Level 4 bascule. Leaves rotate up-and-back clear of the channel."""
import math, os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bridge
from kit import B, save, SUB

def approach(b, x0, x1, left, right, lowL, lowR, n=6, depth=2.2):
    dx = (x1 - x0) / n
    top = [left] + [b.add(x0 + i * dx, 0.0) for i in range(1, n)] + [right]
    bots = [b.add(x0 + (i + 0.5) * dx, -depth) for i in range(n)]
    for a, c in zip(top, top[1:]):
        b.mem(a, c, 'road')
    if lowL:
        b.mem(lowL, bots[0], 'wood')
    if lowR:
        b.mem(bots[-1], lowR, 'wood')
    b.mem(left, bots[0], 'wood')
    b.mem(right, bots[-1], 'wood')
    for i in range(n - 1):
        b.mem(bots[i], bots[i + 1], 'wood')
    for i in range(n):
        b.mem(top[i], bots[i], 'wood')
        b.mem(bots[i], top[i + 1], 'wood')
    return top, bots

def build():
    b = B()
    # pivots
    # left approach 0 -> 8.7, right 15.3 -> 24
    LP = b.add(8.7, 0.0)
    RP = b.add(15.3, 0.0)
    approach(b, 0.0, 8.7, 'A0', LP, 'A1', None, n=6, depth=2.4)
    approach(b, 15.3, 24.0, RP, 'A3', None, 'A4', n=6, depth=2.4)

    # left leaf
    LM = b.add(10.5, 0.0)
    LT = b.add(11.9, 0.0)
    LB = b.add(10.5, 1.0)
    b.mem(LP, LM, 'road')
    b.mem(LM, LT, 'road')
    b.mem(LP, LB, 'wood')
    b.mem(LB, LM, 'wood')
    b.mem(LB, LT, 'wood')
    LF = b.add(7.0, -1.0)
    b.mem(LF, LB, 'hydraulic', 'D')
    # fix F into the approach: connect to nearby deck/bottom and A-side
    # deck node near x=7 exists from approach (dx=8.7/6=1.45, nodes at 1.45,2.9,4.35,5.8,7.25)
    # connect F to pivot and to a new brace down to a bottom-ish node
    b.mem(LF, LP, 'wood')
    brace = b.add(7.0, -2.4)
    b.mem(LF, brace, 'wood')
    b.mem(brace, 'A1', 'steel')  # (7,-2.4) to (0,-2) = 7.01 > 6, too long
    return b  # placeholder, will fix below

def build2():
    b = B()
    LP = b.add(8.7, 0.0)
    RP = b.add(15.3, 0.0)
    approach(b, 0.0, 8.7, 'A0', LP, 'A1', None, n=6, depth=2.4)
    approach(b, 15.3, 24.0, RP, 'A3', None, 'A4', n=6, depth=2.4)

    def leaf(pivot, sign, tip_x, mid_x, Fxy):
        M = b.add(mid_x, 0.0)
        T = b.add(tip_x, 0.0)
        B = b.add(mid_x, 1.0)
        b.mem(pivot, M, 'road')
        b.mem(M, T, 'road')
        b.mem(pivot, B, 'wood')
        b.mem(B, M, 'wood')
        b.mem(B, T, 'wood')
        F = b.add(*Fxy)
        b.mem(F, B, 'hydraulic', 'D')
        b.mem(F, pivot, 'wood')
        # tie F down into the approach bottom chord region with a short post and a diagonal to pivot-side
        foot = b.add(Fxy[0], -2.4)
        b.mem(F, foot, 'wood')
        # steel tie toward the bank anchor, split if needed
        anchor = 'A1' if sign > 0 else 'A4'
        ax = 0.0 if sign > 0 else 24.0
        ay = -2.0
        # intermediate so steel <= 6
        mx = (Fxy[0] + ax) / 2
        my = (-2.4 + ay) / 2
        mid = b.add(mx, my)
        b.mem(foot, mid, 'steel')
        b.mem(mid, anchor, 'steel')
        # also wood/steel up to a deck node isn't necessary
        return F

    leaf(LP, 1, 11.9, 10.5, (7.0, -1.0))
    leaf(RP, -1, 12.1, 13.5, (17.0, -1.0))

    b.sensors.append({'id': 'h', 'type': 'horn'})
    b.lights += [
        {'id': 'LL', 'x': -1.0, 'dir': 'right', 'init': 'green'},
        {'id': 'RL', 'x': 25.0, 'dir': 'left', 'init': 'green'},
    ]
    b.rules += [
        {'on': 'h', 'delay': 4.5, 'do': 'light', 'light': 'LL', 'state': 'red'},
        {'on': 'h', 'delay': 5.5, 'do': 'light', 'light': 'RL', 'state': 'red'},
        {'on': 'h', 'delay': 7.5, 'do': 'hyd', 'group': 'D', 'ratio': 0.55, 'speed': 6.0},
        {'on': 'h', 'delay': 16.3, 'do': 'hyd', 'group': 'D', 'ratio': 1.0, 'speed': 6.0},
        {'on': 'h', 'delay': 18.4, 'do': 'light', 'light': 'LL', 'state': 'green'},
        {'on': 'h', 'delay': 18.4, 'do': 'light', 'light': 'RL', 'state': 'green'},
    ]
    return b.design()

if __name__ == '__main__':
    d = build2()
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
        sm = bridge.summarize(res, P, sc)
        print('----', sc['name'], 'OK' if sm['ok'] else 'FAIL')
        print(sm['text'])
        if not sm['ok']:
            print(bridge.peak_report(res, P, 6))
            ev = [e for e in res['events'] if any(k in e for k in ('SHIP', 'VFAIL', 'BREAK', 'ACT', 'HORN'))][:18]
            print(ev)
    else:
        if all(bridge.simulate(lv, P, bridge.load_json(p))[0].get('ok') for p in bridge.sample_paths(lv)):
            save(d, 'level4_best.json')
            with open(os.path.join(SUB, 'level4.json'), 'w') as f:
                json.dump(d, f); f.write('\n')
            print('SAVED')
