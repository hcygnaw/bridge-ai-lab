"""Pre-sagged road experiments for level 1."""
import math, sys
sys.path.insert(0, ".")
from scripts.lib import B, run, check

def sag_road(n=6, sag=1.0, span=15.0, extra=None):
    b = B()
    # nodes at i/n * span, y = -sag * sin(pi * i/n)  (0 at ends)
    tops = []
    for i in range(1, n):
        x = span * i / n
        y = -sag * math.sin(math.pi * i / n)
        tops.append(b.node(x, y, key=("t", i)))
    seq = ["A0"] + tops + ["A2"]
    for a, c in zip(seq, seq[1:]):
        b.mem(a, c, "road")
    if extra == "ties":
        # tie each node down? no that doesn't help
        # add a cable underneath as a deeper catenary to share tension? 
        pass
    if extra == "arch":
        # compression arch above to hold the deck up (reduce sag under load)
        # arch nodes
        rise = 3.0
        arch = []
        for i in range(1, n):
            x = span * i / n
            y = rise * math.sin(math.pi * i / n)
            arch.append(b.node(x, y, key=("a", i)))
        aseq = ["A0"] + arch + ["A2"]
        for a, c in zip(aseq, aseq[1:]):
            # length?
            b.mem(a, c, "wood")
        for t, a in zip(tops, arch):
            b.mem(t, a, "wood")
    if extra == "under":
        depth = 3.5
        bots = []
        for i in range(1, n):
            x = span * i / n
            y = -depth
            bots.append(b.node(x, y, key=("b", i)))
        b.mem("A1", bots[0], "cable")
        for a, c in zip(bots, bots[1:]):
            b.mem(a, c, "cable")
        b.mem(bots[-1], "A3", "cable")
        for t, bo in zip(tops, bots):
            # vertical from sagged deck to bottom
            b.mem(t, bo, "cable")
        # also triangulate ends
        b.mem("A0", bots[0], "cable")
        b.mem("A2", bots[-1], "cable")
    return b.design()

if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 6
    sag = float(sys.argv[2]) if len(sys.argv) > 2 else 1.0
    extra = sys.argv[3] if len(sys.argv) > 3 else None
    d = sag_road(n=n, sag=sag, extra=extra)
    try:
        P = check(1, d)
        print("legal", P["cost"], P["cost_detail"])
    except Exception as e:
        print("ILLEGAL", e)
        sys.exit(1)
    run(1, d)
