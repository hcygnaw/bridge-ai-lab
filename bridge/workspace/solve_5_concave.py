import json, math, sys
from pathlib import Path

WS = Path(__file__).resolve().parent
sys.path.insert(0, str(WS))
import bridge
from opt_util import eval_design, save_if_better

SUB = WS / "submission"
SUB.mkdir(exist_ok=True)

def make_l5_concave(
    # Concave pit ramp: A5=(-6,-4) or A6=(-8,-4) up to A0=(0,0)
    p_pts=((-6.0, -3.6), (-3.8, -2.9), (-1.8, -1.5)),
    pit_start="A6",
    # River left ramp: A0=(0,0) -> (lx, ry)
    lx=7.2, ry=1.4,
    # River right landing: (rx, ly) -> A7=(24,0)
    rx=14.2, ly=-2.8,
    th_l=3.4,
    l_pow=1.15,
):
    nodes, members = [], []
    def add(x, y):
        nodes.append([round(x, 4), round(y, 4)])
        return len(nodes) - 1

    # 1. Concave pit ramp
    pr = [pit_start] + [add(x, y) for (x, y) in p_pts] + ["A0"]
    for i in range(len(pr) - 1):
        members.append([pr[i], pr[i+1], "road"])
    # Support each interior node from nearest pit anchor A5=(-6,-4), A4=(-4,-4), A3=(-2,-4)
    if len(p_pts) == 3:
        members += [["A5", pr[1], "steel"], ["A4", pr[2], "steel"], ["A3", pr[3], "steel"]]
    elif len(p_pts) == 2:
        members += [["A4", pr[1], "steel"], ["A3", pr[2], "steel"]]

    # 2. Left river ramp: A0=(0,0) -> (lx, ry)
    n_l = max(2, math.ceil(math.hypot(lx, ry) / 2.4))
    l_r = ["A0"]
    for i in range(1, n_l + 1):
        t = i / n_l
        l_r.append(add(lx * t, ry * (t ** l_pow)))
    for i in range(n_l):
        members.append([l_r[i], l_r[i+1], "road"])

    tl = add(0.0, th_l)
    members += [["A0", tl, "steel"], ["A4", tl, "cable"], ["A1", l_r[1], "steel"]]
    for i in range(2, n_l + 1):
        members.append([tl, l_r[i], "cable"])

    # 3. Right river landing: (rx, ly) -> A7=(24,0)
    span_r = 24.0 - rx
    n_r = max(2, math.ceil(math.hypot(span_r, -ly) / 2.4))
    r_r = []
    for i in range(n_r):
        t = i / n_r
        r_r.append(add(rx + span_r * t, ly * (1.0 - t)))
    r_r.append("A7")
    for i in range(n_r):
        members.append([r_r[i], r_r[i+1], "road"])
    members.append(["A8", r_r[n_r - 1], "steel"])
    for i in range(0, n_r - 1):
        members.append(["A7", r_r[i], "cable"])

    return {"nodes": nodes, "members": members}

lv = bridge.load_level("5")
sc1 = json.loads(open(bridge.sample_paths(lv)[0]).read())
sc2 = json.loads(open(bridge.sample_paths(lv)[1]).read())

# First test if car & van climb out of the pit cleanly!
print("=== TESTING CONCAVE PIT RAMP ===", flush=True)
pit_candidates = [
    ("A6", ((-6.0, -3.65), (-3.8, -2.8), (-1.7, -1.4))),
    ("A6", ((-5.8, -3.6), (-3.6, -2.7), (-1.6, -1.35))),
    ("A6", ((-6.0, -3.5), (-3.9, -2.5), (-1.8, -1.2))),
    ("A5", ((-3.9, -3.3), (-1.8, -1.7))),
    ("A5", ((-3.8, -3.1), (-1.8, -1.6))),
]
good_pit = None
for ps, pts in pit_candidates:
    d = make_l5_concave(pts, ps, 7.2, 1.4, 15.0, -2.8, 3.2)
    try:
        P = bridge.parse_design(lv, d)
    except Exception as e:
        print("INVALID:", e)
        continue
    r1, rep1 = bridge.simulate(lv, P, sc1, replay=True)
    r2, rep2 = bridge.simulate(lv, P, sc2, replay=True)
    # Check max x reached by v0 in sample1 and sample2!
    nb = P["n_anchor"] + len(d["nodes"])
    mx1 = max((fr["p"][2*nb] for fr in rep1["frames"] if len(fr["p"]) > 2*nb), default=-99)
    mx2 = max((fr["p"][2*nb] for fr in rep2["frames"] if len(fr["p"]) > 2*nb), default=-99)
    print(f"ps={ps} pts={pts} cost={P['cost']:.1f} max_x1={mx1:.1f} max_x2={mx2:.1f} pk1={max(r1['peak_members'])*100:.0f}% pk2={max(r2['peak_members'])*100:.0f}%", flush=True)
    if mx1 > 5.0 and mx2 > 5.0 and good_pit is None:
        good_pit = (ps, pts)

if good_pit:
    ps, pts = good_pit
    print(f"\n=== SWEEPING RIVER JUMP WITH GOOD PIT {ps} {pts} ===", flush=True)
    best5 = None
    for lx in [6.8, 7.2, 7.8, 8.4]:
        for ry in [0.8, 1.3, 1.8, 2.2]:
            for rx in [12.5, 13.5, 14.3, 15.0, 15.8]:
                for ly in [-2.2, -2.8, -3.5, -4.2]:
                    d = make_l5_concave(pts, ps, lx, ry, rx, ly, 3.2)
                    ok, cost, pk, msgs = eval_design(5, d)
                    if cost is not None:
                        if ok:
                            if best5 is None or cost < best5[0]:
                                best5 = (cost, d)
                                print(f"PASS L5!! cost={cost:.1f} lx={lx} ry={ry} rx={rx} ly={ly} pk={pk*100:.1f}%", flush=True)
                                save_if_better(5, d, SUB / "level5.json")
    if best5:
        print("\n=== BEST L5 ===")
        eval_design(5, best5[1], verbose=True)
    else:
        print("No full pass yet; tracing river jump on lx=7.2 ry=1.4 rx=14.3 ly=-2.8:")
        d = make_l5_concave(pts, ps, 7.2, 1.4, 14.3, -2.8, 3.2)
        P = bridge.parse_design(lv, d)
        nb = P["n_anchor"] + len(d["nodes"])
        for name, sc in [("s1", sc1), ("s2", sc2)]:
            res, rep = bridge.simulate(lv, P, sc, replay=True)
            print(name, res["events"][:6])
            for fr in rep["frames"][120:280:8]:
                vp = fr["p"][2*nb:]
                if len(vp) >= 4:
                    print(f"  t={fr['t']:.2f} v0=({vp[0]:.2f},{vp[1]:.2f})..({vp[2]:.2f},{vp[3]:.2f}) st={fr['v'][0]}")
                if fr["v"][0] != 1: break
