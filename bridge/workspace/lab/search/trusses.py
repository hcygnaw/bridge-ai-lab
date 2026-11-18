import itertools
import math
import sys

from design_lab import Bench, Design


def bar(d, a, b, mode="wood", grp=None):
    length = math.dist(d.pos(a), d.pos(b))
    if mode == "wood" and (length > 3 or "wood" in d.lv.get("banned", [])):
        mode = "steel"
    d.m(a, b, mode, grp)


def warren(d, a, b, n, h, rise=0, chord="wood", web="wood", feet=None, taper=0):
    aa, ab = d.pos(a), d.pos(b)

    def pos(t, lower=False):
        x = aa[0] + (ab[0]-aa[0])*t
        y = aa[1] + (ab[1]-aa[1])*t + rise*4*t*(1-t)
        if lower:
            y -= h*((1-taper)+taper*4*t*(1-t))
        return d.n(x, y)

    top = [a] + [pos(i/n) for i in range(1, n)] + [b]
    low = [pos((i+.5)/n, True) for i in range(n)]
    for i, z in enumerate(low):
        bar(d,top[i],top[i+1],"road")
        for u in top[i:i+2]:
            bar(d,u,z,web)
        if i:
            bar(d,low[i-1],z,chord)
    if feet:
        for u, v in zip(feet, (low[0],low[-1])):
            if u is not None:
                bar(d,u,v)
    return top, low


def standard(k, n, h, rise, chord="wood", web="wood", brace=True):
    d = Design(k)
    right = {1:"A2",2:"A4",3:"A3","final":"A3"}[k]
    feet = ["A1",{"A2":"A3","A3":"A4","A4":"A5"}[right]] if brace else None
    top, low = warren(d,"A0",right,n,h,rise,chord,web,feet)
    if k==3:
        for z in [top[n//2],low[n//2-1],low[n//2]]:
            if z != "A2":
                bar(d,"A2",z)
    return d


def pit_deck(d, h=.1, count=5, posts=(1,3)):
    ns = d.span("A2","A0",h,count)
    pts = ["A3","A4","A5","A6"]
    for j in posts:
        u=ns[j]
        v=min(pts,key=lambda v:math.dist(d.pos(u), d.pos(v)))
        bar(d,v,u,"steel")
    return ns


def crown5(n=11, rise=1.0, idx=(2,4,7,9), cap=4, pit_posts=(1,3)):
    # A crown above each abutment pulls up on the road via cable stays;
    # its shoreward stay closes the triangle against a pit or shore anchor.
    d=Design(5)
    pit_deck(d,posts=pit_posts)
    road=d.span("A0","A7",-rise,n)
    for right in [False,True]:
        tower=d.n(24 if right else 0,cap)
        bar(d,"A7" if right else "A0",tower,"steel")
        bar(d,"A9" if right else "A2",tower,"cable")
        for j in idx:
            if (j>n/2)==right:
                bar(d,road[j],tower,"cable")
    return d


if __name__=="__main__":
    k = sys.argv[1]
    k = k if k=="final" else int(k)
    b=Bench(k)
    if k != 5:
        n0 = {1:7,2:13,3:12,"final":14}[k]
        for n,h,rise,chord,brace in itertools.product(range(n0,n0+3),[1.65,2.1,1.3,1,.65,2.5],[1,0,2,-1],["wood","cable","steel"],[True,False]):
            b.test(standard(k,n,h,rise,chord,brace=brace),tag=(n,h,rise,chord,brace))
    else:
        for n,rise,cap,posts in itertools.product((11,12),(1.2,0,-1.2,2),(4,5,3),( (1,3),(2,),(2,4))):
            for idx in ((2,4,n-4,n-2),(3,n-3),(4,n-4),(2,5,n-5,n-2)):
                b.test(crown5(n,rise,idx,cap,posts),tag=(n,rise,idx,cap,posts))
