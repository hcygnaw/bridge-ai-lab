import json, math, sys
from pathlib import Path

WS = Path(__file__).resolve().parent
sys.path.insert(0, str(WS))
import bridge
from opt_util import eval_design, save_if_better

SUB = WS / "submission"
SUB.mkdir(exist_ok=True)

def dist(a, b):
    return math.hypot(a[0]-b[0], a[1]-b[1])

def make_l4_bascule_v4(
    hinge_x=8.5,
    gap=0.14,
    tower_h=5.2,
    h_x=6.8,
    h_y=3.6,
    leaf_h=1.2,
    hyd_ratio=0.5,
    open_delay=5.5,
    close_delay=16.2,
    green_l_delay=18.0,
    green_r_delay=22.5,
    light_offset=1.0,
    leaf_mat="wood",
    tower_mat="steel",
):
    nodes = []
    members = []

    def add_node(x, y):
        idx = len(nodes)
        nodes.append([round(x, 4), round(y, 4)])
        return idx

    def build_half(is_left):
        def wx(lx):
            return lx if is_left else 24.0 - lx

        a0 = "A0" if is_left else "A3"
        a1 = "A1" if is_left else "A4"
        a2 = "A2" if is_left else "A5"
        a9 = "A9" if is_left else "A12"

        # Fixed span road: 4 segments from 0 to hinge_x
        n_fix = 4
        fix_r = [a0]
        for i in range(1, n_fix + 1):
            fix_r.append(add_node(wx(hinge_x * i / n_fix), 0.0))
        for i in range(n_fix):
            members.append([fix_r[i], fix_r[i+1], "road"])

        # Main tower at x=0 (two tiers)
        t_mid = add_node(wx(0.0), tower_h * 0.5)
        t_top = add_node(wx(0.0), tower_h)
        b_mid = add_node(wx(-2.0), tower_h * 0.5)
        members.append([a0, t_mid, tower_mat])
        members.append([t_mid, t_top, tower_mat])
        members.append([a2, b_mid, "steel" if dist((-4,0), (-2, tower_h*0.5)) > 3.0 else "wood"])
        members.append([b_mid, t_top, "steel" if dist((-2, tower_h*0.5), (0, tower_h)) > 3.0 else "wood"])
        members.append([b_mid, t_mid, "wood"])
        members.append([a0, b_mid, "steel" if dist((0,0), (-2, tower_h*0.5)) > 3.0 else "wood"])
        members.append([a9, t_top, "cable"])

        # Stay cables from t_top to fix_r[1..4]
        for i in range(1, n_fix + 1):
            members.append([t_top, fix_r[i], "cable"])

        # Hydraulic anchor post at (h_x, h_y), braced to fix_r[2], fix_r[3], fix_r[4], and cable to t_top
        h_post = add_node(wx(h_x), h_y)
        for r_idx in [fix_r[3], fix_r[4]]:
            L = dist(nodes[r_idx], nodes[h_post])
            members.append([r_idx, h_post, "steel" if L > 3.0 else "wood"])
        members.append([t_top, h_post, "cable"])

        # Leaf: hinged at fix_r[4] (lx = hinge_x)
        tip_lx = 12.0 - gap / 2.0
        mid_lx = 0.5 * (hinge_x + tip_lx)
        l_mid = add_node(wx(mid_lx), 0.0)
        l_tip = add_node(wx(tip_lx), 0.0)
        members.append([fix_r[4], l_mid, "road"])
        members.append([l_mid, l_tip, "road"])

        # Leaf upper triangle: peak at (mid_lx, leaf_h)
        l_top = add_node(wx(mid_lx), leaf_h)
        members.append([fix_r[4], l_top, leaf_mat])
        members.append([l_mid, l_top, leaf_mat])
        members.append([l_tip, l_top, leaf_mat])

        # Hydraulic from h_post to l_top
        members.append([h_post, l_top, "hydraulic", "A"])

    build_half(True)
    build_half(False)

    sensors = [{"id": "h", "type": "horn"}]
    lights = [
        {"id": "L", "x": -light_offset, "dir": "right", "init": "green"},
        {"id": "R", "x": 24.0 + light_offset, "dir": "left", "init": "green"},
    ]
    rules = [
        {"on": "h", "delay": 0.0, "do": "light", "light": "L", "state": "red"},
        {"on": "h", "delay": 0.0, "do": "light", "light": "R", "state": "red"},
        {"on": "h", "delay": open_delay, "do": "hyd", "group": "A", "ratio": hyd_ratio, "speed": 2.5},
        {"on": "h", "delay": close_delay, "do": "hyd", "group": "A", "ratio": 1.0, "speed": 2.5},
        {"on": "h", "delay": green_l_delay, "do": "light", "light": "L", "state": "green"},
        {"on": "h", "delay": green_r_delay, "do": "light", "light": "R", "state": "green"},
    ]
    return {
        "nodes": nodes,
        "members": members,
        "sensors": sensors,
        "lights": lights,
        "rules": rules,
    }

print("=== LEVEL 4 BASCULE V4 TEST ===", flush=True)
best4 = None
for h_x in [6.4, 6.8, 7.2]:
    for h_y in [3.2, 3.6, 4.0]:
        for lh in [1.1, 1.3]:
            for lm in ["wood", "steel"]:
                d = make_l4_bascule_v4(8.5, 0.14, 5.2, h_x, h_y, lh, 0.5, 5.5, 16.2, 18.0, 23.0, 1.0, lm, "steel")
                ok, cost, pk, msgs = eval_design(4, d)
                if ok:
                    if best4 is None or cost < best4[0]:
                        best4 = (cost, d)
                        print(f"NEW BEST L4: {cost:.1f} (hx={h_x} hy={h_y} lh={lh} {lm}) pk={pk*100:.1f}%", flush=True)
                        save_if_better(4, d, SUB / "level4.json")

if best4:
    print("\n=== BEST L4 ===")
    eval_design(4, best4[1], verbose=True)
else:
    d = make_l4_bascule_v4(8.5, 0.14, 5.2, 6.8, 3.6, 1.2, 0.5, 5.5, 16.2, 18.0, 23.0, 1.0, "wood", "steel")
    eval_design(4, d, verbose=True)
