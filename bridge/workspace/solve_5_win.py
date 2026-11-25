import json, math, sys
from pathlib import Path

WS = Path(__file__).resolve().parent
sys.path.insert(0, str(WS))
import bridge
from opt_util import eval_design, save_if_better

SUB = WS / "submission"
SUB.mkdir(exist_ok=True)

# LEVEL 5 DOUBLE-JUMP (FIXED!):
# - Pit: 3-seg convex ramp from A2=(-11,0) to (pit_ex, pit_ey) hung from tl=(0, th_l)
#   + optional 1-seg landing (-2.2, pit_ly) -> A0=(0,0) hung from tl (or direct jump to A0!)
# - River left ramp: A0=(0,0) -> (lx, ry) with 3-4 segs, braced by A1=(0,-2) and hung from tl=(0, th_l)
# - River right landing: (rx, ly) -> A7=(24,0), NO right tower, braced by A8=(24,-2) and hung from A7=(24,0)!

def make_l5_win(
    pit_ex=-3.8, pit_ey=1.0, pit_bow=0.15,
    pit_land=True, pit_lx=-2.1, pit_ly=-0.4,
    lx=7.2, ry=1.4, l_bow=0.15,
    rx=14.5, ly=-2.8,
    th_l=3.8,
    backstay="A5", # A5, A2, or None
):
    nodes, members = [], []
    def add(x, y):
        nodes.append([round(x, 4), round(y, 4)])
        return len(nodes) - 1

    tl = add(0.0, th_l)
    members.append(["A0", tl, "steel"])
    if backstay:
        members.append([backstay, tl, "cable"])

    # 1. Pit ramp: 3 segs from A2=(-11,0) to (pit_ex, pit_ey)
    n_p = max(3, math.ceil(math.hypot(pit_ex + 11.0, pit_ey) / 2.42))
    pr = ["A2"]
    for i in range(1, n_p + 1):
        t = i / n_p
        x = -11.0 + (pit_ex + 11.0) * t
        y = pit_ey * t + pit_bow * 4.0 * t * (1.0 - t)
        pr.append(add(x, y))
    for i in range(n_p):
        members.append([pr[i], pr[i+1], "road"])
    for i in range(1, n_p + 1):
        members.append([tl, pr[i], "cable"])

    if pit_land:
        pl = add(pit_lx, pit_ly)
        members += [[pl, "A0", "road"], [tl, pl, "cable"]]

    # 2. River left ramp: A0=(0,0) to (lx, ry)
    n_l = max(2, math.ceil(math.hypot(lx, ry) / 2.42))
    l_r = ["A0"]
    for i in range(1, n_l + 1):
        t = i / n_l
        x = lx * t
        y = ry * t + l_bow * 4.0 * t * (1.0 - t)
        l_r.append(add(x, y))
    for i in range(n_l):
        members.append([l_r[i], l_r[i+1], "road"])
    members.append(["A1", l_r[1], "steel"])
    for i in range(2, n_l + 1):
        members.append([tl, l_r[i], "cable"])

    # 3. River right landing: (rx, ly) to A7=(24,0), NO right tower!
    span_r = 24.0 - rx
    n_r = max(2, math.ceil(math.hypot(span_r, -ly) / 2.42))
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

# Step 1: Verify pit crossing with pit_land=True!
print("=== STEP 1: CHECK PIT CROSSING ===", flush=True)
for pit_ex in [-3.9, -4.3, -4.7]:
    for pit_ey in [0.4, 0.8, 1.2]:
        for pit_land in [True, False]:
            d = make_l5_win(pit_ex, pit_ey, 0.15, pit_land, -2.1, -0.4, 7.0, 1.4, 0.15, 15.2, -2.8, 3.4, None)
            try:
                P = bridge.parse_design(lv, d)
            except Exception:
                continue
            r1, rep1 = bridge.simulate(lv, P, sc1, replay=True)
            r2, rep2 = bridge.simulate(lv, P, sc2, replay=True)
            nb = P["n_anchor"] + len(d["nodes"])
            mx1 = max((fr["p"][2*nb] for fr in rep1["frames"] if len(fr["p"]) > 2*nb), default=-99)
            mx2 = max((fr["p"][2*nb] for fr in rep2["frames"] if len(fr["p"]) > 2*nb), default=-99)
            if mx1 > 5.0 and mx2 > 5.0:
                print(f"PIT PASS!! cost={P['cost']:.1f} ex={pit_ex} ey={pit_ey} land={pit_land} mx1={mx1:.1f} mx2={mx2:.1f} pk1={max(r1['peak_members'])*100:.0f}% pk2={max(r2['peak_members'])*100:.0f}%", flush=True)
                best_pit = (pit_ex, pit_ey, pit_land)
                break
        else: continue
        break
    else: continue
    break
else:
    best_pit = None
    print("Pit still didn't reach x>5, checking why on ex=-4.2 ey=0.8 land=True:")
    d = make_l5_win(-4.2, 0.8, 0.15, True, -2.1, -0.4, 7.0, 1.4, 0.15, 15.2, -2.8, 3.4, None)
    P = bridge.parse_design(lv, d)
    r1, rep1 = bridge.simulate(lv, P, sc1, replay=True)
    nb = P["n_anchor"] + len(d["nodes"])
    print("cost:", P["cost"], "ev1:", r1["events"][:6])
    for fr in rep1["frames"][60:180:6]:
        vp = fr["p"][2*nb:]
        if len(vp) >= 4:
            print(f"  t={fr['t']:.2f} v0=({vp[0]:.2f},{vp[1]:.2f})..({vp[2]:.2f},{vp[3]:.2f}) st={fr['v'][0]}")
        if fr["v"][0] != 1: break

if best_pit:
    pit_ex, pit_ey, pit_land = best_pit
    print(f"\n=== STEP 2: SWEEP RIVER JUMP WITH PIT {best_pit} ===", flush=True)
    best5 = None
    for lx in [6.8, 7.2, 7.8, 8.4]:
        for ry in [0.8, 1.4, 2.0, 2.5]:
            for rx in [12.5, 13.5, 14.3, 15.0, 15.8]:
                for ly in [-2.0, -2.8, -3.5, -4.2]:
                    for bs in ["A5", None]:
                        d = make_l5_win(pit_ex, pit_ey, 0.15, pit_land, -2.1, -0.4, lx, ry, 0.15, rx, ly, 3.8, bs)
                        ok, cost, pk, msgs = eval_design(5, d)
                        if cost is not None and ok:
                            if best5 is None or cost < best5[0]:
                                best5 = (cost, d)
                                print(f"PASS L5!! cost={cost:.1f} lx={lx} ry={ry} rx={rx} ly={ly} bs={bs} pk={pk*100:.1f}%", flush=True)
                                save_if_better(5, d, SUB / "level5.json")
    if best5:
        print("\n=== BEST L5 ===")
        eval_design(5, best5[1], verbose=True)
    else:
        print("No full pass yet; tracing river jump:")
        d = make_l5_win(pit_ex, pit_ey, 0.15, pit_land, -2.1, -0.4, 7.2, 1.5, 0.15, 14.5, -2.8, 3.8, None)
        P = bridge.parse_design(lv, d)
        nb = P["n_anchor"] + len(d["nodes"])
        for name, sc in [("s1", sc1), ("s2", sc2)]:
            res, rep = bridge.simulate(lv, P, sc, replay=True)
            print(name, "cost:", P["cost"], res["events"][:6])
            for fr in rep["frames"][100:240:6]:
                vp = fr["p"][2*nb:]
                if len(vp) >= 4:
                    print(f"  t={fr['t']:.2f} v0=({vp[0]:.2f},{vp[1]:.2f})..({vp[2]:.2f},{vp[3]:.2f}) st={fr['v'][0]}")
                if fr["v"][0] != 1: break
