import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bridge
from opt_helper import save_submission

def make_l5_cable(tw_h=2.8, riv_sag=0.8):
    # A0=(0,0), A1=(0,-2), A2=(-11,0), A3=(-2,-4), A4=(-4,-4), A5=(-6,-4), A6=(-8,-4)
    # A7=(24,0), A8=(24,-2), A9=(30,0)
    nodes = []
    members = []

    # 1. Pit deck: -11 to 0, 5 segments of 2.2m, catenary sag
    pit_nodes = ["A2"]
    for i in range(1, 5):
        t = i / 5.0
        x = -11.0 + 11.0 * t
        y = -4.0 * 0.9 * t * (1.0 - t)
        pit_nodes.append(len(nodes))
        nodes.append([round(x, 3), round(y, 3)])
    pit_nodes.append("A0")
    for i in range(5):
        members.append([pit_nodes[i], pit_nodes[i + 1], "road"])
    # No steel struts under pit — pure sagged road!

    # 2. River deck: 0 to 24, 10 segments of 2.4m, slight sag
    riv_nodes = ["A0"]
    for i in range(1, 10):
        t = i / 10.0
        x = 24.0 * t
        y = -4.0 * riv_sag * t * (1.0 - t)
        riv_nodes.append(len(nodes))
        nodes.append([round(x, 3), round(y, 3)])
    riv_nodes.append("A7")
    for i in range(10):
        members.append([riv_nodes[i], riv_nodes[i + 1], "road"])

    # 3. Minimal suspension cable over river
    tL = len(nodes); nodes.append([0.0, tw_h])
    tR = len(nodes); nodes.append([24.0, tw_h])
    members.append(["A0", tL, "steel"])
    members.append(["A7", tR, "steel"])
    # Backstays to real anchors A4=(-4,-4) and A9=(30,0)!
    members.append(["A4", tL, "cable"])
    members.append(["A9", tR, "cable"])

    # Main cable: tL -> c1=(8, 0.8) -> c2=(16, 0.8) -> tR
    c1 = len(nodes); nodes.append([8.0, 0.9])
    c2 = len(nodes); nodes.append([16.0, 0.9])
    members.append([tL, c1, "cable"])
    members.append([c1, c2, "cable"])
    members.append([c2, tR, "cable"])

    # Short hangers from c1 and c2 to deck
    members.append([c1, riv_nodes[3], "cable"])  # x=7.2
    members.append([c1, riv_nodes[4], "cable"])  # x=9.6
    members.append([c2, riv_nodes[6], "cable"])  # x=14.4
    members.append([c2, riv_nodes[7], "cable"])  # x=16.8

    return {"nodes": nodes, "members": members}


if __name__ == "__main__":
    lv = bridge.load_level("5")
    for h in [2.6, 3.0, 3.4]:
        for sag in [0.4, 0.8, 1.2]:
            d = make_l5_cable(tw_h=h, riv_sag=sag)
            try:
                P = bridge.parse_design(lv, d)
            except Exception as e:
                print(f"h={h},sag={sag}: PARSE ERR {e}")
                continue
            ok_all = True
            msgs = []
            for sp in bridge.sample_paths(lv):
                sc = bridge.load_json(sp)
                res, _ = bridge.simulate(lv, P, sc)
                s = bridge.summarize(res, P, sc)
                if not s["ok"]:
                    ok_all = False
                msgs.append(f"{os.path.basename(sp)}:{'PASS' if s['ok'] else s['text'].strip().splitlines()[0]}")
            print(f"h={h},sag={sag}: cost={P['cost']:.1f} | {' | '.join(msgs)}")
            if ok_all:
                save_submission("level5.json", d)
                sys.exit(0)
