"""Drop-deck over a ship-clear foundation truss."""
from scripts.lib import B
from scripts.span import pratt_span

def build(ratio=0.52, speed=2.2, open_delay=0.6, close_delay=16.3, green_delay=19.2):
    b = B()
    # foundation truss entirely at y <= -2.35 so it never touches the ship box
    # top chord y=-2.35, bottom y=-4.6, x=0 to 24, n=12 panels of 2.0
    # ends tie up to A1 (0,-2) and A4 (24,-2)
    n = 8
    x0, x1 = 0.4, 23.6
    yt, yb = -2.35, -4.55
    tops, bots = [], []
    panel = (x1 - x0) / n
    for i in range(n + 1):
        x = x0 + panel * i
        tops.append(b.node(x, yt, ("ft", round(x, 2))))
        bots.append(b.node(x, yb, ("fb", round(x, 2))))
    for a, c in zip(tops, tops[1:]):
        b.mem(a, c, "steel")
    for a, c in zip(bots, bots[1:]):
        b.mem(a, c, "cable")
    for t, bo in zip(tops, bots):
        b.mem(t, bo, "steel")
    for i in range(n):
        if i < n / 2:
            b.mem(tops[i], bots[i + 1], "cable")
        else:
            b.mem(tops[i + 1], bots[i], "cable")
    # tie ends to anchors (short)
    b.mem("A1", tops[0], "steel")
    b.mem("A4", tops[-1], "steel")
    b.mem("A0", tops[0], "steel")
    b.mem("A3", tops[-1], "steel")

    # side decks at y=0, outside channel, posted down to foundation top
    def side_deck(xs, anchor_end, which):
        ids = [b.node(x, 0.0, ("s", which, x)) for x in xs]
        if which == "L":
            b.mem(anchor_end, ids[0], "road")
            for a, c in zip(ids, ids[1:]):
                b.mem(a, c, "road")
        else:
            for a, c in zip(ids, ids[1:]):
                b.mem(a, c, "road")
            b.mem(ids[-1], anchor_end, "road")
        for nid in ids:
            x = b.nodes[nid][0]
            # nearest foundation top
            foot = min(tops, key=lambda i: abs(b.nodes[i][0] - x))
            L = abs(b.nodes[nid][1] - b.nodes[foot][1])
            if L <= 2.95:
                b.mem(nid, foot, "wood")
            else:
                b.mem(nid, foot, "steel")
        return ids

    left = side_deck([2.0, 4.0, 6.0, 7.6], "A0", "L")
    right = side_deck([16.4, 18.0, 20.0, 22.0], "A3", "R")

    # moving deck over the channel, plus a little overlap outside so the gap is small
    pxs = [8.0, 10.0, 12.0, 14.0, 16.0]
    pids = [b.node(x, 0.0, ("p", x)) for x in pxs]
    for a, c in zip(pids, pids[1:]):
        b.mem(a, c, "road")
    for x, pid in zip(pxs, pids):
        foot = min(bots, key=lambda i: abs(b.nodes[i][0] - x))
        b.mem(foot, pid, "hydraulic", "D")

    b.sensors.append({"id": "horn", "type": "horn"})
    b.lights.append({"id": "WL", "x": 3.0, "dir": "right", "init": "green"})
    b.lights.append({"id": "WR", "x": 21.0, "dir": "left", "init": "green"})
    b.rules += [
        {"on": "horn", "delay": 0.15, "do": "light", "light": "WL", "state": "red"},
        {"on": "horn", "delay": 0.15, "do": "light", "light": "WR", "state": "red"},
        {"on": "horn", "delay": open_delay, "do": "hyd", "group": "D", "ratio": ratio, "speed": speed, "accel": 4.0},
        {"on": "horn", "delay": close_delay, "do": "hyd", "group": "D", "ratio": 1.0, "speed": speed, "accel": 4.0},
        {"on": "horn", "delay": green_delay, "do": "light", "light": "WL", "state": "green"},
        {"on": "horn", "delay": green_delay, "do": "light", "light": "WR", "state": "green"},
    ]
    return b
