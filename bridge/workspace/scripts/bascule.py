"""Level 4 double-leaf bascule. Leaves swing onto the banks, clear of the channel."""
import math
from scripts.lib import B

def approach(b, x0, x1, topL, topR, botL, botR, n, depth, ydeck=0.0):
    from scripts.span import pratt_span
    return pratt_span(x0, x1, ydeck, ydeck - depth, n, topL, topR, botL, botR,
                      bot_mat="wood", post_mat="wood", diag_mat="wood", b=b)

def bascule():
    b = B()
    # Left approach 0 -> 8.6, right 15.4 -> 24
    # hinge nodes
    hL = b.node(8.6, 0.0, "hL")
    hR = b.node(15.4, 0.0, "hR")
    approach(b, 0.0, 8.6, "A0", hL, "A1", None, n=4, depth=1.6)
    # approach() with botR None won't work. Build manually below.
    return b

def build(gap=0.45, depth=2.0, ratio_open=None, open_delay=2.0, close_delay=16.5, green_delay=20.0, speed=1.2):
    b = B()
    # --- left approach: A0 to hinge ---
    hL = b.node(8.55, 0.0, "hL")
    hR = b.node(15.45, 0.0, "hR")
    # deck nodes left
    left_xs = [2.14, 4.28, 6.42]
    left_tops = [b.node(x, 0.0, ("lt", x)) for x in left_xs]
    left_bots = [b.node(x, -depth, ("lb", x)) for x in left_xs]
    seqt = ["A0"] + left_tops + [hL]
    seqb_end = "A1"
    # bottom: A1 to bots to a node under hinge
    hLb = b.node(8.55, -depth, "hLb")
    seqb = ["A1"] + left_bots + [hLb]
    for a, c in zip(seqt, seqt[1:]):
        b.mem(a, c, "road")
    for a, c in zip(seqb, seqb[1:]):
        b.mem(a, c, "steel")
    for t, bo in zip(left_tops, left_bots):
        b.mem(t, bo, "wood")
    b.mem(hL, hLb, "wood")
    # diagonals flipped pratt
    n = 4
    seq_t = seqt
    seq_b = seqb
    for i in range(n):
        b.mem(seq_t[i], seq_b[i + 1], "cable")
        b.mem(seq_t[i + 1], seq_b[i], "cable")
    # right approach mirror
    right_xs = [24 - x for x in left_xs]  # 21.86, 19.72, 17.58
    right_xs = sorted(right_xs)
    right_tops = [b.node(x, 0.0, ("rt", round(x, 2))) for x in right_xs]
    right_bots = [b.node(x, -depth, ("rb", round(x, 2))) for x in right_xs]
    hRb = b.node(15.45, -depth, "hRb")
    seqt = [hR] + right_tops + ["A3"]
    seqb = [hRb] + right_bots + ["A4"]
    for a, c in zip(seqt, seqt[1:]):
        b.mem(a, c, "road")
    for a, c in zip(seqb, seqb[1:]):
        b.mem(a, c, "steel")
    for t, bo in zip(right_tops, right_bots):
        b.mem(t, bo, "wood")
    b.mem(hR, hRb, "wood")
    for i in range(n):
        b.mem(seqt[i], seqb[i + 1], "cable")
        b.mem(seqt[i + 1], seqb[i], "cable")

    # --- leaves ---
    # left leaf tip at 12.0 - gap/2, right tip at 12.0 + gap/2
    tipL = 12.0 - gap / 2
    tipR = 12.0 + gap / 2
    # two road segments per leaf
    def leaf(hinge, tip, sign, tag, hyd_fixed, group):
        # sign +1 leaf goes to +x
        xh = b.nodes[hinge][0]
        mid = (xh + tip) / 2
        d1 = b.node(mid, 0.0, (tag, "d1"))
        d2 = b.node(tip, 0.0, (tag, "d2"))
        b.mem(hinge, d1, "road")
        b.mem(d1, d2, "road")
        # upper chord
        u0 = b.node(xh, 1.15, (tag, "u0"))
        u1 = b.node(mid, 1.15, (tag, "u1"))
        u2 = b.node(tip, 1.05, (tag, "u2"))
        b.mem(u0, u1, "wood")
        b.mem(u1, u2, "wood")
        b.mem(hinge, u0, "wood")
        b.mem(d1, u1, "wood")
        b.mem(d2, u2, "wood")
        b.mem(hinge, u1, "wood")
        b.mem(d1, u0, "wood")
        b.mem(d1, u2, "wood")
        b.mem(d2, u1, "wood")
        # hydraulic to the upper mid node so the line of action misses the hinge
        b.mem(hyd_fixed, u1, "hydraulic", group)
        return d1, d2, u1

    # hydraulic fixed nodes, outside channel, triangulated to approach
    # actuator anchors sit above the approach, line of action misses the hinge
    fL = b.node(7.5, 4.8, "fL")
    fR = b.node(16.5, 4.8, "fR")
    # strong frame down to the steel approach
    pL = b.node(6.2, 2.2, "pL")
    pR = b.node(17.8, 2.2, "pR")
    b.mem(fL, pL, "steel")
    b.mem(fR, pR, "steel")
    b.mem(left_tops[2], pL, "steel")
    b.mem(left_bots[2], pL, "steel")
    b.mem(left_tops[1], pL, "steel")
    b.mem(right_tops[0], pR, "steel")
    b.mem(right_bots[0], pR, "steel")
    b.mem(right_tops[1], pR, "steel")

    leaf(hL, tipL, 1, "LL", fL, "L")
    leaf(hR, tipR, -1, "RL", fR, "R")

    # sensors / lights / rules
    b.sensors.append({"id": "horn", "type": "horn"})
    b.lights.append({"id": "WL", "x": 5.0, "dir": "right", "init": "green"})
    b.lights.append({"id": "WR", "x": 19.0, "dir": "left", "init": "green"})
    # open
    ro = ratio_open if ratio_open is not None else 0.72
    for g in ("L", "R"):
        b.rules.append({"on": "horn", "delay": open_delay, "do": "hyd", "group": g, "ratio": ro, "speed": speed, "accel": 2.0})
        b.rules.append({"on": "horn", "delay": close_delay, "do": "hyd", "group": g, "ratio": 1.0, "speed": speed, "accel": 2.0})
    b.rules.append({"on": "horn", "delay": 0.3, "do": "light", "light": "WL", "state": "red"})
    b.rules.append({"on": "horn", "delay": 0.3, "do": "light", "light": "WR", "state": "red"})
    b.rules.append({"on": "horn", "delay": green_delay, "do": "light", "light": "WL", "state": "green"})
    b.rules.append({"on": "horn", "delay": green_delay, "do": "light", "light": "WR", "state": "green"})
    return b

def kin_check(b, theta_deg=85):
    """Print raised positions of left leaf + hydraulic vs channel box."""
    # identify left leaf nodes by key prefix stored? we don't store keys.
    # recompute from known coordinates
    print("design members", len(b.members), "nodes", len(b.nodes))
