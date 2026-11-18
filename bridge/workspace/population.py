from design import *
import time,copy,random

def mutate(a,r):
    a0=a;a=Deck(a0.lv['id']);d=a.d=copy.deepcopy(a0.d);nd=d['nodes'];ms=d['members']
    for _ in range(r.choice([1,1,1,2,2,3])):
        if r.random()<.54:
            i=r.randrange(len(nd));x,y=nd[i]
            scale=r.choice([.08,.32,.7])
            nd[i]=[round(x+r.uniform(-scale,scale),5),round(y+r.uniform(-scale,scale),5)]
        else:
            m=r.choice(ms)
            if m[2] in ('road','hydraulic'):continue
            if r.random()<.18:ms.remove(m)
            else:m[2]=r.choice(['wood','wood','cable','steel','spring'])
    if a.lv['id']==5 and r.random()<.6:
        for rule in d.get('rules',[]):rule['delay']=max(0,rule['delay']+r.uniform(-.22,.22))
    return a

if __name__=='__main__':
    r=random.Random(5411);end=float(sys.argv[1]);pools={}
    while time.time()<end:
        l=r.choice([1,2,3,4,5,6]);pool=pools.setdefault(l,[])
        live=Deck(l);live.d=json.loads(Path(f'submission/level{l}.json').read_text())
        cost=b.parse_design(live.lv,live.d)['cost']
        a=mutate(r.choice(pool)[1] if pool and r.random()<.65 else live,r)
        try:p=b.parse_design(a.lv,a.d)
        except b.DesignError:continue
        c=p['cost']
        if c>cost*1.04 or any(abs(c-v)<.01 for v,_ in pool):continue
        if a.test(False):
            if c<cost:a.test()
            pool.append((c,a));pool.sort(key=lambda t:t[0])
            if len(pool)>12:pool.pop(r.randrange(4,len(pool)))
