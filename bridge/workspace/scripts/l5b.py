"""Level 5: pit truss, horizontal hydraulic bumper, small kicker, far landing."""
import math
from scripts.lib import B
from scripts.span import pratt_span

def build(ratio=1.8, speed=15.0, delay=0.05, accel=40.0):
    b = B()
    botL = b.node(-10.6, -2.4, "pitBL")
    botR = b.node(-0.6, -2.4, "pitBR")
    pratt_span(-11, 0, 0.0, -2.4, 5, "A2", "A0", botL, botR,
               bot_mat="cable", post_mat="steel", diag_mat="cable", b=b)
    b.mem(botL, "A6", "steel")
    b.mem(botR, "A1", "steel")
    # runway
    r1 = b.node(2.2, 0.0, "r1")
    r2 = b.node(4.4, 0.0, "r2")
    b.mem("A0", r1, "road")
    b.mem(r1, r2, "road")
    # kicker
    k1 = b.node(6.2, 0.55, "k1")
    k2 = b.node(7.8, 1.15, "k2")
    b.mem(r2, k1, "road")
    b.mem(k1, k2, "road")
    # bumper: vertical road, base slides? base is pushed by hydraulic
    # fixed anchor of hydraulic at (-1.5, 0.3), bumper nodes at (0.6, 0.05) and (0.6, 0.55)
    bb = b.node(0.55, 0.08, "bb")
    bt = b.node(0.55, 0.55, "bt")
    b.mem(bb, bt, "road")
    fix = b.node(-1.2, 0.3, "fix")
    b.mem("A1", fix, "steel")
    b.mem("A0", fix, "steel")
    b.mem(fix, bb, "hydraulic", "P")
    # keep bumper from falling: steel up to a high fixed node
    hold = b.node(-0.2, 1.2, "hold")
    b.mem("A0", hold, "steel")
    b.mem(hold, bt, "cable")
    # minimal landing lip at the bank
    lip = b.node(22.6, 0.35, "lip")
    b.mem(lip, "A7", "road")
    b.mem(lip, "A8", "steel")
    b.sensors.append({"id": "g", "type": "gate", "x": 1.5, "dir": "right"})
    b.rules.append({"on": "g", "delay": delay, "do": "hyd", "group": "P", "ratio": ratio, "speed": speed, "accel": accel})
    b.rules.append({"on": "g", "delay": delay + 1.2, "do": "hyd", "group": "P", "ratio": 1.0, "speed": 6.0, "accel": 10})
    return b
