"""Level 5 arch sled. Two parallel 30-degree hydraulics, arch deck long enough to stop on."""
import math, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bridge
from kit import B, save

ANG = math.radians(30.0)
DIR = (math.cos(ANG), math.sin(ANG))


def build(hyd_L=4.3, light_x=7.4, fire_delay=1.45, back_delay=2.3,
          hyd_speed=15.0, hyd_accel=28.0, bump_h=0.12, x0=-1.82, span=2.2, rise=0.42):
    b = B()
    pit_x = [-9.0, -8.0, -6.0, -4.0, -2.0]
    pit = [b.add(x, 0.0) for x in pit_x]
    b.mem('A2', pit[0], 'road')
    for a, c in zip(pit, pit[1:]):
        b.mem(a, c, 'road')
    # deck ends at x=-2; sled starts just after, small gap
    for x, anc in ((-8.0, 'A6'), (-6.0, 'A5'), (-4.0, 'A4'), (-2.0, 'A3')):
        b.mem(anc, pit[pit_x.index(x)], 'spring')
    # one X in the middle bay — cables only catch sway one way each
    b.mem('A5', pit[3], 'cable')
    b.mem('A4', pit[2], 'cable')

    y0 = 0.06
    xs = [x0, x0 + span, x0 + 2 * span]
    ys = [y0, y0 + rise, y0]
    R = [b.add(x, y) for x, y in zip(xs, ys)]
    sled_road = len(b.members)
    b.mem(R[0], R[1], 'road')
    b.mem(R[1], R[2], 'road')
    if bump_h > 0:
        bump = b.add(x0 + 0.36, y0 + bump_h)
        b.mem(R[0], bump, 'road')
        b.mem(bump, R[1], 'cable')

    bases = []
    for x, y in ((xs[0], ys[0]), (xs[2], ys[2])):
        bases.append(b.add(round(x - hyd_L * DIR[0], 4), round(y - hyd_L * DIR[1], 4)))
    b.mem(bases[0], R[0], 'hydraulic', 'P')
    b.mem(bases[1], R[2], 'hydraulic', 'P')
    # short braces down to floor anchors
    # only short braces — the long A6 link buckled
    b.mem('A5', bases[0], 'steel')
    b.mem('A4', bases[0], 'steel')
    b.mem('A4', bases[1], 'steel')
    b.mem('A3', bases[1], 'steel')

    b.lights.append({'id': 'S', 'x': light_x, 'dir': 'right', 'init': 'red'})
    b.sensors.append({'id': 'p', 'type': 'plate', 'member': sled_road})
    b.rules.append({'on': 'p', 'delay': fire_delay, 'do': 'light', 'light': 'S', 'state': 'green'})
    b.rules.append({'on': 'p', 'delay': fire_delay, 'do': 'hyd', 'group': 'P',
                    'ratio': 2.0, 'speed': hyd_speed, 'accel': hyd_accel})
    b.rules.append({'on': 'p', 'delay': back_delay, 'do': 'hyd', 'group': 'P',
                    'ratio': 1.0, 'speed': 15.0, 'accel': 60.0})
    b.rules.append({'on': 'p', 'delay': back_delay + 0.12, 'do': 'light', 'light': 'S', 'state': 'red'})
    return b.design()


def debug(design, label, sample=0):
    lv = bridge.load_level('5')
    try:
        P = bridge.parse_design(lv, design)
    except bridge.DesignError as e:
        print(label, 'INVALID', e)
        return None
    print(label, 'cost', round(P['cost'], 1), 'budget left', round(10000 - P['cost'], 1))
    sc = bridge.load_json(bridge.sample_paths(lv)[sample])
    res, rep = bridge.simulate(lv, P, sc, replay=True)
    print(bridge.summarize(res, P, sc)['text'])
    nb = len(P['nodes'])
    shown = set()
    for fr in rep['frames']:
        t = round(fr['t'], 1)
        if t < 3.6 or t > 10 or t in shown:
            continue
        if abs(t * 2 - round(t * 2)) > 0.06:
            continue
        shown.add(t)
        pts = fr['p']
        rw = pts[2 * nb], pts[2 * nb + 1]
        fw = pts[2 * (nb + 1)], pts[2 * (nb + 1) + 1]
        print(f'  t={t:.1f} rear=({rw[0]:.1f},{rw[1]:.1f}) front=({fw[0]:.1f},{fw[1]:.1f})')
    return res


if __name__ == '__main__':
    for i, kw in enumerate((
        dict(bump_h=0.12, fire_delay=1.35, light_x=7.2),
        dict(bump_h=0.18, fire_delay=1.5, light_x=7.6, hyd_accel=22),
    )):
        d = build(**kw)
        save(d, f'l5sled_{i}.json')
        debug(d, f'v{i} {kw}', 0)
