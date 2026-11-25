import math
from opt_utils import eval_design, save_if_best


def make_l4_drawbridge():
    # Anchors: A0=(0,0), A1=(0,-2), A2=(-4,0), A3=(24,0), A4=(24,-2), A5=(28,0)
    # Fixed approach [0, 6] and [18, 24], pivoting leaves [6, 12] and [12, 18]
    nodes = []
    members = []

    def add_n(x, y):
        nodes.append([round(x, 4), round(y, 4)])
        return len(nodes) - 1

    # Left approach road: 0 -> 2 -> 4 -> 6
    l1 = add_n(2.0, 0.0)
    l2 = add_n(4.0, 0.0)
    lpiv = add_n(6.0, 0.0)
    members += [["A0", l1, "road"], [l1, l2, "road"], [l2, lpiv, "road"]]
    # Left approach bottom chord from A1=(0,-2) to (2,-2), (4,-2), (6,-2)
    lb1 = add_n(2.0, -2.0)
    lb2 = add_n(4.0, -2.0)
    lb3 = add_n(6.0, -2.0)
    members += [["A1", lb1, "wood"], [lb1, lb2, "wood"], [lb2, lb3, "wood"]]
    members += [[l1, lb1, "wood"], [l2, lb2, "wood"], [lpiv, lb3, "wood"]]
    members += [["A0", lb1, "wood"], [l1, lb2, "wood"], [l2, lb3, "wood"]]

    # Left tower above approach for hydraulic: T=(3.5, 2.5) braced to A0, l1, l2, lpiv
    ltow = add_n(3.5, 2.5)
    members += [["A0", ltow, "steel"], [l1, ltow, "wood"], [l2, ltow, "wood"], [lpiv, ltow, "wood"]]
    #Wait: if lpiv-ltow is fixed, leaf can still pivot around lpiv!

    # Left leaf [6, 12]: 3 road segments: 6 -> 8 -> 10 -> 11.94 (leave 0.12m gap at mid for node_gap >= 0.1!)
    ll1 = add_n(8.0, 0.0)
    ll2 = add_n(10.0, 0.0)
    ltip = add_n(11.93, 0.0)
    members += [[lpiv, ll1, "road"], [ll1, ll2, "road"], [ll2, ltip, "road"]]
    # Leaf truss above road (so it rotates cleanly up & back)
    llu1 = add_n(8.0, 1.8)
    llu2 = add_n(10.0, 1.2)
    members += [[lpiv, llu1, "wood"], [llu1, llu2, "wood"], [llu2, ltip, "wood"]]
    members += [[ll1, llu1, "wood"], [ll2, llu2, "wood"]]
    members += [[llu1, ll2, "wood"], [llu2, ll1, "wood"]]  #Wait: avoid duplicate! Just Pratt: [llu1, ll2]
    # Remove duplicate? Wait: llu1-ll2 and llu2-ll1 are different pairs! Wait: [llu1, ll2] and [lpiv, ll1] etc.
    # Hydraulic from ltow=(3.5, 2.5) to llu1=(8.0, 1.8)? dist = hypot(4.5, 0.7) = 4.55 <= 5.0!
    # Wait: if ltow=(3.5, 2.5) and llu1=(8.0, 1.8), pulling llu1 toward ltow lifts the leaf!
    # Let's check angle: dist(lpiv(6,0), ltow(3.5,2.5)) = hypot(2.5,2.5) = 3.535.
    # dist(lpiv(6,0), llu1(8,1.8)) = hypot(2,1.8) = 2.69.
    # When hyd contracts from 4.55 to 0.5*4.55=2.28: llu1 rotates toward ltow by ~60-70 deg!
    # Let's check if ltip (radius 5.93) clears x=9:
    # Closed angle of llu1 from lpiv: atan2(1.8, 2.0) = 42 deg. ltow angle from lpiv: atan2(2.5, -2.5) = 135 deg.
    # If llu1 rotates to ~115 deg (73 deg rotation), ltip rotates by 73 deg -> x = 6 + 5.93*cos(73) = 7.73 < 9.0!
    # Wait: if we also connect hydraulic from ltow to ll1=(8,0)? dist(ltow(3.5,2.5), ll1(8,0)) = hypot(4.5, 2.5) = 5.15 > 5.0!
    # So put ltow at (4.0, 2.5) -> dist to llu1(8, 1.8) = hypot(4.0, 0.7) = 4.06m!
    # At ratio=0.5, L=2.03m! Let's compute alpha: D=hypot(2,2.5)=3.20, R=2.69 -> cos(a1) = (10.24+7.24-4.12)/(2*3.20*2.69) = 0.776 -> a1=39 deg -> llu1 at 128.7-39 = 89.7 deg -> rotation = 89.7 - 42 = 47.7 deg -> 6+5.93*cos(47.7) = 9.99 (STILL IN CHANNEL!).
    # So we want bigger rotation! Put ltow at (3.5, 2.8) and attach to (7.5, 1.5) or ratio=0.5 with ltow at (2.8, 2.2) and attach to llu1=(7.2, 1.5)!
    # Wait: let's test this cleanly right now with exact geometry calculation!
    return None


def make_l4_drawbridge_v2(rot_target_deg=80.0):
    nodes = []
    members = []

    def add_n(x, y):
        nodes.append([round(x, 4), round(y, 4)])
        return len(nodes) - 1

    # Left approach [0, 6]:
    l1 = add_n(2.0, 0.0)
    l2 = add_n(4.0, 0.0)
    lpiv = add_n(6.0, 0.0)
    members += [["A0", l1, "road"], [l1, l2, "road"], [l2, lpiv, "road"]]
    lb1 = add_n(2.0, -2.0)
    lb2 = add_n(4.0, -2.0)
    lb3 = add_n(6.0, -2.0)
    members += [["A1", lb1, "wood"], [lb1, lb2, "wood"], [lb2, lb3, "wood"]]
    members += [[l1, lb1, "wood"], [l2, lb2, "wood"], [lpiv, lb3, "wood"]]
    members += [["A0", lb1, "wood"], [l1, lb2, "wood"], [l2, lb3, "wood"]]

    # Tower at (3.0, 2.2) braced to A0, l1, l2, lpiv
    ltow = add_n(3.0, 2.2)
    members += [["A0", ltow, "wood"], [l1, ltow, "wood"], [l2, ltow, "wood"], [lpiv, ltow, "steel"]]
    #Wait: A0=(0,0) to (3,2.2) is 3.72m (>3m wood), so use steel or A10=(-2,0)!
    members[-4] = ["A0", ltow, "steel"]

    # Left leaf [6, 11.93]: attach point at (7.5, 1.0)
    ll1 = add_n(8.0, 0.0)
    ll2 = add_n(10.0, 0.0)
    ltip = add_n(11.93, 0.0)
    members += [[lpiv, ll1, "road"], [ll1, ll2, "road"], [ll2, ltip, "road"]]
    # Leaf upper nodes
    llu1 = add_n(7.5, 1.3)
    llu2 = add_n(9.8, 1.0)
    members += [[lpiv, llu1, "wood"], [llu1, llu2, "wood"], [llu2, ltip, "wood"]]
    members += [[llu1, ll1, "wood"], [llu2, ll2, "wood"], [llu1, ll2, "wood"]]
    # Hydraulic from ltow=(3.0, 2.2) to llu1=(7.5, 1.3): L = hypot(4.5, 0.9) = 4.59m <= 5.0m!
    # At ratio=0.5: L=2.29m. D=hypot(3,2.2)=3.72, R=hypot(1.5,1.3)=1.985 -> min dist = 3.72-1.985=1.735!
    # cos(a1) = (13.84 + 3.94 - 5.24)/(2*3.72*1.985) = 0.849 -> a1=31.9 deg!
    # ltow angle from lpiv = 180 - atan2(2.2, 3.0) = 143.7 deg.
    # llu1 angle when closed = atan2(1.3, 1.5) = 40.9 deg.
    # llu1 angle when open = 143.7 - 31.9 = 111.8 deg -> rotation = 70.9 deg!
    # Tip x when open = 6 + 5.93*cos(70.9) = 7.94 < 9.0! Clears [9, 15] completely!
    members.append([ltow, llu1, "hydraulic", "L"])

    # Right side (mirror around x=12: x' = 24 - x)
    r1 = add_n(22.0, 0.0)
    r2 = add_n(20.0, 0.0)
    rpiv = add_n(18.0, 0.0)
    members += [["A3", r1, "road"], [r1, r2, "road"], [r2, rpiv, "road"]]
    rb1 = add_n(22.0, -2.0)
    rb2 = add_n(20.0, -2.0)
    rb3 = add_n(18.0, -2.0)
    members += [["A4", rb1, "wood"], [rb1, rb2, "wood"], [rb2, rb3, "wood"]]
    members += [[r1, rb1, "wood"], [r2, rb2, "wood"], [rpiv, rb3, "wood"]]
    members += [["A3", rb1, "wood"], [r1, rb2, "wood"], [r2, rb3, "wood"]]

    rtow = add_n(21.0, 2.2)
    members += [["A3", rtow, "steel"], [r1, rtow, "wood"], [r2, rtow, "wood"], [rpiv, rtow, "steel"]]

    rl1 = add_n(16.0, 0.0)
    rl2 = add_n(14.0, 0.0)
    rtip = add_n(12.07, 0.0)
    members += [[rpiv, rl1, "road"], [rl1, rl2, "road"], [rl2, rtip, "road"]]
    rlu1 = add_n(16.5, 1.3)
    rlu2 = add_n(14.2, 1.0)
    members += [[rpiv, rlu1, "wood"], [rlu1, rlu2, "wood"], [rlu2, rtip, "wood"]]
    members += [[rlu1, rl1, "wood"], [rlu2, rl2, "wood"], [rlu1, rl2, "wood"]]
    members.append([rtow, rlu1, "hydraulic", "R"])

    sensors = [{"id": "h", "type": "horn"}]
    lights = [
        {"id": "LL", "x": -1.0, "dir": "right", "init": "green"},
        {"id": "LR", "x": 25.0, "dir": "left", "init": "green"},
    ]
    rules = [
        {"on": "h", "delay": 6.5, "do": "light", "light": "LL", "state": "red"},
        {"on": "h", "delay": 6.5, "do": "light", "light": "LR", "state": "red"},
        {"on": "h", "delay": 7.5, "do": "hyd", "group": "L", "ratio": 0.5, "speed": 2.0},
        {"on": "h", "delay": 7.5, "do": "hyd", "group": "R", "ratio": 0.5, "speed": 2.0},
        {"on": "h", "delay": 16.2, "do": "hyd", "group": "L", "ratio": 1.0, "speed": 2.0},
        {"on": "h", "delay": 16.2, "do": "hyd", "group": "R", "ratio": 1.0, "speed": 2.0},
        {"on": "h", "delay": 18.5, "do": "light", "light": "LL", "state": "green"},
        {"on": "h", "delay": 18.5, "do": "light", "light": "LR", "state": "green"},
    ]
    return {"nodes": nodes, "members": members, "sensors": sensors, "lights": lights, "rules": rules}


if __name__ == "__main__":
    d = make_l4_drawbridge_v2()
    ok, cost, pk, _ = eval_design(4, d, quiet=False)
    print(f"L4 drawbridge: ok={ok}, cost={cost:.2f}, max_peak={pk*100:.1f}%")
    if ok:
        save_if_best(4, d)
