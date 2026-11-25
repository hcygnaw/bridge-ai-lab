import math, json, l7_gauntlet as G, bridge as B, saboteur as S

lv = G.lv

def make_deck(N, y_fn=None):
    dx = 28.0 / N
    nodes = []
    deck = ['A0']
    for i in range(1, N):
        x = round(i * dx, 3)
        y = round(y_fn(x), 3) if y_fn else 0.0
        deck.append(len(nodes)); nodes.append([x, y])
    deck.append('A3')
    members = [[deck[i], deck[i+1], 'road'] for i in range(N)]
    return nodes, members, deck

# === CANDIDATE FORTRESSES (ALL <= 26,000, BUCKLE-PROOF SHORT MEMBERS!) ===
def F1_subdiv_arch(N=12, y_mid=-3.8):
    # Underslung steel arch (y=-2.0..-3.8) with mid-height steel bracing ONLY on central 5 struts (i=3..7) -> ~25.8k!
    nodes, members, deck = make_deck(N)
    dx = 28.0 / N
    arch = []
    for i in range(1, N):
        x = i * dx; s = (x - 14.0) / 14.0
        y = round(-2.0 + (y_mid + 2.0) * (1.0 - s*s), 3)
        arch.append(len(nodes)); nodes.append([round(x, 3), y])
    members += [['A1', arch[0], 'steel'], ['A0', arch[0], 'steel'], ['A4', arch[-1], 'steel'], ['A3', arch[-1], 'steel']]
    mids = {}
    for i in range(len(arch)):
        if 3 <= i <= 7:
            mid = len(nodes); nodes.append([nodes[arch[i]][0], round(nodes[arch[i]][1] * 0.5, 3)])
            mids[i] = mid
            members += [[deck[i+1], mid, 'steel'], [mid, arch[i], 'steel']]
        else:
            members.append([deck[i+1], arch[i], 'steel'])
    for i in range(len(arch) - 1):
        members.append([arch[i], arch[i+1], 'steel'])
        if i in mids and (i+1) in mids:
            members.append([mids[i], mids[i+1], 'wood'])
            if i < len(arch)//2:
                members += [[deck[i+2], mids[i], 'steel'], [mids[i+1], arch[i], 'steel']]
            else:
                members += [[deck[i+1], mids[i+1], 'steel'], [mids[i], arch[i+1], 'steel']]
        elif i in mids:
            members += [[mids[i], arch[i+1], 'steel'], [deck[i+1], arch[i+1], 'steel']]
        elif (i+1) in mids:
            members += [[arch[i], mids[i+1], 'steel'], [deck[i+2], arch[i], 'steel']]
        else:
            if i < len(arch)//2: members.append([deck[i+2], arch[i], 'steel'])
            else: members.append([deck[i+1], arch[i+1], 'steel'])
    return {'nodes': nodes, 'members': members}

def F2_shallow_x_arch(N=12, y_mid=-3.1):
    # Shallow buckle-proof underslung arch (max strut 3.1m -> maxC > 95 kN!) + FULL X-BRACING with cables + A2/A5 backstays!
    nodes, members, deck = make_deck(N)
    dx = 28.0 / N
    arch = []
    for i in range(1, N):
        x = i * dx; s = (x - 14.0) / 14.0
        y = round(-2.0 + (y_mid + 2.0) * (1.0 - s*s), 3)
        arch.append(len(nodes)); nodes.append([round(x, 3), y])
    members += [['A1', arch[0], 'steel'], ['A0', arch[0], 'steel'], ['A4', arch[-1], 'steel'], ['A3', arch[-1], 'steel']]
    for i in range(len(arch)):
        members.append([deck[i+1], arch[i], 'steel'])
        if i + 1 < len(arch):
            members.append([arch[i], arch[i+1], 'steel'])
            if i < len(arch)//2:
                members.append([deck[i+2], arch[i], 'steel'])
                members.append([deck[i+1], arch[i+1], 'cable'])
            else:
                members.append([deck[i+1], arch[i+1], 'steel'])
                members.append([deck[i+2], arch[i], 'cable'])
    # Backstay piers at A0/A2 and A3/A5 supporting midspan via cables!
    tL = len(nodes); nodes.append([0.0, 2.8])
    tR = len(nodes); nodes.append([28.0, 2.8])
    members += [
        ['A0', tL, 'steel'], ['A2', tL, 'cable'], [tL, deck[2], 'cable'], [tL, deck[4], 'cable'],
        ['A3', tR, 'steel'], ['A5', tR, 'cable'], [tR, deck[10], 'cable'], [tR, deck[8], 'cable'],
    ]
    return {'nodes': nodes, 'members': members}

def F3_stiff_warren_under(N=12, y_bot=-2.4):
    # Pure short-member UNDER-DECK STEEL WARREN TRUSS anchored to A0, A1, A3, A4 + cable backstays!
    # Every diagonal L = hypot(1.17, 2.4) = 2.67m -> ZERO buckling (maxC = 115 kN!), NO tall 4.6m struts!
    nodes, members, deck = make_deck(N)
    dx = 28.0 / N
    bot = []
    for i in range(N):
        x = (i + 0.5) * dx; s = (x - 14.0) / 14.0
        y = round(-2.0 - 0.8 * (1.0 - s*s), 3)
        bot.append(len(nodes)); nodes.append([round(x, 3), y])
    for i in range(N):
        members.append([deck[i], bot[i], 'steel'])
        members.append([deck[i+1], bot[i], 'steel'])
    for i in range(N - 1):
        members.append([bot[i], bot[i+1], 'steel'])
    members += [
        ['A1', bot[0], 'steel'], ['A4', bot[-1], 'steel'],
        ['A1', deck[1], 'steel'], ['A4', deck[N-1], 'steel'],
    ]
    # Add overhead cable-stayed towers using remaining budget!
    tL = len(nodes); nodes.append([0.0, 3.2])
    tR = len(nodes); nodes.append([28.0, 3.2])
    members += [
        ['A0', tL, 'steel'], ['A2', tL, 'cable'], [tL, deck[3], 'cable'], [tL, deck[5], 'cable'],
        ['A3', tR, 'steel'], ['A5', tR, 'cable'], [tR, deck[9], 'cable'], [tR, deck[7], 'cable'],
    ]
    return {'nodes': nodes, 'members': members}

def F4_double_warren_cable(N=12):
    # Under-deck steel Warren truss + overhead wood/cable arch! Dual redundant load path!
    nodes, members, deck = make_deck(N)
    dx = 28.0 / N
    bot = []
    for i in range(N):
        x = (i + 0.5) * dx; s = (x - 14.0) / 14.0
        y = round(-2.0 - 1.2 * (1.0 - s*s), 3)
        bot.append(len(nodes)); nodes.append([round(x, 3), y])
    for i in range(N):
        members.append([deck[i], bot[i], 'steel'])
        members.append([deck[i+1], bot[i], 'steel'])
    for i in range(N - 1):
        members.append([bot[i], bot[i+1], 'steel'])
    members += [['A1', bot[0], 'steel'], ['A4', bot[-1], 'steel'], ['A1', deck[1], 'steel'], ['A4', deck[N-1], 'steel']]
    # Extra steel tie-back from A2/A5 through short piers to deck[2..10]
    tL = len(nodes); nodes.append([0.0, 4.0])
    tR = len(nodes); nodes.append([28.0, 4.0])
    members += [
        ['A0', tL, 'steel'], ['A2', tL, 'cable'], ['A0', len(nodes), 'steel'], # skip extra
    ]
    members.pop()
    # Add braced strut from A2 to tL? No, keep tL at y=2.6m (no buckling!)
    nodes[tL] = [0.0, 2.6]; nodes[tR] = [28.0, 2.6]
    members += [['A3', tR, 'steel'], ['A5', tR, 'cable'],
                [tL, deck[2], 'cable'], [tL, deck[4], 'cable'], [tL, deck[6], 'cable'],
                [tR, deck[10], 'cable'], [tR, deck[8], 'cable'], [tR, deck[6], 'cable']]
    return {'nodes': nodes, 'members': members}

def F5_compact_warren_N13():
    # N=13 shorter panels (dx=2.15m!) under-deck deep parabolic steel Warren truss!
    N = 13
    nodes, members, deck = make_deck(N)
    dx = 28.0 / N
    bot = []
    for i in range(N):
        x = (i + 0.5) * dx; s = (x - 14.0) / 14.0
        y = round(-2.0 - 1.5 * (1.0 - s*s), 3)
        bot.append(len(nodes)); nodes.append([round(x, 3), y])
    for i in range(N):
        members.append([deck[i], bot[i], 'steel'])
        members.append([deck[i+1], bot[i], 'steel'])
    for i in range(N - 1):
        members.append([bot[i], bot[i+1], 'steel'])
    members += [['A1', bot[0], 'steel'], ['A4', bot[-1], 'steel'],
                ['A1', deck[1], 'steel'], ['A4', deck[N-1], 'steel']]
    return {'nodes': nodes, 'members': members}

def F6_tall_warren_N12():
    # N=12 OVERHEAD deep parabolic steel Warren truss (y=+2.5..+3.5) + A1/A4 end compression struts + A2/A5 cable backstays + under-deck central cable!
    N = 12
    nodes, members, deck = make_deck(N)
    dx = 28.0 / N
    top = []
    for i in range(N):
        x = (i + 0.5) * dx; s = (x - 14.0) / 14.0
        y = round(2.5 + 1.0 * (1.0 - s*s), 3)
        top.append(len(nodes)); nodes.append([round(x, 3), y])
    for i in range(N):
        members.append([deck[i], top[i], 'steel'])
        members.append([deck[i+1], top[i], 'steel'])
    for i in range(N - 1):
        members.append([top[i], top[i+1], 'steel'])
    members += [
        ['A2', top[0], 'cable'], ['A2', top[1], 'cable'],
        ['A5', top[-1], 'cable'], ['A5', top[-2], 'cable'],
        ['A1', deck[1], 'steel'], ['A1', deck[2], 'steel'],
        ['A4', deck[N-1], 'steel'], ['A4', deck[N-2], 'steel'],
    ]
    return {'nodes': nodes, 'members': members}

# === BUILD FULL ATTACKER SUITE (7 diverse saboteurs!) ===
def fill_ballast(d, target_nodes):
    d0 = dict(d); d0['ballast'] = []
    sp0 = S.parse_sab(lv, d0)
    avail = min(2495 - sp0['mass'], 5990 - sp0['cost'])
    each = max(1.0, math.floor(avail / len(target_nodes) * 10) / 10.0)
    d['ballast'] = [[n, each] for n in target_nodes]
    return S.parse_sab(lv, d)

def mk_toggle(wb=2.3, off=0.32, h0=0.45, h_arm=0.08, x_arm=14.0, x_fire=18.5, r_snap=0.72, speed=10.0, arm_sp=1.2, arm_acc=2.0):
    a = wb / 2.0; L_arm = math.hypot(a, h0)
    r_arm = round(2.0 * math.sqrt(L_arm*L_arm - h_arm*h_arm) / wb, 4)
    yA = round(0.22 + h0, 4)
    nodes = [[0.0,0.22],[-wb,0.22],[-a,yA],[-off,0.22],[-wb-off,0.22],[-a-off,yA]]
    members = [[0,1,'hydraulic','H'],[0,2,'steel'],[1,2,'steel'],[3,4,'hydraulic','H'],[3,5,'steel'],[4,5,'steel'],[0,3,'steel'],[1,4,'steel'],[2,5,'steel']]
    return fill_ballast({
        'nodes':nodes,'members':members,'wheels':[0,1,3,4],'motor':{'speed':speed,'accel':4.0},
        'sensors':[{'id':'ga','type':'mygate','x':x_arm},{'id':'gf','type':'mygate','x':x_fire}],
        'rules':[{'on':'ga','delay':0.0,'do':'hyd','group':'H','ratio':r_arm,'speed':arm_sp,'accel':arm_acc},
                 {'on':'gf','delay':0.0,'do':'hyd','group':'H','ratio':r_snap,'speed':3.0,'accel':5.0}],
    }, [2, 5])

def mk_piledriver(xf=15.5, r1=0.65):
    nodes = [[0.0,0.22],[-2.25,0.22],[-1.125,1.48],[-0.35,0.22],[-2.6,0.22],[-1.475,1.48]]
    members = [[0,1,'steel'],[0,2,'hydraulic','H'],[1,2,'hydraulic','H'],[3,4,'steel'],[3,5,'hydraulic','H'],[4,5,'hydraulic','H'],[0,3,'steel'],[1,4,'steel'],[2,5,'steel']]
    return fill_ballast({
        'nodes':nodes,'members':members,'wheels':[0,1,3,4],'motor':{'speed':9.8,'accel':4.0},
        'sensors':[{'id':'g0','type':'mygate','x':xf}],
        'rules':[{'on':'g0','delay':0.0,'do':'hyd','group':'H','ratio':r1,'speed':3.0,'accel':5.0},
                 {'on':'g0','delay':0.45,'do':'hyd','group':'H','ratio':1.0,'speed':3.0,'accel':5.0}],
    }, [2, 5])

def mk_upkick(xf=15.5, r1=1.45):
    nodes = [[0.0,0.22],[-1.8,0.22],[-0.9,0.52]]
    members = [[0,1,'steel'],[0,2,'hydraulic','H'],[1,2,'hydraulic','H']]
    return fill_ballast({
        'nodes':nodes,'members':members,'wheels':[0,1],'motor':{'speed':9.8,'accel':4.0},
        'sensors':[{'id':'g0','type':'mygate','x':xf}],
        'rules':[{'on':'g0','delay':0.0,'do':'hyd','group':'H','ratio':r1,'speed':3.0,'accel':5.0},
                 {'on':'g0','delay':0.22,'do':'hyd','group':'H','ratio':1.0,'speed':3.0,'accel':5.0}],
    }, [2])

def mk_crawler():
    # Heavy slow 2500kg static crawler!
    nodes = [[0.0,0.22],[-2.6,0.22],[-1.3,0.90]]
    members = [[0,1,'steel'],[0,2,'steel'],[1,2,'steel']]
    return fill_ballast({'nodes':nodes,'members':members,'wheels':[0,1],'motor':{'speed':5.5,'accel':4.0},'sensors':[],'rules':[]}, [2])

attackers = [
    ('TOG_14', mk_toggle(x_arm=9.5,  x_fire=14.0)),
    ('TOG_16', mk_toggle(x_arm=11.5, x_fire=16.0)),
    ('TOG_18', mk_toggle(x_arm=14.0, x_fire=18.5)),
    ('TOG_21', mk_toggle(x_arm=16.5, x_fire=21.0)),
    ('PILED',  mk_piledriver(15.5, 0.65)),
    ('UPKICK', mk_upkick(15.5, 1.45)),
    ('CRAWL',  mk_crawler()),
]

forts = [
    ('F1_subdiv',  F1_subdiv_arch),
    ('F2_x_arch',  F2_shallow_x_arch),
    ('F3_u_warr',  F3_stiff_warren_under),
    ('F4_dbl_war', F4_double_warren_cable),
    ('F5_u_w_N13', F5_compact_warren_N13),
    ('F6_o_w_N12', F6_tall_warren_N12),
]

print(f'{"FORTRESS":12s} {"COST":7s} {"BASE":5s} | ' + ' '.join(f'{a:10s}' for a,_ in attackers) + ' | HOLD (b0)')
print('-'*120)
for fname, ffn in forts:
    try:
        P = B.parse_design(lv, ffn())
    except Exception as e:
        print(f'{fname:12s} ERR: {e}'); continue
    res, _ = B.simulate(lv, P, {'vehicles': lv['convoy']})
    base_ok = all(v['status']==2 for v in res['vehicles'])
    cols, held, b0 = [], 0, 0
    for aname, sp in attackers:
        out, _ = S.duel(lv, P, sp)
        if not out['sab_win']: held += 1
        if out['broken'] == 0 and not out['sab_win']: b0 += 1
        tag = ('OK' if not out['sab_win'] else 'KO') + f' b{out["broken"]:<2d}' + ('A' if out['sab_arrived'] else 'D')
        cols.append(f'{tag:10s}')
    print(f'{fname:12s} {P["cost"]:7.1f} {str(base_ok):5s} | ' + ' '.join(cols) + f' | {held}/7 (b0={b0})')
