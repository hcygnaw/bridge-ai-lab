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

def make_l4_bascule_v3(
    hinge_x=8.5,
    gap=0.12,
    tower_h=5.2,
    h_dx=1.0,       # h_post is at hinge_x - h_dx
    h_y=3.2,        # h_post height
    leaf_h=1.2,
    hyd_ratio=0.5,
    open_delay=5.5,
    close_delay=16.2,
    green_delay=18.2,
    light_offset=1.0,
    use_under_truss=False,
    leaf_mat="wood",
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
        members.append([a0, t_mid, "steel"])
        members.append([t_mid, t_top, "steel"])
        members.append([a2, b_mid, "steel" if dist((-4,0), (-2, tower_h*0.5)) > 3.0 else "wood"])
        members.append([b_mid, t_top, "steel" if dist((-2, tower_h*0.5), (0, tower_h)) > 3.0 else "wood"])
        members.append([b_mid, t_mid, "wood"])
        members.append([a0, b_mid, "steel" if dist((0,0), (-2, tower_h*0.5)) > 3.0 else "wood"])
        members.append([a9, t_top, "cable"])

        # Stay cables from t_top to fix_r[1..4]
        for i in range(1, n_fix + 1):
            members.append([t_top, fix_r[i], "cable"])

        if use_under_truss:
            fix_b = []
            for i in range(n_fix):
                lx = hinge_x * (i + 0.5) / n_fix
                fix_b.append(add_node(wx(lx), -1.6))
            for i in range(n_fix):
                members.append([fix_r[i], fix_b[i], "wood"])
                members.append([fix_r[i+1], fix_b[i], "wood"])
                if i + 1 < n_fix:
                    members.append([fix_b[i], fix_b[i+1], "wood"])
            members.append([a1, fix_b[0], "wood"])

        # Hydraulic anchor post at (hinge_x - h_dx, h_y), braced to fix_r[3], fix_r[4], and cable to t_top
        h_lx = hinge_x - h_dx
        h_post = add_node(wx(h_lx), h_y)
        for r_idx in [fix_r[3], fix_r[4]]:
            L = dist(nodes[r_idx], nodes[h_post])
            members.append([r_idx, h_post, "steel"])
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
        {"on": "h", "delay": green_delay, "do": "light", "light": "L", "state": "green"},
        {"on": "h", "delay": green_delay, "do": "light", "light": "R", "state": "green"},
    ]
    return {
        "nodes": nodes,
        "members": members,
        "sensors": sensors,
        "lights": lights,
        "rules": rules,
    }

print("=== LEVEL 4 BASCULE V3 TEST ===", flush=True)
best4 = None
for uut in [False, True]:
    for h_dx in [0.5, 1.0, 1.5]:
        for h_y in [2.8, 3.3]:
            for lh in [1.0, 1.4]:
                for lm in ["wood", "steel"]:
                    d = make_l4_bascule_v3(8.5, 0.12, 5.2, h_dx, h_y, lh, 0.5, 5.5, 16.2, 18.2, 1.0, uut, lm)
                    ok, cost, pk, msgs = eval_design(4, d)
                    if ok:
                        if best4 is None or cost < best4[0]:
                            best4 = (cost, d)
                            print(f"NEW BEST L4: {cost:.1f} (uut={uut} dx={h_dx} hy={h_y} lh={lh} {lm}) pk={pk*100:.1f}%", flush=True)
                            save_if_better(4, d, SUB / "level4.json")

if best4:
    print("\n=== BEST L4 ===")
    eval_design(4, best4[1], verbose=True)
else:
    print("No pass yet, printing diagnostic:")
    d = make_l4_bascule_v3(8.5, 0.12, 5.2, 0.5, 3.3, 1.0, 0.5, 5.5, 16.2, 18.2, 1.0, True, "steel")
    eval_design(4, d, verbose=True)
