"""Suspension bridge generator."""
import math
from scripts.lib import B

def suspension(deck0, deck1, n, ydeck,
               tower_x, tower_y, tower_base_y,
               back_anchors,  # (left_anchor, right_anchor) strings
               deck_anchors,  # (left, right) top anchors the road ties to
               y_mid,  # cable y at midspan
               tower_mat="wood", tower_seg=1.5,
               hanger_prefer="wood"):
    b = B()
    txL, txR = tower_x
    panel = (deck1 - deck0) / n
    # deck nodes
    tops = []
    for i in range(1, n):
        x = deck0 + panel * i
        tops.append(b.node(x, ydeck, ("deck", round(x, 3))))
    seq = [deck_anchors[0]] + tops + [deck_anchors[1]]
    for a, c in zip(seq, seq[1:]):
        b.mem(a, c, "road")
    # cable nodes above each deck node, parabolic between towers
    # y = y_tower - (y_tower - y_mid) * (1 - ((x-mid)/half)^2) but towers may not be at deck ends
    mid = 0.5 * (txL + txR)
    half = 0.5 * (txR - txL)
    sag = tower_y - y_mid
    cables = []
    for i, x in enumerate([deck0 + panel * i for i in range(1, n)]):
        u = (x - mid) / half
        y = tower_y - sag * (1 - u * u)
        # keep hanger at least 0.35
        if y < ydeck + 0.35:
            y = ydeck + 0.35
        cables.append(b.node(x, y, ("cab", round(x, 3))))
    # tower tops
    topL = b.node(txL, tower_y, ("tw", "L"))
    topR = b.node(txR, tower_y, ("tw", "R"))
    # main cable
    cseq = [topL] + cables + [topR]
    for a, c in zip(cseq, cseq[1:]):
        b.mem(a, c, "cable")
    # hangers: wood if short, else cable
    for t, c in zip(tops, cables):
        x1, y1 = b.nodes[t]
        x2, y2 = b.nodes[c]
        L = math.hypot(x1 - x2, y1 - y2)
        mat = "wood" if L <= 2.95 else "cable"
        b.mem(t, c, mat)
    # towers: segmented mast from base to top
    def mast(x, y_top, side):
        y0 = tower_base_y
        h = y_top - y0
        nseg = max(1, int(math.ceil(h / tower_seg - 1e-9)))
        seg = h / nseg
        prev = b.node(x, y0, ("base", side))
        for k in range(1, nseg):
            y = y0 + seg * k
            nxt = b.node(x, y, ("mast", side, k))
            mat = "wood" if seg <= 2.98 else "steel"
            b.mem(prev, nxt, mat)
            prev = nxt
        mat = "wood" if seg <= 2.98 else "steel"
        b.mem(prev, topL if side == "L" else topR, mat)
        return b.node(x, y0, ("base", side))
    baseL = mast(txL, tower_y, "L")
    baseR = mast(txR, tower_y, "R")
    # backstays
    b.mem(topL, back_anchors[0], "cable")
    b.mem(topR, back_anchors[1], "cable")
    # brace tower base to deck anchors if distinct
    # also a strut from tower base toward the deck anchor so the tower foot doesn't swing
    return b

if __name__ == "__main__":
    import sys
    from scripts.lib import run, check
    # level 2 trial
    b = suspension(
        deck0=0, deck1=30, n=12, ydeck=0.0,
        tower_x=(-2.0, 32.0), tower_y=8.0, tower_base_y=0.3,
        back_anchors=("A3", "A7"),
        deck_anchors=("A0", "A4"),
        y_mid=1.2,
        tower_seg=1.4,
    )
    # extra braces: tower base to A0/A4
    b.mem("A0", b._idx[("base", "L")], "wood")
    b.mem("A4", b._idx[("base", "R")], "wood")
    # also brace tower top laterally already has backstay and main cable
    d = b.design()
    try:
        P = check(2, d)
        print("legal", round(P["cost"], 1), P["cost_detail"])
    except Exception as e:
        print("ILLEGAL", e)
        sys.exit(1)
    run(2, d)
