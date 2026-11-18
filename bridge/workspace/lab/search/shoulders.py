import math
import random
import sys
import time

from design_lab import Bench, Design
from ribbons import control
from trusses import bar
from strengthen import repair


def shoulder(d,root,foot,sign,n,length,tip_y,profile,arch,mat="wood",web="wood",end=None):
    x,y=d.pos(root);xf,yf=d.pos(foot)
    if n==0:return root
    up=[root];low=[foot]
    for i in range(1,n+1):
        t=i/n
        top=end if i==n and end is not None else d.n(x+sign*t*length,y*(1-t)+tip_y*t+profile*4*t*(1-t))
        bar(d,up[-1],top,"road")
        # A triangular cantilever: deck, diagonal compression rib and web.
        if i<n:
            bt=d.n(xf+(x+sign*length-xf)*t,yf*(1-t)+tip_y*t+arch*4*t*(1-t))
            bar(d,low[-1],bt,mat)
            bar(d,up[-1] if i>1 else root,bt,web)
            bar(d,bt,top,web)
            low.append(bt)
        else:
            bar(d,low[-1],top,mat)
        up.append(top)
    return up[-1]


def suspended_center(d,a,b,n,sag,braces=0,wiggle=0):
    xa,ya=d.pos(a);xb,yb=d.pos(b)
    ns=[a]
    for j in range(1,n):
        t=j/n
        ns.append(d.n(xa+(xb-xa)*t,ya+(yb-ya)*t-4*t*(1-t)*sag+(wiggle if j%2 else 0)))
    ns.append(b)
    for p,q in zip(ns,ns[1:]):bar(d,p,q,"road")
    if braces==1:
        for i in range(0,n-1,2):bar(d,ns[i],ns[i+2],"cable")
    if braces==2 and n>=4:
        bar(d,a,ns[n//2],"cable");bar(d,b,ns[n//2],"cable")
    return ns


def solve2(k,s):
    d=Design(k)
    if k==1:right,feet="A2",["A1","A3"]
    else:right,feet="A4",["A2" if s["deep"] else "A1","A6" if s["deep"] else "A5"]
    ends=[]
    for i,base in enumerate(["A0",right]):
        ends.append(shoulder(d,base,feet[i],1 if i==0 else -1,s["n"],s["len"],s["end"],
                             s["profile"],s["arch"],s["mat"]))
    suspended_center(d,*ends,s["nc"],s["sag"],s["br"],s["wig"])
    control(d,d.pos(right)[0],s["off"],s["l"],s["r"])
    return d


def solve3(s):
    d=Design(3)
    tip=d.n(14,s["crown"])
    bar(d,"A2",tip,"steel" if s["crown"]>-2.4 else "wood")
    for i,(root,foot) in enumerate([("A0","A1"),("A3","A4")]):
        sign=1 if i==0 else -1
        outside=shoulder(d,root,foot,sign,s["n"],s["len"],s["end"],s["profile"],s["arch"],s["mat"])
        inside=shoulder(d,tip,"A2",-sign,s["ni"],s["li"],s["ei"],s["profile"],s["arch"],s["mat"])
        suspended_center(d,outside,inside,s["nc"],s["sag"],s["br"],s["wig"])
    control(d,28,s["off"],s["l"],s["r"])
    return d


def search(k,secs):
    rng=random.Random(310+k)
    end=time.monotonic()+secs;cnt=0
    b=Bench(k,{1:[1,2,0],2:[1,0],3:[1,0,2]}[k])
    while time.monotonic()<end:
        n=rng.randint(1,5 if k==2 else 2);l=n*rng.uniform(1.3,2.38)
        ni=rng.randint(1,2);li=ni*rng.uniform(1.0,2.35)
        dist=(30 if k==2 else 15)-2*l if k!=3 else 14-l-li
        nc=max(2,math.ceil(dist/2.42)+rng.randint(0,3))
        s=dict(n=n,len=l,nc=nc,deep=rng.randrange(2),ni=ni,li=li,crown=rng.uniform(-2.1,0),
               ei=rng.uniform(-1.55,.55),end=rng.uniform(-1.3,1.3),profile=rng.uniform(-.38,.42),
               arch=rng.uniform(-.6,.6),mat=rng.choice(["wood","wood","wood","steel"]),
               sag=rng.uniform(.035,.18)*dist,br=rng.choice([0,0,0,1,2]),wig=rng.uniform(-.15,.15),
               l=rng.choice([0,0,6.6,8.5]),r=rng.choice([0,0,8.5,16.,19.5]),off=rng.uniform(-.1,3.8))
        d=solve3(s) if k==3 else solve2(k,s)
        if b.test(d,tag=(n,round(l,2),nc,round(s["sag"],2))):
            from design_lab import write
            write(f"scratch/shoulder{k}.json",s)
        cnt+=1
    print("shoulder",k,cnt,b.existing(),flush=True)


if __name__=="__main__":
    search(int(sys.argv[1]),float(sys.argv[2]))
