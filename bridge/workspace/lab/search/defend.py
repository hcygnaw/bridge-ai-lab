import copy
import math
import random
import sys
import time

import bridge
import saboteur
from design_lab import Bench, target, write
from final_trials import bounce, challenges, stress


def improve(d,b,rng):
    ps=d["nodes"];ms=d["members"]
    def pos(q):return b.lv['anchors'][int(q[1:])] if isinstance(q,str) else ps[q]
    def add(x,y):
        i=len(ps);ps.append([round(x,5),round(y,5)]);return i
    twin=rng.random()<.85
    fix=rng.random()<.85
    dx=rng.uniform(-1.6,1.4);dy=rng.uniform(-.6,.7)
    for j in [0,1]:
        sign=1-2*j;foot=["A1","A4"][j];root=["A0","A3"][j]
        mid=[13,16][j];upper=[14,17][j];head=[15,18][j]
        x,y=ps[mid];ps[mid]=[round(x+sign*dx,5),round(y+dy,5)]
        if fix:
            m=next((m for m in ms if set(m[:2])=={mid,foot}),None)
            if m:
                # Anchor the intermediate node laterally to the abutment.
                x,y=ps[mid];fx,fy=pos(foot)
                u=add((x+fx)/2+sign*rng.uniform(.22,.62),(y+fy)/2)
                ms.remove(m);ms.extend([[mid,u,"steel"],[u,foot,"steel"],[u,root,"steel"]])
        if twin:
            x,y=ps[mid];u=add(x+sign*rng.uniform(.42,1.65),y+rng.uniform(-.2,.2))
            ms.extend([[u,root,"steel"],[u,upper,"steel"],[u,mid,"wood"]])
        if rng.random()<.5:
            ps[head][0]=round(ps[head][0]+sign*rng.uniform(-.4,.75),5)
            ps[head][1]=round(ps[head][1]+rng.uniform(-.4,.7),5)
    return d


if __name__=="__main__":
    b=Bench("final");rng=random.Random(8261);base=bridge.load_json(target("final"))
    best,_=stress(base);lim=time.monotonic()+float(sys.argv[1])
    sv=saboteur.sab_vehicle(b.lv,saboteur.parse_sab(b.lv,bounce()),.5)
    cnt=0
    while time.monotonic()<lim:
        d=improve(copy.deepcopy(base),b,rng)
        try:p=bridge.parse_design(b.lv,d)
        except bridge.DesignError:continue
        cnt+=1;r,_=bridge.simulate(b.lv,p,b.sc[0],sab=sv)
        if not all(v["status"]==2 for v in r["std_vehicles"]) or r["anomaly"]:continue
        v,ts=stress(d)
        if v>best and ts[0][0]:
            best=v;write(target('final'),d);print("strong",v,flush=True)
    print("defense trials",cnt,best,flush=True)
