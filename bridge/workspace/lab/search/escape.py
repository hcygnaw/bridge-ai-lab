import copy
import math
import random
import sys
import time

import bridge
from design_lab import Bench, target, write
from polish import refine


def improve(k,secs):
    b=Bench(k,{4:[1,0],6:[2,1,0],3:[1,0,2]}.get(k))
    rng=random.Random(24365+k);d=bridge.load_json(target(k));lim=time.monotonic()+secs
    # Permit temporarily heavier or stronger designs. A small population
    # includes pristine alternatives as well as designs that pass with breaks.
    pool=[];best=b.existing()
    def run(x):
        try:p=bridge.parse_design(b.lv,x)
        except bridge.DesignError:return
        cost=p['cost']
        if cost>min(b.lv['budget'],best+1350):return
        br=0;worst=0;first=None
        for i in b.order:
            r,_=bridge.simulate(b.lv,p,b.sc[i])
            if not r['ok']:return
            br+=r['bridge_broken'];worst=max(worst,max(r['peak_members']))
            if not first:first=next((e.split() for e in r['events'] if ' BREAK ' in e),None)
        return cost,br,worst,first
    init=run(d);pool=[(init,d)]
    promoted=cnt=0;seen=set()
    while time.monotonic()<lim:
        cnt+=1
        if cnt%120==0:
            best=b.existing();src=bridge.load_json(target(k))
            if src!=d:
                it=run(src)
                if it:pool.append((it,src));d=src
        meta,src=rng.choice(pool)
        x=copy.deepcopy(src);forced=False
        if meta[3] and rng.random()<.30:
            j=int(meta[3][2]);m=x["members"][j];f=float(meta[3][3])
            if m[2]=="wood":m[2]="cable" if f>0 and rng.random()<.65 else "steel";forced=True
            elif m[2]=="cable":m[2]="steel";forced=True
        if not forced:
            x=refine(x,b,rng)
            if not x:continue
        h=repr(x)
        if h in seen:continue
        if len(seen)>15000:seen.clear()
        seen.add(h)
        try:c=bridge.parse_design(b.lv,x)['cost']
        except bridge.DesignError:continue
        if not forced and c>=meta[0]+rng.choice([0,.01,4,50,180]):continue
        v=run(x)
        if not v:continue
        if v[0]<b.existing():
            write(target(k),x);best=v[0];promoted+=1
            if promoted%10==1:print("frontier",k,v[:3],flush=True)
        pool.append((v,x))
        if len(pool)>12:
            # Keep representatives along the cost / damage trade-off.
            chosen=[min(pool,key=lambda p:p[0][0]),min(pool,key=lambda p:(p[0][1],p[0][2],p[0][0]))]
            for weight in [5,15,35,70,100,150,230,350]:
                a=min(pool,key=lambda p:p[0][0]+p[0][1]*weight+p[0][2]*weight*.25+rng.uniform(0,40))
                if a not in chosen:chosen.append(a)
            remaining=list(pool)
            rng.shuffle(remaining)
            for z in remaining:
                if len(chosen)>=10:break
                if z not in chosen:chosen.append(z)
            pool=chosen
    print("frontier done",k,cnt,promoted,b.existing(),flush=True)


if __name__=="__main__":
    improve(int(sys.argv[1]),float(sys.argv[2]))
