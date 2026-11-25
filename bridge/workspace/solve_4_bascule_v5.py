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

def make_l4_bascule_v5(
    hinge_x=8.5,
    gap=0.14,
    tower_h=5.2,
    leaf_h=2.0,
    hyd_ratio=0.5,
    open_delay=5.5,
    close_delay=16.2,
    green_l_delay=18.0,
    green_r_delay=23.0,
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

        # Stay cables from t_top to fix_r[2..4]
        for i in range(2, n_fix + 1):
            members.append([t_top, fix_r[i], "cable"])

        # Wood under-truss on fixed span so fix_r[2] can't lift up!
        a1 = "A1" if is_left else "A4"
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

        # Leaf: hinged at fix_r[4] (lx = hinge_x)
        tip_lx = 12.0 - gap / 2.0
        mid_lx = 0.5 * (hinge_x + tip_lx)
        l_mid = add_node(wx(mid_lx), 0.0)
        l_tip = add_node(wx(tip_lx), 0.0)
        members.append([fix_r[4], l_mid, "road"])
        members.append([l_mid, l_tip, "road"])

        # Rigidifying L-bracket on leaf: l_top directly above hinge at (hinge_x, leaf_h)!
        # Connected to fix_r[4] (hinge), l_mid, and l_tip (steel if > 3m)
        l_top = add_node(wx(hinge_x), leaf_h)
        members.append([fix_r[4], l_top, leaf_mat if leaf_h <= 3.0 else "steel"])
        L_mid = dist((hinge_x, leaf_h), (mid_lx, 0.0))
        L_tip = dist((hinge_x, leaf_h), (tip_lx, 0.0))
        members.append([l_mid, l_top, leaf_mat if L_mid <= 3.0 else "steel"])
        members.append([l_tip, l_top, "steel" if L_tip > 3.0 else leaf_mat])

        # Hydraulic directly from fix_r[2] (lx = hinge_x/2) to l_top (hinge_x, leaf_h)!
        members.append([fix_r[2], l_top, "hydraulic", "A"])

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

print("=== LEVEL 4 BASCULE V5 TEST ===", flush=True)
best4 = None
for hinge_x in [8.4, 8.6]:
    for leaf_h in [1.8, 2.0, 2.2]:
        for hr in [0.5, 0.52]:
            for lm in ["wood", "steel"]:
                d = make_l4_bascule_v5(hinge_x, 0.14, 5.2, leaf_h, hr, 5.5, 16.2, 18.0, 23.0, 1.0, lm, "steel")
                ok, cost, pk, msgs = eval_design(4, d)
                if ok:
                    if best4 is None or cost < best4[0]:
                        best4 = (cost, d)
                        print(f"NEW BEST L4: {cost:.1f} (hinge={hinge_x} lh={leaf_h} hr={hr} {lm}) pk={pk*100:.1f}%", flush=True)
                        save_if_better(4, d, SUB / "level4.json")

if best4:
    print("\n=== BEST L4 ===")
    eval_design(4, best4[1], verbose=True)
else:
    d = make_l4_bascule_v5(8.4, 0.14, 5.2, 2.0, 0.5, 5.5, 16.2, 18.0, 23.0, 1.0, "wood", "steel")
    eval_design(4, d, verbose=True)
