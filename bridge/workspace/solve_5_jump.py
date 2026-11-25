import json, math, sys
from pathlib import Path

WS = Path(__file__).resolve().parent
sys.path.insert(0, str(WS))
import bridge
from opt_util import eval_design, save_if_better

SUB = WS / "submission"
SUB.mkdir(exist_ok=True)

# LEVEL 5: RIGID CANTILEVER RAMP JUMP!
# Pit (-11 to 0): 5 road segs dipping slightly to y=-1.0, propped by 4 steel struts from A6, A5, A4, A3 -> rock solid!
# Wait: A6=(-8,-4) to (-8.8,-0.8) = 3.3m ($528), A5=(-6,-4) to (-6.6,-1.2) = 2.86m ($458),
#       A4=(-4,-4) to (-4.4,-1.2) = 2.83m ($453), A3=(-2,-4) to (-2.2,-0.8) = 3.2m ($512) -> ~$1950 + $1700 = $3650.
# Even cheaper pit: 2 steel V-struts from A5=(-6,-4) and A4=(-4,-4)? Let's test 4 struts first (rock solid)!
#
# River (0 to 24):
# Left cantilever ramp: A0=(0,0) -> (lx_end, ry) with n_l road segs,
#   supported by a short tower (0, th_l) with cable stays to every ramp node + backstay to A3=(-2,-4) or A2=(-11,0)!
#   Wait: A1=(0,-2) can ALSO strut the first ramp node!
# Right cantilever landing: (rx_start, ly) -> A7=(24,0) with n_r road segs,
#   supported by a short tower (24, th_r) with cable stays to every landing node + backstay to A9=(30,0)!
#   Plus A8=(24,-2) struts the last landing node!

def make_l5_jump(
    lx_end=8.5, ry=1.5,
    rx_start=14.5, ly=-2.2,
    th_l=3.8, th_r=2.5,
    pit_y1=-0.8, pit_y2=-1.2,
    pit_mode="4steel",
    left_curve=0.0,
):
    nodes = []
    members = []
    def add(x, y):
        nodes.append([round(x, 4), round(y, 4)])
        return len(nodes) - 1

    # 1. Pit: 5 road segs from A2=(-11,0) to A0=(0,0)
    p1 = add(-8.8, pit_y1)
    p2 = add(-6.6, pit_y2)
    p3 = add(-4.4, pit_y2)
    p4 = add(-2.2, pit_y1)
    pit_r = ["A2", p1, p2, p3, p4, "A0"]
    for i in range(5):
        members.append([pit_r[i], pit_r[i+1], "road"])
    if pit_mode == "4steel":
        members += [["A6", p1, "steel"], ["A5", p2, "steel"], ["A4", p3, "steel"], ["A3", p4, "steel"]]
    elif pit_mode == "2v":
        # A6 to p1, p2; A3 to p3, p4? No, A5=(-6,-4) to p2, A4=(-4,-4) to p3, plus cables from tl?
        members += [["A5", p2, "steel"], ["A4", p3, "steel"], ["A6", p1, "steel"], ["A3", p4, "steel"]]

    # 2. Left ramp: A0=(0,0) to (lx_end, ry)
    n_l = max(2, math.ceil(math.hypot(lx_end, ry) / 2.35))
    l_r = ["A0"]
    for i in range(1, n_l + 1):
        t = i / n_l
        # Optional slight upward curve (t**1.3) for smoother ramp entry!
        y = ry * (t ** (1.0 + left_curve))
        l_r.append(add(lx_end * t, y))
    for i in range(n_l):
        members.append([l_r[i], l_r[i+1], "road"])

    tl = add(0.0, th_l)
    members.append(["A0", tl, "steel"])
    # Backstay from tl to A3=(-2,-4)? Wait: A3 is (-2,-4), dist from (0,3.8) is 8.05m ($563), angle 75 deg (steep!).
    # Better: A4=(-4,-4) -> dist = 8.7m ($609), angle 63 deg! Or A5=(-6,-4) -> dist = 9.8m ($686)!
    members.append(["A5", tl, "cable"])
    members.append(["A1", l_r[1], "steel"])
    for i in range(2, n_l + 1):
        members.append([tl, l_r[i], "cable"])

    # 3. Right landing deck: (rx_start, ly) to A7=(24,0)
    span_r = 24.0 - rx_start
    n_r = max(2, math.ceil(math.hypot(span_r, -ly) / 2.35))
    r_r = []
    for i in range(n_r):
        t = i / n_r
        r_r.append(add(rx_start + span_r * t, ly * (1.0 - t)))
    r_r.append("A7")
    for i in range(n_r):
        members.append([r_r[i], r_r[i+1], "road"])

    tr = add(24.0, th_r)
    members.append(["A7", tr, "steel"])
    members.append(["A9", tr, "cable"])
    members.append(["A8", r_r[n_r - 1], "steel"])
    for i in range(0, n_r - 1):
        members.append([tr, r_r[i], "cable"])

    return {"nodes": nodes, "members": members}

print("=== LEVEL 5 RIGID RAMP JUMP SWEEP ===", flush=True)
best5 = None
for lx_end in [7.5, 8.5, 9.5]:
    for ry in [1.0, 1.5, 2.0]:
        for gap in [5.0, 6.0, 7.0]:
            rx_start = lx_end + gap
            if rx_start > 19.0: continue
            for ly in [-1.5, -2.5, -3.2]:
                d = make_l5_jump(lx_end, ry, rx_start, ly, 3.6, 2.6)
                ok, cost, pk, msgs = eval_design(5, d)
                if cost is not None:
                    if ok:
                        if best5 is None or cost < best5[0]:
                            best5 = (cost, d)
                            print(f"PASS L5 JUMP!! cost={cost:.1f} lx={lx_end} ry={ry} rx={rx_start} ly={ly} pk={pk*100:.1f}%", flush=True)
                            save_if_better(5, d, SUB / "level5.json")
                    elif pk < 1.5:
                        print(f"  close: cost={cost:.1f} pk={pk*100:.1f}% lx={lx_end} ry={ry} rx={rx_start} ly={ly} | {msgs[0].splitlines()[0][:55]}", flush=True)

if best5:
    print("\n=== BEST L5 ===")
    eval_design(5, best5[1], verbose=True)
else:
    print("No pass yet; checking diagnostic:")
    d = make_l5_jump(8.5, 1.5, 14.5, -2.2, 3.6, 2.6)
    eval_design(5, d, verbose=True)
