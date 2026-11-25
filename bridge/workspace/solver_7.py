import json
import math
from opt_utils import eval_design, save_if_best
import bridge as B
import saboteur as S


def make_final_bridge():
    # Level final: 28m river, budget 26000, static_only=True
    # Anchors: A0=(0,0), A1=(0,-2), A2=(-5,0), A3=(28,0), A4=(28,-2), A5=(33,0)
    # Build a 14-panel (2.0m) ultra-stiff double-reinforced steel Pratt+Arch bridge!
    nodes, members = [], []

    def add_n(x, y):
        nodes.append([round(x, 4), round(y, 4)])
        return len(nodes) - 1

    n_seg = 14  # 2.0m each -> road comp = 75 kN (or 16 segs of 1.75m -> 90 kN!)
    n_seg = 16  # 1.75m each -> FULL 90 kN road strength!
    top = ["A0"] + [add_n(28.0 * i / n_seg, 0.0) for i in range(1, n_seg)] + ["A3"]
    for i in range(n_seg):
        members.append([top[i], top[i + 1], "road"])

    # Deep steel bottom arch/truss from A1=(0,-2) to A4=(28,-2) dipping to -4.0 at midspan!
    # Wait: depth -2.0 at ends, -3.8 at midspan -> steel verticals <= 3.8m (comp=62 kN), or steel arch above too!
    bot = ["A1"]
    for i in range(1, n_seg):
        t = i / n_seg
        x = 28.0 * t
        y = -2.0 - 1.6 * math.sin(math.pi * t)
        bot.append(add_n(x, y))
    bot.append("A4")
    for i in range(n_seg):
        members.append([bot[i], bot[i + 1], "steel"])
    for i in range(1, n_seg):
        members.append([top[i], bot[i], "steel"])
    mid = n_seg // 2
    for i in range(n_seg):
        if i < mid:
            members.append([top[i], bot[i + 1], "steel"])
        else:
            members.append([bot[i], top[i + 1], "steel"])

    # Also add an upper steel arch/tie-back from A2=(-5,0) and A5=(33,0) -> (0, 3.0) and (28, 3.0)?
    # Wait: let's check cost first!
    return {"nodes": nodes, "members": members}


def make_sab_pile_driver(use_hyd=True, ballast_kg=1800.0):
    # 4-wheel, 3.0m long, <= 1.5m high, <= 2500 kg, <= 6000 cost
    # Nodes:
    #   0: (0.0, 0.22) front wheel
    #   1: (-1.0, 0.22) mid-front wheel
    #   2: (-2.0, 0.22) mid-rear wheel
    #   3: (-3.0, 0.22) rear wheel
    #   4: (-0.5, 1.1) top front
    #   5: (-1.5, 1.45) top hammer (carries big ballast!)
    #   6: (-2.5, 1.1) top rear
    #   7: (-1.5, 0.35) hammer base? Wait: if 5 is connected to 1,2 via hydraulics!
    nodes = [
        [0.0, 0.22],
        [-1.0, 0.22],
        [-2.0, 0.22],
        [-3.0, 0.22],
        [-0.5, 0.95],
        [-1.5, 1.45],
        [-2.5, 0.95],
    ]
    wheels = [0, 1, 2, 3]
    # Rigid chassis on wheels 0-1-2-3 + 4-6:
    members = [
        [0, 1, "steel"], [1, 2, "steel"], [2, 3, "steel"],
        [0, 4, "steel"], [1, 4, "steel"], [4, 6, "steel"], [2, 6, "steel"], [3, 6, "steel"],
        [1, 6, "steel"], [2, 4, "steel"],  # X-brace rigid chassis!
    ]
    if use_hyd:
        # Hammer mass 5 suspended by two hydraulics from 4 and 6, plus vertical-ish hydraulics to 1 and 2!
        # Wait: 4(-0.5, 0.95) to 5(-1.5, 1.45) = 1.118m.
        # 1(-1.0, 0.22) to 5(-1.5, 1.45) = 1.328m.
        # If 4-5 & 6-5 are steel (wait: then 5 can't move vertically!).
        # To let 5 slam vertically, make 4-5 and 6-5 hydraulics OR 1-5 and 2-5 hydraulics and 4-5, 6-5 spring/hyd!
        # Even simpler: 5 is guided ONLY by hydraulics 1-5, 2-5, 4-5, 6-5 (all group H)!
        # Wait: at ratio=0.5, 1-5 (1.33->0.66), 2-5 (1.33->0.66), 4-5 (1.12->0.56), 6-5 (1.12->0.56):
        #Wait: if 4-5 and 1-5 BOTH contract to 0.5, 4-1 is fixed (1.0m), so 0.66 + 0.56 = 1.22 > 1.0 (works, pulls 5 DOWN toward y=0.6)!
        # Actually, better: 4(-0.5, 1.1) and 6(-2.5, 1.1), 5(-1.5, 1.45):
        # Put 4-5 and 6-5 as hydraulics (A), and 1-5 and 2-5 as hydraulics (B)!
        # Wait: if A extends (1.1 -> 1.8) while B contracts? No, triangle 1-4-5!
        # Simpler: put 5 at (-1.5, 0.9) and push it DOWN into the bridge? No, 5 is body radius 0.1, y >= 0.1!
        # If 5 slams DOWN to y=0.15, stopping abruptly at y=0.15 transfers momentum through the chassis, OR 5 ITSELF hits the road at y=0.1!
        # Better: drive wheels 1 & 2 DOWNWARD with vertical hydraulics while 5 goes UP, OR drop 5 onto 1 & 2!
        members += [
            [4, 5, "hydraulic", "A"],
            [6, 5, "hydraulic", "A"],
            [1, 5, "hydraulic", "B"],
            [2, 5, "hydraulic", "B"],
        ]
    else:
        members += [[4, 5, "steel"], [6, 5, "steel"], [1, 5, "steel"], [2, 5, "steel"]]

    # Calculate remaining mass for ballast:
    # 4 wheels * 80 = 320 kg, 3 body nodes * 5 = 15 kg, ~14m steel * 35 = 490 kg -> ~825 kg
    ballast = [[5, ballast_kg]] if ballast_kg > 0 else []
    sensors = [
        {"id": "s", "type": "start"},
        {"id": "g1", "type": "mygate", "x": 8.0},
        {"id": "g2", "type": "mygate", "x": 14.0},
        {"id": "g3", "type": "mygate", "x": 20.0},
    ]
    rules = []
    if use_hyd:
        # Cycle: at g1/g2/g3, contract B (pull 5 down hard!) and extend A!
        rules = [
            {"on": "g1", "delay": 0.0, "do": "hyd", "group": "B", "ratio": 0.5, "speed": 3.0, "accel": 5.0},
            {"on": "g1", "delay": 0.0, "do": "hyd", "group": "A", "ratio": 1.3, "speed": 3.0, "accel": 5.0},
            {"on": "g1", "delay": 0.4, "do": "hyd", "group": "B", "ratio": 1.2, "speed": 3.0, "accel": 5.0},
            {"on": "g1", "delay": 0.4, "do": "hyd", "group": "A", "ratio": 0.8, "speed": 3.0, "accel": 5.0},
            {"on": "g2", "delay": 0.0, "do": "hyd", "group": "B", "ratio": 0.5, "speed": 3.0, "accel": 5.0},
            {"on": "g2", "delay": 0.0, "do": "hyd", "group": "A", "ratio": 1.3, "speed": 3.0, "accel": 5.0},
            {"on": "g2", "delay": 0.4, "do": "hyd", "group": "B", "ratio": 1.2, "speed": 3.0, "accel": 5.0},
            {"on": "g2", "delay": 0.4, "do": "hyd", "group": "A", "ratio": 0.8, "speed": 3.0, "accel": 5.0},
            {"on": "g3", "delay": 0.0, "do": "hyd", "group": "B", "ratio": 0.5, "speed": 3.0, "accel": 5.0},
            {"on": "g3", "delay": 0.0, "do": "hyd", "group": "A", "ratio": 1.3, "speed": 3.0, "accel": 5.0},
        ]
    return {
        "nodes": nodes,
        "members": members,
        "wheels": wheels,
        "ballast": ballast,
        "motor": {"speed": 10.0, "accel": 4.0},
        "sensors": sensors,
        "rules": rules,
    }


if __name__ == "__main__":
    lv = B.load_level("final")
    fb = make_final_bridge()
    ok_b, cost_b, pk_b, _ = eval_design("final", fb, quiet=False)
    print(f"Final bridge baseline: ok={ok_b}, cost={cost_b:.0f}/{lv['budget']}, pk={pk_b*100:.1f}%")
    if ok_b:
        with open("submission/final_bridge.json", "w", encoding="utf-8") as f:
            json.dump(fb, f, ensure_ascii=False, indent=1)

    sab = make_sab_pile_driver(True, 1500.0)
    try:
        ps = S.parse_sab(lv, sab)
        print(f"Saboteur valid: mass={ps['mass']:.1f}/2500, cost={ps['cost']:.0f}/6000")
        pb = B.parse_design(lv, fb)
        res, _ = S.duel(lv, pb, ps)
        print(res["text"])
    except B.DesignError as e:
        print("Saboteur DesignError:", e)
