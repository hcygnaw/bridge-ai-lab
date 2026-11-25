import json, math, sys
from pathlib import Path

WS = Path(__file__).resolve().parent
sys.path.insert(0, str(WS))
import bridge
from opt_util import eval_design, save_if_better

SUB = WS / "submission"
SUB.mkdir(exist_ok=True)

# Let's test CHEAP PIT + CHEAP RIVER (arch/catenary/cable-stayed) for Level 5!
# Key insight:
# 1. Pit (-11 to 0, 11m):
#    Dip road down to y = -1.6 (parabola) with 5 road segs (2.25m each).
#    Prop all 4 interior nodes from A6=(-8,-4), A5=(-6,-4), A4=(-4,-4), A3=(-2,-4) with STEEL!
#    Wait: lengths are ~2.5m each -> 4 * 2.5 * 160 = $1600? Too much!
#    Instead: 5 road segs dipping to y = -2.2, propped by ONLY TWO steel struts?
#    Wait: what if road goes: A2(-11,0) -> (-8.8,-1.5) -> (-6.6,-2.7) -> (-4.4,-2.7) -> (-2.2,-1.5) -> A0(0,0)
#    Length of A6(-8,-4) to (-8.8,-1.5) = 2.62m ($419)
#    Length of A5(-6,-4) to (-6.6,-2.7) = 1.43m ($229)
#    Length of A4(-4,-4) to (-4.4,-2.7) = 1.36m ($218)
#    Length of A3(-2,-4) to (-2.2,-1.5) = 2.51m ($401)
#    TOTAL PIT SUPPORT = $1,267!! + 12.2m road ($1,830) = $3,097 (rock solid, 0 flex!)
#    Even better: what if (-6.6,-2.7) is (-6,-3.5) -> 0.5m steel ($80)!
#    Let's check what max slope car & van can climb cleanly!

def make_l5(
    pit_y1=-0.9, pit_y2=-1.5,
    riv_mode="cable_stayed",
    n_riv=10,
    riv_sag=1.0,
    tower_h=4.0,
    depth=2.5,
    pit_support="4steel",
):
    nodes = []
    members = []
    def add(x, y):
        nodes.append([round(x, 4), round(y, 4)])
        return len(nodes) - 1

    # Pit: 5 road segs from A2=(-11,0) to A0=(0,0) (dx=2.2m, dy<=1.1m -> L<=2.46m!)
    p1 = add(-8.8, pit_y1)
    p2 = add(-6.6, pit_y2)
    p3 = add(-4.4, pit_y2)
    p4 = add(-2.2, pit_y1)
    pit_r = ["A2", p1, p2, p3, p4, "A0"]
    for i in range(5):
        members.append([pit_r[i], pit_r[i+1], "road"])
    if pit_support == "4steel":
        members += [["A6", p1, "steel"], ["A5", p2, "steel"], ["A4", p3, "steel"], ["A3", p4, "steel"]]
    elif pit_support == "2steel_2cable":
        # 2 steel props at p2, p3 + 2 cables from A2->p2? No, A5->p2, A4->p3, and cables A2->p1?
        # Better: A6->p1, A3->p4 steel? No, A5->p2, A4->p3 steel, and road is arched between A2-p2 and p3-A0!
        members += [["A5", p2, "steel"], ["A4", p3, "steel"]]
    elif pit_support == "1steel_mid":
        # 6 segs or 5 segs with V from A5=(-6,-4) to p2 and A4=(-4,-4) to p3
        members += [["A5", p2, "steel"], ["A4", p3, "steel"], ["A6", p1, "cable"], ["A3", p4, "cable"]]

    # River: A0=(0,0) to A7=(24,0)
    riv_r = ["A0"]
    for i in range(1, n_riv):
        t = i / n_riv
        x = 24.0 * t
        y = -4.0 * riv_sag * t * (1.0 - t)
        riv_r.append(add(x, y))
    riv_r.append("A7")
    for i in range(n_riv):
        members.append([riv_r[i], riv_r[i+1], "road"])

    if riv_mode == "catenary_cables":
        # Pure sagging road + stabilizing cables from A0, A7 (and A1, A8 struts)
        members.append(["A1", riv_r[1], "steel"])
        members.append(["A8", riv_r[n_riv-1], "steel"])
        for k in range(2, n_riv // 2 + 1):
            members.append(["A0", riv_r[k], "cable"])
            members.append(["A7", riv_r[n_riv - k], "cable"])
    elif riv_mode == "catenary_sparse":
        for k in [2, 4, 5]:
            if k < n_riv:
                members.append(["A0", riv_r[k], "cable"])
                members.append(["A7", riv_r[n_riv - k], "cable"])
    elif riv_mode == "one_tower_cs":
        # TWO short steel towers at x=0 and x=24, backstays to A3=(-2,-4) and A9=(30,0)
        tl = add(0.0, tower_h)
        tr = add(24.0, tower_h)
        members += [["A0", tl, "steel"], ["A7", tr, "steel"]]
        members += [["A3", tl, "cable"], ["A9", tr, "cable"]]
        for k in range(1, n_riv // 2 + 1):
            members.append([tl, riv_r[k], "cable"])
            members.append([tr, riv_r[n_riv - k], "cable"])
    elif riv_mode == "suspension":
        # Classic suspension bridge: 2 towers, 1 main cable, vertical hangers
        tl = add(0.0, tower_h)
        tr = add(24.0, tower_h)
        members += [["A0", tl, "steel"], ["A7", tr, "steel"]]
        members += [["A3", tl, "cable"], ["A9", tr, "cable"]]
        c_nodes = [tl]
        for i in range(1, n_riv):
            t = i / n_riv
            x = 24.0 * t
            # Parabolic main cable from y=tower_h down to y=0.5 at midspan
            y = tower_h - (tower_h - 0.5) * 4.0 * t * (1.0 - t)
            cn = add(x, y)
            c_nodes.append(cn)
            members.append([cn, riv_r[i], "cable"])
        c_nodes.append(tr)
        for i in range(n_riv):
            members.append([c_nodes[i], c_nodes[i+1], "cable"])
    elif riv_mode == "arch_cable_tie":
        # Upward ROAD arch (riv_sag < 0!) with horizontal/chord cables under it!
        for k in [2, 3, 4, 5]:
            if k < n_riv:
                members.append(["A1", riv_r[k], "cable"])
                members.append(["A8", riv_r[n_riv - k], "cable"])

    return {"nodes": nodes, "members": members}

lv = bridge.load_level("5")
print("=== CHECKING COSTS & SIM FOR LEVEL 5 ===", flush=True)
best5 = None
for pit_sup in ["4steel", "2steel_2cable"]:
    for riv_mode in ["suspension", "catenary_sparse", "catenary_cables", "arch_cable_tie"]:
        for n_riv in [10, 11]:
            for riv_sag in ([2.0, 2.8] if "catenary" in riv_mode else ([-2.0, -2.5] if riv_mode == "arch_cable_tie" else [0.0, 0.5])):
                for th in ([2.8, 3.3, 3.8] if riv_mode == "suspension" else [0.0]):
                    d = make_l5(-0.9, -1.5, riv_mode, n_riv, riv_sag, th, 2.5, pit_sup)
                    ok, cost, pk, msgs = eval_design(5, d)
                    if cost is not None:
                        if ok:
                            if best5 is None or cost < best5[0]:
                                best5 = (cost, d)
                                print(f"PASS L5!! cost={cost:.1f} pit={pit_sup} mode={riv_mode} n={n_riv} sag={riv_sag} th={th} pk={pk*100:.1f}%", flush=True)
                                save_if_better(5, d, SUB / "level5.json")
                        else:
                            short_m = msgs[0].split('\n')[0] if msgs else ''
                            if pk < 2.0 or "断裂杆件：0 " in (msgs[0] if msgs else "") or "断裂杆件：1 " in (msgs[0] if msgs else "") or "断裂杆件：2 " in (msgs[0] if msgs else ""):
                                print(f"  close: cost={cost:.1f} pit={pit_sup} mode={riv_mode} n={n_riv} sag={riv_sag} th={th} pk={pk*100:.1f}% | {short_m[:60]}", flush=True)

if best5:
    print("\n=== BEST L5 ===")
    eval_design(5, best5[1], verbose=True)
else:
    print("No pass yet; printing one diagnostic per mode:")
    for riv_mode, sag, th in [("suspension", 0.0, 3.0), ("catenary_sparse", 2.2, 0), ("arch_cable_tie", -2.2, 0)]:
        d = make_l5(-0.9, -1.5, riv_mode, 10, sag, th, 2.5, "2steel_2cable")
        print(f"--- {riv_mode} ---")
        eval_design(5, d, verbose=True)
