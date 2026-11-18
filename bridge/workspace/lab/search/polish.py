import copy
import math
import random
import sys
import time

import bridge
from design_lab import Bench, target, write
from trim import compact, member_cost, mutations, point


def refine(d,b,rng):
    mats=bridge.MATERIALS
    ms=d["members"]; ns=d["nodes"]
    def pos(q):return point(d,b.lv,q)
    def dist(a,c):return math.dist(pos(a),pos(c))
    def nc(a,c,t,normal):
        x,y=pos(a);u,v=pos(c);l=math.hypot(u-x,v-y)
        p=[round(x+(u-x)*t-normal*(v-y)/l,5),round(y+(v-y)*t+normal*(u-x)/l,5)]
        ns.append(p);return len(ns)-1
    def nearest(mid,avoid):
        options=list(range(len(ns))) + [f"A{i}" for i in range(len(b.lv["anchors"]))]
        options=[q for q in options if q not in avoid and q!=mid and dist(q,mid)>.3]
        options.sort(key=lambda q:dist(q,mid))
        return options
    mode=rng.choices(["buckling","slot","bypass","edge","column","height","shift","signals","guide","dyn","orig"],
                     [12,12,8,11,7,9,10,3,7,4,12])[0]
    if mode=="orig":return mutations(d,b,rng)
    if mode in ("buckling","slot","bypass","edge","guide"):
        if mode=="buckling":sel=[j for j,m in enumerate(ms) if m[2] in ("steel","cable","spring")]
        elif mode=="slot":sel=[j for j,m in enumerate(ms) if m[2]=="road"]
        elif mode=="guide":sel=[j for j,m in enumerate(ms) if m[2]=="hydraulic" and not any(r.get("group")==m[3] for r in d.get("rules",[]))]
        else:sel=[j for j,m in enumerate(ms) if m[2]!="hydraulic"]
        if not sel:return
        j=rng.choice(sel);m=ms[j];a,c=m[:2]
    if mode=="buckling":
        if b.k==5:return
        t=rng.uniform(.36,.64)
        h=rng.choice([0,0,rng.uniform(-.24,.24)])
        mid=nc(a,c,t,h);ms[j]=[a,mid,"wood"];ms.append([mid,c,"wood"])
        if rng.random()<.78:
            opts=nearest(mid,{a,c})
            z=rng.choice(opts[:min(3,len(opts))]);ms.append([z,mid,rng.choice(["wood","wood","cable"])])
        if rng.random()<.18:ms.append([a,c,"wood"])
    elif mode=="slot":
        gap=rng.uniform(.32,.90) if rng.random()<.73 else rng.uniform(.9,1.55)
        L=dist(a,c)
        if gap>=L-.30:return
        if rng.random()<.5:a,c=c,a
        m0="cable" if b.k==5 else rng.choice(["wood","wood","cable"])
        mid=nc(a,c,gap/L,rng.uniform(-.045,.085))
        ms[j]=[a,mid,m0];ms.append([mid,c,"road"])
        opts=nearest(mid,{a,c})
        # A pin on a split top chord needs a web, not just two collinear bars.
        z=rng.choice(opts[:min(2,len(opts))])
        ms.append([mid,z,("steel" if b.k==5 else rng.choice(["wood","wood","cable"]))])
    elif mode=="bypass":
        # Triangulate through an existing adjacent knot instead of retaining a long spar.
        near=sorted((dist(a,q)+dist(c,q),str(q),q) for q in range(len(ns)) if q not in (a,c))
        if not near:return
        z=rng.choice(near[:min(3,len(near))])[2];ms.pop(j)
        for u in (a,c):
            e=next((m for m in ms if set(m[:2])=={u,z}),None)
            if e is None:
                mat=rng.choice(["cable","wood","wood","steel"])
                ms.append([u,z,mat])
            elif rng.random()<.5:
                e[2]=rng.choice(["road","wood","cable","steel"])
        compact(d)
    elif mode=="edge" or mode=="guide":
        m[2:]=[rng.choice(["cable","wood","wood","spring","steel"])]
        if mode=="guide" and rng.random()<.65:
            i=rng.randrange(2);opts=nearest(m[i],set(m[:2]))
            m[i]=rng.choice(opts[:min(4,len(opts))])
        if mode=="edge" and rng.random()<.23:
            for other in ms:
                if other is not m and other[2]==m[2] and set(other[:2])&set(m[:2]):
                    ms.remove(other);compact(d);break
    elif mode in ("height","column"):
        z=rng.randrange(len(ns));x,y=ns[z]
        rad=rng.uniform(.65,7)
        f=rng.uniform(.65,1.25)
        x0,y0=rng.choice([0,15,12,24,28,30]),rng.choice([0,-1,.5,-2])
        for p in ns:
            weight=max(0,1-abs(p[0]-x)/rad)
            if not weight:continue
            if mode=="height":p[1]=round(y0+(p[1]-y0)*(1+(f-1)*weight),5)
            else:p[0]=round(x+(p[0]-x)*(1+(f-1)*weight),5)
    elif mode=="shift":
        i=rng.randrange(len(ns));x,y=ns[i];dx,dy=rng.uniform(-.48,.48),rng.uniform(-.48,.48)
        rad=rng.uniform(.4,3.8)
        for p in ns:
            w=max(0,1-math.dist(p,(x,y))/rad)
            p[0]=round(p[0]+w*dx,5);p[1]=round(p[1]+w*dy,5)
    elif mode=="signals":
        if not d.get("lights"):return
        light=rng.choice(d["lights"]);name=light["id"]
        if rng.random()<.7:
            d["lights"].remove(light);d["rules"]=[r for r in d["rules"] if r.get("light")!=name]
        else:light["dir"]="both"
    elif mode=="dyn":
        if not d.get("rules"):return
        r=rng.choice(d["rules"]);what=rng.choice(["speed","accel","delay","ratio"])
        if what not in r:return
        if what=="delay":r[what]=round(max(0,r[what]+rng.uniform(-.7,.7)),5)
        else:r[what]=round(r[what]*rng.uniform(.91,1.09),5)
    return d


def run(k,secs,seed=878):
    b=Bench(k,{1:[1,2,0],2:[1,0],3:[1,0,2],4:[1,0],5:[1,0],6:[0,2,1]}[k])
    rng=random.Random(seed)
    end=time.monotonic()+secs;cnt=0;acc=0;best=b.existing()
    cur=bridge.load_json(target(k));price=best
    seen=set()
    while time.monotonic()<end:
        cnt+=1
        if cnt%90==0 or rng.random()<.008:
            cur=bridge.load_json(target(k));price=best=b.existing()
        d=refine(copy.deepcopy(cur),b,rng)
        if not d:continue
        key=repr(d)
        if key in seen:continue
        if len(seen)>40000:seen.clear()
        seen.add(key)
        try:p=bridge.parse_design(b.lv,d)
        except bridge.DesignError:continue
        c=p["cost"]
        if c>price and (c>best*1.025 or rng.random()>.10*math.exp(-(c-price)/max(20,price*.008))):continue
        if c==price and rng.random()>.30:continue
        if b.test(d,cheaper=False,save=False):
            cur=d;price=c;acc+=1
            if c<b.existing():
                write(target(k),d);best=c
                if acc%30==1:print("polish",k,c,flush=True)
    print("polished",k,cnt,acc,b.existing(),flush=True)


if __name__=="__main__":
    run(int(sys.argv[1]),float(sys.argv[2]),int(sys.argv[3]) if len(sys.argv)>3 else 878)
