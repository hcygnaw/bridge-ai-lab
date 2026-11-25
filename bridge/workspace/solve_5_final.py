import json, math, sys
from pathlib import Path

WS = Path(__file__).resolve().parent
sys.path.insert(0, str(WS))
import bridge
from opt_util import eval_design, save_if_better

SUB = WS / "submission"
SUB.mkdir(exist_ok=True)

# LEVEL 5:
# 1. Pit ($2,524!): 5 road segs dipping to y=-1.6, propped ONLY at p2 (from A5) and p3 (from A4)!
#    p1 and p4 are slight catenary dips between A2-p2 and p3-A0 (only 4.4m sub-spans -> tiny tension!)
# 2. River ($6,800!):
#    Left rigid cantilever ramp A0=(0,0) -> (lx, ry) braced by A1=(0,-2) and tower tl=(0, th_l) + backstay to A4 or A3!
#    Right rigid landing (rx, ly) -> A7=(24,0) braced by A8=(24,-2) and direct cables from A7=(24,0) (NO right tower!)

def make_l5_final(
    pit_y1=-1.1, pit_y2=-1.6,
    lx=7.2, ry=1.4,
    rx=14.2, ly=-2.8,
    th_l=3.6,
    l_pow=1.1,
    pit_cables=False,
):
    nodes, members = [], []
    def add(x, y):
        nodes.append([round(x, 4), round(y, 4)])
        return len(nodes) - 1

    # 1. Pit
    p1 = add(-8.8, pit_y1)
    p2 = add(-6.6, pit_y2)
    p3 = add(-4.4, pit_y2)
    p4 = add(-2.2, pit_y1)
    pit_r = ["A2", p1, p2, p3, p4, "A0"]
    for i in range(5):
        members.append([pit_r[i], pit_r[i+1], "road"])
    members += [["A5", p2, "steel"], ["A4", p3, "steel"]]
    # Brace p2 and p3 horizontally? p2-p3 road + A5/A4 diagonal struts already triangulate!
    if pit_cables:
        members += [["A6", p2, "cable"], ["A3", p3, "cable"]]

    # 2. Left river ramp: A0=(0,0) -> (lx, ry)
    n_l = max(2, math.ceil(math.hypot(lx, ry) / 2.42))
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

    # 3. Right river landing: (rx, ly) -> A7=(24,0), NO right tower!
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

print("=== LEVEL 5 PIT-2PROP + RIVER-JUMP SWEEP ===", flush=True)
best5 = None
for lx in [6.8, 7.2, 7.8]:
    for ry in [0.8, 1.3, 1.8, 2.2]:
        for rx in [12.5, 13.5, 14.2, 15.0, 15.8]:
            for ly in [-2.2, -2.8, -3.5, -4.2]:
                d = make_l5_final(-1.1, -1.6, lx, ry, rx, ly, 3.4, 1.1, False)
                ok, cost, pk, msgs = eval_design(5, d)
                if cost is not None:
                    if ok:
                        if best5 is None or cost < best5[0]:
                            best5 = (cost, d)
                            print(f"PASS L5!! cost={cost:.1f} lx={lx} ry={ry} rx={rx} ly={ly} pk={pk*100:.1f}%", flush=True)
                            save_if_better(5, d, SUB / "level5.json")
                    elif pk < 1.0:
                        # check if any vehicle arrived
                        pass

if best5:
    print("\n=== BEST L5 ===")
    eval_design(5, best5[1], verbose=True)
else:
    print("No pass yet; tracing lx=7.2 ry=1.4 rx=14.2 ly=-3.2:")
    d = make_l5_final(-1.1, -1.6, 7.2, 1.4, 14.2, -3.2, 3.4, 1.1, False)
    P = bridge.parse_design(lv, d)
    print("cost:", P["cost"])
    nb = P["n_anchor"] + len(d["nodes"])
    for name, sc in [("s1", sc1), ("s2", sc2)]:
        res, rep = bridge.simulate(lv, P, sc, replay=True)
        print(name, "pk:", f"{max(res['peak_members'])*100:.1f}%", "ev:", res["events"][:8])
        for fr in rep["frames"][60:240:8]:
            vp = fr["p"][2*nb:]
            if len(vp) >= 4:
                print(f"  t={fr['t']:.2f} v0=({vp[0]:.2f},{vp[1]:.2f})..({vp[2]:.2f},{vp[3]:.2f}) st={fr['v'][0]}")
            if fr["v"][0] != 1: break
