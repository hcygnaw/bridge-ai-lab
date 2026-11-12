"""Level 5: pit springs + short deep flinging leaf pivoted at A0."""
import math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bridge
from kit import B, save

def ratio_at(F, attach, theta):
    r = math.hypot(*attach)
    a0 = math.atan2(attach[1], attach[0])
    x = r * math.cos(a0 + theta)
    y = r * math.sin(a0 + theta)
    L = math.hypot(x - F[0], y - F[1])
    L0 = math.hypot(attach[0] - F[0], attach[1] - F[1])
    return L / L0, L0


def build(depth=1.55, hyd_speed=8.0, hyd_accel=25.0, gate_x=2.2, fire_delay=0.05,
          back_delay=1.5, fire_ratio=1.5, do_fire=True):
    b = B()
    pit_x = [-9.0, -8.0, -6.0, -4.0, -2.0]
    pit = [b.add(x, 0.0) for x in pit_x]
    b.mem('A2', pit[0], 'road')
    for a, c in zip(pit, pit[1:]):
        b.mem(a, c, 'road')
    b.mem(pit[-1], 'A0', 'road')
    for x, anc in ((-8.0, 'A6'), (-6.0, 'A5'), (-4.0, 'A4'), (-2.0, 'A3')):
        b.mem(anc, pit[pit_x.index(x)], 'spring')
    b.mem('A6', pit[0], 'steel')

    xs = [2.0, 4.0]
    ys = [0.08, 0.18]
    N = [b.add(x, y) for x, y in zip(xs, ys)]
    b.mem('A0', N[0], 'road')
    b.mem(N[0], N[1], 'road')
    Bn = [b.add(x, y - depth) for x, y in zip(xs, ys)]
    b.mem(N[0], Bn[0], 'steel')
    b.mem(N[1], Bn[1], 'steel')
    b.mem(Bn[0], Bn[1], 'steel')
    b.mem(N[0], Bn[1], 'steel')
    b.mem(Bn[0], N[1], 'steel')
    b.mem('A0', Bn[0], 'steel')

    F = (0.55, -2.15)
    Fid = b.add(*F)
    b.mem('A0', Fid, 'steel')
    b.mem('A1', Fid, 'steel')
    b.mem(Fid, Bn[0], 'hydraulic', 'L')

    b.sensors.append({'id': 'go', 'type': 'gate', 'x': gate_x, 'dir': 'right'})
    if do_fire:
        b.rules.append({'on': 'go', 'delay': fire_delay, 'do': 'hyd', 'group': 'L',
                        'ratio': fire_ratio, 'speed': hyd_speed, 'accel': hyd_accel})
        b.rules.append({'on': 'go', 'delay': back_delay, 'do': 'hyd', 'group': 'L',
                        'ratio': 1.0, 'speed': 10.0, 'accel': 30.0})
    return b.design()


def debug_one(design, label):
    lv = bridge.load_level('5')
    P = bridge.parse_design(lv, design)
    print(label, 'cost', round(P['cost'], 1), P['cost_detail'])
    sc = bridge.load_json(bridge.sample_paths(lv)[0])
    res, rep = bridge.simulate(lv, P, sc, replay=True)
    print(bridge.summarize(res, P, sc)['text'])
    frames = rep['frames']
    nbridge = len(P['nodes'])
    want = [3.5, 4.5, 5.0, 5.5, 6.0, 6.5, 7.0]
    shown = set()
    for fr in frames:
        t = round(fr['t'], 1)
        if t not in want or t in shown:
            continue
        shown.add(t)
        pts = fr['p']
        def xy(i):
            return pts[2 * i], pts[2 * i + 1]
        fw = xy(nbridge + 1)
        tip = None
        for i, (x, y, fixed) in enumerate(P['nodes']):
            if not fixed and abs(x - 4.0) < 0.2 and y > 0:
                tip = xy(i)
        print(f'  t={t:.1f} front=({fw[0]:.1f},{fw[1]:.1f}) tip={tip}')


def main():
    attach = (2.0, 0.08 - 1.55)
    F = (0.55, -2.15)
    print('attach', attach)
    for deg in (0, 15, 25, 35, 45):
        ratio, L0 = ratio_at(F, attach, math.radians(deg))
        print(f'  theta={deg} ratio={ratio:.3f} buildL={L0:.2f}')

    d = build(do_fire=False)
    try:
        debug_one(d, 'STATIC')
    except bridge.DesignError as e:
        print('INVALID static', e)
        return

    configs = [
        dict(hyd_speed=7, hyd_accel=20, gate_x=1.2, fire_delay=0.25, fire_ratio=1.55, back_delay=1.8),
        dict(hyd_speed=12, hyd_accel=40, gate_x=2.4, fire_delay=0.02, fire_ratio=1.70, back_delay=1.4),
        dict(hyd_speed=5, hyd_accel=12, gate_x=0.8, fire_delay=0.45, fire_ratio=1.45, back_delay=2.0),
    ]
    for i, cfg in enumerate(configs):
        d = build(**cfg)
        save(d, f'l5leaf_{i}.json')
        try:
            debug_one(d, f'FIRE{i}')
        except bridge.DesignError as e:
            print('INVALID', i, e)


if __name__ == '__main__':
    main()
