"""Level 5: drive the pit, hydraulic launch arm over the river."""
from scripts.lib import B

def build(ratio=1.6, speed=8.0, delay=0.12, reset=1.6, accel=12.0):
    b = B()
    from scripts.span import pratt_span
    # flat deck over the pit, y=0, so cars never climb
    botL = b.node(-10.6, -2.4, "pitBL")
    botR = b.node(-0.6, -2.4, "pitBR")
    pratt_span(-11, 0, 0.0, -2.4, 5, "A2", "A0", botL, botR,
               bot_mat="cable", post_mat="steel", diag_mat="cable", b=b)
    b.mem(botL, "A6", "steel")
    b.mem(botR, "A1", "steel")
    b.mem(botR, "A3", "cable")
    # launch arm hinge at (1.2, 0), tip at (4.0, 0)
    hinge = b.node(1.2, 0.0, "hinge")
    mid = b.node(2.6, 0.0, "mid")
    tip = b.node(4.0, 0.05, "tip")
    b.mem("A0", hinge, "road")
    b.mem(hinge, mid, "road")
    b.mem(mid, tip, "road")
    # one lever node above the mid so the hydraulic has a moment arm
    u1 = b.node(2.6, 0.9, "u1")
    b.mem(hinge, u1, "steel")
    b.mem(mid, u1, "steel")
    b.mem(tip, u1, "steel")
    fix = b.node(0.3, -1.6, "fix")
    b.mem("A1", fix, "steel")
    b.mem("A0", fix, "steel")
    b.mem(fix, u1, "hydraulic", "L")
    # landing ramp on the right, from x=22 down? cars land in the air and need a deck
    # a gentle ramp from (22, 1.2) down to A7 (24, 0) then to A9
    r1 = b.node(21.5, 1.4, "r1")
    r2 = b.node(22.8, 0.6, "r2")
    b.mem(r1, r2, "road")
    b.mem(r2, "A7", "road")
    # plate on the arm's first road segment (hinge-mid). member index depends on order.
    # We'll set it after counting. Placeholder filled by caller if needed.
    b.sensors.append({"id": "p", "type": "plate", "member": 13})
    b.sensors.append({"id": "s", "type": "start"})
    b.rules += [
        {"on": "p", "delay": delay, "do": "hyd", "group": "L", "ratio": ratio, "speed": speed, "accel": accel},
        {"on": "p", "delay": delay + reset, "do": "hyd", "group": "L", "ratio": 1.0, "speed": 4.0, "accel": 8.0},
    ]
    return b

if __name__ == "__main__":
    from scripts.lib import check
    b = build()
    d = b.design()
    # print member index of hinge-mid road
    for i, m in enumerate(d["members"]):
        print(i, m)
    try:
        P = check(5, d)
        print("cost", P["cost"])
    except Exception as e:
        print("ILLEGAL", e)
