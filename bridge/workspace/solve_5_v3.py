import json, math, sys
from pathlib import Path

WS = Path(__file__).resolve().parent
sys.path.insert(0, str(WS))
import bridge
from opt_util import eval_design, save_if_better

SUB = WS / "submission"
SUB.mkdir(exist_ok=True)

def make_l5_minimal(pit_sag=-0.8, pit_type="arch_tie", n_riv=11, riv_sag=2.5,
                    stays=(3, 5), end_strut=False, tie_under=False,
                    jump_gap=0.0, ramp_y=1.0, land_y=-2.0):
    nodes = []
    members = []
    def add(x, y):
        nodes.append([round(x, 4), round(y, 4)])
        return len(nodes) - 1

    # Pit: A2=(-11,0) to A0=(0,0), 5 segs (2.2m each)
    n_pit = 5
    pit_r = ["A2"]
    for i in range(1, n_pit):
        t = i / n_pit
        x = -11.0 + 11.0 * t
        y = -4.0 * pit_sag * t * (1.0 - t) # negative pit_sag -> upward arch!
        pit_r.append(add(x, y))
    pit_r.append("A0")
    for i in range(n_pit):
        members.append([pit_r[i], pit_r[i+1], "road"])

    if pit_type == "arch_tie":
        # Anchor pit arch down with 2 cables to A5=(-6,-4) and A4=(-4,-4)
        members.append(["A6", pit_r[1], "cable"])
        members.append(["A5", pit_r[2], "cable"])
        members.append(["A4", pit_r[3], "cable"])
        members.append(["A3", pit_r[4], "cable"])
    elif pit_type == "arch_2tie":
        members.append(["A5", pit_r[2], "cable"])
        members.append(["A4", pit_r[3], "cable"])
    elif pit_type == "one_v":
        members.append(["A5", pit_r[2], "steel"])
        members.append(["A5", pit_r[3], "steel"])
    elif pit_type == "cat_cable":
        members.append(["A2", pit_r[2], "cable"])
        members.append(["A0", pit_r[3], "cable"])
    elif pit_type == "pure":
        pass

    if jump_gap <= 0.0:
        # Continuous river road: A0=(0,0) to A7=(24,0)
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
            members.append(["A1", riv_r[1], "steel"])
            members.append(["A8", riv_r[n_riv-1], "steel"])
        for k in stays:
            members.append(["A0", riv_r[k], "cable"])
            members.append(["A7", riv_r[n_riv - k], "cable"])
        if tie_under:
            # Cable from A1=(0,-2) to riv_r[2], etc.
            members.append(["A1", riv_r[2], "cable"])
            members.append(["A8", riv_r[n_riv - 2], "cable"])
    else:
        # Jump across river!
        # Left ramp: A0=(0,0) to (lx_end, ramp_y)
        lx_end = 12.0 - jump_gap * 0.5
        rx_start = 12.0 + jump_gap * 0.5
        n_l = max(2, math.ceil(math.hypot(lx_end, ramp_y) / 2.35))
        l_r = ["A0"]
        for i in range(1, n_l + 1):
            t = i / n_l
            l_r.append(add(lx_end * t, ramp_y * t))
        for i in range(n_l):
            members.append([l_r[i], l_r[i+1], "road"])
        # Support left ramp from A1=(0,-2) + cable/steel
        members.append(["A1", l_r[1], "steel"])
        if n_l >= 2:
            # Make a simple cantilever truss underneath with steel? Or tower at (0, 3)?
            tl = add(0.0, 3.5)
            members.append(["A0", tl, "steel"])
            members.append(["A2", tl, "cable"])
            for i in range(2, n_l + 1):
                members.append([tl, l_r[i], "cable"])

        # Right landing deck: (rx_start, land_y) up to A7=(24,0)
        n_r = max(2, math.ceil(math.hypot(24.0 - rx_start, -land_y) / 2.35))
        r_r = []
        for i in range(n_r):
            t = i / n_r
            r_r.append(add(rx_start + (24.0 - rx_start) * t, land_y * (1.0 - t)))
        r_r.append("A7")
        for i in range(n_r):
            members.append([r_r[i], r_r[i+1], "road"])
        tr = add(24.0, 3.5)
        members.append(["A7", tr, "steel"])
        members.append(["A9", tr, "cable"])
        for i in range(0, n_r - 1):
            members.append([tr, r_r[i], "cable"])
        members.append(["A8", r_r[n_r - 1], "steel"])

    return {"nodes": nodes, "members": members}

print("=== TEST 1: CONTINUOUS MINIMAL CATENARY/ARCH ===", flush=True)
best5 = None
for pit_sag, pit_type in [(-1.0, "arch_2tie"), (-1.2, "arch_tie"), (0.5, "one_v"), (1.2, "pure")]:
    for n_riv in [11, 12]:
        for riv_sag in [1.5, 2.2, 3.0, -2.0, -2.8]:
            for stays in [(3, 5), (2, 4, 5), (3, 4, 5), (2, 4)]:
                for es in [False, True]:
                    d = make_l5_minimal(pit_sag, pit_type, n_riv, riv_sag, stays, es)
                    ok, cost, pk, msgs = eval_design(5, d)
                    if cost is not None and cost <= 10000:
                        if ok:
                            if best5 is None or cost < best5[0]:
                                best5 = (cost, d)
                                print(f"PASS L5!! cost={cost:.1f} pit={pit_type} n={n_riv} sag={riv_sag} stays={stays} es={es} pk={pk*100:.1f}%", flush=True)
                                save_if_better(5, d, SUB / "level5.json")
                        elif pk < 1.5:
                            print(f"  close: cost={cost:.1f} pk={pk*100:.1f}% pit={pit_type} sag={riv_sag} stays={stays} es={es}", flush=True)

print("=== TEST 2: JUMP GAP ===", flush=True)
for gap in [4.0, 5.0, 6.0, 7.0]:
    for ramp_y in [0.5, 1.2, 1.8]:
        for land_y in [-1.5, -2.5, -3.5]:
            d = make_l5_minimal(-1.0, "arch_2tie", 11, 0, (), False, False, gap, ramp_y, land_y)
            ok, cost, pk, msgs = eval_design(5, d)
            if cost is not None and cost <= 10000:
                if ok:
                    if best5 is None or cost < best5[0]:
                        best5 = (cost, d)
                        print(f"PASS L5 JUMP!! cost={cost:.1f} gap={gap} ry={ramp_y} ly={land_y} pk={pk*100:.1f}%", flush=True)
                        save_if_better(5, d, SUB / "level5.json")
                elif pk < 2.0:
                    print(f"  jump close: cost={cost:.1f} pk={pk*100:.1f}% gap={gap} ry={ramp_y} ly={land_y} {msgs[0][:55]}", flush=True)

if best5:
    print("\n=== BEST L5 ===")
    eval_design(5, best5[1], verbose=True)
else:
    print("No pass yet; checking sample jump diagnostic:")
    d = make_l5_minimal(-1.0, "arch_2tie", 11, 0, (), False, False, 5.0, 1.2, -2.5)
    eval_design(5, d, verbose=True)
