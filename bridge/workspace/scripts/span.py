"""General Pratt deck truss between two top anchors and two bottom anchors."""
import math
from scripts.lib import B

def pratt_span(x0, x1, ydeck, ybot, n, topL, topR, botL, botR,
               bot_mat="wood", post_mat="wood", diag_mat="wood", b=None):
    """Tension-diagonal Pratt (flipped orientation that worked on level 1).
    Bottom nodes sit at ybot. Ends tie to botL/botR anchors (any y).
    """
    if b is None:
        b = B()
    panel = (x1 - x0) / n
    tops, bots = [], []
    for i in range(1, n):
        x = x0 + panel * i
        tops.append(b.node(x, ydeck, ("t", round(x, 3), round(ydeck, 3))))
        bots.append(b.node(x, ybot, ("b", round(x, 3), round(ybot, 3))))
    seq_t = [topL] + tops + [topR]
    seq_b = [botL] + bots + [botR]
    for a, c in zip(seq_t, seq_t[1:]):
        b.mem(a, c, "road")
    for a, c in zip(seq_b, seq_b[1:]):
        b.mem(a, c, bot_mat)
    for t, bo in zip(tops, bots):
        b.mem(t, bo, post_mat)
    for i in range(n):
        if i < n / 2.0:
            b.mem(seq_t[i], seq_b[i + 1], diag_mat)
        else:
            b.mem(seq_t[i + 1], seq_b[i], diag_mat)
    return b

def auto_mats(panel, depth):
    diag = math.hypot(panel, depth)
    post = abs(depth)
    diag_mat = "wood" if diag <= 2.98 else ("steel" if diag <= 5.98 else "cable")
    post_mat = "wood" if post <= 2.98 else ("steel" if post <= 5.98 else "cable")
    return diag_mat, post_mat, diag, post
