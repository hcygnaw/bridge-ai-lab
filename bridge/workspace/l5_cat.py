"""Level 5 catapult: pit springs + rising ramp + hydraulic wheel pusher."""
import math, os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bridge
from kit import B, save, report

def build(theta_deg=28.0, ramp_len=8.0, seg=2.0, hyd_L=4.8, hyd_speed=14.0, hyd_accel=40.0,
          gate_x=0.4, fire_delay=0.0, back_delay=1.4, chock_s=-1.2, base_s=-6.0):
    b = B()
    th = math.radians(theta_deg)
    d = (math.cos(th), math.sin(th))
    p = (-math.sin(th), math.cos(th))  # above ramp

    def pt(s, off=0.0, origin=(0.6, 0.08)):
        return (origin[0] + s * d[0] + off * p[0], origin[1] + s * d[1] + off * p[1])

    # --- pit deck at y=0, springs exactly 4 m ---
    pit_x = [-9.0, -8.0, -6.0, -4.0, -2.0]
    pit = [b.add(x, 0.0) for x in pit_x]
    b.mem('A2', pit[0], 'road')
    for a, c in zip(pit, pit[1:]):
        b.mem(a, c, 'road')
    b.mem(pit[-1], 'A0', 'road')
    spring_at = {-8.0: 'A6', -6.0: 'A5', -4.0: 'A4', -2.0: 'A3'}
    for x, anc in spring_at.items():
        b.mem(anc, pit[pit_x.index(x)], 'spring')
    # support the -9 node and brace against sway
    b.mem('A6', pit[0], 'steel')
    b.mem('A6', pit[2], 'steel')  # -8,-4 to -6,0
    b.mem('A5', pit[3], 'steel')
    b.mem('A4', pit[4], 'steel')

    # --- ramp ---
    nseg = int(round(ramp_len / seg))
    ramp = [b.add(*pt(i * seg)) for i in range(nseg + 1)]
    b.mem('A0', ramp[0], 'road')
    road_ids = []
    for i in range(nseg):
        before = len(b.members)
        b.mem(ramp[i], ramp[i + 1], 'road')
        road_ids.append(before)
    # shallow truss under the ramp
    low = [b.add(*pt(i * seg, -1.1)) for i in range(nseg + 1)]
    for i in range(nseg + 1):
        b.mem(ramp[i], low[i], 'steel')
    for i in range(nseg):
        b.mem(low[i], low[i + 1], 'steel')
        b.mem(ramp[i], low[i + 1], 'steel')
    # supports from anchors / a mast
    mast = b.add(1.2, -1.2)
    b.mem('A1', mast, 'steel')
    b.mem('A0', mast, 'steel')
    b.mem(mast, low[0], 'steel')
    b.mem(mast, low[1], 'steel')
    b.mem('A1', low[0], 'steel')
    # relay deeper in the gorge if needed
    relay = b.add(4.0, -1.5)
    b.mem(mast, relay, 'steel')
    b.mem(relay, low[min(2, nseg)], 'steel')
    if nseg >= 3:
        b.mem(relay, low[3], 'steel')
    if nseg >= 4:
        relay2 = b.add(6.5, -0.4)
        b.mem(relay, relay2, 'steel')
        b.mem(relay2, low[4], 'steel')
        b.mem(relay2, ramp[4], 'steel')

    # --- pusher chock: two nodes, road between, two parallel hydraulics ---
    # build length must equal distance at construction (ratio 1)
    c_lo = b.add(*pt(chock_s, 0.16))
    c_hi = b.add(*pt(chock_s, 0.40))
    b.mem(c_lo, c_hi, 'road')
    base_lo = b.add(*pt(base_s, 0.16))
    base_hi = b.add(*pt(base_s, 0.40))
    b.mem(base_lo, base_hi, 'steel')
    b.mem(base_lo, c_lo, 'hydraulic', 'P')
    b.mem(base_hi, c_hi, 'hydraulic', 'P')
    # fix bases
    b.mem('A5', base_lo, 'steel')
    b.mem('A4', base_lo, 'steel')
    b.mem('A5', base_hi, 'steel')
    b.mem('A4', base_hi, 'steel')
    b.mem('A3', base_lo, 'steel')

    b.sensors.append({'id': 'go', 'type': 'gate', 'x': gate_x, 'dir': 'right'})
    b.sensors.append({'id': 'st', 'type': 'start'})
    b.rules.append({'on': 'st', 'delay': 0.0, 'do': 'hyd', 'group': 'P', 'ratio': 0.5,
                    'speed': 15.0, 'accel': 80.0})
    b.rules.append({'on': 'go', 'delay': fire_delay, 'do': 'hyd', 'group': 'P', 'ratio': 2.0,
                    'speed': hyd_speed, 'accel': hyd_accel})
    b.rules.append({'on': 'go', 'delay': back_delay, 'do': 'hyd', 'group': 'P', 'ratio': 0.5,
                    'speed': 15.0, 'accel': 60.0})
    return b.design()


def main():
    lv = bridge.load_level('5')
    variants = [
        dict(theta_deg=28, ramp_len=8, hyd_speed=14, hyd_accel=35, gate_x=0.3, fire_delay=0.05, back_delay=1.6),
        dict(theta_deg=32, ramp_len=8, hyd_speed=15, hyd_accel=45, gate_x=0.2, fire_delay=0.0, back_delay=1.5),
        dict(theta_deg=25, ramp_len=10, seg=2.0, hyd_speed=15, hyd_accel=30, gate_x=0.5, fire_delay=0.1, back_delay=1.8),
    ]
    for i, kw in enumerate(variants):
        d = build(**kw)
        print('=' * 60)
        print('VAR', i, kw)
        try:
            P = bridge.parse_design(lv, d)
        except bridge.DesignError as e:
            print('INVALID', e)
            continue
        print('cost', P['cost'], P['cost_detail'])
        if P['cost'] > 10000:
            print('OVER BUDGET')
        save(d, f'l5_v{i}.json')
        report('5', d, f'v{i}')


if __name__ == '__main__':
    main()
