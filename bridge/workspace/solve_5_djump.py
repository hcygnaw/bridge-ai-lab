import json, math, sys
from pathlib import Path

WS = Path(__file__).resolve().parent
sys.path.insert(0, str(WS))
import bridge
from opt_util import eval_design, save_if_better

SUB = WS / "submission"
SUB.mkdir(exist_ok=True)

# LEVEL 5 DOUBLE-JUMP (PIT JUMP + RIVER JUMP, ZERO RIGHT TOWER!)
def make_l5_double_jump(
    # Pit ramp: A2=(-11,0) -> p1 -> p2, jump to p3 -> A0=(0,0)
    pit_jump=True,
    pit_rx=-6.6, pit_ry=0.8,
    pit_lx=-2.3, pit_ly=-0.5,
    # River left ramp: A0=(0,0) -> (lx_end, ry)
    lx_end=7.0, ry=1.4,
    # River right landing: (rx_start, ly) -> A7=(24,0)
    rx_start=14.5, ly=-2.8,
    th_l=3.6,
    right_stays="A7_only",
):
    nodes = []
    members = []
    def add(x, y):
        nodes.append([round(x, 4), round(y, 4)])
        return len(nodes) - 1

    # Left tower at (0, th_l)
    tl = add(0.0, th_l)
    members.append(["A0", tl, "steel"])
    members.append(["A5", tl, "cable"]) # backstay to (-6, -4)

    # 1. Pit
    if pit_jump:
        # 2 road segs from A2=(-11,0) to (pit_rx, pit_ry)
        p1 = add(-11.0 + 0.5*(pit_rx + 11.0), 0.45*pit_ry)
        p2 = add(pit_rx, pit_ry)
        members += [["A2", p1, "road"], [p1, p2, "road"]]
        # Support pit ramp by cables from tl (or steel from A6)?
        # Wait: A2->p1->p2 is pushed DOWN by car, so cables from tl=(0, th_l) pull UP and RIGHT (into compression in A2->p1->p2)!
        members += [[tl, p1, "cable"], [tl, p2, "cable"]]
        # Landing segment (pit_lx, pit_ly) -> A0=(0,0)
        p3 = add(pit_lx, pit_ly)
        members.append([p3, "A0", "road"])
        members.append([tl, p3, "cable"])
    else:
        # Continuous 5-seg pit hung from tl?
        p1 = add(-8.8, -0.5)
        p2 = add(-6.6, -0.8)
        p3 = add(-4.4, -0.8)
        p4 = add(-2.2, -0.5)
        pit_r = ["A2", p1, p2, p3, p4, "A0"]
        for i in range(5):
            members.append([pit_r[i], pit_r[i+1], "road"])
        members += [["A6", p1, "steel"], ["A5", p2, "steel"], ["A4", p3, "steel"], ["A3", p4, "steel"]]

    # 2. River left ramp: A0=(0,0) to (lx_end, ry), 3 road segs
    n_l = max(2, math.ceil(math.hypot(lx_end, ry) / 2.4))
    l_r = ["A0"]
    for i in range(1, n_l + 1):
        t = i / n_l
        l_r.append(add(lx_end * t, ry * (t ** 1.15)))
    for i in range(n_l):
        members.append([l_r[i], l_r[i+1], "road"])
    members.append(["A1", l_r[1], "steel"])
    for i in range(2, n_l + 1):
        members.append([tl, l_r[i], "cable"])

    # 3. River right landing: (rx_start, ly) to A7=(24,0), NO RIGHT TOWER!
    span_r = 24.0 - rx_start
    n_r = max(2, math.ceil(math.hypot(span_r, -ly) / 2.4))
    r_r = []
    for i in range(n_r):
        t = i / n_r
        r_r.append(add(rx_start + span_r * t, ly * (1.0 - t)))
    r_r.append("A7")
    for i in range(n_r):
        members.append([r_r[i], r_r[i+1], "road"])

    if right_stays == "A7_only":
        # A8=(24,-2) struts r_r[-2], cables from A7=(24,0) to r_r[0..n_r-2]
        members.append(["A8", r_r[n_r - 1], "steel"])
        for i in range(0, n_r - 1):
            members.append(["A7", r_r[i], "cable"])
    elif right_stays == "tiny_tr":
        tr = add(24.0, 1.8)
        members += [["A7", tr, "steel"], ["A9", tr, "cable"], ["A8", r_r[n_r - 1], "steel"]]
        for i in range(0, n_r - 1):
            members.append([tr, r_r[i], "cable"])

    return {"nodes": nodes, "members": members}

print("=== LEVEL 5 DOUBLE-JUMP SWEEP ===", flush=True)
best5 = None
for rs_mode in ["A7_only", "tiny_tr"]:
    for lx_end in [6.8, 7.2, 7.8]:
        for ry in [1.0, 1.4, 1.8]:
            for rx_start in [13.5, 14.2, 15.0, 15.8]:
                for ly in [-2.2, -2.8, -3.4]:
                    d = make_l5_double_jump(True, -6.6, 0.7, -2.3, -0.4, lx_end, ry, rx_start, ly, 3.6, rs_mode)
                    ok, cost, pk, msgs = eval_design(5, d)
                    if cost is not None:
                        if ok:
                            if best5 is None or cost < best5[0]:
                                best5 = (cost, d)
                                print(f"PASS L5!! cost={cost:.1f} rs={rs_mode} lx={lx_end} ry={ry} rx={rx_start} ly={ly} pk={pk*100:.1f}%", flush=True)
                                save_if_better(5, d, SUB / "level5.json")
                        elif pk < 1.5:
                            print(f"  close: cost={cost:.1f} pk={pk*100:.1f}% rs={rs_mode} lx={lx_end} ry={ry} rx={rx_start} ly={ly} | {msgs[0].splitlines()[0][:55]}", flush=True)

if best5:
    print("\n=== BEST L5 ===")
    eval_design(5, best5[1], verbose=True)
else:
    print("No pass yet; printing diagnostic:")
    d = make_l5_double_jump(True, -6.6, 0.7, -2.3, -0.4, 7.2, 1.4, 14.5, -2.8, 3.6, "A7_only")
    eval_design(5, d, verbose=True)
