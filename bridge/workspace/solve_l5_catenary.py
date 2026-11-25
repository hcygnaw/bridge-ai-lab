import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bridge
from opt_helper import save_submission

def make_l5_catenary(pit_sag=1.1, river_sag=2.4, add_river_cable=True):
    # A0=(0,0), A1=(0,-2), A2=(-11,0), A7=(24,0), A8=(24,-2), A9=(30,0)
    nodes = []
    members = []

    # 1. Pit catenary: A2=(-11,0) to A0=(0,0), 5 segments (~2.23m each)
    n_pit = 5
    pit_nodes = ["A2"]
    for i in range(1, n_pit):
        t = i / n_pit
        x = -11.0 + 11.0 * t
        y = -4.0 * pit_sag * t * (1.0 - t)
        pit_nodes.append(len(nodes))
        nodes.append([round(x, 3), round(y, 3)])
    pit_nodes.append("A0")
    for i in range(n_pit):
        members.append([pit_nodes[i], pit_nodes[i + 1], "road"])

    # 2. River catenary: A0=(0,0) to A7=(24,0), 11 segments (~2.25m each)
    n_riv = 11
    riv_nodes = ["A0"]
    for i in range(1, n_riv):
        t = i / n_riv
        x = 24.0 * t
        y = -4.0 * river_sag * t * (1.0 - t)
        riv_nodes.append(len(nodes))
        nodes.append([round(x, 3), round(y, 3)])
    riv_nodes.append("A7")
    for i in range(n_riv):
        members.append([riv_nodes[i], riv_nodes[i + 1], "road"])

    if add_river_cable:
        members.append(["A0", riv_nodes[4], "cable"])
        members.append([riv_nodes[4], riv_nodes[7], "cable"])
        members.append([riv_nodes[7], "A7", "cable"])

    return {"nodes": nodes, "members": members}


if __name__ == "__main__":
    lv = bridge.load_level("5")
    for ps in [0.9, 1.1, 1.3]:
        for rs in [2.0, 2.5, 3.0]:
            for cab in [False, True]:
                d = make_l5_catenary(ps, rs, cab)
                try:
                    P = bridge.parse_design(lv, d)
                except Exception as e:
                    print(f"ps={ps},rs={rs},cab={cab}: ERR {e}")
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
                print(f"ps={ps},rs={rs},cab={cab}: cost={P['cost']:.1f} | {' | '.join(msgs)}")
                if ok_all:
                    save_submission("level5.json", d)
                    sys.exit(0)
