"""Cable-stayed high bridge for level 4. Deck clears y=6.05 over the channel."""
import math, os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bridge
from kit import B, save, SUB

YC = 6.08

def y_at(x):
    if x <= 9:
        return YC * (x + 12) / 21.0
    if x >= 15:
        return YC * (36 - x) / 21.0
    return YC

def build():
    b = B()
    anchors = {
        -12: 'A6', -10: 'A7', -8: 'A8', -6: 'A9', -4: 'A2', -2: 'A10', 0: 'A0',
        24: 'A3', 26: 'A11', 28: 'A5', 30: 'A12', 32: 'A13', 34: 'A14', 36: 'A15',
    }
    # deck x every 2 m on banks, every 2.25 over water so segments <= 2.5
    xs = [-12, -10, -8, -6, -4, -2, 0, 2.25, 4.5, 6.75, 9, 11.25, 13.5, 15, 17.25, 19.5, 21.75, 24, 26, 28, 30, 32, 34, 36]
    ids = []
    for x in xs:
        yy = y_at(x)
        if abs(yy) < 1e-8 and x in anchors:
            ids.append(anchors[x])
        else:
            ids.append(b.add(x, round(yy, 4)))
    for a, c in zip(ids, ids[1:]):
        b.mem(a, c, 'road')
    # posts to bank anchors directly below, split if > 2.9
    for x, aid in anchors.items():
        if not (-12 <= x <= 0 or 24 <= x <= 36):
            continue
        yy = y_at(x)
        if yy < 0.35:
            continue
        # find deck node at this x
        deck = None
        for nid in ids:
            if isinstance(nid, str):
                continue
            if abs(b.nodes[nid][0] - x) < 0.05:
                deck = nid
                break
        if deck is None:
            continue
        if yy <= 2.9:
            b.mem(deck, aid, 'wood')
        else:
            m = b.add(x, round(yy / 2, 4))
            b.mem(deck, m, 'wood')
            b.mem(m, aid, 'wood')
    # towers: left at x=-1, heights 4 and 8 and 12. Right at x=25.
    def tower(x, side):
        n4 = b.add(x, 4.0)
        n8 = b.add(x, 8.0)
        n12 = b.add(x, 12.0)
        b.mem(n4, n8, 'steel')
        b.mem(n8, n12, 'steel')
        if side == 'L':
            b.mem('A0', n4, 'steel')          # (0,0)-( -1,4) = 4.12
            b.mem('A1', n4, 'steel')          # (0,-2)-(-1,4) = 6.08 TOO LONG
            b.mem(n12, 'A6', 'cable')         # backstay
        else:
            b.mem('A3', n4, 'steel')
            b.mem('A4', n4, 'steel')
            b.mem(n12, 'A15', 'cable')
        return n12
    # fix A1 brace length: use intermediate
    LT = tower(-1.0, 'L')
    RT = tower(25.0, 'R')
    # remove illegal A1/A4 direct if too long — handled below by not adding them in tower
    return b, ids, LT, RT

# rewrite tower connections carefully in build2
def build2():
    b = B()
    anchors = {-12:'A6',-10:'A7',-8:'A8',-6:'A9',-4:'A2',-2:'A10',0:'A0',
               24:'A3',26:'A11',28:'A5',30:'A12',32:'A13',34:'A14',36:'A15'}
    xs = [-12,-10,-8,-6,-4,-2,0, 2.25,4.5,6.75,9, 11.25,13.5,15, 17.25,19.5,21.75,24, 26,28,30,32,34,36]
    ids=[]
    for x in xs:
        yy=round(y_at(x),4)
        if abs(yy)<1e-8 and x in anchors:
            ids.append(anchors[x])
        else:
            ids.append(b.add(x, yy))
    for a,c in zip(ids, ids[1:]):
        b.mem(a,c,'road')
    for x,aid in list(anchors.items()):
        yy=y_at(x)
        if yy<0.35: continue
        deck=None
        for nid in ids:
            if isinstance(nid,str): continue
            if abs(b.nodes[nid][0]-x)<0.05:
                deck=nid
        if deck is None: continue
        if yy<=2.9:
            b.mem(deck, aid, 'wood')
        else:
            m=b.add(x, round(yy/2,4))
            b.mem(deck, m, 'wood')
            b.mem(m, aid, 'wood')
    # left tower x=-1
    L4=b.add(-1,4); L8=b.add(-1,8); L12=b.add(-1,12)
    b.mem(L4,L8,'steel'); b.mem(L8,L12,'steel')
    b.mem('A0', L4, 'steel')                 # 4.12
    mid=b.add(-0.5, 1.0)
    b.mem('A1', mid, 'steel')                # (0,-2)-(-0.5,1)=3.04
    b.mem(mid, L4, 'steel')                  # (-0.5,1)-(-1,4)=3.04
    b.mem(L12, 'A6', 'cable')                # backstay (-1,12)-(-12,0)=16.3
    # right tower x=25
    R4=b.add(25,4); R8=b.add(25,8); R12=b.add(25,12)
    b.mem(R4,R8,'steel'); b.mem(R8,R12,'steel')
    b.mem('A3', R4, 'steel')                 # (24,0)-(25,4)=4.12
    midr=b.add(24.5, 1.0)
    b.mem('A4', midr, 'steel')
    b.mem(midr, R4, 'steel')
    b.mem(R12, 'A15', 'cable')
    # forestays: left tower holds the left water ramp, right tower the right ramp
    for nid in ids:
        if isinstance(nid, str):
            continue
        x, yy = b.nodes[nid]
        if 1.5 <= x <= 9.05:
            b.mem(nid, L12, 'cable')
        if 14.95 <= x <= 22.5:
            b.mem(nid, R12, 'cable')
    # channel span truss entirely above y=6.08
    a9 = b.add(9.0, 8.2)
    a12 = b.add(12.0, 8.6)
    a15 = b.add(15.0, 8.2)
    b.mem(a9, a12, 'steel')
    b.mem(a12, a15, 'steel')
    # hangers and ties down to deck nodes at x=9, 12-ish, 15
    for nid in ids:
        if isinstance(nid, str):
            continue
        x, yy = b.nodes[nid]
        if abs(x - 9) < 0.05:
            b.mem(nid, a9, 'wood')
        elif abs(x - 15) < 0.05:
            b.mem(nid, a15, 'wood')
        elif abs(x - 11.25) < 0.05 or abs(x - 13.5) < 0.05:
            # diagonal to nearest arch node if short enough
            target = a12
            dist = math.hypot(x - 12, yy - 8.6)
            if dist <= 2.95:
                b.mem(nid, target, 'wood')
            elif dist <= 6:
                b.mem(nid, target, 'steel')
    # small compression arch above channel so deck nodes aren't only on cables
    # already have cables. Add a wood king post above mid channel for stiffness? optional.
    return b.design()

def report_lengths(d):
    lv=bridge.load_level(4)
    anchors=lv['anchors']
    def xy(r):
        return anchors[int(r[1:])] if isinstance(r,str) else d['nodes'][r]
    lim={'road':2.5,'wood':3,'steel':6,'cable':30,'hydraulic':5}
    bad=[]
    for i,m in enumerate(d['members']):
        p,q=xy(m[0]),xy(m[1])
        L=math.hypot(p[0]-q[0], p[1]-q[1])
        if L>lim[m[2]]+1e-6 or L<0.3:
            bad.append((i,m[2],round(L,3),p,q))
    return bad

if __name__=='__main__':
    d=build2()
    bad=report_lengths(d)
    print('bad lengths', len(bad))
    for item in bad[:12]:
        print(item)
    if bad:
        raise SystemExit
    lv=bridge.load_level(4)
    # channel check
    anchors=lv['anchors']
    def xy(r):
        return anchors[int(r[1:])] if isinstance(r,str) else d['nodes'][r]
    def hits(p,q):
        ax,ay=p; bx,by=q
        dx,dy=bx-ax, by-ay
        t0,t1=0.0,1.0
        for p_,q_ in ((-dx,ax-9),(dx,15-ax),(-dy,ay-(-2)),(dy,6-ay)):
            if abs(p_)<1e-12:
                if q_< -1e-8: return False
            else:
                r=q_/p_
                if p_<0:
                    if r>t1: return False
                    if r>t0: t0=r
                else:
                    if r<t0: return False
                    if r<t1: t1=r
        return True
    ch=[i for i,m in enumerate(d['members']) if hits(xy(m[0]), xy(m[1]))]
    print('channel hits', ch)
    try:
        P=bridge.parse_design(lv,d)
    except bridge.DesignError as e:
        print('INV', e)
        raise SystemExit
    print('cost', P['cost'], P['cost_detail'])
    for pth in bridge.sample_paths(lv):
        sc=bridge.load_json(pth)
        res,_=bridge.simulate(lv,P,sc)
        print('----', sc['name'], 'OK' if res.get('ok') else 'FAIL')
        print(bridge.summarize(res,P,sc)['text'])
        if not res.get('ok'):
            print(bridge.peak_report(res,P,4))
            print([e for e in res['events'] if any(k in e for k in ('SHIP','VFAIL','BREAK'))][:8])
    if all(bridge.simulate(lv,P,bridge.load_json(p))[0].get('ok') for p in bridge.sample_paths(lv)):
        save(d,'level4_best.json')
        with open(os.path.join(SUB,'level4.json'),'w') as f:
            json.dump(d,f); f.write('\n')
        print('SAVED')
