import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bridge
from opt_helper import eval_design, save_submission

def make_l5_jump(launch_x=4.0, launch_y=2.6, land_x=17.5, land_y=-0.6):
    # Anchors:
    # A0=(0,0), A1=(0,-2), A2=(-11,0), A3=(-2,-4), A4=(-4,-4), A5=(-6,-4), A6=(-8,-4)
    # A7=(24,0), A8=(24,-2), A9=(30,0)
    nodes = []
    members = []

    pit_pts = [
        (-8.8, -0.6),
        (-6.6, -1.7),
        (-4.5, -2.7),
        (-2.4, -2.0),
        (-1.0, -0.9),
    ]
    p_idx = []
    for x, y in pit_pts:
        p_idx.append(len(nodes))
        nodes.append([round(x, 3), round(y, 3)])

    seq = ["A2"] + p_idx + ["A0"]
    for i in range(len(seq) - 1):
        members.append([seq[i], seq[i + 1], "road"])

    # Triangulate pit road using A6=(-8,-4), A5=(-6,-4), A4=(-4,-4), A3=(-2,-4), A1=(0,-2)
    # Use cable where possible? No, steel struts from floor anchors to adjacent pit nodes!
    members.append(["A6", p_idx[0], "steel"])
    members.append(["A6", p_idx[1], "steel"])
    members.append(["A5", p_idx[1], "steel"])
    members.append(["A5", p_idx[2], "steel"])
    members.append(["A4", p_idx[2], "steel"])
    members.append(["A4", p_idx[3], "steel"])
    members.append(["A3", p_idx[3], "steel"])
    members.append(["A3", p_idx[4], "steel"])
    members.append(["A1", p_idx[4], "steel"])

    l1 = len(nodes); nodes.append([round(launch_x * 0.5, 3), round(launch_y * 0.5, 3)])
    l2 = len(nodes); nodes.append([round(launch_x, 3), round(launch_y, 3)])
    members.append(["A0", l1, "road"])
    members.append([l1, l2, "road"])
    members.append(["A1", l1, "steel"])
    members.append(["A1", l2, "steel"])

    n_land = 3
    land_nodes = []
    for i in range(n_land):
        t = i / n_land
        x = land_x + (24.0 - land_x) * t
        y = land_y * (1.0 - t)
        land_nodes.append(len(nodes))
        nodes.append([round(x, 3), round(y, 3)])
    land_seq = land_nodes + ["A7"]
    for i in range(len(land_seq) - 1):
        members.append([land_seq[i], land_seq[i + 1], "road"])

    tw = len(nodes); nodes.append([24.0, 3.0])
    members.append(["A7", tw, "steel"])
    members.append(["A9", tw, "cable"])
    for ln in land_nodes:
        members.append([tw, ln, "cable"])
    members.append(["A8", land_nodes[-1], "steel"])

    return {"nodes": nodes, "members": members}


if __name__ == "__main__":
    lv = bridge.load_level("5")
    for lx, ly in [(3.4, 2.0), (3.8, 2.2), (4.0, 2.4)]:
        for rx, ry in [(17.0, -1.0), (18.0, -0.8), (19.0, -0.5)]:
            d = make_l5_jump(lx, ly, rx, ry)
            try:
                P = bridge.parse_design(lv, d)
            except Exception as e:
                print(f"lx={lx},ly={ly},rx={rx},ry={ry}: PARSE ERR {e}")
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
            print(f"lx={lx},ly={ly},rx={rx},ry={ry}: cost={P['cost']:.1f} | {' | '.join(msgs)}")
            if ok_all:
                save_submission("level5.json", d)
                sys.exit(0)
