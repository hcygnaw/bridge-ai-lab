"""High bridge that clears a ship channel, with sloped approaches."""
import math
from scripts.lib import B

def high_bridge(x_left, x_right, x_ch0, x_ch1, y_top,
                left_anchor, right_anchor,
                seg=2.2, post_mat="steel", bot_y_water=-1.2, bot_y_land=0.35,
                upper=1.5):
    b = B()
    # build deck polyline
    def add_chain(pts, mat="road"):
        ids = []
        for x, y in pts:
            ids.append(b.node(x, y, ("d", round(x, 3), round(y, 3))))
        for a, c in zip(ids, ids[1:]):
            b.mem(a, c, mat)
        return ids

    def interp(x0, y0, x1, y1, seg):
        dist = math.hypot(x1 - x0, y1 - y0)
        n = max(1, int(math.ceil(dist / seg)))
        pts = []
        for i in range(n + 1):
            t = i / n
            pts.append((x0 + (x1 - x0) * t, y0 + (y1 - y0) * t))
        return pts

    # approaches end just outside channel
    left_pts = interp(x_left, 0.05, x_ch0 - 0.15, y_top, seg)
    # drop the first point; we'll tie to anchor instead if close
    flat = interp(x_ch0 - 0.15, y_top, x_ch1 + 0.15, y_top, seg)
    right_pts = interp(x_ch1 + 0.15, y_top, x_right, 0.05, seg)
    # merge shared endpoints
    pts = left_pts + flat[1:] + right_pts[1:]
    ids = []
    for i, (x, y) in enumerate(pts):
        ids.append(b.node(x, y, ("deck", round(x, 3))))
    # connect to shore anchors
    b.mem(left_anchor, ids[0], "road")
    for a, c in zip(ids, ids[1:]):
        b.mem(a, c, "road")
    b.mem(ids[-1], right_anchor, "road")

    # supports under approaches
    bots = []
    for nid in ids:
        x, y = b.nodes[nid]
        if x_ch0 - 0.2 <= x <= x_ch1 + 0.2:
            continue
        if y < 0.5:
            continue
        by = bot_y_land if (x < 0.2 or x > 23.8) else bot_y_water
        # don't place inside rock/ground
        if x <= 0 and by <= 0.05:
            by = 0.3
        if x >= 24 and by <= 0.05:
            by = 0.3
        L = abs(y - by)
        if L < 0.35:
            continue
        bo = b.node(x, by, ("bot", round(x, 3)))
        mat = "wood" if L <= 2.9 else ("steel" if L <= 5.9 else None)
        if mat is None:
            # split post with a mid node braced later
            midy = (y + by) / 2
            mid = b.node(x, midy, ("mid", round(x, 3)))
            b.mem(nid, mid, "steel")
            b.mem(mid, bo, "steel")
        else:
            b.mem(nid, bo, mat if mat != "wood" or L <= 2.9 else "steel")
        bots.append(bo)
    bots_sorted = sorted(set(bots), key=lambda i: b.nodes[i][0])
    for a, c in zip(bots_sorted, bots_sorted[1:]):
        x1, y1 = b.nodes[a]
        x2, y2 = b.nodes[c]
        # don't cross the channel
        if x1 < x_ch0 and x2 > x_ch0:
            continue
        if x1 < x_ch1 and x2 > x_ch1 and x1 > x_ch0:
            continue
        L = math.hypot(x2 - x1, y2 - y1)
        if L < 0.3 or L > 6:
            continue
        mat = "wood" if L <= 2.95 else "steel"
        b.mem(a, c, mat)
    # diagonals: deck node to next bottom, if short enough and not crossing channel
    deck_ids = ids
    bot_by_x = {round(b.nodes[i][0], 3): i for i in bots_sorted}
    for i in range(len(deck_ids) - 1):
        x1, y1 = b.nodes[deck_ids[i]]
        x2, y2 = b.nodes[deck_ids[i + 1]]
        if min(x1, x2) >= x_ch0 - 0.3 and max(x1, x2) <= x_ch1 + 0.3:
            continue
        # diagonal to bottom of neighbor
        for bx in (round(x2, 3),):
            if bx in bot_by_x:
                bo = bot_by_x[bx]
                xb, yb = b.nodes[bo]
                if (x1 < x_ch0 <= xb) or (xb < x_ch0 <= x1):
                    continue
                if (x1 < x_ch1 <= xb) or (xb < x_ch1 <= x1):
                    continue
                L = math.hypot(x1 - xb, y1 - yb)
                if 0.3 <= L <= 5.9:
                    b.mem(deck_ids[i], bo, "steel" if L > 2.95 else "wood")
    # upper truss over channel
    ups = []
    for nid in ids:
        x, y = b.nodes[nid]
        if x_ch0 - 0.3 <= x <= x_ch1 + 0.3:
            up = b.node(x, y + upper, ("up", round(x, 3)))
            b.mem(nid, up, "wood")
            ups.append(up)
    for a, c in zip(ups, ups[1:]):
        b.mem(a, c, "wood")
    # upper diagonals
    ch_deck = [nid for nid in ids if x_ch0 - 0.3 <= b.nodes[nid][0] <= x_ch1 + 0.3]
    for i in range(len(ch_deck) - 1):
        # find up of next
        x2 = b.nodes[ch_deck[i + 1]][0]
        for up in ups:
            if abs(b.nodes[up][0] - x2) < 0.05:
                b.mem(ch_deck[i], up, "wood")
                break
    return b
