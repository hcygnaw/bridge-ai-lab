"""Minimal legal high road to test whether a van can crest the channel."""
import math, json, bridge
from kit import B

def build():
    b = B()
    yc = 6.08
    def yy(x):
        if x <= 9: return yc * (x + 12) / 21
        if x >= 15: return yc * (36 - x) / 21
        return yc
    # deck points, spacing <= 2.4
    xs = [-12,-10,-8,-6,-4,-2,0, 2.2,4.4,6.5,7.8,9, 11.5,13.5,15, 16.2,17.5,19.6,21.8,24, 26,28,30,32,34,36]
    anch = {-12:'A6',-10:'A7',-8:'A8',-6:'A9',-4:'A2',-2:'A10',0:'A0',
            24:'A3',26:'A11',28:'A5',30:'A12',32:'A13',34:'A14',36:'A15'}
    ids=[]
    for x in xs:
        y=round(yy(x),4)
        if abs(y)<1e-8 and x in anch:
            ids.append(anch[x])
        else:
            ids.append(b.add(x,y))
    for a,c in zip(ids, ids[1:]):
        b.mem(a,c,'road')
    # posts to bank anchors
    for x,aid in anch.items():
        y=yy(x)
        if y<0.35: continue
        deck=None
        for nid in ids:
            if isinstance(nid,str): continue
            if abs(b.nodes[nid][0]-x)<0.05:
                deck=nid
        if deck is None: continue
        if y<=2.95:
            b.mem(deck, aid, 'wood')
        else:
            m=b.add(x, round(y/2,4))
            b.mem(deck, m, 'wood')
            b.mem(m, aid, 'wood')
    # support water ramps with steel posts down to y=-3, x strictly outside [9,15]
    # left water nodes x=2.2,4.4,6.6,8.8
    for nid in ids:
        if isinstance(nid,str): continue
        x,y=b.nodes[nid]
        if x<=0 or x>=24 or y<1: continue
        if 8.95 < x < 15.05: continue
        # post in steel segments of 3m down to -3.2, x unchanged (outside channel)
        h = y - (-3.2)
        nseg = int(math.ceil(h/5.5))
        prev=nid
        for k in range(1, nseg+1):
            py = y - h*k/nseg
            node=b.add(x, round(py,4))
            b.mem(prev, node, 'steel')
            prev=node
    # tie the bottoms of those posts into a steel chord and to A1/A4
    bots=[i for i,n in enumerate(b.nodes) if abs(n[1]+3.2)<0.05 and (n[0]<8.9 or n[0]>15.1)]
    bots.sort(key=lambda i: b.nodes[i][0])
    for a,c in zip(bots, bots[1:]):
        if math.hypot(*(b.nodes[a][j]-b.nodes[c][j] for j in (0,1)))<=6:
            b.mem(a,c,'steel')
    if bots:
        # connect leftmost bottom toward A1 if short enough, else via mid
        x0=b.nodes[bots[0]][0]
        if x0<8:
            mid=b.add(x0/2, -2.6)
            b.mem(bots[0], mid, 'steel')
            b.mem(mid, 'A1', 'steel')
        x1=b.nodes[bots[-1]][0]
        if x1>16:
            mid=b.add((x1+24)/2, -2.6)
            b.mem(bots[-1], mid, 'steel')
            b.mem(mid, 'A4', 'steel')
    # channel deck: small steel beam above, from x=9 to 15 at y=6.08, already road.
    # add a compression strut under it but ABOVE y=6.1 so it misses the ship box
    # king post above
    k=b.add(12.0, 8.5)
    for nid in ids:
        if isinstance(nid,str): continue
        x,y=b.nodes[nid]
        if 8.9<=x<=15.1:
            L=math.hypot(x-12, y-8.5)
            if 0.3<L<=6:
                b.mem(nid, k, 'steel')
    return b.design()

if __name__=='__main__':
    d=build()
    lv=bridge.load_level(4)
    try:
        P=bridge.parse_design(lv,d)
    except bridge.DesignError as e:
        print('INV', e)
        raise SystemExit
    print('cost', P['cost'], P['cost_detail'])
    # channel
    anch=lv['anchors']
    def xy(r):
        return anch[int(r[1:])] if isinstance(r,str) else d['nodes'][r]
    def hits(p,q):
        ax,ay=p; bx,by=q; dx,dy=bx-ax, by-ay
        t0,t1=0.,1.
        for pp,qq in ((-dx,ax-9),(dx,15-ax),(-dy,ay+2),(dy,6-ay)):
            if abs(pp)<1e-12:
                if qq<-1e-8: return False
            else:
                r=qq/pp
                if pp<0:
                    if r>t1: return False
                    if r>t0: t0=r
                else:
                    if r<t0: return False
                    if r<t1: t1=r
        return True
    bad=[i for i,m in enumerate(d['members']) if hits(xy(m[0]), xy(m[1]))]
    print('channel hits', bad[:6], 'count', len(bad))
    for pth in bridge.sample_paths(lv):
        sc=bridge.load_json(pth)
        res,_=bridge.simulate(lv,P,sc)
        print(sc['name'], 'OK' if res.get('ok') else 'FAIL')
        print(bridge.summarize(res,P,sc)['text'])
