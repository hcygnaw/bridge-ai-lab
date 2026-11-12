"""Level 5 last attempt: sway-braced spring pit + rigid sled."""
import math, sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bridge
from kit import B, save, SUB

ANG = math.radians(28.0)
D = (math.cos(ANG), math.sin(ANG))


def build(hyd_L=4.0, light_x=6.8, fire_delay=1.2, back_delay=2.1, hyd_accel=32.0):
    b = B()
    xs = [-9.0, -8.0, -6.0, -4.0, -2.05]
    pit = [b.add(x, 0.0) for x in xs]
    b.mem('A2', pit[0], 'road')
    for a, c in zip(pit, pit[1:]):
        b.mem(a, c, 'road')
    for x, anc in ((-8.0, 'A6'), (-6.0, 'A5'), (-4.0, 'A4')):
        b.mem(anc, pit[xs.index(x)], 'spring')
    # end post slightly off A3 x so the sled gap can be 0.15 m
    b.mem('A3', pit[-1], 'steel')  # (-2,-4) to (-2.05,0) ~ 4.00
    # X that catches both sway directions
    b.mem('A6', pit[2], 'steel')   # (-8,-4)-(-6,0)
    b.mem('A5', pit[1], 'steel')   # (-6,-4)-(-8,0)

    # rigid sled, 0.15 m gap after x=-2.05
    x0, y, L = -1.90, 0.04, 2.35
    R0, R1 = b.add(x0, y), b.add(x0 + L, y)
    road_i = len(b.members)
    b.mem(R0, R1, 'road')
    bump = b.add(x0 + 0.32, y + 0.16)
    b.mem(R0, bump, 'road')
    B0 = b.add(round(x0 - hyd_L * D[0], 3), round(y - hyd_L * D[1], 3))
    B1 = b.add(round(x0 + L - hyd_L * D[0], 3), round(y - hyd_L * D[1], 3))
    b.mem(B0, R0, 'hydraulic', 'P')
    b.mem(B1, R1, 'hydraulic', 'P')
    b.mem('A5', B0, 'steel')
    b.mem('A4', B0, 'steel')
    b.mem('A4', B1, 'steel')
    b.mem('A3', B1, 'steel')

    b.lights.append({'id': 'S', 'x': light_x, 'dir': 'right', 'init': 'red'})
    b.sensors.append({'id': 'p', 'type': 'plate', 'member': road_i})
    b.rules += [
        {'on': 'p', 'delay': fire_delay, 'do': 'light', 'light': 'S', 'state': 'green'},
        {'on': 'p', 'delay': fire_delay, 'do': 'hyd', 'group': 'P', 'ratio': 2.0, 'speed': 15.0, 'accel': hyd_accel},
        {'on': 'p', 'delay': back_delay, 'do': 'hyd', 'group': 'P', 'ratio': 1.0, 'speed': 15.0, 'accel': 50.0},
        {'on': 'p', 'delay': back_delay + 0.1, 'do': 'light', 'light': 'S', 'state': 'red'},
    ]
    return b.design()


def run(d, label):
    lv = bridge.load_level('5')
    try:
        P = bridge.parse_design(lv, d)
    except bridge.DesignError as e:
        print(label, 'INV', str(e)[:400])
        return False
    print(label, 'cost', round(P['cost'], 1))
    ok = True
    for sp in bridge.sample_paths(lv):
        sc = bridge.load_json(sp)
        res, rep = bridge.simulate(lv, P, sc, replay=True)
        print(sc['name'], 'ok', res.get('ok'), 'brk', res.get('broken'))
        print(bridge.summarize(res, P, sc)['text'])
        if not res.get('ok'):
            ok = False
            nb = len(P['nodes'])
            shown = set()
            for fr in rep['frames']:
                t = round(fr['t'], 1)
                if t < 3.5 or t > 8 or t in shown or abs(t * 2 - round(t * 2)) > 0.05:
                    continue
                shown.add(t)
                pts = fr['p']
                fw = pts[2 * (nb + 1)], pts[2 * (nb + 1) + 1]
                print(f'  t={t:.1f} front=({fw[0]:.1f},{fw[1]:.1f})')
    return ok


if __name__ == '__main__':
    d = build()
    save(d, 'l5final.json')
    if run(d, 'final'):
        with open(os.path.join(SUB, 'level5.json'), 'w') as f:
            json.dump(d, f, indent=1)
            f.write('\n')
        print('SAVED level5')
