import json, math, sys
from pathlib import Path

WS = Path(__file__).resolve().parent
sys.path.insert(0, str(WS))
import bridge
from opt_util import eval_design, save_if_better

SUB = WS / "submission"
SUB.mkdir(exist_ok=True)

# LEVEL 5 GENIUS DISCOVERY:
# Vehicles drive off (-11, 0), drop smoothly into the pit, and climb out on a ramp anchored at A6=(-8,-4) or A5=(-6,-4) to A0=(0,0)!
# Cost of entire pit crossing: ~$1,300 - $1,800!
# Leaving ~$8,200 for the 24m river (plenty for a rigid river jump OR cable-stayed / suspension bridge)!

def make_l5_pit_ramp(
    pit_start="A6", # A6=(-8,-4) or A5=(-6,-4)
    pit_props=True,
    # River: rigid cantilever ramp jump!
    lx_end=8.5, ry=1.5,
    rx_start=15.0, ly=-2.8,
    th_l=3.6,
    th_r=0.0, # 0 = no right tower (cables from A7 directly!)
):
    nodes, members = [], []
    def add(x, y):
        nodes.append([round(x, 4), round(y, 4)])
        return len(nodes) - 1

    # 1. Pit exit ramp: from A6=(-8,-4) or A5=(-6,-4) to A0=(0,0)
    sx = -8.0 if pit_start == "A6" else -6.0
    n_p = 4 if pit_start == "A6" else 3
    p_r = [pit_start]
    for i in range(1, n_p):
        t = i / n_p
        p_r.append(add(sx * (1.0 - t), -4.0 * (1.0 - t)))
    p_r.append("A0")
    for i in range(n_p):
        members.append([p_r[i], p_r[i+1], "road"])
    if pit_props:
        if pit_start == "A6":
            # Prop p_r[1] (-6,-3) from A5=(-6,-4) [1m steel!], p_r[2] (-4,-2) from A4=(-4,-4) [2m steel!], p_r[3] (-2,-1) from A3=(-2,-4) [3m steel!]
            members += [["A5", p_r[1], "steel"], ["A4", p_r[2], "steel"], ["A3", p_r[3], "steel"]]
        else:
            # A5=(-6,-4) -> (-4,-2.67) -> (-2,-1.33) -> A0
            members += [["A4", p_r[1], "steel"], ["A3", p_r[2], "steel"]]

    # 2. Left river ramp: A0=(0,0) -> (lx_end, ry)
    n_l = max(2, math.ceil(math.hypot(lx_end, ry) / 2.4))
    l_r = ["A0"]
    for i in range(1, n_l + 1):
        t = i / n_l
        l_r.append(add(lx_end * t, ry * (t ** 1.15)))
    for i in range(n_l):
        members.append([l_r[i], l_r[i+1], "road"])

    tl = add(0.0, th_l)
    members += [["A0", tl, "steel"], ["A4", tl, "cable"], ["A1", l_r[1], "steel"]]
    for i in range(2, n_l + 1):
        members.append([tl, l_r[i], "cable"])

    # 3. Right river landing: (rx_start, ly) -> A7=(24,0)
    span_r = 24.0 - rx_start
    n_r = max(2, math.ceil(math.hypot(span_r, -ly) / 2.4))
    r_r = []
    for i in range(n_r):
        t = i / n_r
        r_r.append(add(rx_start + span_r * t, ly * (1.0 - t)))
    r_r.append("A7")
    for i in range(n_r):
        members.append([r_r[i], r_r[i+1], "road"])
    members.append(["A8", r_r[n_r - 1], "steel"])

    if th_r > 0:
        tr = add(24.0, th_r)
        members += [["A7", tr, "steel"], ["A9", tr, "cable"]]
        top_r = tr
    else:
        top_r = "A7"
    for i in range(0, n_r - 1):
        members.append([top_r, r_r[i], "cable"])

    return {"nodes": nodes, "members": members}

print("=== LEVEL 5 PIT-RAMP + RIVER-JUMP SWEEP ===", flush=True)
best5 = None
for pit_s in ["A6", "A5"]:
    for lx_end in [7.2, 8.2, 9.2]:
        for ry in [1.0, 1.5, 2.0]:
            for gap in [4.5, 5.5, 6.5, 7.5]:
                rx_start = lx_end + gap
                if rx_start > 19.0: continue
                for ly in [-2.0, -2.8, -3.5]:
                    for th_r in [0.0, 2.0]:
                        d = make_l5_pit_ramp(pit_s, True, lx_end, ry, rx_start, ly, 3.6, th_r)
                        ok, cost, pk, msgs = eval_design(5, d)
                        if cost is not None:
                            if ok:
                                if best5 is None or cost < best5[0]:
                                    best5 = (cost, d)
                                    print(f"PASS L5!! cost={cost:.1f} pit={pit_s} lx={lx_end} ry={ry} rx={rx_start} ly={ly} thr={th_r} pk={pk*100:.1f}%", flush=True)
                                    save_if_better(5, d, SUB / "level5.json")
                            elif pk < 1.5:
                                # Check if car survived past t=6s
                                pass

if best5:
    print("\n=== BEST L5 ===")
    eval_design(5, best5[1], verbose=True)
else:
    print("No pass yet; printing diagnostic on one candidate:")
    d = make_l5_pit_ramp("A6", True, 8.5, 1.5, 14.5, -2.8, 3.6, 0.0)
    eval_design(5, d, verbose=True)
