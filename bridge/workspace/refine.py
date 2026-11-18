from design import *
import random,time,copy,os

def optimize(l,r):
    a=Deck(l)
    fp=Path('submission')/f'level{l}.json'
    if not fp.exists():return
    a.d=json.loads(fp.read_text())
    nodes=a.d['nodes'];ms=a.d['members']
    if r.random()<.54:
        i=r.randrange(len(ms));m=ms[i]
        if m[2] in ('road','hydraulic'):return
        mat=r.choice(['wood','cable','spring','omit'])
        if mat=='omit':del ms[i]
        else:m[2]=mat
    else:
        i=r.randrange(len(nodes));x,y=nodes[i]
        near=[m for m in ms if i in m[:2]]
        if not near:return
        targets=[m[0] if m[1]==i else m[1] for m in near]
        k=r.choice(targets)
        u,v=nodes[k] if isinstance(k,int) else a.lv['anchors'][int(k[1:])]
        s=r.uniform(.01,.45)
        nodes[i]=[round(x+(u-x)*s,4),round(y+(v-y)*s,4)]
    a.test()

if __name__=='__main__':
    r=random.Random(519)
    end=float(sys.argv[1])
    while time.time()<end:
        optimize(r.choice([1,2,3,4,5,6]),r)
