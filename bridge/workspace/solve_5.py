import json, math, sys
from pathlib import Path

WS = Path(__file__).resolve().parent
sys.path.insert(0, str(WS))
import bridge
from opt_util import eval_design, save_if_better

SUB = WS / "submission"
SUB.mkdir(exist_ok=True)

def dist(a, b):
    return math.hypot(a[0]-b[0], a[1]-b[1])

# Level 5 anchors:
# A0=(0,0), A1=(0,-2), A2=(-11,0), A3=(-2,-4), A4=(-4,-4), A5=(-6,-4), A6=(-8,-4),
# A7=(24,0), A8=(24,-2), A9=(30,0)
# Budget: 10000, NO WOOD!

def make_l5_cable_stayed(
    pit_sag=0.5,
    pit_prop=True,
    n_riv=10,
    riv_sag=1.5,
    tower_h=4.0,
    stays=(2, 4),
    use_right_tower=True,
    tower_brace=True,
):
    nodes = []
    members = []
    def add(x, y):
        nodes.append([round(x, 4), round(y, 4)])
        return len(nodes) - 1

    # 1. Pit bridge: A2=(-11,0) to A0=(0,0), 5 road segments (2.2m each)
    n_pit = 5
    pit_r = ["A2"]
    for i in range(1, n_pit):
        t = i / n_pit
        x = -11.0 + 11.0 * t
        y = -4.0 * pit_sag * t * (1.0 - t)
        pit_r.append(add(x, y))
    pit_r.append("A0")
    for i in range(n_pit):
        members.append([pit_r[i], pit_r[i+1], "road"])
    if pit_prop:
        # Steel props from A5=(-6,-4) to pit_r[2] (-6.6, y) and pit_r[3] (-4.4, y)
        # Wait: A5=(-6,-4) to (-6.6, -0.5) is 3.55m -> steel buckles at 900/12.6 = 71 kN! Plenty!
        members.append(["A5", pit_r[2], "steel"])
        members.append(["A4", pit_r[3], "steel"])
        # Optional cable from A2 to pit_r[2] and A0 to pit_r[3]? No, road is in tension/compression.

    # 2. River bridge: A0=(0,0) to A7=(24,0), n_riv segments
    riv_r = ["A0"]
    for i in range(1, n_riv):
        t = i / n_riv
        x = 24.0 * t
        y = -4.0 * riv_sag * t * (1.0 - t)
        riv_r.append(add(x, y))
    riv_r.append("A7")
    for i in range(n_riv):
        members.append([riv_r[i], riv_r[i+1], "road"])

    # Left tower at (0, tower_h)
    tl = add(0.0, tower_h)
    members.append(["A0", tl, "steel"])
    members.append(["A2", tl, "cable"]) # backstay to (-11, 0)!
    if tower_brace:
        # mid brace to prevent buckling if tower_h > 3.5
        pass

    # Right tower at (24, tower_h)
    if use_right_tower:
        tr = add(24.0, tower_h)
        members.append(["A7", tr, "steel"])
        members.append(["A9", tr, "cable"]) # backstay to (30, 0)!

    for idx in stays:
        members.append([tl, riv_r[idx], "cable"])
        if use_right_tower:
            members.append([tr, riv_r[n_riv - idx], "cable"])

    return {"nodes": nodes, "members": members}

print("=== LEVEL 5 CABLE-STAYED CATENARY SWEEP ===", flush=True)
best5 = None
for n_riv in [10, 11]:
    for riv_sag in [0.5, 1.0, 1.5, 2.0, 2.5]:
        for th in [3.5, 4.5, 5.5]:
            for stays in [(2, 4), (2, 5), (3, 5), (2, 3, 4, 5)]:
                d = make_l5_cable_stayed(0.4, True, n_riv, riv_sag, th, stays, True)
                ok, cost, pk, msgs = eval_design(5, d)
                if ok:
                    if best5 is None or cost < best5[0]:
                        best5 = (cost, d)
                        print(f"NEW BEST L5: {cost:.1f} (n={n_riv} sag={riv_sag} th={th} stays={stays}) pk={pk*100:.1f}%", flush=True)
                        save_if_better(5, d, SUB / "level5.json")

if best5:
    print("\n=== BEST L5 ===")
    eval_design(5, best5[1], verbose=True)
else:
    print("No pass yet, printing diagnostic on one candidate:")
    d = make_l5_cable_stayed(0.4, True, 10, 1.5, 4.5, (2, 4, 5), True)
    eval_design(5, d, verbose=True)
