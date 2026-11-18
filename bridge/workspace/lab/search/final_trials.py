import copy
import math
import random

import bridge
import saboteur
from design_lab import Bench, target, write
from fan import stayed
from trusses import bar


def cart(length,mass,speed,front):
    load=mass-160-35*length
    return dict(nodes=[[0,.22],[-length,.22]],members=[[0,1,"steel"]],wheels=[0,1],
                motor=dict(speed=speed,accel=4),ballast=[[0,round(load*front,4)],[1,round(load*(1-front),4)]])


def bounce(span=1.1,mass=2499,speed=9.4,gate=10,h=1.22,ratio=1.92,period=.65):
    raw=dict(nodes=[[0,.22],[-span,.22],[0,h],[-span,h]],wheels=[0,1],
             members=[[0,1,"steel"],[0,2,"hydraulic","p"],[1,3,"hydraulic","p"],[2,3,"steel"],
                      [0,3,"cable"]],motor=dict(speed=speed,accel=4),
             sensors=[dict(id="g",type="mygate",x=gate)],rules=[])
    # One diagonal of controlled length keeps the guided ballast level.
    raw["members"][-1]=[0,3,"hydraulic","d"]
    b=Bench("final")
    prior=saboteur.parse_sab(b.lv,raw)["mass"]
    raw["ballast"]=[[2,round((mass-prior)*.57,3)],[3,round((mass-prior)*.43,3)]]
    for j in range(5):
        rise=ratio if j%2==0 else .7
        diag=math.hypot(span,rise*(h-.22))/math.hypot(span,h-.22)
        for g,rt in [("p",rise),("d",diag)]:
            raw["rules"].append(dict(on="g",delay=round(j*period,3),do="hyd",group=g,ratio=rt,speed=3,accel=5))
    return raw


def reinforced(opts=0,cap=6,inset=1,rise=0):
    d=stayed("final",14,cap,inset,1,rise)
    for i in (0,1):
        bank=("A2","A5")[i]
        top=d.n(inset if not i else 28-inset,cap)
        bx,by=d.pos(bank);tx,ty=d.pos(top)
        mid=d.n((bx+tx)/2,(by+ty)/2+.05)
        bar(d,mid,top,"steel");bar(d,mid,bank,"steel")
        if opts&1:
            lower=d.n(tx + (-1 if not i else 1)*inset/3,cap*2/3)
            bar(d,mid,lower,"wood" if math.dist(d.pos(mid),d.pos(lower))<3 else "cable")
        if opts&2:
            root=("A0","A3")[i]
            loc=d.n(tx+(-1 if not i else 1)*inset/3,cap*2/3)
            bar(d,root,loc,"steel")
        if opts&4:
            node=d.n(12 if not i else 16,rise*4*(12/28)*(16/28))
            tx1=d.n(tx+(-1 if not i else 1)*inset/3,cap*2/3)
            bar(d,tx1,node,"cable")
    return d


def challenges():
    return [cart(l,2499,v,f) for l,v,f in [(.42,10,.97),(2.9,10,.03),(1.2,8,.95),(.6,6,.05),
             (1.7,7,.55),(2.6,9,.48)]]+[bounce()]


def stress(raw,vehicles=None):
    b=Bench("final")
    p=bridge.parse_design(b.lv,raw)
    tests=challenges() if vehicles is None else vehicles
    score=[]
    for c in [None]+tests:
        sv=saboteur.sab_vehicle(b.lv,saboteur.parse_sab(b.lv,c),.5) if c else None
        r,_=bridge.simulate(b.lv,p,b.sc[0],sab=sv)
        score.append((all(v['status']==2 for v in r['std_vehicles']) and not r['anomaly'],r["bridge_broken"],max(r['peak_members'])))
    return (sum(x[0] for x in score), -sum(x[1] for x in score),-max(x[2] for x in score),-sum(x[2] for x in score)),score


if __name__=="__main__":
    import itertools
    b=Bench("final")
    incumbent=bridge.load_json(target("final"))
    best,_=stress(incumbent)
    print("base",best,flush=True)
    for cap,inset,rise,opt in itertools.product((6,6.6,7.2,5.5),(1,1.8,.5),(0,.5,-.4),(0,1,2,4,3)):
        d=reinforced(opt,cap,inset,rise)
        try:score,details=stress(d.raw())
        except bridge.DesignError:continue
        if details[0][0] and score>best:
            best=score;write(target("final"),d.raw());print("defense",best,(cap,inset,rise,opt),flush=True)
