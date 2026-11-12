"""Level 4: deck span drops below the ship box on the horn."""
import math
from scripts.lib import B
from scripts.span import pratt_span

def build(drop_ratio=0.52, speed=2.0, open_delay=0.8, close_delay=16.4, green_delay=19.5):
    b = B()
    yb = -4.7  # foundation, always below ship box
    # foundation nodes
    fxs = [2.0, 4.0, 6.0, 7.7, 8.05, 10.0, 12.0, 14.0, 15.95, 16.3, 18.3, 20.3, 22.0]
    fids = [b.node(x, yb, ("f", x)) for x in fxs]
    for a, c in zip(fids, fids[1:]):
        b.mem(a, c, "steel")
    # tie foundation to bank anchors
    b.mem("A1", fids[0], "steel")
    b.mem("A4", fids[-1], "steel")
    b.mem("A0", fids[0], "cable")
    b.mem("A3", fids[-1], "cable")

    # approaches: Pratt, ends supported by posts to foundation
    hL = b.node(7.7, 0.0, "hL")
    hR = b.node(16.3, 0.0, "hR")
    hLb = b.node(7.7, -1.8, "hLb")
    hRb = b.node(16.3, -1.8, "hRb")
    pratt_span(0, 7.7, 0.0, -1.8, 4, "A0", hL, "A1", hLb,
               bot_mat="wood", post_mat="wood", diag_mat="wood", b=b)
    pratt_span(16.3, 24.0, 0.0, -1.8, 4, hR, "A3", hRb, "A4",
               bot_mat="wood", post_mat="wood", diag_mat="wood", b=b)
    # end posts down to the deep foundation (outside the channel)
    b.mem(hL, fids[3], "steel")
    b.mem(hLb, fids[3], "steel")
    b.mem(hR, fids[9], "steel")
    b.mem(hRb, fids[9], "steel")

    # platform road, hydraulics down to foundation
    pxs = [8.05, 10.0, 12.0, 14.0, 15.95]
    pids = [b.node(x, 0.0, ("p", x)) for x in pxs]
    for a, c in zip(pids, pids[1:]):
        b.mem(a, c, "road")
    # map platform x to foundation
    fmap = {8.05: fids[4], 10.0: fids[5], 12.0: fids[6], 14.0: fids[7], 15.95: fids[8]}
    for x, pid in zip(pxs, pids):
        b.mem(fmap[x], pid, "hydraulic", "D")

    b.sensors.append({"id": "horn", "type": "horn"})
    b.lights.append({"id": "WL", "x": 4.5, "dir": "right", "init": "green"})
    b.lights.append({"id": "WR", "x": 19.5, "dir": "left", "init": "green"})
    b.rules.append({"on": "horn", "delay": 0.2, "do": "light", "light": "WL", "state": "red"})
    b.rules.append({"on": "horn", "delay": 0.2, "do": "light", "light": "WR", "state": "red"})
    b.rules.append({"on": "horn", "delay": open_delay, "do": "hyd", "group": "D", "ratio": drop_ratio, "speed": speed, "accel": 3.0})
    b.rules.append({"on": "horn", "delay": close_delay, "do": "hyd", "group": "D", "ratio": 1.0, "speed": speed, "accel": 3.0})
    b.rules.append({"on": "horn", "delay": green_delay, "do": "light", "light": "WL", "state": "green"})
    b.rules.append({"on": "horn", "delay": green_delay, "do": "light", "light": "WR", "state": "green"})
    return b
