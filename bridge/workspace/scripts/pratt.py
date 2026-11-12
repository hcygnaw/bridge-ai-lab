"""Tension-diagonal Pratt truss. Depth can be a number or 'sine'."""
import math, sys
sys.path.insert(0, ".")
from scripts.lib import B, run, check

def pratt(span, n, depth, bot_mat="wood", post_mat="wood", diag_mat="wood",
          ydeck=0.0, end_bot_y=None, topL="A0", topR="A2", botL="A1", botR="A3",
          bot_y_anchor=-2.0, rise_fn=None):
    """depth: center depth if rise_fn is None (constant). 
    rise_fn(t) returns depth at fraction t in (0,1), not including anchors.
    Bottom chord y = ydeck - depth(x).
    End bottom anchors are connected directly if their y is close; otherwise
    we still connect botL/botR to the first/last bottom nodes.
    """
    b = B()
    panel = span / n
    tops, bots = [], []
    for i in range(1, n):
        x = panel * i
        t = i / n
        if rise_fn:
            d = rise_fn(t)
        else:
            d = depth
        tops.append(b.node(x, ydeck, ("t", round(x, 3))))
        bots.append(b.node(x, ydeck - d, ("b", round(x, 3))))
    seq_t = [topL] + tops + [topR]
    seq_b = [botL] + bots + [botR]
    for a, c in zip(seq_t, seq_t[1:]):
        b.mem(a, c, "road")
    for a, c in zip(seq_b, seq_b[1:]):
        b.mem(a, c, bot_mat)
    for t, bo in zip(tops, bots):
        b.mem(t, bo, post_mat)
    # tension diagonals: left half bottom-left -> top-right; right half mirrored
    # bay i (0..n-1): if i < n/2: seq_b[i] -> seq_t[i+1]
    # else: seq_b[i+1] -> seq_t[i]
    for i in range(n):
        if i < n / 2:
            b.mem(seq_b[i], seq_t[i + 1], diag_mat)
        else:
            b.mem(seq_b[i + 1], seq_t[i], diag_mat)
    return b.design()

def try_design(level, d, label):
    try:
        P = check(level, d)
    except Exception as e:
        print(f"{label}: ILLEGAL {e}")
        return False, 1e18
    ok, cost, _ = run(level, d, quiet=True)
    print(f"{label}: cost={cost:.1f} {'PASS' if ok else 'FAIL'}")
    if not ok:
        run(level, d, quiet=False)
    return ok, cost

if __name__ == "__main__":
    level = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    # sweep
    best = None
    for n in (6, 8, 10, 12):
        for depth in (1.6, 1.8, 2.0, 2.2, 2.4, 2.6):
            for bot in ("wood", "cable"):
                d = pratt(15.0, n, depth, bot_mat=bot)
                label = f"n={n} d={depth} bot={bot}"
                ok, cost = try_design(level, d, label)
                if ok and (best is None or cost < best[0]):
                    best = (cost, label, d)
    print("BEST", best[0] if best else None, best[1] if best else None)
    if best:
        import json
        json.dump(best[2], open("/tmp/l1best.json", "w"), indent=1)
