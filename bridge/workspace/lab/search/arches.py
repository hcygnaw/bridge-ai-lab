import math
import random
import sys
import time

import bridge
from design_lab import Bench, Design
from trusses import bar, warren
from ribbons import control


def smallfan(d,a,b,n,rise,depth,step,foot,web="wood",chord="wood",q=.5,skew=0,mode=0):
    p0,p1=d.pos(a),d.pos(b)
    def at(t,dh=0):
        x=p0[0]+(p1[0]-p0[0])*t
        y=p0[1]+(p1[1]-p0[1])*t+rise*4*t*(1-t)*(1+skew*(t-.5))
        return d.n(x,y+dh)
    ns=[a]+[at(i/n) for i in range(1,n)]+[b]
    for z,u in zip(ns,ns[1:]):bar(d,z,u,"road")
    # Each macrocell triangulates two or three roadway panels from a
    # single hub. Neighbouring cells share their vertex and flange.
    hubs=[];joint=[0]+list(range(step,n,step))+[n]
    for l,r in zip(joint,joint[1:]):
        t=(l+r)/2/n
        h=at(t,depth*(1-q+q*4*t*(1-t)))
        for i in range(l,r+1):
            L=math.dist(d.pos(ns[i]),d.pos(h))
            m=web if not (mode&1) or i in (l,r) else "cable" if depth>0 else "wood"
            if L>3 and L<=4 and mode&2 and m=="wood":m="spring"
            bar(d,h,ns[i],m)
        if hubs:
            bar(d,hubs[-1],h,chord)
        hubs.append(h)
    for f,h in zip(foot,(hubs[0],hubs[-1])):
        if f:bar(d,f,h)
    return ns,hubs


def gen(k,s):
    d=Design(k)
    if k==1:right,feet="A2",["A1","A3"]
    elif k==2:right,feet="A4",["A1","A5"]
    elif k=="final":right,feet="A3",["A1","A4"]
    else:right,feet="A3",["A1","A4"]
    if k==3:
        mid=d.n(14,s["mid"])
        if mid!="A2":bar(d,"A2",mid,"steel" if s["mid"]>-2.25 else "wood")
        blocks=[("A0",mid,[feet[0],"A2"]),(mid,right,["A2",feet[1]])]
    else:
        blocks=[("A0",right,feet)]
    for a,b,ft in blocks:
        ft=ft if s["foot"] else [None,None]
        z,hs=smallfan(d,a,b,s['n'],s['r'],s['h'],s['step'],ft,s['web'],s['chord'],s['q'],mode=s['mode'])
        if s['leg']:
            for f,nd in [(ft[0],z[1]),(ft[1],z[-2])]:
                if f:bar(d,f,nd)
    if k==3 and s["light"]:
        control(d,28,1,0,17)
    return d


def search(k,secs):
    b=Bench(k,{1:[1,2,0],2:[1,0],3:[1,0,2]}.get(k))
    rng=random.Random(498+(0 if k=="final" else k))
    w={1:15,2:30,3:14,"final":28}[k]
    end=time.monotonic()+secs;cnt=0
    while time.monotonic()<end:
        n=rng.randint(math.ceil(w/2.42),math.ceil(w/1.30))
        s=dict(n=n,r=rng.uniform(-.08,.22)*w,h=rng.uniform(.25,2.4)*rng.choice([-1,1]),step=rng.choice([1,1,2,2,2,3]),
               foot=rng.randrange(2),web="wood",chord=rng.choice(["wood","wood","cable","steel"]),q=rng.uniform(-.5,1.05),
               mode=rng.randrange(4),leg=rng.randrange(2),mid=rng.uniform(-2.2,.25),light=rng.randrange(2))
        d=gen(k,s);cnt+=1
        if b.test(d,tag=(n,round(s["r"],2),round(s["h"],2),s["step"])):
            from design_lab import write
            write(f"scratch/arch{k}.json",s)
    print("arch",k,cnt,b.existing(),flush=True)


if __name__=="__main__":
    search(int(sys.argv[1]),float(sys.argv[2]))
