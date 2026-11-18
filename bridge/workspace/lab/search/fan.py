import math
import sys
import itertools
import random

from design_lab import Bench, Design
from trusses import bar


def bow(d,a,b,n,sag,connections,*,skew=0,rim=0,mat="road",kind="cable"):
    xa,ya=d.pos(a); xb,yb=d.pos(b)
    ns=[a]
    for i in range(1,n):
        t=i/n
        x=xa+(xb-xa)*t
        shape=4*t*(1-t)*(1+skew*(t-.5))
        y=ya+(yb-ya)*t-sag*shape+rim*((-1)**i)
        ns.append(d.n(x,y))
    ns.append(b)
    for p,q in zip(ns,ns[1:]):
        d.m(p,q,mat)
    pairs=set()
    def edge(i,j):
        if j<i:i,j=j,i
        if j-i<2 or (i==0 and j==n) or (i,j) in pairs:return
        pairs.add((i,j))
        m=kind
        if kind=="mixed":
            m="wood" if math.dist(d.pos(ns[i]),d.pos(ns[j]))<=3 and "wood" not in d.lv.get("banned",[]) else "cable"
        d.m(ns[i],ns[j],m)
    if "tri" in connections:
        def rec(i,j):
            if j-i<3:return
            k=(i+j)//2
            edge(i,k); edge(k,j)
            rec(i,k); rec(k,j)
        rec(0,n)
    if "near" in connections:
        for i in range(2,(n+2)//2+1,2):
            edge(0,i);edge(n-i,n)
    if "stay" in connections:
        for i in range(2,n//2+1):
            edge(0,i);edge(n-i,n)
    if "mid" in connections:
        edge(0,n//2);edge(n//2,n)
    if "odd" in connections:
        for i in range(0,n-1,2):edge(i,i+2)
    if "deep" in connections:
        edge(0,n-2);edge(2,n)
    return ns


def tower(d, base, back, foot, tipx, tipy, stages=3):
    a=d.pos(base)
    ns=[base]+[d.n(a[0]+(tipx-a[0])*i/stages, a[1]+(tipy-a[1])*i/stages) for i in range(1,stages+1)]
    for i,(p,q) in enumerate(zip(ns,ns[1:])):
        bar(d,p,q,"steel")
        if i+1<stages:
            length=math.dist(d.pos(foot),d.pos(q))
            if length<6:bar(d,foot,q,"steel")
            else:bar(d,back,q,"cable")
    bar(d,back,ns[-1],"cable")
    return ns[-1]


def stayed(k,n,cap,inset,step,rise=0,extra=True):
    d=Design(k)
    right,footback={2:("A4",("A2","A6","A3","A7")),"final":("A3",("A1","A4","A2","A5"))}[k]
    w=d.pos(right)[0]
    road=d.span("A0",right,-rise,n)
    for side in [0,1]:
        root=("A0",right)[side]
        top=tower(d,root,footback[2+side],footback[side],w-inset if side else inset,cap)
        for i in range(step, n//2+1,step):
            idx=n-i if side else i
            bar(d,top,road[idx],"cable")
        if n//2%step:bar(d,top,road[n//2],"cable")
        if extra:
            # Brace the mast midsection fore and aft.
            ax=d.pos(root)[0]
            for f,idx in [(1/3,2),(2/3,4)]:
                loc=d.n(ax+(d.pos(top)[0]-ax)*f,cap*f)
                bar(d,loc,road[-idx-1 if side else idx],"cable")
    return d


if __name__=="__main__":
    k=sys.argv[1]
    k=k if k=="final" else int(k)
    b=Bench(k)
    if k=="final":
        for n,cap,ins,step,r in itertools.product((14,16,18),(6.,7.5,5.,9.),(2.5,4.,1.),(1,2,3),(0,1,-1)):
            if b.test(stayed(k,n,cap,ins,step,r),tag=(n,cap,ins,step,r)):break
    elif k in (1,2):
        n0=7 if k==1 else 14
        right="A2" if k==1 else "A4"
        cases=list(itertools.product(range(n0,n0+4),(.7,1.3,1.8,2.4,3.3,4.,-1.6,-2.4),("mid","tri","tri deep","near","near odd","stay","mid odd","deep","mid deep")))
        random.Random(72).shuffle(cases)
        for n,sag,pat in cases:
            d=Design(k); bow(d,"A0",right,n,sag,pat)
            b.test(d,tag=(n,sag,pat))
