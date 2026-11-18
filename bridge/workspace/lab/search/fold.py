import copy
import math
import random
import sys
import time
from pathlib import Path

import bridge
from design_lab import Bench, Design, target, write
from arches import smallfan
from lifts import timer
from trusses import bar
from strengthen import repair


def original_approaches(d):
    fp=Path("scratch/pier-template.json")
    if not fp.exists():write(fp,bridge.load_json(target(6)))
    raw=bridge.load_json(fp)
    ids={}
    for i,(x,y) in enumerate(raw["nodes"]):
        if (x<11.98 or x>24.04) and y<1.6:
            ids[i]=d.n(x,y)
    for m in raw["members"]:
        a,b=m[:2]
        if (isinstance(a,str) or a in ids) and (isinstance(b,str) or b in ids):
            d.m(ids.get(a,a),ids.get(b,b),m[2],m[3] if len(m)>3 else None)
    left=max((d.pos(q)[0],q) for q in ids.values() if d.pos(q)[0]<12)[1]
    right=min((d.pos(q)[0],q) for q in ids.values() if d.pos(q)[0]>24)[1]
    act=min((math.dist(d.pos(q),(26,0)),q) for q in ids.values())[1]
    return left,right,act


def make(k,n=6,sag=1.28,h=1.22,camber=.08,ch="cable",step=1,taper=.72,tie=True,
         shove=1.35,lag=7.,rootbr=False,mid=.5,flip=False):
    d=Design(k)
    if k==4:
        a="A0"; end=d.n(23.86,.02);pin="A4";root="A11"
    else:
        a,right,root=original_approaches(d)
        end=d.n(23.86,.02);pin="A5"
    bar(d,end,pin,"steel");bar(d,root,end,"hydraulic","lift")
    ax,ay=d.pos(a);bx,by=d.pos(end)
    c=d.n(ax+(bx-ax)*mid,ay+(by-ay)*mid-sag)
    for j,(u,v) in enumerate(((a,c),(c,end))):
        foot=[None,None]
        up,lo=smallfan(d,u,v,n,camber,-h,step,foot,web="wood",chord=ch,q=taper)
        if tie:
            bar(d,u,v,"cable")
        if rootbr and k==4 and not j:
            bar(d,"A1",lo[0])
    initial=math.dist(d.pos(root),d.pos(end))
    rad=math.dist(d.pos(pin),d.pos(end))
    opened=(bx-shove,-2+math.sqrt(max(.02,rad**2-(bx-shove-d.pos(pin)[0])**2)))
    ratio=math.dist(d.pos(root),opened)/initial
    timer(d,ratio,{4:26.08,6:30.08}[k],speed=.8,ready=3.,lag=lag)
    return d


def search(k,secs):
    b=Bench(k);rng=random.Random(582+k);cnt=0
    end=time.monotonic()+secs
    while time.monotonic()<end:
        n=rng.choice([5,6,6,7,8] if k==4 else [3,3,4,5])
        s=dict(n=n,sag=rng.uniform(.78,1.67),h=rng.uniform(.45,2.1),camber=rng.uniform(-.26,.43),
               ch=rng.choice(["wood","wood","cable","steel"]),step=rng.choice([1,1,2]),taper=rng.uniform(.1,.98),
               tie=rng.choice([True,True,False]),shove=rng.uniform(.85,1.72),lag=rng.uniform(5.5,9.),rootbr=rng.randrange(2),
               mid=rng.uniform(.46,.54))
        d=make(k,**s);cnt+=1
        if repair(b,d,limit=9):
            print("fold",k,s,flush=True);write(f"scratch/fold{k}.json",s)
    print("fold trials",k,cnt,b.existing(),flush=True)


if __name__=="__main__":
    search(int(sys.argv[1]),float(sys.argv[2]))
