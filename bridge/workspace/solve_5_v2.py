import json, math, sys
from pathlib import Path

WS = Path(__file__).resolve().parent
sys.path.insert(0, str(WS))
import bridge
from opt_util import eval_design, save_if_better

SUB = WS / "submission"
SUB.mkdir(exist_ok=True)

def make_pit_cheap(pit_sag=0.8, n_pit=5, prop_mode="single"):
    nodes = []
    members = []
    def add(x, y):
        nodes.append([round(x, 4), round(y, 4)])
        return len(nodes) - 1
    pit_r = ["A2"]
    for i in range(1, n_pit):
        t = i / n_pit
        x = -11.0 + 11.0 * t
        y = -4.0 * pit_sag * t * (1.0 - t)
        pit_r.append(add(x, y))
    pit_r.append("A0")
    for i in range(n_pit):
        members.append([pit_r[i], pit_r[i+1], "road"])
    if prop_mode == "single":
        # A5=(-6,-4) to pit_r[2] (-6.6, y) and cable/steel to pit_r[3]?
        members.append(["A5", pit_r[2], "steel"])
        members.append(["A4", pit_r[3], "steel"])
    elif prop_mode == "none":
        # pure catenary road + 2 cables from A2, A0
        members.append(["A2", pit_r[2], "cable"])
        members.append(["A0", pit_r[3], "cable"])
    elif prop_mode == "one_v":
        # One V from A5=(-6,-4) to pit_r[2] and pit_r[3]
        members.append(["A5", pit_r[2], "steel"])
        members.append(["A5", pit_r[3], "steel"])
    elif prop_mode == "one_prop":
        # n_pit=4 -> mid node at (-5.5, -pit_sag), prop from A5=(-6,-4)
        members.append(["A5", pit_r[n_pit//2], "steel"])
    return nodes, members, pit_r

def make_l5_catenary_cables(pit_mode="none", pit_sag=1.2, n_riv=10, riv_sag=2.5,
                            cable_pattern="chords", end_strut=True, tower_h=0.0):
    nodes, members, pit_r = make_pit_cheap(pit_sag, 5 if pit_mode != "one_prop" else 4, pit_mode)
    def add(x, y):
        nodes.append([round(x, 4), round(y, 4)])
        return len(nodes) - 1

    riv_r = ["A0"]
    for i in range(1, n_riv):
        t = i / n_riv
        x = 24.0 * t
        y = -4.0 * riv_sag * t * (1.0 - t)
        riv_r.append(add(x, y))
    riv_r.append("A7")
    for i in range(n_riv):
        members.append([riv_r[i], riv_r[i+1], "road"])

    if end_strut:
        # Short steel diagonal struts from A1=(0,-2) to riv_r[1] and A8=(24,-2) to riv_r[-2]
        members.append(["A1", riv_r[1], "steel"])
        members.append(["A8", riv_r[n_riv-1], "steel"])

    if tower_h > 0:
        tl = add(0.0, tower_h)
        tr = add(24.0, tower_h)
        members.append(["A0", tl, "steel"])
        members.append(["A7", tr, "steel"])
        members.append(["A2", tl, "cable"])
        members.append(["A9", tr, "cable"])
        top_l, top_r = tl, tr
    else:
        top_l, top_r = "A0", "A7"

    if cable_pattern == "chords":
        for k in [2, 3, 4, 5]:
            if k < n_riv:
                members.append([top_l, riv_r[k], "cable"])
                members.append([top_r, riv_r[n_riv - k], "cable"])
    elif cable_pattern == "sparse":
        for k in [2, 4, 5]:
            if k < n_riv:
                members.append([top_l, riv_r[k], "cable"])
                members.append([top_r, riv_r[n_riv - k], "cable"])
    elif cable_pattern == "very_sparse":
        for k in [3, 5]:
            if k < n_riv:
                members.append([top_l, riv_r[k], "cable"])
                members.append([top_r, riv_r[n_riv - k], "cable"])
    elif cable_pattern == "fan_all":
        for k in range(2, n_riv // 2 + 1):
            members.append([top_l, riv_r[k], "cable"])
            members.append([top_r, riv_r[n_riv - k], "cable"])

    return {"nodes": nodes, "members": members}

print("=== LEVEL 5 NO-TOWER / LOW-TOWER CATENARY SWEEP ===", flush=True)
best5 = None
for pit_mode in ["none", "one_prop"]:
    for n_riv in [9, 10]:
        for riv_sag in [1.5, 2.2, 3.0, 3.8]:
            for th in [0.0, 2.0, 3.0]:
                for pat in ["very_sparse", "sparse", "chords"]:
                    for es in [True, False]:
                        d = make_l5_catenary_cables(pit_mode, 1.0, n_riv, riv_sag, pat, es, th)
                        ok, cost, pk, msgs = eval_design(5, d)
                        if cost is not None and cost <= 10000 and ok:
                            if best5 is None or cost < best5[0]:
                                best5 = (cost, d)
                                print(f"NEW BEST L5: {cost:.1f} (pit={pit_mode} n={n_riv} sag={riv_sag} th={th} pat={pat} es={es}) pk={pk*100:.1f}%", flush=True)
                                save_if_better(5, d, SUB / "level5.json")
                        elif cost is not None and cost <= 10000 and pk < 1.5:
                            print(f"  close: cost={cost:.1f} pk={pk*100:.1f}% (pit={pit_mode} n={n_riv} sag={riv_sag} th={th} pat={pat} es={es}) {msgs[0][:60]}", flush=True)

if best5:
    print("\n=== BEST L5 ===")
    eval_design(5, best5[1], verbose=True)
else:
    print("No pass yet, testing cheapest valid ones:")
    for riv_sag in [2.5, 3.5]:
        d = make_l5_catenary_cables("none", 1.0, 10, riv_sag, "sparse", True, 0.0)
        eval_design(5, d, verbose=True)
