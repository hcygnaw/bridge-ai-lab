import json, math, sys
from pathlib import Path

WS = Path(__file__).resolve().parent
sys.path.insert(0, str(WS))
import bridge
from opt_util import eval_design, save_if_better

SUB = WS / "submission"
SUB.mkdir(exist_ok=True)

# LEVEL 5: 2-prop + cable-supported pit + rigid river jump!
def make_l5_v2(
    pit_y1=-0.9, pit_y2=-1.4,
    lx=7.0, ry=1.4,
    rx=15.0, ly=-3.2,
    th_l=3.2,
    p1_sup="A6_steel", # "A6_steel", "none", "A2_mid"
    p4_sup="tl_cable", # "tl_cable", "A3_steel"
):
    nodes, members = [], []
    def add(x, y):
        nodes.append([round(x, 4), round(y, 4)])
        return len(nodes) - 1

    # Tower
    tl = add(0.0, th_l)
    members += [["A0", tl, "steel"], ["A4", tl, "cable"]]

    # Pit
    p1 = add(-8.8, pit_y1)
    p2 = add(-6.6, pit_y2)
    p3 = add(-4.4, pit_y2)
    p4 = add(-2.2, pit_y1)
    pit_r = ["A2", p1, p2, p3, p4, "A0"]
    for i in range(5):
        members.append([pit_r[i], pit_r[i+1], "road"])
    members += [["A5", p2, "steel"], ["A4", p3, "steel"]]
    if p1_sup == "A6_steel":
        members.append(["A6", p1, "steel"])
    elif p1_sup == "tl_cable":
        members.append([tl, p1, "cable"])
    if p4_sup == "tl_cable":
        members.append([tl, p4, "cable"])
    elif p4_sup == "A3_steel":
        members.append(["A3", p4, "steel"])

    # Left river ramp: A0=(0,0) -> (lx, ry)
    n_l = max(2, math.ceil(math.hypot(lx, ry) / 2.42))
    l_r = ["A0"]
    for i in range(1, n_l + 1):
        t = i / n_l
        l_r.append(add(lx * t, ry * (t ** 1.1)))
    for i in range(n_l):
        members.append([l_r[i], l_r[i+1], "road"])
    members.append(["A1", l_r[1], "steel"])
    for i in range(2, n_l + 1):
        members.append([tl, l_r[i], "cable"])

    # Right river landing: (rx, ly) -> A7=(24,0), NO right tower!
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

print("=== LEVEL 5 FULL PASS SWEEP ===", flush=True)
best5 = None
for p1_sup in ["none", "A6_steel"]:
    for lx in [6.8, 7.2, 7.6]:
        for ry in [1.0, 1.5, 2.0, 2.4]:
            for rx in [13.8, 14.5, 15.2, 16.0]:
                for ly in [-2.5, -3.2, -4.0, -4.6]:
                    d = make_l5_v2(-0.9, -1.4, lx, ry, rx, ly, 3.2, p1_sup, "tl_cable")
                    ok, cost, pk, msgs = eval_design(5, d)
                    if cost is not None:
                        if ok:
                            if best5 is None or cost < best5[0]:
                                best5 = (cost, d)
                                print(f"PASS L5!! cost={cost:.1f} p1={p1_sup} lx={lx} ry={ry} rx={rx} ly={ly} pk={pk*100:.1f}%", flush=True)
                                save_if_better(5, d, SUB / "level5.json")

if best5:
    print("\n=== BEST L5 ===")
    eval_design(5, best5[1], verbose=True)
else:
    print("No pass yet; tracing lx=7.0 ry=1.5 rx=15.0 ly=-3.5:")
    d = make_l5_v2(-0.9, -1.4, 7.0, 1.5, 15.0, -3.5, 3.2, "none", "tl_cable")
    P = bridge.parse_design(lv, d)
    print("cost:", P["cost"])
    nb = P["n_anchor"] + len(d["nodes"])
    for name, sc in [("s1", sc1), ("s2", sc2)]:
        res, rep = bridge.simulate(lv, P, sc, replay=True)
        print(name, "pk:", f"{max(res['peak_members'])*100:.1f}%", "ev:", res["events"][:8])
        for fr in rep["frames"][100:260:8]:
            vp = fr["p"][2*nb:]
            if len(vp) >= 4:
                print(f"  t={fr['t']:.2f} v0=({vp[0]:.2f},{vp[1]:.2f})..({vp[2]:.2f},{vp[3]:.2f}) st={fr['v'][0]}")
            if fr["v"][0] != 1: break
