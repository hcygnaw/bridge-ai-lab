"""Level 1 experiments."""
import math, sys
sys.path.insert(0, ".")
from scripts.lib import B, run, check

def pratt(span=15.0, panel=1.5, depth=2.4, ydeck=0.0, ybot=-2.4, end_anchors=("A0", "A2", "A1", "A3")):
    """Parallel-chord Pratt from left anchor to right anchor.
    end_anchors: topL, topR, botL, botR
    """
    b = B()
    n = int(round(span / panel))
    panel = span / n
    topL, topR, botL, botR = end_anchors
    # deck nodes (not including anchors at 0 and span)
    tops = []
    bots = []
    for i in range(1, n):
        tops.append(b.node(i * panel, ydeck, key=("t", i)))
    for i in range(1, n):
        bots.append(b.node(i * panel, ybot, key=("b", i)))
    # top chord
    seq_t = [topL] + tops + [topR]
    for a, c in zip(seq_t, seq_t[1:]):
        b.mem(a, c, "road")
    # bottom chord
    seq_b = [botL] + bots + [botR]
    for a, c in zip(seq_b, seq_b[1:]):
        b.mem(a, c, "wood")
    # verticals at intermediate
    for t, bo in zip(tops, bots):
        b.mem(t, bo, "wood")
    # end diagonals / posts: top anchor to first bottom, bottom anchor to first top
    b.mem(topL, bots[0], "wood")
    b.mem(botL, tops[0], "wood")
    b.mem(topR, bots[-1], "wood")
    b.mem(botR, tops[-1], "wood")
    # diagonals in each bay, tension-oriented both ways: X with wood if short enough else one direction
    # bays between bottom nodes including anchors
    # Use diagonals from bottom-left of bay to top-right (and opposite if length allows) 
    # Bay i: between x=i*panel and (i+1)*panel
    for i in range(n):
        left_t = seq_t[i]
        right_t = seq_t[i + 1]
        left_b = seq_b[i]
        right_b = seq_b[i + 1]
        # one diagonal
        b.mem(left_b, right_t, "wood")
        b.mem(left_t, right_b, "wood")
    return b.design()

def warren_cable(span=15.0, panel=2.5, depth=4.0):
    """Deck road + deep cable bottom chord + wood/steel diagonals."""
    b = B()
    n = int(round(span / panel))
    panel = span / n
    tops = [b.node(i * panel, 0.0, key=("t", i)) for i in range(1, n)]
    bots = [b.node(i * panel, -depth, key=("b", i)) for i in range(1, n)]
    seq_t = ["A0"] + tops + ["A2"]
    # bottom uses A1 and A3 if depth close to 2, else free end nodes tied to A1/A3
    # connect bottom ends to A1 (0,-2) and A3 (15,-2)
    seq_b_nodes = bots
    for a, c in zip(seq_t, seq_t[1:]):
        b.mem(a, c, "road")
    # bottom chord cable segments via A1, bots, A3 — but A1 is at y=-2 not -depth
    # add end bottom nodes? connect first bot to A1 with cable, bots together with cable, last to A3
    b.mem("A1", bots[0], "cable")
    for a, c in zip(bots, bots[1:]):
        b.mem(a, c, "cable")
    b.mem(bots[-1], "A3", "cable")
    for t, bo in zip(tops, bots):
        b.mem(t, bo, "wood" if depth <= 3.0 else "steel")
    # diagonals
    for i in range(len(bots) - 1):
        b.mem(bots[i], tops[i + 1] if i + 1 < len(tops) else "A2", "cable")
        b.mem(tops[i], bots[i + 1], "cable")
    b.mem("A0", bots[0], "cable")
    b.mem("A1", tops[0], "wood")
    b.mem("A2", bots[-1], "cable")
    b.mem("A3", tops[-1], "wood")
    return b.design()

if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "pratt"
    if which == "pratt":
        panel = float(sys.argv[2]) if len(sys.argv) > 2 else 1.5
        depth = float(sys.argv[3]) if len(sys.argv) > 3 else 2.4
        d = pratt(panel=panel, depth=depth, ybot=-depth)
        print("trying pratt", panel, depth)
        try:
            P = check(1, d)
            print("legal cost", P["cost"], P["cost_detail"])
        except Exception as e:
            print("ILLEGAL", e)
            sys.exit(1)
        run(1, d)
    elif which == "cable":
        panel = float(sys.argv[2]) if len(sys.argv) > 2 else 2.5
        depth = float(sys.argv[3]) if len(sys.argv) > 3 else 4.0
        d = warren_cable(panel=panel, depth=depth)
        print("trying cable", panel, depth)
        try:
            P = check(1, d)
            print("legal cost", P["cost"], P["cost_detail"])
        except Exception as e:
            print("ILLEGAL", e)
            sys.exit(1)
        run(1, d)
