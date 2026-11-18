import bridge as b
import json, math, os, sys, fcntl
from pathlib import Path

class Deck:
    def __init__(self,l):
        self.lv=b.load_level(str(l))
        self.d={'nodes':[],'members':[]}
        self.pts={tuple(p):f'A{i}' for i,p in enumerate(self.lv['anchors'])}
    def node(self,x,y):
        p=round(x,5),round(y,5)
        if p not in self.pts:
            self.pts[p]=len(self.d['nodes'])
            self.d['nodes'].append(list(p))
        return self.pts[p]
    def bar(self,a,c,m='road',*args):
        self.d['members'].append([a,c,m,*args])
    def span(self,x,z,n,h=0,y=0,v=0):
        ns=[]
        for i in range(n+1):
            t=i/n
            ns.append(self.node(x+(z-x)*t,y+(v-y)*t+4*h*t*(1-t)))
        for a,c in zip(ns,ns[1:]):self.bar(a,c)
        return ns
    def test(self,save=True,verbose=False):
        try:p=b.parse_design(self.lv,self.d)
        except b.DesignError as e:
            if verbose:print(e)
            return
        l=self.lv['id']
        f=Path('submission')/(f'level{l}.json' if l!='final' else 'final_bridge.json')
        f.parent.mkdir(exist_ok=True)
        if save and f.exists() and b.parse_design(self.lv,json.loads(f.read_text()))['cost']<=p['cost']:return
        for path in b.sample_paths(self.lv):
            s=b.load_json(path); r,_=b.simulate(self.lv,p,s)
            if verbose:print(b.summarize(r,p,s)['text'])
            if not r['ok']:return
        if save:
            with open('.best.lock','a') as lock:
                fcntl.flock(lock,fcntl.LOCK_EX)
                if f.exists() and b.parse_design(self.lv,json.loads(f.read_text()))['cost']<=p['cost']:return
                tmp=f.with_suffix(f'.{os.getpid()}.tmp')
                tmp.write_text(json.dumps(self.d));tmp.replace(f)
                print('PASS',l,p['cost'],flush=True)
        return True

def basic(l,h,n):
    a=Deck(l)
    if l==1:a.span(0,15,n,h)
    if l==2:a.span(0,30,n,h)
    if l==3:
        for x in (0,14):a.span(x,x+14,n,h)
        a.bar(a.node(14,0),'A2','steel')
    if l==5:
        a.span(-11,0,5,-.4);a.span(0,24,n,h)
    if l=='final':a.span(0,28,n,h)
    return a

if __name__=='__main__':
    for l,n in [(1,6),(2,12),(3,6),(5,10),('final',12)]:
        for k in range(n,n+4):
            for h in [0,-.2,-.5,-1,-1.5,-2,-2.5,-3,.5,1,1.5,2]:
                basic(l,h,k).test()
