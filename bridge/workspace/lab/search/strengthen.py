import copy
import math
import random

import bridge
from design_lab import Bench, target, write
from lifts import suspended
from trusses import bar
from trim import point, compact


def repair(b,raw,limit=20,verbose=False):
    if not isinstance(raw,dict):raw=raw.raw()
    d=copy.deepcopy(raw)
    for step in range(limit):
        try:p=bridge.parse_design(b.lv,d)
        except bridge.DesignError as e:
            if verbose:print("illegal:",str(e).splitlines()[:2])
            return
        if p["cost"]>=b.existing():return
        for i in b.order:
            r,_=bridge.simulate(b.lv,p,b.sc[i])
            if not r["ok"]:break
        else:
            if p["cost"]<b.existing():
                write(target(b.k),d);print("PASS",b.k,p["cost"],"repairs",step,flush=True)
            return d
        ev=[e.split() for e in r["events"] if " BREAK " in e]
        if not ev:return
        _,_,j,force=ev[0]
        m=d["members"][int(j)]
        if verbose:print(p["cost"],i+1,ev[0],m)
        mat=m[2];tension=float(force)>0
        if mat=="wood":
            m[2]="cable" if tension else "steel"
        elif mat=="cable":
            m[2]="steel"
        elif mat=="steel" and math.dist(*(point(d,b.lv,q) for q in m[:2]))<5 and not b.lv.get("static_only"):
            m[2:]=["hydraulic","strut"]
        elif mat=="road" or mat=="steel":
            # Add a short triangular arch rib to share axial thrust.
            a,c=(point(d,b.lv,q) for q in m[:2])
            n=len(d["nodes"]);d["nodes"].append([round((a[0]+c[0])/2,5),round((a[1]+c[1])/2-.16,5)])
            for q in m[:2]:d["members"].append([q,n,"steel"])
            near=sorted((math.dist(point(d,b.lv,q),d["nodes"][n]),q) for q in range(n) if q not in m[:2])
            for dist,q in near:
                if dist<.3:continue
                d["members"].append([n,q,"wood" if dist<=3 else "steel"]);break
        else:return


def six(n=7,h=2.2,chord="cable",taper=.75,app_h=1.6,app_rise=.35,app_n=6,nlegs=1,lag=5,lash=1,down=2.55):
    d=suspended(6,n,h,0,chord=chord,taper=taper,app_n=app_n,app_h=app_h,app_rise=app_rise,lag=lag,lash=lash,down=down)
    for side in [0,1]:
        stops=sorted((i for i,p in enumerate(d.nodes) if p[1]>=0 and (p[0]<11.8 if side==0 else p[0]>24.2)),
                     key=lambda i: abs(36*side-d.pos(i)[0]))
        for i in range(min(nlegs,len(stops))):
            root=("A1" if side==0 else "A7") if i==0 else ("A2" if side==0 else "A8")
            ni=stops[i]; length=math.dist(d.pos(root),d.pos(ni))
            if length<6:bar(d,root,ni,"wood" if length<2.8 else "steel")
    return d


if __name__=="__main__":
    import itertools
    b=Bench(6)
    cases=list(itertools.product((6,7,8),(1.45,1.9,2.4),("cable","wood"),(.5,.8),
                                 (1.3,1.7,2.1),(.4,1.1,-.4),(6,7),(0,1,2)))
    random.Random(26).shuffle(cases)
    for j,args in enumerate(cases[:750]):
        d=six(*args); res=repair(b,d)
        if res:print("from",args,flush=True);break
