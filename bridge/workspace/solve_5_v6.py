import json, math, sys
from pathlib import Path

WS = Path(__file__).resolve().parent
sys.path.insert(0, str(WS))
import bridge
from opt_util import eval_design, save_if_better

SUB = WS / "submission"
SUB.mkdir(exist_ok=True)

# BRILLIANT IDEA FOR LEVEL 5:
# Use the left tower's backstay to A2=(-11,0) to ALSO suspend the 11m pit bridge!
# Zero steel props in the pit!
# Let's test BOTH:
# (A) Continuous suspension bridge (pit hung from backstay, river hung from main cable between (0,th) and (24,th))
# (B) Jump-gap + cable-stayed!

def make_l5_shared_backstay(
    th_l=3.5, th_r=3.5,
    n_riv=10,
    main_mid_y=0.3,
    riv_sag=0.0,
    pit_sag=0.0,
    hanger_every=1,
    pit_hangers="all",
    diag_brace=False,
):
    nodes = []
    members = []
    def add(x, y):
        nodes.append([round(x, 4), round(y, 4)])
        return len(nodes) - 1

    # Pit road: 5 segs from A2=(-11,0) to A0=(0,0) (2.2m each)
    pit_r = ["A2"]
    for i in range(1, 5):
        t = i / 5.0
        pit_r.append(add(-11.0 + 11.0*t, -4.0*pit_sag*t*(1.0-t)))
    pit_r.append("A0")
    for i in range(5):
        members.append([pit_r[i], pit_r[i+1], "road"])

    # River road: n_riv segs from A0=(0,0) to A7=(24,0)
    riv_r = ["A0"]
    for i in range(1, n_riv):
        t = i / n_riv
        riv_r.append(add(24.0*t, -4.0*riv_sag*t*(1.0-t)))
    riv_r.append("A7")
    for i in range(n_riv):
        members.append([riv_r[i], riv_r[i+1], "road"])

    # Towers
    tl = add(0.0, th_l)
    tr = add(24.0, th_r)
    members += [["A0", tl, "steel"], ["A7", tr, "steel"]]
    members.append(["A9", tr, "cable"])

    # Pit backstay from A2=(-11,0) to tl=(0, th_l), with intermediate nodes for hangers!
    if pit_hangers == "direct_stays":
        # Direct cable stays from tl to pit_r[1..4], plus backstay A2->tl
        members.append(["A2", tl, "cable"])
        for i in [2, 3]:
            members.append([tl, pit_r[i], "cable"])
        members.append(["A2", pit_r[2], "cable"])
    elif pit_hangers == "backstay_chain":
        # Backstay is a chain from A2 -> b1 -> b2 -> b3 -> b4 -> tl, with vertical hangers to pit_r!
        bs = ["A2"]
        for i in range(1, 5):
            t = i / 5.0
            # slight sag below straight line A2->tl
            bx = -11.0 + 11.0 * t
            by = th_l * t - 0.3 * 4.0 * t * (1.0 - t)
            bn = add(bx, by)
            bs.append(bn)
            members.append([bn, pit_r[i], "cable"])
        bs.append(tl)
        for i in range(5):
            members.append([bs[i], bs[i+1], "cable"])
    elif pit_hangers == "backstay_2":
        # Backstay chain with 2 nodes at i=2, 3 (x=-6.6, -4.4)
        b2 = add(-6.6, th_l * 0.4 - 0.2)
        b3 = add(-4.4, th_l * 0.6 - 0.2)
        members += [["A2", b2, "cable"], [b2, b3, "cable"], [b3, tl, "cable"]]
        members += [[b2, pit_r[2], "cable"], [b3, pit_r[3], "cable"]]
        members += [[b2, pit_r[1], "cable"], [b3, pit_r[4], "cable"]]

    # River main suspension cable from tl=(0, th_l) to tr=(24, th_r)
    c_nodes = [tl]
    for i in range(1, n_riv):
        if i % hanger_every != 0:
            continue
        t = i / n_riv
        x = 24.0 * t
        y_line = th_l * (1.0 - t) + th_r * t
        y = y_line - (y_line - main_mid_y) * 4.0 * t * (1.0 - t)
        cn = add(x, y)
        c_nodes.append(cn)
        members.append([cn, riv_r[i], "cable"])
        if hanger_every == 2:
            # Also support adjacent road nodes with V-cables?
            if i - 1 > 0:
                members.append([cn, riv_r[i - 1], "cable"])
            if i + 1 < n_riv:
                members.append([cn, riv_r[i + 1], "cable"])
    c_nodes.append(tr)
    for i in range(len(c_nodes) - 1):
        members.append([c_nodes[i], c_nodes[i+1], "cable"])

    if diag_brace:
        # Add 2 stabilizing cables from A1=(0,-2) and A8=(24,-2) or A0/A7
        members.append(["A0", riv_r[2], "cable"])
        members.append(["A7", riv_r[n_riv-2], "cable"])

    return {"nodes": nodes, "members": members}

print("=== LEVEL 5 SHARED-BACKSTAY SUSPENSION SWEEP ===", flush=True)
best5 = None
for pit_h in ["backstay_2", "backstay_chain"]:
    for th in [2.6, 3.0, 3.4, 3.8]:
        for mid_y in [0.2, 0.5, 0.8]:
            for riv_sag in [0.0, 0.4, -0.4]:
                for he in [1, 2]:
                    d = make_l5_shared_backstay(th, th, 10, mid_y, riv_sag, 0.0, he, pit_h, False)
                    ok, cost, pk, msgs = eval_design(5, d)
                    if cost is not None:
                        if ok:
                            if best5 is None or cost < best5[0]:
                                best5 = (cost, d)
                                print(f"PASS L5!! cost={cost:.1f} pit={pit_h} th={th} mid={mid_y} sag={riv_sag} he={he} pk={pk*100:.1f}%", flush=True)
                                save_if_better(5, d, SUB / "level5.json")
                        elif pk < 1.5:
                            print(f"  close: cost={cost:.1f} pk={pk*100:.1f}% pit={pit_h} th={th} mid={mid_y} sag={riv_sag} he={he} | {msgs[0].splitlines()[0][:55]}", flush=True)

if best5:
    print("\n=== BEST L5 ===")
    eval_design(5, best5[1], verbose=True)
else:
    print("No pass yet; printing diagnostic on cheapest valid:")
    for th in [2.8, 3.4]:
        d = make_l5_shared_backstay(th, th, 10, 0.4, 0.0, 0.0, 1, "backstay_2", False)
        eval_design(5, d, verbose=True)
