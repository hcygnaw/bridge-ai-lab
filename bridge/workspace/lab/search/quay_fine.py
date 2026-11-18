import copy
import math
import random
import sys
import time

import bridge
from design_lab import Bench, target, write


def build(s,base):
    d=copy.deepcopy(base)
    for (p0,p),move in zip(zip(base["nodes"],d["nodes"]),s["moves"]):
        p[:]=[round(p0[0]+move[0],5),round(p0[1]+move[1],5)]
    for j in (0,1,2,3,5):d["members"][j][2]=s["m"][j]
    d["sensors"][0]["x"]=round(s["g"],5)
    r=d["rules"][0]
    r.update(speed=round(s["sp"],5),ratio=round(s["rt"],6),accel=round(s["acc"],5))
    return d


def change(s,rng):
    s=copy.deepcopy(s)
    j=rng.randrange(4)
    sigma=rng.choice([.05,.14,.35,.68])
    if rng.random()<.54:
        for _ in range(rng.choice([1,1,2,3])):
            j=rng.randrange(4);k=rng.randrange(2);s["moves"][j][k]+=rng.gauss(0,sigma)
    if rng.random()<.32:
        j=rng.choice([0,1,2,3,5]);s["m"][j]=rng.choice(["cable","steel","spring"])
    for k,lo,hi,st in [("g",-7.7,-5.7,.17),("sp",8,15,.8),("rt",1.25,2,.07),("acc",70,120,5)]:
        if rng.random()<.32:s[k]=max(lo,min(hi,s[k]+rng.gauss(0,st)))
    return s


def search(secs):
    b=Bench(5);rng=random.Random(43711);base=bridge.load_json(target(5))
    if len(base["members"])!=8 or len(base["nodes"])!=4:return
    r=base["rules"][0]
    initial=dict(m={j:base["members"][j][2] for j in (0,1,2,3,5)},moves=[[0.,0.] for _ in range(4)],
                 sp=r['speed'],rt=r['ratio'],acc=r["accel"],g=base["sensors"][0]["x"])
    feasible=[initial];near=[];cnt=0;good=0;lim=time.monotonic()+secs;best=b.existing()
    while time.monotonic()<lim:
        parent=rng.choice(feasible) if not near or rng.random()<.5 else rng.choice(near)[1]
        s=change(parent,rng);d=build(s,base);cnt+=1
        try:p=bridge.parse_design(b.lv,d)
        except bridge.DesignError:continue
        if p["cost"]>=best+180:continue
        result,_=bridge.simulate(b.lv,p,b.sc[0])
        if result["ok"] and b.test(d,save=False,cheaper=False):
            good+=1
            feasible.append(s);feasible=sorted(feasible,key=lambda z:bridge.parse_design(b.lv,build(z,base))['cost'])[:22]
            if p["cost"]<b.existing():
                best=p["cost"];write(target(5),d)
                if good%8==1:print("quay-fine",best,flush=True)
        elif p["cost"]<best-5:
            pts=sum(v["status"]==2 for v in result["vehicles"])
            if pts or (not result["broken"] and rng.random()<.045):
                val=(pts,-min(3,result["broken"]),-bool(result["anomaly"]),-p["cost"]+rng.uniform(0,35))
                near.append((val,s));near.sort(key=lambda t:t[0],reverse=True);near=near[:18]
    print("quay-fine done",cnt,good,b.existing(),flush=True)


if __name__=="__main__":
    search(float(sys.argv[1]))
