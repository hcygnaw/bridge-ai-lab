import json, math, sys
from pathlib import Path

WS = Path(__file__).resolve().parent
sys.path.insert(0, str(WS))
import bridge
from opt_util import eval_design, save_if_better

SUB = WS / "submission"
SUB.mkdir(exist_ok=True)

# Strategy A: Suspension bridge where main cable merges into riv_r[4..6] (0 middle hangers -> no <0.3m error AND cheaper!)
# Plus EVERY other river node (1,2,3 and 7,8,9) has a vertical hanger to the main cable!
# Plus pit has 1-2 hangers from backstay A2->tl (or 1 steel prop from A5)!
def make_l5_merged_full(th=2.6, riv_sag=1.6, pit_sag=1.1, pit_mode="bs2", merge_k=4):
    nodes = []
    members = []
    def add(x, y):
        nodes.append([round(x, 4), round(y, 4)])
        return len(nodes) - 1

    # Pit: 5 road segs from A2=(-11,0) to A0=(0,0)
    pit_r = ["A2"]
    for i in range(1, 5):
        t = i / 5.0
        pit_r.append(add(-11.0 + 11.0*t, -4.0*pit_sag*t*(1.0-t)))
    pit_r.append("A0")
    for i in range(5):
        members.append([pit_r[i], pit_r[i+1], "road"])

    # River: 10 road segs (2.4m each) from A0=(0,0) to A7=(24,0)
    n_riv = 10
    riv_r = ["A0"]
    for i in range(1, n_riv):
        t = i / n_riv
        riv_r.append(add(24.0*t, -4.0*riv_sag*t*(1.0-t)))
    riv_r.append("A7")
    for i in range(n_riv):
        members.append([riv_r[i], riv_r[i+1], "road"])

    # Towers
    tl = add(0.0, th)
    tr = add(24.0, th)
    members += [["A0", tl, "steel"], ["A7", tr, "steel"]]
    members.append(["A9", tr, "cable"])

    # Pit support
    if pit_mode == "bs2":
        # Backstay A2 -> b2 -> b3 -> tl, vertical hangers to pit_r[2], pit_r[3]
        b2 = add(-6.6, th * 0.4 - 0.35)
        b3 = add(-4.4, th * 0.6 - 0.35)
        members += [["A2", b2, "cable"], [b2, b3, "cable"], [b3, tl, "cable"]]
        members += [[b2, pit_r[2], "cable"], [b3, pit_r[3], "cable"]]
    elif pit_mode == "bs4":
        b = ["A2"]
        for i in range(1, 5):
            t = i / 5.0
            bn = add(-11.0 + 11.0*t, th*t - 0.3*4*t*(1-t))
            b.append(bn)
            members.append([bn, pit_r[i], "cable"])
        b.append(tl)
        for i in range(5):
            members.append([b[i], b[i+1], "cable"])
    elif pit_mode == "bs_none":
        members.append(["A2", tl, "cable"])

    # River main cable: merges into riv_r[merge_k .. n_riv-merge_k]
    # Left side: tl -> c[1] -> ... -> c[merge_k-1] -> riv_r[merge_k]
    # Right side: riv_r[n_riv-merge_k] -> c[n_riv-merge_k+1] -> ... -> c[n_riv-1] -> tr
    # Parabola through (0, th) and (x_m, y_m) with slope matching road at x_m!
    tm = merge_k / n_riv
    ym = -4.0 * riv_sag * tm * (1.0 - tm)
    prev_l = tl
    for i in range(1, merge_k):
        u = i / merge_k # 0..1
        t = i / n_riv
        y_road = -4.0 * riv_sag * t * (1.0 - t)
        # Smooth curve from th down to ym
        y_c = th * (1.0 - u)**1.6 + ym * (1.0 - (1.0 - u)**1.6)
        if y_c < y_road + 0.35:
            y_c = y_road + 0.35
        cn = add(24.0 * t, y_c)
        members.append([prev_l, cn, "cable"])
        members.append([cn, riv_r[i], "cable"])
        prev_l = cn
    members.append([prev_l, riv_r[merge_k], "cable"])

    prev_r = tr
    for i in range(n_riv - 1, n_riv - merge_k, -1):
        u = (n_riv - i) / merge_k
        t = i / n_riv
        y_road = -4.0 * riv_sag * t * (1.0 - t)
        y_c = th * (1.0 - u)**1.6 + ym * (1.0 - (1.0 - u)**1.6)
        if y_c < y_road + 0.35:
            y_c = y_road + 0.35
        cn = add(24.0 * t, y_c)
        members.append([prev_r, cn, "cable"])
        members.append([cn, riv_r[i], "cable"])
        prev_r = cn
    members.append([prev_r, riv_r[n_riv - merge_k], "cable"])

    return {"nodes": nodes, "members": members}

print("=== LEVEL 5 MERGED-FULL SUSPENSION SWEEP ===", flush=True)
best5 = None
for pit_m in ["bs2", "bs4", "bs_none"]:
    for merge_k in [3, 4, 5]:
        for th in [2.0, 2.4, 2.8, 3.2]:
            for riv_sag in [0.8, 1.3, 1.8]:
                for pit_sag in [0.6, 1.0, 1.4]:
                    d = make_l5_merged_full(th, riv_sag, pit_sag, pit_m, merge_k)
                    ok, cost, pk, msgs = eval_design(5, d)
                    if cost is not None:
                        if ok:
                            if best5 is None or cost < best5[0]:
                                best5 = (cost, d)
                                print(f"PASS L5!! cost={cost:.1f} pit={pit_m} mk={merge_k} th={th} rsag={riv_sag} psag={pit_sag} pk={pk*100:.1f}%", flush=True)
                                save_if_better(5, d, SUB / "level5.json")
                        elif pk < 1.5:
                            print(f"  close: cost={cost:.1f} pk={pk*100:.1f}% pit={pit_m} mk={merge_k} th={th} rsag={riv_sag} psag={pit_sag}", flush=True)

if best5:
    print("\n=== BEST L5 ===")
    eval_design(5, best5[1], verbose=True)
else:
    print("No pass yet; checking diagnostic:")
    d = make_l5_merged_full(2.4, 1.4, 1.0, "bs2", 4)
    eval_design(5, d, verbose=True)
    lv = bridge.load_level("5")
    sc = json.loads(open(bridge.sample_paths(lv)[0]).read())
    P = bridge.parse_design(lv, d)
    res, _ = bridge.simulate(lv, P, sc, replay=False)
    for ev in res["events"][:10]:
        print(" ", ev)
