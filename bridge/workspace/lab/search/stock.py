import copy
import itertools
import math
import random
import sys
import time

import bridge
from design_lab import Bench, target
from trim import point


def build(d0,b,j,s,rng):
    d=copy.deepcopy(d0);ms=d["members"];pts=d["nodes"]
    m=ms.pop(j);a,c=m[:2]
    def pos(q):return point(d,b.lv,q)
    ax,ay=pos(a);cx,cy=pos(c);L=math.dist((ax,ay),(cx,cy))
    count=s['num']
    if L/count>2.99:return
    seq=[a];others=list(range(len(pts)))+[f"A{i}" for i in range(len(b.lv["anchors"]))]
    for i in range(1,count):
        t=i/count;h=s["height"]*4*t*(1-t)
        p=[round(ax+(cx-ax)*t-h*(cy-ay)/L,5),round(ay+(cy-ay)*t+h*(cx-ax)/L,5)]
        q=len(pts);pts.append(p);seq.append(q)
        near=sorted((math.dist(pos(z),p),str(z),z) for z in others if z not in (a,c))
        if s["brace"] and near:
            for dist,_,z in near[:s["brace"]]:
                if .3<=dist<=3:ms.append([q,z,"wood"])
    seq.append(c)
    for u,v in zip(seq,seq[1:]):ms.append([u,v,"wood"])
    if s["parallel"]:ms.append([a,c,"wood"])
    return d


def run(k,secs):
    b=Bench(k,{4:[1,0],6:[2,1,0]}.get(k));rng=random.Random(28655+k);end=time.monotonic()+secs;cnt=0;seen=set()
    while time.monotonic()<end:
        d0=bridge.load_json(target(k));p=bridge.parse_design(b.lv,d0)
        ids=[i for i,m in enumerate(p["members"]) if m[2]=="steel" or (m[2]=="cable" and m[-1]>3)]
        if not ids:break
        j=rng.choice(ids);L=p['members'][j][-1];n=max(2,math.ceil(L/2.9))
        s=dict(num=n+(rng.random()<.13),height=rng.choice([0,0,rng.uniform(-.3,.3),rng.uniform(-.8,.8)]),brace=rng.choice([0,1,1,1,2]),parallel=rng.random()<.32 and L<2.99)
        d=build(d0,b,j,s,rng);cnt+=1
        if d is None:continue
        sig=repr(d)
        if sig in seen:continue
        if len(seen)>12000:seen.clear()
        seen.add(sig)
        b.test(d,tag=f"stock {j}")
    print("stock",k,cnt,b.existing(),flush=True)


if __name__=="__main__":
    run(int(sys.argv[1]),float(sys.argv[2]))
