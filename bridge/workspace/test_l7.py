import json
import math
import bridge as B
import saboteur as S
from opt_utils import eval_design


def make_fortress_bridge():
    # Level final: 28m river, budget 26000, static_only=True
    # Anchors: A0=(0,0), A1=(0,-2), A2=(-5,0), A3=(28,0), A4=(28,-2), A5=(33,0)
    # Strategy: Make road NOT the primary bending chord!
    # Put road at y=0 (16 segs of 1.75m -> 4200, FULL 90 kN strength).
    # Support road from a DEEP STEEL ARCH/TRUSS ABOVE (peaking at y=+3.6m, anchored to A0, A2, A3, A5!)
    # PLUS steel bottom arch/bracing from A1=(0,-2) to A4=(28,-2) if budget allows!
    nodes, members = [], []

    def add_n(x, y):
        nodes.append([round(x, 4), round(y, 4)])
        return len(nodes) - 1

    n_seg = 16  # 1.75m road segments
    deck = ["A0"] + [add_n(28.0 * i / n_seg, 0.0) for i in range(1, n_seg)] + ["A3"]
    for i in range(n_seg):
        members.append([deck[i], deck[i + 1], "road"])

    # Upper steel arch/truss chord: towers at (0, 3.5) and (28, 3.5) anchored to A2=(-5,0) and A5=(33,0),
    # OR parabolic steel arch from A0=(0,0) -> y=+4.5 at midspan -> A3=(28,0) + lower tie/arch from A1 to A4!
    #Wait: if upper chord is A0 -> (1.75, 1.8) -> ... -> (14, 4.2) -> ... -> A3:
    # Check cost of 16-panel steel upper truss:
    #   road: 4200
    #   upper steel chord (16 segs, ~30m): 4800
    #   15 verticals (~45m steel): 7200 (or cable hangers in tension? No, steel takes BOTH tension & compression and resists shock!)
    #   16 diagonals (~50m steel): 8000
    #   4200 + 4800 + 7200 + 8000 = 24,200!
    # Wait: if upper chord is at y = 3.5 at ends (on towers A0->(0,3.5) and A3->(28,3.5) braced to A2=(-5,0) and A5=(33,0)!):
    # Wait: if road is at y=0 and upper chord is at y=+3.5 (flat or arched +3.5..+4.5), then road takes TENSION (90 kN, no buckling!) and upper chord takes COMPRESSION (140 kN!), AND A2/A5 carry horizontal tension!
    # Wait: if road is at y=0 between A0 and A3, road takes ~40 kN tension under convoy.
    # To take load OFF road: put A1=(0,-2) -> (1.75,-2.2) -> ... -> A4=(28,-2) as a parallel tension/arch cable/steel below OR make the truss 4.5m tall!
    # Let's calculate 14-panel (2.0m) through-truss with y_top = 3.5..4.5 and A2/A5 cantilevers + cable/steel bottom chord!
    n_seg = 14  # 2.0m each -> road comp=75kN, tension=90kN!
    nodes, members = [], []
    deck = ["A0"] + [add_n(28.0 * i / n_seg, 0.0) for i in range(1, n_seg)] + ["A3"]
    for i in range(n_seg):
        members.append([deck[i], deck[i + 1], "road"])

    # Upper chord: towers at x=0 (y=3.0) and x=28 (y=3.0), rising to y=4.6 at midspan!
    # Wait: check vertical lengths (<= 4.6m -> steel OK, comp = 900/4.6^2 = 42 kN? Wait: verticals in Pratt/Howe ABOVE road are in TENSION if Howe? No, hangers above road are in TENSION = 140 kN!).
    # Wait: in a bowstring arch ABOVE road, verticals are in TENSION (140 kN!), diagonals are short or steel!
    # Let's also brace (0, 3.0) back to A2=(-5,0) [steel 5.83m] and (28,3.0) back to A5=(33,0) [steel 5.83m]!
    top = []
    for i in range(n_seg + 1):
        t = i / n_seg
        x = 28.0 * t
        y = 3.2 + 1.4 * 4 * t * (1 - t)  # 3.2 at ends, 4.6 at mid
        top.append(add_n(x, y))
    for i in range(n_seg):
        members.append([top[i], top[i + 1], "steel"])
    # End posts + backstays:
    members += [["A0", top[0], "steel"], ["A2", top[0], "steel"], ["A3", top[-1], "steel"], ["A5", top[-1], "steel"]]
    # Verticals (all steel):
    for i in range(1, n_seg):
        members.append([deck[i], top[i], "steel"])
    # Diagonals: Pratt (top[i] -> deck[i+1] on left? No, for through-truss, load hangs down so tension diagonals go deck[i] -> top[i+1] on left? Wait: at left end, top[0] is supported by A0->top[0], so panel 0 shear goes top[0] -> deck[1] in TENSION! Yes: top[i] -> deck[i+1] on left half, deck[i] -> top[i+1] on right half!)
    # Even better: check cost! If we have budget left, add A1->deck[1], A4->deck[-2], and cable/steel under deck!
    mid = n_seg // 2
    for i in range(n_seg):
        if i < mid:
            members.append([top[i], deck[i + 1], "steel"])
        else:
            members.append([deck[i], top[i + 1], "steel"])
    # Add A1=(0,-2)->deck[1]=(2,0) [steel 2.83m] and A4=(28,-2)->deck[-2]=(26,0) [steel 2.83m] to shield end road segments!
    members += [["A1", deck[1], "steel"], ["A4", deck[-2], "steel"]]
    return {"nodes": nodes, "members": members}


def make_fortress_v2():
    # Even stronger: 14-panel (2.0m) parabolic steel arch + deck + cable/steel lower tie-chord!
    # Wait: if we have BOTH an arch ABOVE (or truss below from A1->A4) AND a steel chord, wait: let's check cost of make_fortress_bridge() first!
    return make_fortress_bridge()


if __name__ == "__main__":
    lv = B.load_level("final")
    fb = make_fortress_bridge()
    ok, cost, pk, _ = eval_design("final", fb, quiet=False)
    print(f"Fortress v1: ok={ok}, cost={cost:.0f}/{lv['budget']}, pk={pk*100:.1f}%")
    if ok:
        pb = B.parse_design(lv, fb)
        sab = B.load_json("submission/saboteur.json")
        ps = S.parse_sab(lv, sab)
        res, _ = S.duel(lv, pb, ps)
        print("Duel vs our saboteur:", res["text"])
