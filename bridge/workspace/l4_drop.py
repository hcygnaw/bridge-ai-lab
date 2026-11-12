"""Level 4 drop-bridge. Center span retracts below the channel on the horn."""
import math, os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bridge
from kit import B, save, SUB

def seg_hits_channel(p, q, x0=9, x1=15, y0=-2, y1=6):
    # Liang-Barsky-ish sample
    for t in [i / 20 for i in range(21)]:
        x = p[0] + t * (q[0] - p[0])
        y = p[1] + t * (q[1] - p[1])
        if x0 - 1e-6 <= x <= x1 + 1e-6 and y0 - 1e-6 <= y <= y1 + 1e-6:
            return True
    return False

def build(drop=True):
    b = B()
    # ---- left approach 0 -> 8.80, 4 panels, depth 1.4
    nL = 4
    xL = 8.80
    dx = xL / nL
    depth = 1.4
    top = ['A0'] + [b.add(i * dx, 0.0) for i in range(1, nL)] + [b.add(xL, 0.0)]
    bots = [b.add((i + 0.5) * dx, -depth) for i in range(nL)]
    for a, c in zip(top, top[1:]):
        b.mem(a, c, 'road')
    b.mem('A1', bots[0], 'wood')
    b.mem('A0', bots[0], 'wood')
    for i in range(nL - 1):
        b.mem(bots[i], bots[i + 1], 'wood')
    b.mem(bots[-1], top[-1], 'wood')
    for i in range(nL):
        b.mem(top[i], bots[i], 'wood')
        b.mem(bots[i], top[i + 1], 'wood')

    # ---- right approach 15.20 -> 24
    xR = 15.20
    nR = 4
    dxr = (24.0 - xR) / nR
    rtop = [b.add(xR, 0.0)] + [b.add(xR + i * dxr, 0.0) for i in range(1, nR)] + ['A3']
    rbots = [b.add(xR + (i + 0.5) * dxr, -depth) for i in range(nR)]
    for a, c in zip(rtop, rtop[1:]):
        b.mem(a, c, 'road')
    b.mem(rbots[-1], 'A4', 'wood')
    b.mem('A3', rbots[-1], 'wood')
    for i in range(nR - 1):
        b.mem(rbots[i], rbots[i + 1], 'wood')
    b.mem(rtop[0], rbots[0], 'wood')
    for i in range(nR):
        b.mem(rtop[i], rbots[i], 'wood')
        b.mem(rbots[i], rtop[i + 1], 'wood')

    # ---- center deck
    cxs = [8.98, 11.0, 13.0, 15.02]
    cnodes = [b.add(x, 0.0) for x in cxs]
    for a, c in zip(cnodes, cnodes[1:]):
        b.mem(a, c, 'road')

    # ---- underwater truss, all y <= -3.0
    # upper chord y=-3.05, lower y=-5.4, from x=1.2 to x=22.8
    ux = [1.2, 3.4, 5.6, 7.8, 9.0, 11.0, 13.0, 15.0, 16.4, 18.6, 20.8, 22.8]
    u_nodes = [b.add(x, -3.05) for x in ux]
    l_nodes = [b.add(x, -5.4) for x in ux]
    for a, c in zip(u_nodes, u_nodes[1:]):
        b.mem(a, c, 'steel')
    for a, c in zip(l_nodes, l_nodes[1:]):
        b.mem(a, c, 'steel')
    for u, l in zip(u_nodes, l_nodes):
        b.mem(u, l, 'wood')
    for i in range(len(ux) - 1):
        b.mem(u_nodes[i], l_nodes[i + 1], 'steel')
    # tie ends to anchors without entering channel (x in [9,15] and y>-2)
    b.mem('A1', u_nodes[0], 'wood')
    b.mem('A1', l_nodes[0], 'steel')
    b.mem('A4', u_nodes[-1], 'wood')
    b.mem('A4', l_nodes[-1], 'steel')
    # A0/A3 are at y=0; don't span a too-long wood member into the pit
    b.mem('A0', u_nodes[0], 'steel')
    b.mem('A3', u_nodes[-1], 'steel')

    # feet: upper chord nodes nearest each center x, hydraulics up
    # map center x to upper node index
    for cn, x in zip(cnodes, cxs):
        # find upper node with same x or nearest
        best = min(range(len(ux)), key=lambda i: abs(ux[i] - x))
        foot = u_nodes[best]
        # if x differs a lot, add a dedicated foot on the upper chord line
        if abs(ux[best] - x) > 0.3:
            foot = b.add(x, -3.05)
            # connect foot into nearest upper nodes
            b.mem(foot, u_nodes[best], 'steel')
        length = 3.05  # from y=-3.05 to y=0
        # want drop to y=-2.3: ratio = (3.05-2.3)/3.05 = 0.246, but min ratio is 0.5
        # so with foot at -3.05, ratio 0.5 gives length 1.525, top at y=-3.05+1.525=-1.525
        # THAT IS STILL INSIDE THE CHANNEL (y>-2). Need a longer hydraulic.
        # Rebuild: foot at y=-5.2, length 5.0 (max 5), ratio 0.5 -> length 2.5, top at -5.2+2.5=-2.7. Good.
        pass

    # dedicated feet at y=-5.0 under each center node, length 5.0 hydraulics (max)
    # ratio 0.5 -> length 2.5, top y = -2.5. Clear of y=-2.
    feet = []
    for cn, x in zip(cnodes, cxs):
        foot = b.add(x, -5.0)
        feet.append(foot)
        # brace foot to lower and upper chords
        best = min(range(len(ux)), key=lambda i: abs(ux[i] - x))
        if math.hypot(ux[best] - x, -5.4 - (-5.0)) >= 0.3:
            b.mem(foot, l_nodes[best], 'wood')
        if math.hypot(ux[best] - x, -3.05 - (-5.0)) <= 2.98:
            b.mem(foot, u_nodes[best], 'wood')
        else:
            b.mem(foot, l_nodes[best], 'wood')
        mat = 'hydraulic' if drop else 'steel'
        if mat == 'hydraulic':
            b.mem(foot, cn, 'hydraulic', 'D')
        else:
            b.mem(foot, cn, 'steel')

    if drop:
        b.sensors.append({'id': 'h', 'type': 'horn'})
        b.lights.append({'id': 'LL', 'x': -1.0, 'dir': 'right', 'init': 'green'})
        b.lights.append({'id': 'RL', 'x': 25.0, 'dir': 'left', 'init': 'green'})
        b.rules += [
            {'on': 'h', 'delay': 5.0, 'do': 'light', 'light': 'LL', 'state': 'red'},
            {'on': 'h', 'delay': 6.0, 'do': 'light', 'light': 'RL', 'state': 'red'},
            {'on': 'h', 'delay': 8.0, 'do': 'hyd', 'group': 'D', 'ratio': 0.5, 'speed': 8.0},
            {'on': 'h', 'delay': 16.2, 'do': 'hyd', 'group': 'D', 'ratio': 1.0, 'speed': 8.0},
            {'on': 'h', 'delay': 18.2, 'do': 'light', 'light': 'LL', 'state': 'green'},
            {'on': 'h', 'delay': 18.2, 'do': 'light', 'light': 'RL', 'state': 'green'},
        ]
    return b.design()

def check_fixed_clear(design):
    """Members that are not hydraulic should not intersect channel if they are 'fixed'.
    We only warn for members whose both ends are below -2 or outside x — report offenders that are NOT hydraulic and NOT road on the approaches.
    """
    nodes = design['nodes']
    anchors = bridge.load_level(4)['anchors']
    def xy(r):
        if isinstance(r, str):
            return anchors[int(r[1:])]
        return nodes[r]
    bad = []
    for i, m in enumerate(design['members']):
        if m[2] in ('hydraulic', 'road'):
            continue
        p, q = xy(m[0]), xy(m[1])
        if seg_hits_channel(p, q):
            bad.append((i, m[2], p, q))
    return bad

if __name__ == '__main__':
    d = build(drop=True)
    bad = check_fixed_clear(d)
    print('fixed members in channel:', len(bad))
    for item in bad[:8]:
        print(' ', item)
    lv = bridge.load_level(4)
    try:
        P = bridge.parse_design(lv, d)
        print('cost', P['cost'], P['cost_detail'])
    except bridge.DesignError as e:
        print('INV', e)
        raise SystemExit
    ok_all = True
    for p in bridge.sample_paths(lv):
        sc = bridge.load_json(p)
        res, _ = bridge.simulate(lv, P, sc)
        sm = bridge.summarize(res, P, sc)
        print('----', sc['name'], 'OK' if sm['ok'] else 'FAIL', 'peak', round(max(res.get('peak_members') or [0]), 2))
        print(sm['text'])
        if not sm['ok']:
            ok_all = False
            print('TOP', bridge.peak_report(res, P, 5))
            ev = [e for e in res['events'] if any(k in e for k in ('SHIP', 'VFAIL', 'BREAK', 'HORN', 'ACT', 'SENSOR'))][:15]
            print('EV', ev)
    if ok_all:
        save(d, 'level4_best.json')
        with open(os.path.join(SUB, 'level4.json'), 'w') as f:
            json.dump(d, f); f.write('\n')
        print('SAVED', P['cost'])
