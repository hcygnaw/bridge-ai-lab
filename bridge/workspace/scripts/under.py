"""Underspanned (cable below, posts in compression) level 1."""
import math, sys
sys.path.insert(0, ".")
from scripts.lib import B, run, check

def under(n=8, depth=2.5, span=15.0, diag="cable", post="wood", bot="cable", y0=0.0):
    b = B()
    panel = span / n
    tops, bots = [], []
    for i in range(1, n):
        x = span * i / n
        # parabolic sag of cable
        t = i / n
        sag = depth * math.sin(math.pi * t)  # 0 at ends
        tops.append(b.node(x, y0, key=("t", i)))
        bots.append(b.node(x, y0 - sag, key=("b", i)))
    seq_t = ["A0"] + tops + ["A2"]
    for a, c in zip(seq_t, seq_t[1:]):
        b.mem(a, c, "road")
    # bottom cable: ends to A1 and A3 which are at y=-2, not y=0
    # connect A1 to first bot, bots, last bot to A3
    b.mem("A1", bots[0], bot)
    for a, c in zip(bots, bots[1:]):
        b.mem(a, c, bot)
    b.mem(bots[-1], "A3", bot)
    for t, bo in zip(tops, bots):
        b.mem(t, bo, post)
    # diagonals for anti-sway: cable from bot i to top i+1 and top i to bot i+1
    if diag:
        for i in range(len(bots) - 1):
            b.mem(bots[i], tops[i + 1], diag)
            b.mem(tops[i], bots[i + 1], diag)
        # ends
        b.mem("A0", bots[0], diag)
        b.mem("A1", tops[0], "wood")
        b.mem("A2", bots[-1], diag)
        b.mem("A3", tops[-1], "wood")
    return b.design()

if __name__ == "__main__":
    n = int(sys.argv[1])
    depth = float(sys.argv[2])
    diag = sys.argv[3] if len(sys.argv) > 3 else "cable"
    post = sys.argv[4] if len(sys.argv) > 4 else "wood"
    bot = sys.argv[5] if len(sys.argv) > 5 else "cable"
    if diag == "none":
        diag = None
    d = under(n=n, depth=depth, diag=diag, post=post, bot=bot)
    try:
        P = check(1, d)
        print("legal", round(P["cost"], 1), P["cost_detail"])
    except Exception as e:
        print("ILLEGAL", e)
        sys.exit(1)
    run(1, d)
