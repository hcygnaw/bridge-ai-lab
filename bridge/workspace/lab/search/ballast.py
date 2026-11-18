import copy
import math
import random
import sys
import time
from pathlib import Path

import bridge
import saboteur
from design_lab import Bench, SUB, target, write
from duel_lab import trainset, matches
from final_trials import bounce
from arches import gen


def rivals(b):
    fp=Path("scratch/arch-rivals.json")
    if fp.exists():return [bridge.parse_design(b.lv,x) for x in bridge.load_json(fp)]
    rng=random.Random(92113);out=[]
    for i in range(1200):
        s=dict(n=rng.randint(13,20),r=rng.choice([-1,1])*rng.uniform(1,4.1),h=-rng.uniform(1.25,2.7),step=1,
               foot=rng.randrange(2),web="wood",chord=rng.choice(["wood","wood","steel","cable"]),
               q=rng.uniform(-.25,.78),mode=rng.randrange(4),leg=rng.randrange(2),mid=0,light=0)
        d=gen("final",s).raw()
        for j in range(7):
            try:p=bridge.parse_design(b.lv,d)
            except bridge.DesignError:break
            r,_=bridge.simulate(b.lv,p,b.sc[0])
            if r["ok"]:
                out.append(copy.deepcopy(d));break
            first=next((e.split() for e in r["events"] if " BREAK " in e),None)
            if not first:break
            m=d["members"][int(first[2])]
            if m[2]=="wood":m[2]="steel"
            elif m[2]=="cable":m[2]="steel"
            else:break
        if len(out)==5:break
    write(fp,out)
    return [bridge.parse_design(b.lv,x) for x in out]


def variant(s,b):
    w,h=s["w"],s["h"]
    d=bounce(w,speed=s["speed"],gate=s["x"],h=h,ratio=s["rt"],period=s["period"])
    d['members'][2][3]="q"
    d["ballast"]=[]
    total=saboteur.parse_sab(b.lv,d)['mass']
    available=2499-total
    d["ballast"]=[[2,round(available*s["bal"],3)],[3,round(available*(1-s["bal"]),3)]]
    d["rules"]=[]
    for j in range(4):
        rt=s["rt"] if not j%2 else s["low"]
        r2=max(.5,min(2,rt+s["bias"]*(1 if not j%2 else -1)))
        diag=math.hypot(w,r2*(h-.22))/math.hypot(w,h-.22)
        for key,r,dt in [("p",rt,0),("q",r2,s["lag"]),("d",diag,s["lag"])]:
            d['rules'].append(dict(on="g",delay=round(j*s["period"]+dt,5),do="hyd",group=key,ratio=round(r,6),speed=3,accel=5))
    return d


def run(secs):
    b=Bench("final");rng=random.Random(592135)
    basic=trainset(b);arch=rivals(b)
    # Mix families; the first two will also be used for interim screening.
    ps=[basic[0],*(arch[:2]),*basic[1:],*arch[2:]]
    base=bridge.load_json(SUB/"saboteur.json")
    elite=dict(w=1.515,h=.9954,rt=1.56,period=.72,speed=8.637,x=20.786,bal=.57,lag=0,bias=0,low=.7)
    best,tr=matches(b,ps,base);winners=[(best,elite)];cnt=0
    print("rivals",len(ps),"baseline",best,flush=True)
    end=time.monotonic()+secs
    while time.monotonic()<end:
        s=copy.deepcopy(rng.choice(winners)[1])
        bounds=dict(w=(.48,2.95),h=(.61,1.49),rt=(1.03,1.99),period=(.28,1.08),speed=(6.,10.),x=(4.,28.4),
                    bal=(.04,.96),lag=(0,.34),bias=(-.80,.70),low=(.51,1.05))
        for key in rng.sample(list(bounds),rng.choice([1,2,2,3,4,5])):
            a,c=bounds[key]
            s[key]=rng.uniform(a,c) if rng.random()<.54 else max(a,min(c,s[key]+rng.gauss(0,(c-a)*.10)))
        try:
            d=variant(s,b);score,tr=matches(b,ps,d)
        except bridge.DesignError:continue
        cnt+=1
        if score>best:
            best=score;write(SUB/"saboteur.json",d);print("ballast",cnt,best,flush=True)
        if (len(winners)<9 or score>winners[-1][0]) and not any(q==s for _,q in winners):
            winners.append((score,s));winners.sort(reverse=True,key=lambda v:v[0]);winners=winners[:9]
    print("ballast done",cnt,best,flush=True)


if __name__=="__main__":
    run(float(sys.argv[1]))
