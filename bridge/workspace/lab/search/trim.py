"""Cost descent with official-scenario acceptance; never changes the simulator."""
import copy
import math
import random
import sys
import time

import bridge
from design_lab import Bench, target


def compact(d):
    used = sorted({q for m in d["members"] for q in m[:2] if isinstance(q,int)})
    new = {old:i for i,old in enumerate(used)}
    for m in d["members"]:
        m[:2] = [new[q] if isinstance(q,int) else q for q in m[:2]]
    d["nodes"] = [d["nodes"][q] for q in used]
    return d


def point(d, lv, n):
    return lv["anchors"][int(n[1:])] if isinstance(n,str) else d["nodes"][n]


def member_cost(d, lv, m):
    spec=bridge.MATERIALS[m[2]]
    return math.dist(*(point(d,lv,q) for q in m[:2]))*spec["cost_m"]+spec["cost_each"]


def mutations(d, b, rng):
    lv=b.lv
    ms=d["members"]
    mode=rng.choices(["delete","mat","prune","shift","move","merge","gap","replace","shear"],
                     [13,11,4,16,10,7,17,5,4])[0]
    j=rng.randrange(len(ms))
    m=ms[j]
    if mode == "delete":
        if m[2]=="hydraulic": return
        ms.pop(j)
        compact(d)
    elif mode=="mat":
        if m[2]=="hydraulic": return
        m[2]=rng.choice(["cable","wood","wood","road","steel"] if b.k!=5 else ["cable","steel"])
    elif mode=="prune":
        # Collapse an intermediate node that only divides a straight load path.
        n=rng.randrange(len(d["nodes"]))
        inc=[m for m in ms if n in m[:2]]
        if len(inc)<2 or len(inc)>4 or any(m[2]=="hydraulic" for m in inc): return
        others=[m[0] if m[1]==n else m[1] for m in inc]
        a,c=rng.sample(others,2)
        d["members"]=[m for m in ms if n not in m[:2]]
        if not any(set(m[:2])=={a,c} for m in d["members"]):
            d["members"].append([a,c,rng.choice(inc)[2]])
        compact(d)
    elif mode in ("shift","move"):
        n=rng.randrange(len(d["nodes"]))
        x,y=d["nodes"][n]
        step=rng.choice([.08,.18,.35,.65,1.1])
        xx,yy=x+rng.uniform(-step,step),y+rng.uniform(-step,step)
        if mode=="shift":
            xx=x if rng.random()<.5 else xx
            yy=y if xx!=x and rng.random()<.65 else yy
        d["nodes"][n]=[round(xx,4),round(yy,4)]
    elif mode=="merge":
        n=rng.randrange(len(d["nodes"]))
        x,y=d["nodes"][n]
        available=list(range(len(d["nodes"]))) + [f"A{i}" for i in range(len(lv["anchors"]))]
        near=sorted((math.dist((x,y),point(d,lv,q)),i,q) for i,q in enumerate(available) if q!=n)
        dest=rng.choice(near[:rng.randint(1,min(4,len(near)))])[2]
        edges={}
        for m in ms:
            m[:2]=[dest if q==n else q for q in m[:2]]
            if m[0]==m[1] or all(isinstance(q,str) for q in m[:2]): continue
            key=frozenset(m[:2])
            if key not in edges or m[2]=="road":
                edges[key]=m
        d["members"]=list(edges.values())
        compact(d)
    elif mode=="gap":
        if m[2]!="road": return
        f=rng.uniform(.25,.78)
        a,c=m[:2]
        pa,pc=point(d,lv,a),point(d,lv,c)
        n=len(d["nodes"])
        d["nodes"].append([round(u+f*(v-u),5) for u,v in zip(pa,pc)])
        mat=rng.choice(["wood","wood","cable"]) if b.k!=5 else "cable"
        mats=[mat,"road"];rng.shuffle(mats)
        ms[j]=[a,n,mats[0]];ms.append([n,c,mats[1]])
    elif mode=="replace":
        if m[2]=="hydraulic": return
        e=rng.randrange(2)
        orig=m[e]
        ns=list(range(len(d["nodes"])))+[f"A{i}" for i in range(len(lv["anchors"]))]
        ns=[q for q in ns if q not in m[:2]]
        if not ns:return
        ns.sort(key=lambda q:math.dist(point(d,lv,orig),point(d,lv,q)))
        m[e]=rng.choice(ns[:4])
        compact(d)
    else:
        # Scale the elevation of an entire arch/truss, not just one joint.
        f=rng.uniform(.8,1.15)
        ybase=rng.choice([0,0,-1,1])
        for p in d["nodes"]:
            p[1]=round(ybase+(p[1]-ybase)*f,5)
    return d


def trim(k,secs,seed=1):
    b=Bench(k,{1:[2,1,0],2:[1,0],3:[1,0,2],4:[1,0],5:[1,0],6:[0,2,1]}.get(k))
    rng=random.Random(seed)
    end=time.monotonic()+secs
    cur=bridge.load_json(target(k))
    best=b.existing()
    attempts=passes=0
    seen=set()
    while time.monotonic()<end:
        attempts+=1
        if attempts%100==0 or rng.random()<.01:
            cur=bridge.load_json(target(k));best=b.existing()
        d=mutations(copy.deepcopy(cur),b,rng)
        if not d:continue
        sig=repr(d)
        if sig in seen:continue
        if len(seen)>15000:seen.clear()
        seen.add(sig)
        try:p=bridge.parse_design(b.lv,d)
        except bridge.DesignError:continue
        cost=p["cost"]
        curcost=bridge.parse_design(b.lv,cur)["cost"]
        # Occasionally take a small uphill or cost-neutral step to find a
        # less expensive topology without losing the verified incumbent.
        if cost>curcost and (cost>best*1.012 or rng.random()>0.06*math.exp(-(cost-curcost)/max(10,best*.002))):
            continue
        if cost==curcost and rng.random()>.15:continue
        if b.test(d,save=False,cheaper=False):
            passes+=1;cur=d
            if cost<b.existing():
                from design_lab import write
                write(target(k),d);best=cost
                if attempts%7==0:print("best",k,cost,flush=True)
    print("trim",k,"attempts",attempts,"passes",passes,"best",b.existing(),flush=True)


if __name__=="__main__":
    trim(int(sys.argv[1]),float(sys.argv[2]),int(sys.argv[3]) if len(sys.argv)>3 else 1)
