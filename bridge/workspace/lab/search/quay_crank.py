import copy
import math
import random
import sys
import time

import bridge
from design_lab import Bench, Design, write
from trusses import bar


def crank(s):
    d=Design(5)
    x,y=s["x"],s["y"]
    hi=d.n(x,y);lo=d.n(x,y-2)
    bar(d,"A0",hi,s["upper"])
    bar(d,"A1",lo,s["lower"])
    bar(d,hi,lo,"steel")
    le=s["length"];n=s["n"];ns=[]
    for i in range(n):
        t=(n-i)/n
        z=d.n(x-le*t,y-2+s["slope"]*le*t+s["bump"]*4*t*(1-t))
        ns.append(z)
        if i:bar(d,ns[i-1],z,"road")
        bar(d,hi,z,s["web"])
    bar(d,ns[-1],lo,"road");ns.append(lo)
    act=ns[s["act"]%len(ns)] if s["act"]>=0 else hi
    bar(d,s["base"],act,"hydraulic","pad")
    d.sensors=[dict(id="g",type="gate",x=s["gate"],dir="right")]
    d.rules=[dict(on="g",delay=0,do="hyd",group="pad",ratio=s["rt"],speed=s["speed"],accel=s["acc"]),
             dict(on="g",delay=s["reset"],do="hyd",group="pad",ratio=1,speed=6,accel=28)]
    return d


def grade(b,d,sc):
    p=bridge.parse_design(b.lv,d.raw())
    r,rep=bridge.simulate(b.lv,p,sc,replay=True)
    ix=2*rep["vehicles"][0]["p0"]+2
    pts=[f["p"][ix:ix+2] for f in rep["frames"] if f["v"][0]==1]
    reach=max((q[0] for q in pts if q[1]>-.2),default=-16)
    return (3 if r["ok"] and not r["broken"] else 2 if r["ok"] else 1 if not r["broken"] else 0,
            min(33,reach),-p["cost"])


def search(secs):
    b=Bench(5);rng=random.Random(74177)
    end=time.monotonic()+secs;cnt=0;best=None;pop=[]
    sc=dict(name="crank probe",vehicles=[{"type":"van","from":"left","t":1}])
    while time.monotonic()<end:
        x=rng.uniform(-5,-2.8); y=rng.uniform(-.45,1.1);length=rng.uniform(3.35,5.9)
        s=dict(x=x,y=y,length=length,n=rng.choice([2,2,3]),slope=rng.uniform(.27,.58),bump=rng.uniform(-.15,.15),
               upper=rng.choice(["steel","spring","cable"]),lower=rng.choice(["steel","spring","cable"]),
               web=rng.choice(["cable","steel"]),act=rng.choice([0,1,1,2,-1]),base=rng.choice(["A3","A4","A5","A6"]),
               gate=x-rng.uniform(.55,length-1),rt=rng.uniform(1.48,1.99),speed=rng.uniform(9.5,15),acc=rng.uniform(67,120),reset=rng.uniform(.55,1.25))
        if pop and rng.random()<.54:
            p=copy.deepcopy(rng.choice(pop)[1])
            for key in rng.sample(list(s),rng.choice([1,2,3,4])):p[key]=s[key]
            s=p
        d=crank(s)
        try:p=bridge.parse_design(b.lv,d.raw())
        except bridge.DesignError:continue
        if p["cost"]>=b.existing():continue
        cnt+=1
        val=grade(b,d,sc)
        if not best or val>best:
            best=val;write("scratch/crank-near.json",s);print("crank",cnt,val,flush=True)
        if not pop or val>min(v for v,par in pop) or rng.random()<.025:
            if not any(par==s for _,par in pop):
                pop.append((val,s));pop.sort(key=lambda t:t[0],reverse=True);pop=pop[:30]
        if val[0]>=2 and b.test(d,tag=s):write("scratch/crank5.json",s)
    print("crank done",cnt,best,b.existing(),flush=True)


if __name__=="__main__":
    search(float(sys.argv[1]))
