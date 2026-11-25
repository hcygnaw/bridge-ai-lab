import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bridge
from opt_helper import eval_design, save_submission
from solve_l2_l3_v3 import auto_upgrade_to_pass


def make_l4_high_bridge(peak_y=6.3, n_ramp=10, n_mid=3):
    """High-clearance static bridge over ship channel x in [9,15], y in [-2,6].
    Left ramp: A6=(-12,0) to (9, peak_y) -> 21m horizontal, ~22m slope -> n_ramp=10 segments (~2.2m each).
    Center flat: (9, peak_y) to (15, peak_y) -> 6m -> n_mid=3 segments (2.0m each).
    Right ramp: (15, peak_y) to A15=(36,0) -> 21m horizontal -> n_ramp=10 segments.
    """
    nodes = []
    members = []

    # Build deck nodes from x=-12 (A6) to x=36 (A15)
    # Left ramp: 10 segments from (-12,0) to (9, peak_y)
    # Smoothly curve the top so cars don't hit a sharp crest or dip
    deck_pts = []
    for i in range(1, n_ramp):
        t = i / n_ramp
        x = -12.0 + 21.0 * t
        y = peak_y * t
        deck_pts.append((x, y))
    # Top corners and mid
    for i in range(n_mid + 1):
        t = i / n_mid
        x = 9.0 + 6.0 * t
        y = peak_y
        deck_pts.append((x, y))
    # Right ramp
    for i in range(1, n_ramp):
        t = i / n_ramp
        x = 15.0 + 21.0 * t
        y = peak_y * (1.0 - t)
        deck_pts.append((x, y))

    for x, y in deck_pts:
        nodes.append([round(x, 3), round(y, 3)])

    n_deck = len(nodes)
    # Road members
    members.append(["A6", 0, "road"])
    for i in range(n_deck - 1):
        members.append([i, i + 1, "road"])
    members.append([n_deck - 1, "A15", "road"])

    # Support left ramp using ground anchors A7=(-10,0), A8=(-8,0), A9=(-6,0), A2=(-4,0), A10=(-2,0), A0=(0,0)
    # Support right ramp using ground anchors A3=(24,0), A11=(26,0), A5=(28,0), A12=(30,0), A13=(32,0), A14=(34,0)
    # And support the over-water section (x from 0 to 24) with a clean truss/cable-stayed arch!
    # First, add a lower chord under the deck from x=0 to x=24? Wait: lower chord must stay outside x in [9,15], y in [-2,6]!
    # So over x in [9,15], any truss must be ABOVE the deck (y >= peak_y)!
    # Let's put an OVER-DECK truss from x=0 to x=24 (height +2.2m above deck) AND piers from ground anchors up to the ramps!

    def pos(idx):
        if isinstance(idx, str):
            anc = {
                "A0": (0,0), "A1": (0,-2), "A2": (-4,0), "A3": (24,0), "A4": (24,-2), "A5": (28,0),
                "A6": (-12,0), "A7": (-10,0), "A8": (-8,0), "A9": (-6,0), "A10": (-2,0),
                "A11": (26,0), "A12": (30,0), "A13": (32,0), "A14": (34,0), "A15": (36,0)
            }
            return anc[idx]
        return nodes[idx]

    def add_m(u, v, pref="wood"):
        x1, y1 = pos(u); x2, y2 = pos(v)
        L = math.hypot(x2 - x1, y2 - y1)
        if L < 0.31:
            return
        if pref == "wood" and L <= 2.98:
            mat = "wood"
        elif L <= 5.98:
            mat = "steel"
        else:
            mat = "cable"
        members.append([u, v, mat])

    # Ground-to-ramp piers on left (deck indices 0..5 are x=-9.9, -7.8, -5.7, -3.6, -1.5, 0.6)
    left_ancs = [("A7", 0), ("A8", 1), ("A9", 2), ("A2", 3), ("A10", 4), ("A0", 5)]
    for anc, di in left_ancs:
        add_m(anc, di, "wood")
        if di + 1 < n_deck:
            add_m(anc, di + 1, "wood")

    # Ground-to-ramp piers on right (symmetric)
    right_ancs = [("A14", n_deck - 1), ("A13", n_deck - 2), ("A12", n_deck - 3),
                  ("A5", n_deck - 4), ("A11", n_deck - 5), ("A3", n_deck - 6)]
    for anc, di in right_ancs:
        add_m(anc, di, "wood")
        if di - 1 >= 0:
            add_m(anc, di - 1, "wood")

    # Over-deck truss from deck index 5 (x=0.6) to n_deck-6 (x=23.4)
    i_start = 5
    i_end = n_deck - 6
    top_nodes = []
    for i in range(i_start, i_end):
        x1, y1 = nodes[i]
        x2, y2 = nodes[i + 1]
        mx = 0.5 * (x1 + x2)
        my = 0.5 * (y1 + y2) + 2.0
        ti = len(nodes)
        nodes.append([round(mx, 3), round(my, 3)])
        top_nodes.append(ti)
        add_m(ti, i, "wood")
        add_m(ti, i + 1, "wood")

    for k in range(len(top_nodes) - 1):
        add_m(top_nodes[k], top_nodes[k + 1], "wood")

    # Brace ends of top chord to deck/anchors
    add_m(i_start - 1, top_nodes[0], "wood")
    add_m(i_end + 1, top_nodes[-1], "wood")

    return {"nodes": nodes, "members": members}


if __name__ == "__main__":
    d = make_l4_high_bridge(peak_y=6.3)
    ok, cost, d_out, msg = auto_upgrade_to_pass(4, d, max_iters=20)
    print(f"L4 HighBridge: {ok} cost={cost:.1f} {msg}")
    if ok:
        save_submission("level4.json", d_out)
