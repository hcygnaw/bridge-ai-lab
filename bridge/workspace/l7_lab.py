"""Level 7 adversarial lab: test opponent bridges vs saboteur archetypes."""
import bridge as B, saboteur as S, math, json

lv = B.load_level('final')

def make_opp_truss(h=2.0, n=14, web_mat='wood', top_mat='steel'):
    nodes, members = [], []
    dx = 28.0 / n
    d = [len(nodes) + i for i in range(n - 1)]
    for i in range(1, n): nodes.append([round(i * dx, 4), 0.0])
    members.append(['A0', d[0], 'road'])
    for i in range(len(d) - 1): members.append([d[i], d[i + 1], 'road'])
    members.append([d[-1], 'A3', 'road'])
    t = []
    for i in range(1, n):
        nodes.append([round(i * dx, 4), h])
        t.append(len(nodes) - 1)
    members.append(['A0', t[0], top_mat])
    for i in range(len(t) - 1): members.append([t[i], t[i + 1], top_mat])
    members.append([t[-1], 'A3', top_mat])
    for i in range(len(d)):
        members.append([d[i], t[i], web_mat])
    for i in range(len(d) - 1):
        if i < len(d) // 2:
            members.append([d[i], t[i + 1], web_mat])
        else:
            members.append([t[i], d[i + 1], web_mat])
    members.append(['A1', d[0], 'steel'])
    members.append(['A4', d[-1], 'steel'])
    return {'nodes': nodes, 'members': members}

def make_opp_steel_truss(h=3.2, n=12):
    # Full all-steel Warren/Pratt truss (~25k)
    nodes, members = [], []
    dx = 28.0 / n
    d = []
    for i in range(1, n):
        nodes.append([round(i * dx, 4), 0.0])
        d.append(len(nodes) - 1)
    members.append(['A0', d[0], 'road'])
    for i in range(len(d) - 1): members.append([d[i], d[i + 1], 'road'])
    members.append([d[-1], 'A3', 'road'])
    t = []
    for i in range(n):
        nodes.append([round((i + 0.5) * dx, 4), h])
        t.append(len(nodes) - 1)
    members.append(['A0', t[0], 'steel'])
    for i in range(len(t) - 1): members.append([t[i], t[i + 1], 'steel'])
    members.append([t[-1], 'A3', 'steel'])
    for i in range(len(d)):
        members.append([d[i], t[i], 'steel'])
        members.append([d[i], t[i + 1], 'steel'])
    members.append(['A1', d[0], 'steel'])
    members.append(['A4', d[-1], 'steel'])
    return {'nodes': nodes, 'members': members}

def make_opp_arch(n=12, arch_h=3.6):
    # Under-deck parabolic steel arch from A1(0,-2) to A4(28,-2) + wood/steel spandrel
    nodes, members = [], []
    dx = 28.0 / n
    d = []
    for i in range(1, n):
        nodes.append([round(i * dx, 4), 0.0])
        d.append(len(nodes) - 1)
    members.append(['A0', d[0], 'road'])
    for i in range(len(d) - 1): members.append([d[i], d[i + 1], 'road'])
    members.append([d[-1], 'A3', 'road'])
    a = []
    for i in range(1, n):
        x = i * dx
        u = (x - 14.0) / 14.0
        y = -2.0 + arch_h * (1.0 - u * u) - 2.3  # arch below road
        # Actually put arch from -2 up to -0.6 at midspan, wait: A1=(0,-2), so peak at -0.5 -> height 1.5 too shallow.
        # Better: arch drops to -5.5 at midspan (hanging) OR rises ABOVE road (through-arch)!
        y = -2.0 - 3.0 * (1.0 - u * u)  # inverted arch / catenary
        nodes.append([round(x, 4), round(y, 4)])
        a.append(len(nodes) - 1)
    members.append(['A1', a[0], 'steel'])
    for i in range(len(a) - 1): members.append([a[i], a[i + 1], 'steel'])
    members.append([a[-1], 'A4', 'steel'])
    for i in range(len(d)):
        members.append([d[i], a[i], 'steel'])
        if i < len(d) - 1:
            if i < len(d) // 2:
                members.append([d[i], a[i + 1], 'wood' if math.hypot(dx, a[i+1]) < 3 else 'cable'])
            else:
                members.append([d[i + 1], a[i], 'cable'])
    members.append(['A0', a[0], 'steel'])
    members.append(['A3', a[-1], 'steel'])
    return {'nodes': nodes, 'members': members}

def make_opp_cable_stayed(n=12, th=6.5):
    nodes, members = [], []
    dx = 28.0 / n
    d = []
    for i in range(1, n):
        nodes.append([round(i * dx, 4), 0.0])
        d.append(len(nodes) - 1)
    members.append(['A0', d[0], 'road'])
    for i in range(len(d) - 1): members.append([d[i], d[i + 1], 'road'])
    members.append([d[-1], 'A3', 'road'])
    # Twin steel towers at x=0 and x=28 (2 segments each so L <= 3.5m)
    mL = len(nodes); nodes.append([0.0, th / 2])
    tL = len(nodes); nodes.append([0.0, th])
    mR = len(nodes); nodes.append([28.0, th / 2])
    tR = len(nodes); nodes.append([28.0, th])
    members.extend([
        ['A0', mL, 'steel'], [mL, tL, 'steel'], ['A2', tL, 'cable'], ['A2', mL, 'cable'],
        ['A3', mR, 'steel'], [mR, tR, 'steel'], ['A5', tR, 'cable'], ['A5', mR, 'cable'],
        ['A1', d[0], 'steel'], ['A4', d[-1], 'steel'],
    ])
    for i in range(len(d)):
        if i <= len(d) // 2:
            members.append([tL, d[i], 'cable'])
        if i >= len(d) // 2:
            members.append([tR, d[i], 'cable'])
    # Light under-deck stiffening truss
    b = []
    for i in range(1, n):
        nodes.append([round(i * dx, 4), -1.4])
        b.append(len(nodes) - 1)
    members.append(['A1', b[0], 'steel'])
    for i in range(len(b) - 1): members.append([b[i], b[i + 1], 'steel'])
    members.append([b[-1], 'A4', 'steel'])
    for i in range(len(d)):
        members.append([d[i], b[i], 'wood'])
        if i < len(d) - 1:
            members.append([d[i], b[i + 1], 'wood'])
    return {'nodes': nodes, 'members': members}

def make_opp_through_arch(n=14, arch_h=5.2):
    # Parabolic through-arch from A0 to A3 + hangers + lower steel tie/truss
    nodes, members = [], []
    dx = 28.0 / n
    d = []
    for i in range(1, n):
        nodes.append([round(i * dx, 4), 0.0])
        d.append(len(nodes) - 1)
    members.append(['A0', d[0], 'road'])
    for i in range(len(d) - 1): members.append([d[i], d[i + 1], 'road'])
    members.append([d[-1], 'A3', 'road'])
    a = []
    for i in range(1, n):
        x = i * dx
        u = (x - 14.0) / 14.0
        y = arch_h * (1.0 - u * u)
        nodes.append([round(x, 4), round(y, 4)])
        a.append(len(nodes) - 1)
    members.append(['A0', a[0], 'steel'])
    for i in range(len(a) - 1): members.append([a[i], a[i + 1], 'steel'])
    members.append([a[-1], 'A3', 'steel'])
    for i in range(len(d)):
        members.append([a[i], d[i], 'cable'])
    # Diagonal steel bracing between arch & deck near ends, cables in middle
    for i in range(len(d) - 1):
        if math.hypot(nodes[a[i+1]][0]-nodes[d[i]][0], nodes[a[i+1]][1]) < 4.4:
            members.append([d[i], a[i+1], 'cable'])
        if math.hypot(nodes[a[i]][0]-nodes[d[i+1]][0], nodes[a[i]][1]) < 4.4:
            members.append([d[i+1], a[i], 'cable'])
    members.append(['A1', d[0], 'steel'])
    members.append(['A4', d[-1], 'steel'])
    # Twin arch rib!
    a2 = []
    for i in range(1, n):
        x = i * dx
        u = (x - 14.0) / 14.0
        y = arch_h * (1.0 - u * u) + 1.2
        nodes.append([round(x, 4), round(y, 4)])
        a2.append(len(nodes) - 1)
    members.append(['A0', a2[0], 'steel'])
    for i in range(len(a2) - 1): members.append([a2[i], a2[i + 1], 'steel'])
    members.append([a2[-1], 'A3', 'steel'])
    for i in range(len(a)):
        members.append([a[i], a2[i], 'wood'])
        if i < len(a) - 1:
            members.append([a2[i], a[i + 1], 'wood'])
    return {'nodes': nodes, 'members': members}

def make_opp_humped_arch(n=14, road_h=2.0):
    # Arched road deck (y rises to +2.0m at midspan!)
    nodes, members = [], []
    dx = 28.0 / n
    d = []
    for i in range(1, n):
        x = i * dx
        u = (x - 14.0) / 14.0
        y = road_h * (1.0 - u * u)
        nodes.append([round(x, 4), round(y, 4)])
        d.append(len(nodes) - 1)
    members.append(['A0', d[0], 'road'])
    for i in range(len(d) - 1): members.append([d[i], d[i + 1], 'road'])
    members.append([d[-1], 'A3', 'road'])
    b = []
    for i in range(1, n):
        x = i * dx
        u = (x - 14.0) / 14.0
        y = -2.0 + (road_h + 1.0) * (1.0 - u * u)
        nodes.append([round(x, 4), round(y, 4)])
        b.append(len(nodes) - 1)
    members.append(['A1', b[0], 'steel'])
    for i in range(len(b) - 1): members.append([b[i], b[i + 1], 'steel'])
    members.append([b[-1], 'A4', 'steel'])
    for i in range(len(d)):
        members.append([d[i], b[i], 'steel'])
        if i < len(d) - 1:
            members.append([d[i], b[i + 1], 'steel'])
    return {'nodes': nodes, 'members': members}

def get_opponents():
    specs = [
        ('opp1_wood_truss', make_opp_truss()),
        ('opp2_steel_warren', make_opp_steel_truss()),
        ('opp3_cable_stayed', make_opp_cable_stayed()),
        ('opp4_double_arch', make_opp_through_arch()),
        ('opp5_humped_arch', make_opp_humped_arch()),
    ]
    out = []
    for name, br in specs:
        try:
            P = B.parse_design(lv, br)
            res, _ = B.simulate(lv, P, S.convoy_scenario(lv))
            pk = max(res.get('peaks', [0]))
            print(f'[OPP {name}] cost={P["cost"]:.0f} base_ok={res["ok"]} peak={pk*100:.1f}%')
            if res['ok']:
                out.append((name, P))
        except Exception as e:
            print(f'[OPP {name}] ERR: {e}')
    return out

if __name__ == '__main__':
    get_opponents()
