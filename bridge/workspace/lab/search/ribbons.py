import itertools
import math
import random
import sys
import time

import bridge
from design_lab import Bench, Design
from trusses import bar


def ribbon(d,a,b,feet,rng,spec):
    p1,p2=d.pos(a),d.pos(b)
    span=p2[0]-p1[0]
    ramps=[]
    for rev,start in enumerate((a,b)):
        base=feet[rev];cnt=spec["toes"]
        z=start
        x,y=d.pos(start); sg=1 if rev==0 else -1
        route=[z]
        for i in range(1,cnt+1):
            u=d.n(x+sg*i*spec["panel"],y+spec["fall"]*(i/cnt)**spec["exp"])
            bar(d,z,u,"road")
            if base is not None:
                l=math.dist(d.pos(base),d.pos(u))
                if l<=6:bar(d,base,u,"spring" if l<=4 and l>3 and spec["spr"] else "wood")
            z=u;route.append(z)
        ramps.append(z)
    n=spec["n"]
    ns=[ramps[0]]
    xa,ya=d.pos(ramps[0]);xb,yb=d.pos(ramps[1])
    for i in range(1,n):
        t=i/n
        bump=spec["bump"] if i%2 else 0
        s=4*t*(1-t)
        y=ya+(yb-ya)*t-spec["sag"]*s**spec["pow"]+bump
        ns.append(d.n(xa+(xb-xa)*t,y))
    ns.append(ramps[1])
    for u,v in zip(ns,ns[1:]):bar(d,u,v,"road")
    pattern=spec["braces"]
    edges=set()
    if pattern in (1,2):
        edges.update((i,i+2) for i in range(pattern-1,n-1,2))
    elif pattern==3:
        edges.update([(0,n//2),(n//2,n)])
    elif pattern==4:
        edges.update([(0,2),(n-2,n)])
    elif pattern==5:
        edges.update([(1,n-1)])
    elif pattern==6:
        edges.update((i,min(i+3,n)) for i in range(0,n-1,3))
    elif pattern==7:
        edges.update([(0,n-1),(1,n)])
    for i,j in edges:
        if j>i+1:
            length=math.dist(d.pos(ns[i]),d.pos(ns[j]))
            bar(d,ns[i],ns[j],"wood" if spec["wood"] and length<=3 else "cable")


def control(d,width,offset,t1,t2):
    d.sensors.append(dict(id="s",type="start"))
    for k,t in enumerate([t1,t2]):
        if t==0:continue
        name=["L","R"][k]
        d.lights.append(dict(id=name,x= -offset if k==0 else width+offset,dir="right" if not k else "left",init="red"))
        d.rules.append(dict(on="s",delay=t,do="light",light=name,state="green"))


def gen(k,s):
    d=Design(k)
    if k==1: spans=[("A0","A2",("A1","A3"))]
    elif k==2:spans=[("A0","A4",("A1","A5"))]
    else:
        mid=d.n(14,s["mid"])
        if mid!="A2":bar(d,"A2",mid,"wood" if -4<s["mid"]<=-1 else "steel")
        spans=[("A0",mid,("A1","A2")),(mid,"A3",("A2","A4"))]
    for a,b,ft in spans:ribbon(d,a,b,ft,None,s)
    control(d,{1:15,2:30,3:28}[k],s["offset"],s["t1"],s["t2"])
    return d


def search(k,secs,seed=919):
    rng=random.Random(seed)
    b=Bench(k,{1:[1,2,0],2:[1,0],3:[1,0,2]}[k])
    w={1:15,2:30,3:14}[k]
    end=time.monotonic()+secs;cnt=0
    while time.monotonic()<end:
        toes=rng.choice([0,0,1,1,2,3])
        panel=rng.uniform(1.05,2.38)
        nmin=max(2,math.ceil((w-2*toes*panel)/2.49))
        if nmin<2:continue
        n=rng.randint(nmin+int(rng.random()<.3),nmin+5)
        s=dict(toes=toes,panel=panel,n=n,fall=rng.uniform(-1.35,.55),exp=rng.uniform(.8,2.8),
               sag=rng.uniform(.25,3.8)*((w-2*toes*panel)/15),pow=rng.uniform(.75,1.4),
               braces=rng.choice([0,0,0,0,1,2,3,4,5,6,7]),bump=rng.uniform(-.24,.24),wood=rng.randrange(2),
               mid=rng.uniform(-2.2,-.18),offset=rng.uniform(-.24,2.7),spr=rng.randrange(2))
        s["t1"]=rng.choice([0,0,6,8.5]);s["t2"]=rng.choice([0,0,8,13.5,17])
        d=gen(k,s);cnt+=1
        if b.test(d,tag=(toes,n,round(s["sag"],2),s["braces"],s["t1"],s["t2"])):
            from design_lab import write
            write(f"scratch/ribbon{k}.json",s)
    print("ribbon",k,cnt,b.existing(),flush=True)


if __name__=="__main__":
    search(int(sys.argv[1]),float(sys.argv[2]),int(sys.argv[3]) if len(sys.argv)>3 else 919)
