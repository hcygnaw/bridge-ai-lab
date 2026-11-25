import math, json, bridge as B, saboteur as S

lv = B.load_level('final')

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

def f1_subdivided_arch(N=12, y_mid_arch=-4.2):
    # Underslung steel arch with mid-height horizontal bracing nodes on the deep central struts so NO steel bar > 2.6m!
    nodes, members, deck = make_deck(N)
    dx = 28.0 / N
    arch = []
    for i in range(1, N):
        x = i * dx
        s = (x - 14.0) / 14.0
        y = round(-2.0 + (y_mid_arch + 2.0) * (1.0 - s*s), 3)
        arch.append(len(nodes))
        nodes.append([round(x, 3), y])
    members += [['A1', arch[0], 'steel'], ['A0', arch[0], 'steel'], ['A4', arch[-1], 'steel'], ['A3', arch[-1], 'steel']]
    # Mid-height bracing nodes for interior verticals (i=2..8 where height > 2.8m)
    mids = {}
    for i in range(len(arch)):
        ay = nodes[arch[i]][1]
        if abs(ay) > 2.8:
            mid = len(nodes)
            nodes.append([nodes[arch[i]][0], round(ay * 0.5, 3)])
            mids[i] = mid
            members += [[deck[i+1], mid, 'steel'], [mid, arch[i], 'steel']]
        else:
            members.append([deck[i+1], arch[i], 'steel'])
    # Connect horizontal mid-braces + arch chord + diagonals (all short <= 2.9m!)
    for i in range(len(arch) - 1):
        members.append([arch[i], arch[i+1], 'steel'])
        if i in mids and (i+1) in mids:
            members.append([mids[i], mids[i+1], 'steel'])
            if i < len(arch)//2:
                members.append([deck[i+2], mids[i], 'steel'])
                members.append([mids[i+1], arch[i], 'steel'])
            else:
                members.append([deck[i+1], mids[i+1], 'steel'])
                members.append([mids[i], arch[i+1], 'steel'])
        elif i in mids:
            members.append([mids[i], arch[i+1], 'steel'])
            members.append([deck[i+1], arch[i+1], 'steel'])
        elif (i+1) in mids:
            members.append([arch[i], mids[i+1], 'steel'])
            members.append([deck[i+2], arch[i], 'steel'])
        else:
            if i < len(arch)//2:
                members.append([deck[i+2], arch[i], 'steel'])
            else:
                members.append([deck[i+1], arch[i+1], 'steel'])
    return {'nodes': nodes, 'members': members}

def f2_short_truss_both(N=12, y_top=2.2, y_bot=-2.0):
    # Double-layer short-member steel truss: BOTH above (y=+2.2) AND below (y=-2.0)! Every member <= 2.6m!
    # Wait: total depth 4.2m, ALL steel <= 2.5m -> maxC > 125 kN everywhere!
    nodes, members, deck = make_deck(N)
    dx = 28.0 / N
    top = []
    for i in range(N):
        top.append(len(nodes))
        nodes.append([round((i+0.5)*dx, 3), y_top])
    for i in range(N):
        members.append([deck[i], top[i], 'steel'])
        members.append([deck[i+1], top[i], 'steel'])
    for i in range(N-1):
        members.append([top[i], top[i+1], 'steel'])
    # Under-deck parallel chord anchored directly to A1, A4 (pure tension/compression relief for deck!)
    bot = []
    for i in range(1, N):
        bot.append(len(nodes))
        nodes.append([round(i*dx, 3), y_bot])
    members += [['A1', bot[0], 'steel'], ['A4', bot[-1], 'steel'],
                ['A2', top[0], 'cable'], ['A5', top[-1], 'cable']]
    for i in range(len(bot)):
        members.append([deck[i+1], bot[i], 'wood'])
        if i + 1 < len(bot):
            members.append([bot[i], bot[i+1], 'steel'])
    return {'nodes': nodes, 'members': members}

def f3_lenticular_steel(N=12, h_top=2.3, h_bot=2.5):
    # Lenticular double-arch: upper steel parabolic arch + lower steel parabolic arch + backstays to A2/A5!
    nodes, members, deck = make_deck(N)
    dx = 28.0 / N
    top, bot = [], []
    for i in range(1, N):
        x = i * dx
        s = (x - 14.0) / 14.0
        yt = round(0.8 + h_top * (1.0 - s*s), 3)
        yb = round(-1.8 - h_bot * (1.0 - s*s) * 0.5, 3)
        top.append(len(nodes)); nodes.append([round(x, 3), yt])
        bot.append(len(nodes)); nodes.append([round(x, 3), yb])
    members += [
        ['A0', top[0], 'steel'], ['A3', top[-1], 'steel'],
        ['A2', top[0], 'cable'], ['A5', top[-1], 'cable'],
        ['A1', bot[0], 'steel'], ['A0', bot[0], 'steel'],
        ['A4', bot[-1], 'steel'], ['A3', bot[-1], 'steel'],
    ]
    for i in range(len(top)):
        members.append([deck[i+1], top[i], 'cable' if 2 <= i <= 8 else 'steel'])
        members.append([deck[i+1], bot[i], 'steel' if i in (0,1,2,8,9,10) else 'wood'])
        if i + 1 < len(top):
            members.append([top[i], top[i+1], 'steel'])
            members.append([bot[i], bot[i+1], 'steel'])
            if i < len(top)//2:
                members.append([deck[i+2], top[i], 'cable'])
                members.append([deck[i+2], bot[i], 'steel'])
            else:
                members.append([deck[i+1], top[i+1], 'cable'])
                members.append([deck[i+1], bot[i+1], 'steel'])
    return {'nodes': nodes, 'members': members}

def f4_heavy_cantilever_arch(N=12):
    # Backstayed cantilever + deep underslung steel arch utilizing ALL 6 anchors A0..A5!
    nodes, members, deck = make_deck(N)
    dx = 28.0 / N
    # Short-member braced backstay towers at A0/A2 and A3/A5!
    tL = len(nodes); nodes.append([0.0, 2.6])
    tR = len(nodes); nodes.append([28.0, 2.6])
    members += [
        ['A0', tL, 'steel'], ['A2', tL, 'cable'], ['A3', tR, 'steel'], ['A5', tR, 'cable'],
        [tL, deck[2], 'cable'], [tL, deck[4], 'cable'], [tL, deck[6], 'cable'],
        [tR, deck[10], 'cable'], [tR, deck[8], 'cable'], [tR, deck[6], 'cable'],
    ]
    # Deep short-member underslung steel arch (y = -2.0 -> -3.6m, max vertical = 3.6m)
    arch = []
    for i in range(1, N):
        x = i * dx
        s = (x - 14.0) / 14.0
        y = round(-2.0 - 1.5 * (1.0 - s*s), 3)
        arch.append(len(nodes)); nodes.append([round(x, 3), y])
    members += [['A1', arch[0], 'steel'], ['A0', arch[0], 'steel'], ['A4', arch[-1], 'steel'], ['A3', arch[-1], 'steel']]
    for i in range(len(arch)):
        members.append([deck[i+1], arch[i], 'steel'])
        if i + 1 < len(arch):
            members.append([arch[i], arch[i+1], 'steel'])
            # X-brace EVERY bay with steel + cable!
            if i < len(arch)//2:
                members.append([deck[i+2], arch[i], 'steel'])
                members.append([deck[i+1], arch[i+1], 'cable'])
            else:
                members.append([deck[i+1], arch[i+1], 'steel'])
                members.append([deck[i+2], arch[i], 'cable'])
    return {'nodes': nodes, 'members': members}

def f5_xbraced_warren_fortress(N=12):
    # Overhead steel Warren truss (y=2.8m, ALL bars <= 3.0m -> ZERO buckling!) + backstays + under-deck steel tie!
    nodes, members, deck = make_deck(N)
    dx = 28.0 / N
    top = []
    for i in range(N):
        x = (i + 0.5) * dx
        s = (x - 14.0) / 14.0
        y = round(2.5 + 0.6 * (1.0 - s*s), 3)
        top.append(len(nodes)); nodes.append([round(x, 3), y])
    for i in range(N):
        members.append([deck[i], top[i], 'steel'])
        members.append([deck[i+1], top[i], 'steel'])
    for i in range(N-1):
        members.append([top[i], top[i+1], 'steel'])
    # Anchor braces A1, A4 + A2, A5 + double-height cables from top[0] & top[-1] to midspan!
    members += [
        ['A1', deck[1], 'steel'], ['A1', deck[2], 'steel'],
        ['A4', deck[N-1], 'steel'], ['A4', deck[N-2], 'steel'],
        ['A2', top[0], 'cable'], ['A2', top[1], 'cable'],
        ['A5', top[-1], 'cable'], ['A5', top[-2], 'cable'],
    ]
    return {'nodes': nodes, 'members': members}

def make_armed_toggle(wb=2.3, off=0.32, h0=0.45, h_arm=0.08, x_arm=14.0, x_fire=18.5, r_snap=0.72, speed=10.0):
    a = wb / 2.0
    L_arm = math.hypot(a, h0)
    wb_arm = 2.0 * math.sqrt(L_arm*L_arm - h_arm*h_arm)
    r_arm = round(wb_arm / wb, 4)
    yA = round(0.22 + h0, 4)
    nodes = [[0.0,0.22],[-wb,0.22],[-a,yA],[-off,0.22],[-wb-off,0.22],[-a-off,yA]]
    members = [[0,1,'hydraulic','H'],[0,2,'steel'],[1,2,'steel'],[3,4,'hydraulic','H'],[3,5,'steel'],[4,5,'steel'],[0,3,'steel'],[1,4,'steel'],[2,5,'steel']]
    d = {'nodes':nodes,'members':members,'wheels':[0,1,3,4],'ballast':[],'motor':{'speed':speed,'accel':4.0},
         'sensors':[{'id':'ga','type':'mygate','x':x_arm},{'id':'gf','type':'mygate','x':x_fire}],
         'rules':[{'on':'ga','delay':0.0,'do':'hyd','group':'H','ratio':r_arm,'speed':1.5,'accel':2.5},
                  {'on':'gf','delay':0.0,'do':'hyd','group':'H','ratio':r_snap,'speed':3.0,'accel':5.0}]}
    sp0 = S.parse_sab(lv, d)
    avail = min(2495 - sp0['mass'], 5990 - sp0['cost'])
    each = math.floor(avail / 2 * 10) / 10.0
    d['ballast'] = [[2, each], [5, each]]
    return S.parse_sab(lv, d)

# Build 4 nasty saboteurs to attack every fortress!
attackers = [
    ('TOG_x15', make_armed_toggle(wb=2.3, h_arm=0.08, x_arm=10.5, x_fire=15.0, r_snap=0.72)),
    ('TOG_x18', make_armed_toggle(wb=2.3, h_arm=0.08, x_arm=14.0, x_fire=18.5, r_snap=0.72)),
    ('TOG_x21', make_armed_toggle(wb=2.45, h_arm=0.075, x_arm=16.5, x_fire=21.0, r_snap=0.68)),
    ('TOG_x12', make_armed_toggle(wb=2.3, h_arm=0.08, x_arm=7.5, x_fire=12.0, r_snap=0.72)),
]

forts = [
    ('F1_subdiv_arch', f1_subdivided_arch()),
    ('F2_short_both',  f2_short_truss_both()),
    ('F3_lenticular',  f3_lenticular_steel()),
    ('F4_cant_arch',   f4_heavy_cantilever_arch()),
    ('F5_xwarren',     f5_xbraced_warren_fortress()),
]

for fname, fd in forts:
    try:
        P = B.parse_design(lv, fd)
    except Exception as e:
        print(f'{fname:18s}: ERR {e}'); continue
    res, _ = B.simulate(lv, P, {'vehicles': lv['convoy']})
    base_ok = all(v['status']==2 for v in res['vehicles'])
    cols = []
    held = 0
    for aname, sp in attackers:
        out, _ = S.duel(lv, P, sp)
        if not out['sab_win']: held += 1
        cols.append(f'{aname}:{"HOLD" if not out["sab_win"] else "LOST"}(b{out["broken"]:<2d})')
    print(f'{fname:16s} c={P["cost"]:7.1f} base={str(base_ok):5s} | ' + ' '.join(cols) + f' | {held}/{len(attackers)}')
