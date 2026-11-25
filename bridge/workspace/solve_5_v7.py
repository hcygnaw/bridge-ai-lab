import json, math, sys
from pathlib import Path

WS = Path(__file__).resolve().parent
sys.path.insert(0, str(WS))
import bridge
from opt_util import eval_design, save_if_better

SUB = WS / "submission"
SUB.mkdir(exist_ok=True)

# LEVEL 5 UNDER $10,000:
# Strategy 1: Ultra-lean shared-backstay suspension (cost ~8,800 - 9,800!)
# - Pit: 5 road segs (11m = $1650). Backstay from A2=(-11,0) -> b2 -> b3 -> tl=(0, th_l) with ONLY 2 vertical hangers!
# - River: 10 road segs (24m = $3600).
#   Main cable from tl=(0, th_l) -> c1 -> c2 -> ... -> tr=(24, th_r),
#   OR main cable merges directly into riv_r[4], riv_r[5], riv_r[6] (ZERO hangers in the middle!)
#   Wait: if riv_r dips slightly (riv_sag = 1.0..2.0), the road IS the cable in the middle!
#   Let's also test using ONLY A0->tl and A7->tr with th = 2.0..3.0, and even NO hangers at all (cable-stayed with 2-3 stays per tower)!

def make_l5_lean(
    th=2.8,
    riv_sag=1.2,
    pit_sag=0.4,
    mode="merged_susp",
    pit_mode="bs2",
):
    nodes = []
    members = []
    def add(x, y):
        nodes.append([round(x, 4), round(y, 4)])
        return len(nodes) - 1

    # Pit road: 5 segs from A2=(-11,0) to A0=(0,0)
    pit_r = ["A2"]
    for i in range(1, 5):
        t = i / 5.0
        pit_r.append(add(-11.0 + 11.0*t, -4.0*pit_sag*t*(1.0-t)))
    pit_r.append("A0")
    for i in range(5):
        members.append([pit_r[i], pit_r[i+1], "road"])

    # River road: 10 segs (2.4m each) from A0=(0,0) to A7=(24,0)
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

    # Pit support via backstay
    if pit_mode == "bs2":
        # 2 nodes on backstay A2 -> b2 -> b3 -> tl, vertical hangers to pit_r[2], pit_r[3]
        b2 = add(-6.6, th * 0.4 - 0.15)
        b3 = add(-4.4, th * 0.6 - 0.15)
        members += [["A2", b2, "cable"], [b2, b3, "cable"], [b3, tl, "cable"]]
        members += [[b2, pit_r[2], "cable"], [b3, pit_r[3], "cable"]]
    elif pit_mode == "bs1":
        # 1 node on backstay at x=-5.5, V-hangers to pit_r[2], pit_r[3]
        bm = add(-5.5, th * 0.5 - 0.2)
        members += [["A2", bm, "cable"], [bm, tl, "cable"]]
        members += [[bm, pit_r[2], "cable"], [bm, pit_r[3], "cable"]]
    elif pit_mode == "bs_direct":
        # Backstay A2 -> tl + 1 stay tl -> pit_r[3] + 1 stay A2 -> pit_r[2]?
        members += [["A2", tl, "cable"], [tl, pit_r[2], "cable"], [tl, pit_r[3], "cable"]]
    elif pit_mode == "bs3":
        b1 = add(-8.8, th * 0.2 - 0.1)
        b2 = add(-6.6, th * 0.4 - 0.15)
        b3 = add(-4.4, th * 0.6 - 0.15)
        b4 = add(-2.2, th * 0.8 - 0.1)
        members += [["A2", b1, "cable"], [b1, b2, "cable"], [b2, b3, "cable"], [b3, b4, "cable"], [b4, tl, "cable"]]
        members += [[b1, pit_r[1], "cable"], [b2, pit_r[2], "cable"], [b3, pit_r[3], "cable"], [b4, pit_r[4], "cable"]]

    # River support
    if mode == "merged_susp":
        # Main cable goes tl -> c2 -> riv_r[4] -> (road) -> riv_r[6] -> c8 -> tr
        # Plus hangers c2 -> riv_r[2] (and maybe c1 -> riv_r[1]?)
        c2 = add(4.8, th * 0.35 - riv_sag * 0.4)
        c8 = add(19.2, th * 0.35 - riv_sag * 0.4)
        members += [[tl, c2, "cable"], [c2, riv_r[4], "cable"], [riv_r[6], c8, "cable"], [c8, tr, "cable"]]
        members += [[c2, riv_r[2], "cable"], [c8, riv_r[8], "cable"]]
        # Also tie riv_r[3] and riv_r[7] to c2, c8?
        members += [[c2, riv_r[3], "cable"], [c8, riv_r[7], "cable"]]
    elif mode == "merged_susp_v2":
        # tl -> c2 -> c4 -> riv_r[5] -> c6 -> c8 -> tr
        c2 = add(4.8, th * 0.45 - riv_sag * 0.3)
        c4 = add(9.6, th * 0.10 - riv_sag * 0.8)
        c6 = add(14.4, th * 0.10 - riv_sag * 0.8)
        c8 = add(19.2, th * 0.45 - riv_sag * 0.3)
        members += [[tl, c2, "cable"], [c2, c4, "cable"], [c4, riv_r[5], "cable"],
                    [riv_r[5], c6, "cable"], [c6, c8, "cable"], [c8, tr, "cable"]]
        members += [[c2, riv_r[2], "cable"], [c4, riv_r[4], "cable"],
                    [c6, riv_r[6], "cable"], [c8, riv_r[8], "cable"]]
    elif mode == "direct_2stays":
        # Direct cable stays from tl to riv_r[3], riv_r[5] and tr to riv_r[7], riv_r[5]
        members += [[tl, riv_r[3], "cable"], [tl, riv_r[5], "cable"],
                    [tr, riv_r[7], "cable"], [tr, riv_r[5], "cable"]]
    elif mode == "direct_3stays":
        members += [[tl, riv_r[2], "cable"], [tl, riv_r[4], "cable"], [tl, riv_r[5], "cable"],
                    [tr, riv_r[8], "cable"], [tr, riv_r[6], "cable"], [tr, riv_r[5], "cable"]]
    elif mode == "susp_even":
        # Suspension cable with hangers ONLY at even indices 2, 4, 6, 8 (only 4 hangers!)
        c_nodes = [tl]
        for i in [2, 4, 6, 8]:
            t = i / 10.0
            y = th - (th - (-riv_sag + 0.3)) * 4.0 * t * (1.0 - t)
            cn = add(24.0 * t, y)
            c_nodes.append(cn)
            members.append([cn, riv_r[i], "cable"])
        c_nodes.append(tr)
        for k in range(len(c_nodes) - 1):
            members.append([c_nodes[k], c_nodes[k+1], "cable"])

    return {"nodes": nodes, "members": members}

print("=== LEVEL 5 LEAN SHARED-BACKSTAY SWEEP ===", flush=True)
best5 = None
for pit_m in ["bs1", "bs2", "bs3"]:
    for mode in ["susp_even", "merged_susp", "merged_susp_v2", "direct_2stays", "direct_3stays"]:
        for th in [2.2, 2.8, 3.4, 4.0]:
            for riv_sag in [0.0, 0.6, 1.2, 1.8]:
                for pit_sag in [0.0, 0.5]:
                    d = make_l5_lean(th, riv_sag, pit_sag, mode, pit_m)
                    ok, cost, pk, msgs = eval_design(5, d)
                    if cost is not None:
                        if ok:
                            if best5 is None or cost < best5[0]:
                                best5 = (cost, d)
                                print(f"PASS L5!! cost={cost:.1f} pit={pit_m} mode={mode} th={th} rsag={riv_sag} psag={pit_sag} pk={pk*100:.1f}%", flush=True)
                                save_if_better(5, d, SUB / "level5.json")
                        elif pk < 1.5:
                            print(f"  close: cost={cost:.1f} pk={pk*100:.1f}% pit={pit_m} mode={mode} th={th} rsag={riv_sag} psag={pit_sag} | {msgs[0].splitlines()[0][:55]}", flush=True)

if best5:
    print("\n=== BEST L5 ===")
    eval_design(5, best5[1], verbose=True)
else:
    print("No pass yet; printing diagnostic on cheapest valid:")
    for mode in ["susp_even", "merged_susp_v2", "direct_2stays"]:
        d = make_l5_lean(2.8, 0.8, 0.3, mode, "bs2")
        print(f"--- {mode} ---")
        eval_design(5, d, verbose=True)
