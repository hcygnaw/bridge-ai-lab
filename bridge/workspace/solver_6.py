import math
from opt_utils import eval_design, save_if_best


def make_l6_drawbridge():
    # Anchors: A0=(0,0), A1=(0,-2), A2=(0,-4), A3=(-5,0), A4=(12,-2), A5=(24,-2),
    #          A6=(36,0), A7=(36,-2), A8=(36,-4), A9=(41,0)
    nodes, members = [], []

    def add_n(x, y):
        nodes.append([round(x, 4), round(y, 4)])
        return len(nodes) - 1

    # Left span [0, 12]: 6 segments of 2.0m!
    # Top deck: A0(0,0), 2, 4, 6, 8, 10, 12 (let's extend fixed span to pivot x=13.0? Or pivot at 12.0?
    # Wait: if pivot at x=13.0, leaf is [13.0, 17.93] = 4.93m (2 segs of 2.465m).
    # Let's check: [0, 12] = 6 segs of 2m, then 12->13.2 (1.2m) to pivot at x=13.2!
    # Wait: at pivot x=13.2, leaf is [13.2, 17.93] = 4.73m (2 segs of 2.365m)!
    # Rotated 75 deg: 13.2 + 4.73*cos(75) = 14.42 < 15.0!
    l_top = ["A0"] + [add_n(2.0 * i, 0.0) for i in range(1, 7)]  # 2,4,6,8,10,12
    for i in range(6):
        members.append([l_top[i], l_top[i + 1], "road"])
    lpiv = add_n(13.2, 0.0)
    members.append([l_top[6], lpiv, "road"])

    # Bottom chord of left span [0, 12]: A1=(0,-2) -> (2,-2)->(4,-2)->(6,-2)->(8,-2)->(10,-2)->A4(12,-2)!
    # Wait: A4=(12,-2) is ALREADY at (12,-2)! So [0,12] is a simple 2m-deep Pratt truss resting on A1 & A4!
    l_bot = ["A1"] + [add_n(2.0 * i, -2.0) for i in range(1, 6)] + ["A4"]
    for i in range(6):
        members.append([l_bot[i], l_bot[i + 1], "wood"])
    for i in range(1, 7):
        members.append([l_top[i], l_bot[i], "wood"])
    # Pratt diagonals on [0, 12] (mid = 3):
    for i in range(6):
        u, v = (l_top[i], l_bot[i + 1]) if i < 3 else (l_bot[i], l_top[i + 1])
        members.append([u, v, "wood"])
    # Brace lpiv=(13.2,0) to A4=(12,-2)!
    members.append(["A4", lpiv, "steel"])

    # Tower at (12.0, 3.5) supported by l_top[6]=(12,0), l_top[5]=(10,0), lpiv=(13.2,0), A4=(12,-2)?
    ltow = add_n(11.0, 3.2)
    members += [[l_top[5], ltow, "steel"], [l_top[6], ltow, "steel"], [lpiv, ltow, "steel"]]
    # Backstay cable from ltow=(11.0, 3.2) to l_top[3]=(6,0) or A0=(0,0) so tower pulls back cleanly!
    members.append([ltow, l_top[3], "cable"])
    # Backstay to l_top[3] is enough (removing long cable to A0 saves 740!)

    # Left leaf [13.2, 17.93]: 2 road segs (13.2 -> 15.56 -> 17.93)
    ll1 = add_n(15.56, 0.0)
    ltip = add_n(17.93, 0.0)
    members += [[lpiv, ll1, "road"], [ll1, ltip, "road"]]
    llu1 = add_n(14.5, 1.5)
    llu2 = add_n(16.5, 1.0)
    members += [[lpiv, llu1, "steel"], [llu1, llu2, "steel"], [llu2, ltip, "wood"]]
    members += [[llu1, ll1, "wood"], [llu2, ll1, "wood"]]
    # Hydraulic from ltow=(11.0, 3.2) to llu1=(14.5, 1.5): L0 = hypot(3.5, 1.7) = 3.89m <= 5.0m!
    # D = dist((13.2,0), (11.0,3.2)) = hypot(2.2, 3.2) = 3.883m
    # R = dist((13.2,0), (14.5,1.5)) = hypot(1.3, 1.5) = 1.985m
    # At ratio=0.52: L1 = 2.02m. min_dist = 3.883 - 1.985 = 1.898m.
    # cos(a1) = (15.08 + 3.94 - 4.08)/(2*3.883*1.985) = 0.969 -> a1 = 14.3 deg.
    # ltow angle = 180 - atan2(3.2, 2.2) = 124.5 deg -> open llu1 angle = 110.2 deg.
    # closed llu1 angle = atan2(1.5, 1.3) = 49.1 deg -> rotation = 61.1 deg!
    #Wait: 13.2 + 4.73*cos(61.1) = 15.48 (IN CHANNEL [15,21]!).
    # So put ltow at (10.2, 2.8) -> D = hypot(3.0, 2.8) = 4.10m, angle = 137 deg!
    # L0 = hypot(4.3, 1.3) = 4.49m! At ratio=0.52: L1=2.33m, a1=18 deg -> open=119 deg -> rot=70 deg -> 13.2+4.73*cos(70)=14.82 < 15.0!
    nodes[ltow] = [10.2, 2.8]
    members.append([ltow, llu1, "hydraulic", "L"])

    # Mirror right side (x' = 36 - x)
    # Right span [24, 36]: A6=(36,0), A7=(36,-2), A5=(24,-2)
    r_top = ["A6"] + [add_n(36.0 - 2.0 * i, 0.0) for i in range(1, 7)]  # 34,32,30,28,26,24
    for i in range(6):
        members.append([r_top[i], r_top[i + 1], "road"])
    rpiv = add_n(22.8, 0.0)
    members.append([r_top[6], rpiv, "road"])
    r_bot = ["A7"] + [add_n(36.0 - 2.0 * i, -2.0) for i in range(1, 6)] + ["A5"]
    for i in range(6):
        members.append([r_bot[i], r_bot[i + 1], "wood"])
    for i in range(1, 7):
        members.append([r_top[i], r_bot[i], "wood"])
    for i in range(6):
        u, v = (r_top[i], r_bot[i + 1]) if i < 3 else (r_bot[i], r_top[i + 1])
        members.append([u, v, "wood"])
    members.append(["A5", rpiv, "steel"])

    rtow = add_n(25.8, 2.8)
    members += [[r_top[5], rtow, "steel"], [r_top[6], rtow, "steel"], [rpiv, rtow, "steel"]]
    members.append([rtow, r_top[3], "cable"])

    rl1 = add_n(20.44, 0.0)
    rtip = add_n(18.07, 0.0)
    members += [[rpiv, rl1, "road"], [rl1, rtip, "road"]]
    rlu1 = add_n(21.5, 1.5)
    rlu2 = add_n(19.5, 1.0)
    members += [[rpiv, rlu1, "steel"], [rlu1, rlu2, "steel"], [rlu2, rtip, "wood"]]
    members += [[rlu1, rl1, "wood"], [rlu2, rl1, "wood"]]
    members.append([rtow, rlu1, "hydraulic", "R"])

    sensors = [{"id": "h", "type": "horn"}]
    lights = [
        {"id": "LL", "x": -1.0, "dir": "right", "init": "green"},
        {"id": "LR", "x": 37.0, "dir": "left", "init": "green"},
    ]
    rules = [
        {"on": "h", "delay": 2.5, "do": "light", "light": "LL", "state": "red"},
        {"on": "h", "delay": 2.5, "do": "light", "light": "LR", "state": "red"},
        {"on": "h", "delay": 6.0, "do": "hyd", "group": "L", "ratio": 0.50, "speed": 3.0},
        {"on": "h", "delay": 6.0, "do": "hyd", "group": "R", "ratio": 0.50, "speed": 3.0},
        {"on": "h", "delay": 16.2, "do": "hyd", "group": "L", "ratio": 1.0, "speed": 3.0},
        {"on": "h", "delay": 16.2, "do": "hyd", "group": "R", "ratio": 1.0, "speed": 3.0},
        {"on": "h", "delay": 18.2, "do": "light", "light": "LL", "state": "green"},
        {"on": "h", "delay": 18.2, "do": "light", "light": "LR", "state": "green"},
    ]
    return {"nodes": nodes, "members": members, "sensors": sensors, "lights": lights, "rules": rules}


if __name__ == "__main__":
    d = make_l6_drawbridge()
    ok, cost, pk, _ = eval_design(6, d, quiet=False)
    print(f"L6 drawbridge: ok={ok}, cost={cost:.2f}, max_peak={pk*100:.1f}%")
    if ok:
        save_if_best(6, d)
