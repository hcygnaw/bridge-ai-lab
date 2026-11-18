import copy
import math
import random
import sys
import time
from pathlib import Path

import bridge
import saboteur
from design_lab import Bench, SUB, target, write
from fan import stayed
from final_trials import cart, bounce
from trusses import standard


def rocker(wb=1.65,pivotx=-1.52,height=.75,arm=1.44,f=.35,mass=2499,speed=9.7,
           tilt=-.20,where=17,ratio=1.9,period=.65,swap=False):
    # A compact, pin-jointed ballast arm. All moving parts are carried on
    # the chassis, and strictly obey the vehicle's hydraulic speed limits.
    piv=(pivotx,height)
    u=(pivotx+arm*f*math.cos(tilt),height+arm*f*math.sin(tilt))
    v=(pivotx+arm*math.cos(tilt),height+arm*math.sin(tilt))
    aux=(pivotx+arm*.68*math.cos(tilt)-.19*math.sin(tilt),
         height+arm*.68*math.sin(tilt)+.19*math.cos(tilt))
    raw=dict(nodes=[[0,.22],[-wb,.22],list(piv),list(u),list(v),list(aux)],wheels=[0,1],
             members=[[0,1,"steel"],[0,2,"steel"],[1,2,"steel"],[2,3,"steel"],[3,4,"steel"],
                      [2,5,"steel"],[3,5,"steel"],[4,5,"steel"],[0 if swap else 1,3,"hydraulic","p"]],
             motor=dict(speed=speed,accel=4),sensors=[dict(id="g",type="mygate",x=where)],rules=[])
    b=Bench("final")
    prior=saboteur.parse_sab(b.lv,raw)["mass"]
    raw["ballast"]=[[4,math.floor((mass-prior)*1000)/1000]]
    for i,rt in enumerate((ratio,.6,ratio,.6)):
        raw["rules"].append(dict(on="g",delay=round(i*period,4),do="hyd",group="p",ratio=rt,speed=3,accel=5))
    return raw


def beams(b,rng):
    for i in range(2500):
        if i%3:
            n=rng.choice([12,14,16,18]);cap=rng.uniform(4.4,8.5);inset=rng.uniform(.25,4.2)
            d=stayed("final",n,cap,inset,rng.choice([1,1,2]),rng.uniform(-1.3,1.8))
            if i%2==0:
                # Vary restraint and the position of two stays.
                for m in d.members:
                    if m[2]=="cable" and rng.random()<.08:
                        if all(isinstance(q,int) for q in m[:2]) and math.dist(*(d.pos(q) for q in m[:2]))<6:m[2]="steel"
        else:
            n=rng.randint(13,20);h=rng.uniform(1.05,3.8);rise=rng.uniform(-2.2,2.4)
            d=standard("final",n,h,rise,rng.choice(["wood","steel","cable"]),web="wood",brace=rng.randrange(2))
            for m in d.members:
                if m[2]=="wood" and rng.random()<.37:m[2]="steel"
        try:p=bridge.parse_design(b.lv,d.raw())
        except bridge.DesignError:continue
        if bridge.simulate(b.lv,p,b.sc[0])[0]["ok"]:
            yield p


def trainset(b):
    path=Path("scratch/benchbridges.json")
    if path.exists():return [bridge.parse_design(b.lv,d) for d in bridge.load_json(path)]
    raw=[stayed("final",14,6,1,1,0).raw(),bridge.load_json(target("final"))]
    for p in beams(b,random.Random(613)):
        raw.append(p["raw"])
        if len(raw)==12:break
    write(path,raw)
    return [bridge.parse_design(b.lv,d) for d in raw]


def matches(b,ps,c):
    s=saboteur.parse_sab(b.lv,c)
    veh=saboteur.sab_vehicle(b.lv,s,.5)
    wins=arr=0;trace=[]
    for p in ps:
        r,_=bridge.simulate(b.lv,p,b.sc[0],sab=veh)
        finish=(r["sab"]["status"]==2 and r["sab"]["t"]<=12 and not r['anomaly'])
        w=finish and not all(v["status"]==2 for v in r["std_vehicles"])
        wins+=int(w);arr+=int(finish);trace.append((bool(w),finish,r["bridge_broken"],r["anomaly"]))
    return (wins,arr,sum(min(6,t[2]) for t in trace if t[1]),-sum(bool(t[3]) for t in trace)),trace


def optimize(secs):
    b=Bench("final");rng=random.Random(9207);ps=trainset(b)
    path=SUB/"saboteur.json";best,trace=matches(b,ps,bridge.load_json(path))
    print("start",len(ps),best,flush=True)
    start=time.monotonic();j=0;elite=[]
    while time.monotonic()-start<secs:
        j+=1
        params={}
        try:
            if j%5==1:
                c=cart(rng.uniform(.32,2.98),rng.uniform(2250,2499),rng.uniform(5.8,10),rng.uniform(.02,.98))
            elif j%5==2:
                c=bounce(span=rng.uniform(.5,2.4),speed=rng.uniform(6.,10),gate=rng.uniform(-3,24),h=rng.uniform(.7,1.42),
                         ratio=rng.uniform(1.2,1.98),period=rng.uniform(.28,.92))
            elif elite and j%5==0:
                c=copy.deepcopy(rng.choice(elite));s=c["motor"];s["speed"]=max(5,min(10,s["speed"]+rng.gauss(0,.35)))
                if "sensors" in c:c["sensors"][0]["x"]+=rng.gauss(0,1.8)
                if "rules" in c:
                    f=rng.uniform(.8,1.2)
                    for r in c["rules"]:r["delay"]*=f
            else:
                wb=rng.uniform(1.1,2.9);arm=rng.uniform(.9,2.3);px=-max(arm+.025,wb+rng.uniform(-.45,.1))
                c=rocker(wb,px,rng.uniform(.57,1.15),arm,rng.uniform(.28,.57),speed=rng.uniform(6.5,10),
                         tilt=rng.uniform(-.23,.1),where=rng.uniform(3,25),ratio=rng.uniform(1.25,1.99),period=rng.uniform(.29,.98),swap=rng.randrange(2))
            res,ts=matches(b,ps,c)
        except bridge.DesignError:continue
        if res>best:
            best=res;write(path,c);print("sab",j,best,flush=True)
        if res[0]>=max(1,best[0]-1):
            elite.append(c);elite=elite[-24:]
    print("finished",j,best,flush=True)


if __name__=="__main__":
    optimize(float(sys.argv[1]) if len(sys.argv)>1 else 180)
