from design import *
import random,time

def compact(d):
    used=sorted({k for m in d['members'] for k in m[:2] if isinstance(k,int)})
    remap={k:i for i,k in enumerate(used)}
    d['nodes']=[d['nodes'][k] for k in used]
    for m in d['members']:
        for i in [0,1]:
            if isinstance(m[i],int):m[i]=remap[m[i]]

def trim(l,r):
    a=Deck(l);f=Path('submission')/f'level{l}.json';a.d=json.loads(f.read_text());d=a.d;nd=d['nodes'];ms=d['members']
    if any(s.get('type')=='plate' for s in d.get('sensors',[])):return
    j=r.randrange(len(nd));near=[m for m in ms if j in m[:2]]
    def pos(k):return nd[k] if isinstance(k,int) else a.lv['anchors'][int(k[1:])]
    v=r.random()
    if v<.21:
        if any(m[2]=='hydraulic' for m in near):return
        if any(m[2]=='road' for m in near):
            if r.random()<.7:return
            rd=[m for m in near if m[2]=='road']
            if len(rd)!=2:return
            u,w=[m[1] if m[0]==j else m[0] for m in rd];ms.append([u,w,'road'])
        d['members']=[m for m in ms if j not in m[:2]];compact(d)
    elif v<.43:
        m=r.choice(near);k=m[0] if m[1]==j else m[1]
        for mm in near:
            for i in [0,1]:
                if mm[i]==j:mm[i]=k
        unique={}
        for mm in ms:
            if mm[0]==mm[1]:continue
            key=frozenset(mm[:2])
            if key not in unique or mm[2]=='road':unique[key]=mm
        d['members']=list(unique.values());compact(d)
    elif v<.63:
        m=r.choice(ms)
        if m[2] in ['road','hydraulic']:return
        if r.random()<.45:
            k=r.choice(m[:2]);p=pos(k)
            opts=[(math.dist(p,pt),i) for i,pt in enumerate(nd) if i not in m[:2] and math.dist(p,pt)<2.7]
            if not opts:return
            m[m.index(k)]=r.choice(opts)[1]
        else:
            ms.remove(m)
        compact(d)
    else:
        # Move toward the cable/strut length minimum, not only along one bar.
        x,y=nd[j];dx=dy=0
        for m in near:
            k=m[0] if m[1]==j else m[1];xx,yy=pos(k);L=math.hypot(xx-x,yy-y)
            p=b.MATERIALS[m[2]]['cost_m'];dx+=p*(xx-x)/L;dy+=p*(yy-y)/L
        u=r.choice([-.3,1])*r.uniform(.005,.65)/max(1,math.hypot(dx,dy))
        nd[j]=[round(x+dx*u,5),round(y+dy*u,5)]
    if l==5 and r.random()<.67:
        for rule in d.get('rules',[]):rule['delay']=max(0,rule['delay']+r.uniform(-.35,.35))
    a.test()

if __name__=='__main__':
    r=random.Random(511222);end=float(sys.argv[1])
    while time.time()<end:trim(r.choice([1,2,3,4,5,6]),r)
