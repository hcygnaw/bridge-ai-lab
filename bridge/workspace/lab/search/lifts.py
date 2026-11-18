import itertools
import math
import sys

from design_lab import Bench, Design
from trusses import bar, warren


def timer(d, ratio, close, *, red=True, speed=0.9, ready=4, lag=0, signal=None):
    d.sensors.append(dict(id="timer",type="start"))
    d.rules.extend(dict(on="timer",delay=t,do="hyd",group="lift",ratio=r,speed=speed)
                   for t,r in [(0.25,ratio),(close,1)])
    if red:
        width={4:24,6:36}[d.lv["id"]]
        for i,(direc,x) in enumerate([("right",-1.0),("left",width+1.0)] if signal is None else signal):
            name="go"+str(i)
            d.lights.append(dict(id=name,x=x,dir=direc,init="red"))
            d.rules.append(dict(on="timer",delay=close+ready+i*lag,do="light",light=name,state="green"))


def approach(d, shore, end, pier, foot, n, h, rise, chord="wood", web="wood", piers=True):
    top,low=warren(d,shore,end,n,h,rise,chord,web,(foot,pier))
    if piers:
        bar(d,end,pier,"steel")
        # A second path to the rock limits shear at the tip.
        bar(d,top[-2],pier)
    return top,low


def parallel_drop(k,n=None,h=None,rise=0,chord="cable",web="wood",taper=.5,
                  app_h=1.6,app_rise=.35,app_n=6,app_chord="wood",
                  end_y=.14, dx=-.2, down_y=-2.65,speed=1.,lag=4,wait=0,beam=False):
    d=Design(k)
    left,right=(0,24) if k==4 else (12,24)
    pivot1,pivot2=("A1","A4") if k==4 else ("A4","A5")
    if n is None: n=12 if k==4 else 6
    if h is None: h=2.4 if k==4 else 1.8
    m1=d.n(left+dx,end_y);m2=d.n(right+dx,end_y)
    if k==6:
        a=d.n(left+dx-.25,end_y)
        b=d.n(right+dx+.25,end_y)
        atop,_=approach(d,"A0",a,pivot1,"A1",app_n,app_h,app_rise,app_chord)
        approach(d,"A6",b,pivot2,"A7",app_n,app_h,app_rise,app_chord)
        base=atop[-3]
    else:
        base="A2"
    bar(d,pivot1,m1,"steel")
    bar(d,pivot2,m2,"steel")
    upper,lower=warren(d,m1,m2,n,h,rise,chord,web,taper=taper)
    if beam:
        # Cable ties share tension with the segmented lower chord.
        bar(d,m1,lower[n//3],"cable")
        bar(d,m2,lower[-1-n//3],"cable")
    bar(d,base,m1,"hydraulic","lift")
    initial=math.dist(d.pos(base),d.pos(m1))
    rad=math.dist(d.pos(pivot1),d.pos(m1))
    opened=(left+math.sqrt(rad**2-(down_y+2)**2),down_y)
    ratio=math.dist(d.pos(base),opened)/initial
    close={4:26.15,6:30.15}[k]
    timer(d,round(ratio,7),close,speed=speed,ready=wait+max(2.5, (ratio-1)*initial/speed+.9),lag=lag)
    return d


def suspended(k,n=None,h=None,rise=0,chord="cable",web="wood",taper=.8,
              app_h=1.6,app_rise=.35,app_n=6,app_chord="wood",
              end_y=.02,top_y=2.9,down=2.6,lag=5,lash=2, fixed=True):
    d=Design(k)
    if n is None: n=14 if k==4 else 7
    if h is None: h=2.8 if k==4 else 2.2
    left,right=(0,24) if k==4 else (12,24)
    pivots=("A1","A4") if k==4 else ("A4","A5")
    m1=d.n(left+.14,end_y)
    m2=d.n(right-.14,end_y)
    for rev in (0,1):
        x=(left,right)[rev]
        m=(m1,m2)[rev]
        s=1 if not rev else -1
        top=d.n(x+s*.14,top_y)
        if k==4:
            bar(d,("A0","A3")[rev],top,"steel")
            bar(d,("A10","A11")[rev],top,"steel")
        else:
            app=d.n(x-s*.14,end_y)
            route,low=approach(d,("A0","A6")[rev],app,pivots[rev],("A1","A7")[rev],
                               app_n,app_h,app_rise,app_chord)
            bar(d,app,top,"steel")
            bar(d,route[-2],top,"steel")
        bar(d,top,m,"hydraulic","lift")
    upper,lower=warren(d,m1,m2,n,h,rise,chord,web,taper=taper)
    if lash:
        bar(d,pivots[0],upper[lash],"cable")
        bar(d,pivots[1],upper[-lash-1],"cable")
    timer(d,1+down/(top_y-end_y),{4:26.15,6:30.15}[k],speed=1.3,ready=3.,lag=lag)
    return d


if __name__=="__main__":
    k=int(sys.argv[1])
    b=Bench(k)
    if k==4:
        opt=itertools.product((12,14,16),(2.2,3.0,1.8,2.6),("cable","wood","steel"),(.5,.8,0),(0,.2,-.25))
    else:
        opt=itertools.product((6,7,8),(2.,1.4,2.4,1.7),("wood","cable","steel"),(.5,.8,0),(0,.2,-.25))
    for n,h,ch,t,r in opt:
        gen=suspended if "suspended" in sys.argv else parallel_drop
        d=gen(k,n,h,r,ch,taper=t)
        if b.test(d,tag=(n,h,r,ch,t)): break
