import json, math, sys
from pathlib import Path

WS = Path(__file__).resolve().parent
sys.path.insert(0, str(WS))
import bridge
from opt_util import eval_design, save_if_better

SUB = WS / "submission"
SUB.mkdir(exist_ok=True)

def make_l5_pass(
    th_l=2.8, th_r=2.8,
    riv_sag=1.2,
    pit_sag=0.8,
    n_riv=10,
    pit_mode="bs3",
    riv_mode="susp_all",
    h_clear=0.2,
):
    nodes = []
    members = []
    def add(x, y):
        nodes.append([round(x, 4), round(y, 4)])
        return len(nodes) - 1

    # Pit road: 5 segs (dx=2.2m) from A2=(-11,0) to A0=(0,0)
    pit_r = ["A2"]
    for i in range(1, 5):
        t = i / 5.0
        pit_r.append(add(-11.0 + 11.0*t, -4.0*pit_sag*t*(1.0-t)))
    pit_r.append("A0")
    for i in range(5):
        members.append([pit_r[i], pit_r[i+1], "road"])

    # River road: n_riv segs from A0=(0,0) to A7=(24,0)
    riv_r = ["A0"]
    for i in range(1, n_riv):
        t = i / n_riv
        riv_r.append(add(24.0*t, -4.0*riv_sag*t*(1.0-t)))
    riv_r.append("A7")
    for i in range(n_riv):
        members.append([riv_r[i], riv_r[i+1], "road"])

    # Towers
    tl = add(0.0, th_l)
    tr = add(24.0, th_r)
    members += [["A0", tl, "steel"], ["A7", tr, "steel"]]
    members.append(["A9", tr, "cable"])

    # Pit support via backstay A2 -> tl
    if pit_mode == "bs2":
        b2 = add(-6.6, th_l * 0.4 - 0.3)
        b3 = add(-4.4, th_l * 0.6 - 0.3)
        members += [["A2", b2, "cable"], [b2, b3, "cable"], [b3, tl, "cable"]]
        members += [[b2, pit_r[2], "cable"], [b3, pit_r[3], "cable"]]
    elif pit_mode == "bs3":
        b1 = add(-8.8, th_l * 0.2 - 0.15)
        b2 = add(-6.6, th_l * 0.4 - 0.25)
        b3 = add(-4.4, th_l * 0.6 - 0.25)
        b4 = add(-2.2, th_l * 0.8 - 0.15)
        members += [["A2", b1, "cable"], [b1, b2, "cable"], [b2, b3, "cable"], [b3, b4, "cable"], [b4, tl, "cable"]]
        members += [[b1, pit_r[1], "cable"], [b2, pit_r[2], "cable"], [b3, pit_r[3], "cable"], [b4, pit_r[4], "cable"]]
    elif pit_mode == "bs_none":
        # Pure backstay A2 -> tl, NO pit hangers! Pit road is pure catenary!
        members.append(["A2", tl, "cable"])

    # River suspension
    if riv_mode == "susp_even":
        c_nodes = [tl]
        for i in [2, 4, 6, 8]:
            t = i / n_riv
            y_road = -4.0 * riv_sag * t * (1.0 - t)
            y_c = th_l*(1-t) + th_r*t - (0.5*(th_l+th_r) - (-riv_sag + h_clear)) * 4.0 * t * (1.0 - t)
            y_c = max(y_c, y_road + 0.15)
            cn = add(24.0 * t, y_c)
            c_nodes.append(cn)
            members.append([cn, riv_r[i], "cable"])
        c_nodes.append(tr)
        for k in range(len(c_nodes) - 1):
            members.append([c_nodes[k], c_nodes[k+1], "cable"])
    elif riv_mode == "susp_3":
        c_nodes = [tl]
        for i in [3, 5, 7]:
            t = i / n_riv
            y_road = -4.0 * riv_sag * t * (1.0 - t)
            y_c = th_l*(1-t) + th_r*t - (0.5*(th_l+th_r) - (-riv_sag + h_clear)) * 4.0 * t * (1.0 - t)
            y_c = max(y_c, y_road + 0.15)
            cn = add(24.0 * t, y_c)
            c_nodes.append(cn)
            members.append([cn, riv_r[i], "cable"])
        c_nodes.append(tr)
        for k in range(len(c_nodes) - 1):
            members.append([c_nodes[k], c_nodes[k+1], "cable"])
    elif riv_mode == "susp_direct":
        # Main cable connects DIRECTLY to riv_r[4], riv_r[5], riv_r[6] (no hangers in middle!)
        c2 = add(4.8, th_l * 0.4 - riv_sag * 0.3)
        c8 = add(19.2, th_r * 0.4 - riv_sag * 0.3)
        members += [[tl, c2, "cable"], [c2, riv_r[4], "cable"], [riv_r[6], c8, "cable"], [c8, tr, "cable"]]
        members += [[c2, riv_r[2], "cable"], [c8, riv_r[8], "cable"]]
    elif riv_mode == "susp_all":
        c_nodes = [tl]
        for i in range(1, n_riv):
            t = i / n_riv
            y_road = -4.0 * riv_sag * t * (1.0 - t)
            y_c = th_l*(1-t) + th_r*t - (0.5*(th_l+th_r) - (-riv_sag + h_clear)) * 4.0 * t * (1.0 - t)
            y_c = max(y_c, y_road + 0.15)
            cn = add(24.0 * t, y_c)
            c_nodes.append(cn)
            members.append([cn, riv_r[i], "cable"])
        c_nodes.append(tr)
        for k in range(len(c_nodes) - 1):
            members.append([c_nodes[k], c_nodes[k+1], "cable"])

    return {"nodes": nodes, "members": members}

print("=== LEVEL 5 PASS SWEEP ===", flush=True)
best5 = None
for pit_m in ["bs_none", "bs2", "bs3"]:
    for riv_m in ["susp_3", "susp_even", "susp_direct", "susp_all"]:
        for th in [2.4, 3.0, 3.6]:
            for riv_sag in [0.8, 1.4, 2.0]:
                for pit_sag in [0.6, 1.0, 1.4]:
                    n_riv = 11 if riv_sag >= 1.8 else 10
                    d = make_l5_pass(th, th, riv_sag, pit_sag, n_riv, pit_m, riv_m, 0.2)
                    ok, cost, pk, msgs = eval_design(5, d)
                    if cost is not None:
                        if ok:
                            if best5 is None or cost < best5[0]:
                                best5 = (cost, d)
                                print(f"PASS L5!! cost={cost:.1f} pit={pit_m} riv={riv_m} th={th} rsag={riv_sag} psag={pit_sag} pk={pk*100:.1f}%", flush=True)
                                save_if_better(5, d, SUB / "level5.json")
                        elif pk < 1.5:
                            print(f"  close: cost={cost:.1f} pk={pk*100:.1f}% pit={pit_m} riv={riv_m} th={th} rsag={riv_sag} psag={pit_sag}", flush=True)

if best5:
    print("\n=== BEST L5 ===")
    eval_design(5, best5[1], verbose=True)
else:
    print("No pass yet; printing diagnostic on cheapest valid:")
    for pit_m, riv_m, th, rs, ps in [("bs_none", "susp_even", 3.0, 1.4, 1.0), ("bs2", "susp_3", 3.0, 1.4, 1.0), ("bs_none", "susp_all", 2.4, 1.4, 1.2)]:
        d = make_l5_pass(th, th, rs, ps, 10, pit_m, riv_m, 0.2)
        print(f"--- {pit_m} {riv_m} th={th} rs={rs} ps={ps} ---")
        eval_design(5, d, verbose=True)
