from design import *
import saboteur as sab
from itertools import product

def trials(d):
    a=Deck('final');p=b.parse_design(a.lv,d)
    wins=0;worst=0;breaks=0
    for speed,wb,frac in product([5.5,7.5,10],[.4,1.3,2.6],[.15,.5,.85]):
        mass=2500-160-35*wb-.1
        cart=dict(nodes=[[0,.22],[-wb,.22]],members=[[0,1,'steel']],wheels=[0,1],
                  ballast=[[0,mass*frac],[1,mass*(1-frac)]],motor=dict(speed=speed,accel=4))
        s=sab.parse_sab(a.lv,cart)
        out,_=sab.duel(a.lv,p,s)
        wins+=out['bridge_win'];breaks=max(breaks,out['res']['bridge_broken'])
        worst=max(worst,max(out['res']['peak_members']))
    return wins,breaks,worst

if __name__=='__main__':print(trials(json.loads(Path('submission/final_bridge.json').read_text())))
