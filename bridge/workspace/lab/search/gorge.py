import copy
import math
import random
import sys
import time

import bridge
from design_lab import Bench, Design, write
from shoulders import shoulder, suspended_center
from trusses import bar
from ribbons import control


def build(s):
    d=Design(2);ends=[]
    for j in [0,1]:
        base=["A0","A4"][j];foot=(["A2","A6"] if s["deep"] else ["A1","A5"])[j]
        tip=shoulder(d,base,foot,1-2*j,s["n"],s["length"],s["y"],s["upper"],s["bottom"],s["spine"])
        if s["tie"]:bar(d,base,tip,"cable")
        # A short brace to the intermediate anchor limits the first rib's rotation.
        if s["extra"] and s["deep"]:
            x=0 if not j else 30
            cand=[q for q,p in enumerate(d.nodes) if p[1]<-1 and abs(p[0]-x)<s["length"]*.76]
            if cand:bar(d,["A1","A5"][j],min(cand,key=lambda q: abs(d.pos(q)[0]-x)))
        ends.append(tip)
    suspended_center(d,*ends,s["nc"],s["sag"],s["cbr"],s["bump"])
    control(d,30,-s["length"]+s["light"],s["green"],s["green"])
    return d


def run(secs):
    b=Bench(2,[1,0]);rng=random.Random(28655);lim=time.monotonic()+secs;cnt=0;pool=[]
    while time.monotonic()<lim:
        n=rng.choice([2,3,3,4,5]);length=n*rng.uniform(1.45,2.38)
        s0=dict(n=n,length=length,y=rng.uniform(-1.4,1.3),deep=rng.randrange(2),spine=rng.choice(["wood","wood","steel"]),
                upper=rng.uniform(-.45,.65),bottom=rng.uniform(-.5,1.45),tie=rng.randrange(2),extra=rng.randrange(2),
                nc=math.ceil((30-2*length)/rng.uniform(1.5,2.38)),sag=rng.uniform(.09,.16)*(30-2*length),
                cbr=rng.choice([0,0,1,2]),bump=rng.uniform(-.15,.15),light=rng.uniform(.1,2.),green=rng.uniform(7,11))
        if pool and rng.random()<.78:
            s=copy.deepcopy(rng.choice(pool)[1])
            for key in rng.sample(list(s0),rng.randint(1,4)):s[key]=s0[key]
        else:s=s0
        d=build(s);cnt+=1
        try:p=bridge.parse_design(b.lv,d.raw())
        except bridge.DesignError:continue
        if p["cost"]>=b.existing():continue
        r,_=bridge.simulate(b.lv,p,b.sc[1])
        if r["ok"] and b.test(d,tag="interior launch lines"):write("scratch/gorge2.json",s)
        # Normalise arrival-side progress using frame positions for promising nonbroken geometries.
        if r["broken"]>3 and rng.random()>.06:continue
        r,rep=bridge.simulate(b.lv,p,b.sc[1],replay=True)
        ix=2*rep["vehicles"][0]["p0"]+2
        reach=30-min((f["p"][ix] for f in rep["frames"] if f["v"][0]==1 and f["p"][ix+1]>-6),default=44)
        value=reach+(8 if r["ok"] else 0)-.16*min(10,r["broken"])-.5*bool(r["anomaly"])
        if (len(pool)<30 or value>pool[-1][0]) and not any(q==s for _,q in pool):
            pool.append((value,s));pool.sort(reverse=True,key=lambda v:v[0]);pool=pool[:30]
    print("gorge",cnt,b.existing(),pool[0][0] if pool else None,flush=True)


if __name__=="__main__":
    run(float(sys.argv[1]))
