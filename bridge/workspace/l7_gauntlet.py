import math, json, bridge as B, saboteur as S

lv = B.load_level('final')

def check_bridge(name, d):
    P = B.parse_design(lv, d)
    res, _ = B.simulate(lv, P, {'vehicles': lv['convoy']})
    ok = all(v['status'] == 2 for v in res['vehicles'])
    print(f'{name:22s}: ok={str(ok):5s} cost={P["cost"]:8.2f}/26000 brk={res["broken"]:2d} v_ok={sum(v["status"]==2 for v in res["vehicles"])}/{len(res["vehicles"])}')
    return P, ok

def make_deck(N, y_fn=None):
    dx = 28.0 / N
    nodes = []
    deck = ['A0']
    for i in range(1, N):
        x = round(i * dx, 3)
        y = round(y_fn(x), 3) if y_fn else 0.0
        deck.append(len(nodes))
        nodes.append([x, y])
    deck.append('A3')
    members = [[deck[i], deck[i+1], 'road'] for i in range(N)]
    return nodes, members, deck

def b1_steel_warren():
    N = 12
    nodes, members, deck = make_deck(N)
    dx = 28.0 / N
    top = []
    for i in range(N):
        top.append(len(nodes))
        nodes.append([round((i+0.5)*dx, 3), 3.4])
    for i in range(N):
        members.append([deck[i], top[i], 'steel'])
        members.append([deck[i+1], top[i], 'steel'])
    for i in range(N-1):
        members.append([top[i], top[i+1], 'steel'])
    members += [['A2', top[0], 'cable'], ['A5', top[-1], 'cable'],
                ['A1', deck[1], 'steel'], ['A4', deck[N-1], 'steel']]
    return {'nodes': nodes, 'members': members}

def b2_cable_stayed():
    # A-frame braced twin pylons + fan cables + short-segment A-frame towers (no buckling!)
    N = 12
    nodes, members, deck = make_deck(N)
    # Braced towers: base A0=(0,0), A2=(-5,0), mid-brace (-2.0, 3.0), (0.0, 3.0), top (-1.0, 6.5)
    tL1 = len(nodes); nodes.append([0.0, 3.0])
    tLb = len(nodes); nodes.append([-2.2, 3.0])
    tL2 = len(nodes); nodes.append([-0.8, 6.5])
    tR1 = len(nodes); nodes.append([28.0, 3.0])
    tRb = len(nodes); nodes.append([30.2, 3.0])
    tR2 = len(nodes); nodes.append([28.8, 6.5])
    members += [
        ['A0', tL1, 'steel'], ['A2', tLb, 'steel'], [tL1, tLb, 'steel'], ['A0', tLb, 'steel'],
        [tL1, tL2, 'steel'], [tLb, tL2, 'steel'], ['A2', tL2, 'cable'],
        ['A3', tR1, 'steel'], ['A5', tRb, 'steel'], [tR1, tRb, 'steel'], ['A3', tRb, 'steel'],
        [tR1, tR2, 'steel'], [tRb, tR2, 'steel'], ['A5', tR2, 'cable'],
        ['A1', deck[1], 'steel'], ['A4', deck[N-1], 'steel'],
    ]
    for i in range(1, 7):
        members.append([tL2 if i >= 3 else tL1, deck[i], 'cable'])
    for i in range(6, N):
        members.append([tR2 if i <= 9 else tR1, deck[i], 'cable'])
    # Under-deck shallow wood-cable stiffening? Just cables to A1/A4 + light steel bottom chord at midspan
    return {'nodes': nodes, 'members': members}

def b3_suspension():
    # Classic suspension bridge with braced pylons + parabolic main cable + vertical cable hangers + road
    N = 12
    nodes, members, deck = make_deck(N)
    dx = 28.0 / N
    # Braced pylons to y=7.0
    tL1 = len(nodes); nodes.append([0.0, 3.5]); tLb = len(nodes); nodes.append([-2.3, 3.5]); tL2 = len(nodes); nodes.append([0.0, 7.0])
    tR1 = len(nodes); nodes.append([28.0, 3.5]); tRb = len(nodes); nodes.append([30.3, 3.5]); tR2 = len(nodes); nodes.append([28.0, 7.0])
    members += [
        ['A0', tL1, 'steel'], ['A2', tLb, 'steel'], [tL1, tLb, 'steel'], ['A0', tLb, 'steel'],
        [tL1, tL2, 'steel'], [tLb, tL2, 'steel'], ['A2', tL2, 'cable'],
        ['A3', tR1, 'steel'], ['A5', tRb, 'steel'], [tR1, tRb, 'steel'], ['A3', tRb, 'steel'],
        [tR1, tR2, 'steel'], [tRb, tR2, 'steel'], ['A5', tR2, 'cable'],
    ]
    # Parabolic suspension cable from tL2=(0,7) sagging to (14, 1.8) to tR2=(28,7)
    cab = []
    for i in range(1, N):
        x = i * dx
        s = (x - 14.0) / 14.0
        y = round(1.8 + 5.2 * s * s, 3)
        cab.append(len(nodes))
        nodes.append([round(x, 3), y])
    members += [[tL2, cab[0], 'cable'], [tR2, cab[-1], 'cable']]
    for i in range(len(cab)):
        members.append([deck[i+1], cab[i], 'cable'])
        if i + 1 < len(cab):
            members.append([cab[i], cab[i+1], 'cable'])
    # Light under-deck wood truss for live-load distribution
    bot = []
    for i in range(1, N):
        bot.append(len(nodes))
        nodes.append([round(i*dx, 3), -1.6])
    members += [['A1', bot[0], 'steel'], ['A0', bot[0], 'wood'], ['A4', bot[-1], 'steel'], ['A3', bot[-1], 'wood']]
    for i in range(len(bot)):
        members.append([deck[i+1], bot[i], 'wood'])
        if i + 1 < len(bot):
            members.append([bot[i], bot[i+1], 'wood'])
            members.append([deck[i+1], bot[i+1], 'wood'])
    return {'nodes': nodes, 'members': members}

def b4_underslung_arch():
    N = 12
    nodes, members, deck = make_deck(N)
    dx = 28.0 / N
    arch = []
    for i in range(1, N):
        x = i * dx
        s = (x - 14.0) / 14.0
        y = round(-2.0 - 2.6 * (1.0 - s*s), 3)
        arch.append(len(nodes))
        nodes.append([round(x, 3), y])
    members += [['A1', arch[0], 'steel'], ['A0', arch[0], 'steel'], ['A4', arch[-1], 'steel'], ['A3', arch[-1], 'steel']]
    for i in range(len(arch)):
        members.append([deck[i+1], arch[i], 'steel'])
        if i + 1 < len(arch):
            members.append([arch[i], arch[i+1], 'steel'])
            if i < len(arch)//2:
                members.append([deck[i+2], arch[i], 'steel'])
            else:
                members.append([deck[i+1], arch[i+1], 'steel'])
    return {'nodes': nodes, 'members': members}

def b5_humped_arch():
    # Humped parabolic deck + deep underslung steel truss (total depth 4.2m at midspan!)
    N = 12
    nodes, members, deck = make_deck(N, y_fn=lambda x: 0.9 * math.sin(math.pi * x / 28.0))
    dx = 28.0 / N
    bot = []
    for i in range(1, N):
        x = i * dx
        s = (x - 14.0) / 14.0
        y = round(-2.0 - 2.2 * (1.0 - s*s), 3)
        bot.append(len(nodes))
        nodes.append([round(x, 3), y])
    members += [['A1', bot[0], 'steel'], ['A0', bot[0], 'steel'], ['A4', bot[-1], 'steel'], ['A3', bot[-1], 'steel']]
    for i in range(len(bot)):
        members.append([deck[i+1], bot[i], 'steel'])
        if i + 1 < len(bot):
            members.append([bot[i], bot[i+1], 'steel'])
            if i < len(bot)//2:
                members.append([deck[i+2], bot[i], 'steel'])
            else:
                members.append([deck[i+1], bot[i+1], 'steel'])
    return {'nodes': nodes, 'members': members}

def b6_overhead_arch():
    # Overhead parabolic steel Warren arch-truss (short panels, all-steel arch, steel diagonals -> ~24.8k!)
    N = 12
    nodes, members, deck = make_deck(N)
    dx = 28.0 / N
    top = []
    for i in range(N):
        x = (i + 0.5) * dx
        s = (x - 14.0) / 14.0
        y = round(2.2 + 1.6 * (1.0 - s*s), 3)
        top.append(len(nodes))
        nodes.append([round(x, 3), y])
    for i in range(N):
        members.append([deck[i], top[i], 'steel'])
        members.append([deck[i+1], top[i], 'steel'])
    for i in range(N-1):
        members.append([top[i], top[i+1], 'steel'])
    members += [['A2', top[0], 'cable'], ['A5', top[-1], 'cable'],
                ['A1', deck[1], 'steel'], ['A4', deck[N-1], 'steel']]
    return {'nodes': nodes, 'members': members}

def b7_spring_arch():
    # Underslung steel arch + SPRING vertical hangers + steel/cable diagonals (~25.5k!)
    N = 12
    nodes, members, deck = make_deck(N)
    dx = 28.0 / N
    arch = []
    for i in range(1, N):
        x = i * dx
        s = (x - 14.0) / 14.0
        y = round(-2.0 - 1.8 * (1.0 - s*s), 3)
        arch.append(len(nodes))
        nodes.append([round(x, 3), y])
    members += [['A1', arch[0], 'steel'], ['A0', arch[0], 'steel'], ['A4', arch[-1], 'steel'], ['A3', arch[-1], 'steel']]
    for i in range(len(arch)):
        members.append([deck[i+1], arch[i], 'spring'])
        if i + 1 < len(arch):
            members.append([arch[i], arch[i+1], 'steel'])
            if i < len(arch)//2:
                members.append([deck[i+2], arch[i], 'steel'])
            else:
                members.append([deck[i+1], arch[i+1], 'steel'])
    return {'nodes': nodes, 'members': members}

BRIDGES = [
    ('b1_steel_warren', b1_steel_warren),
    ('b2_cable_stayed', b2_cable_stayed),
    ('b3_suspension', b3_suspension),
    ('b4_underslung_arch', b4_underslung_arch),
    ('b5_humped_arch', b5_humped_arch),
    ('b6_overhead_arch', b6_overhead_arch),
    ('b7_spring_arch', b7_spring_arch),
]

if __name__ == '__main__':
    for name, fn in BRIDGES:
        try:
            check_bridge(name, fn())
        except Exception as e:
            print(f'{name:22s}: ERR {e}')
