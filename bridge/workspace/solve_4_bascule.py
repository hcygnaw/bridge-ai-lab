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

def make_l4_bascule(
    hinge_x=8.7,
    gap=0.14,
    tower_h=2.5,
    leaf_h=1.2,
    hyd_ratio=0.5,
    open_delay=4.5,
    close_delay=16.5,
    green_delay=18.5,
    light_offset=1.0,
    fixed_mat="wood",
    tower_mat="wood",
):
    # Left bank A0=(0,0), A1=(0,-2), A2=(-4,0)
    # Right bank A3=(24,0), A4=(24,-2), A5=(28,0)
    # Fixed left span: 0 -> hinge_x (4 road segments, e.g. 8.7/4 = 2.175m each)
    # Left leaf: hinge_x -> 12 - gap/2 (2 road segments, ~1.615m each)
    # Right leaf: 12 + gap/2 -> 24 - hinge_x
    # Fixed right span: 24 - hinge_x -> 24
    nodes = []
    members = []

    def add_node(x, y):
        idx = len(nodes)
        nodes.append([round(x, 4), round(y, 4)])
        return idx

    def build_half(is_left):
        # x_map: maps local x in [0, 12] to world x
        def wx(lx):
            return lx if is_left else 24.0 - lx

        a0 = "A0" if is_left else "A3"
        a1 = "A1" if is_left else "A4"
        a2 = "A2" if is_left else "A5"

        # Fixed span road nodes: 4 segments from 0 to hinge_x
        n_fix = 4
        fix_r = [a0]
        for i in range(1, n_fix + 1):
            fix_r.append(add_node(wx(hinge_x * i / n_fix), 0.0))
        for i in range(n_fix):
            members.append([fix_r[i], fix_r[i+1], "road"])

        # Fixed span inverted Warren truss underneath (y = -1.6)
        fix_b = []
        for i in range(n_fix):
            lx = hinge_x * (i + 0.5) / n_fix
            fix_b.append(add_node(wx(lx), -1.6))
        for i in range(n_fix):
            members.append([fix_r[i], fix_b[i], fixed_mat])
            members.append([fix_r[i+1], fix_b[i], fixed_mat])
            if i + 1 < n_fix:
                members.append([fix_b[i], fix_b[i+1], fixed_mat])
        members.append([a1, fix_b[0], fixed_mat])

        # Backstay / cantilever support for fixed span so hinge doesn't sag!
        # Put a small tower above fix_r[n_fix-1] (at lx = 0.75 * hinge_x ≈ 6.525)
        # Wait: even better, put tower node at (hinge_x - 2.0, tower_h) braced to fix_r[n_fix-2], fix_r[n_fix-1], fix_r[n_fix]
        # AND cable back to a2 = (-4, 0) / (28, 0)!
        t_lx = hinge_x - 2.1
        t_node = add_node(wx(t_lx), tower_h)
        # Connect tower node to fix_r[2], fix_r[3], fix_r[4] (hinge)
        for r_idx in [fix_r[2], fix_r[3], fix_r[4]]:
            p_r = (0.0 if is_left else 24.0, 0.0) if isinstance(r_idx, str) else nodes[r_idx]
            L = dist(p_r, nodes[t_node])
            m = tower_mat if L <= 3.0 else "steel"
            members.append([r_idx, t_node, m])
        # Cable backstay to a2!
        members.append([a2, t_node, "cable"])

        # Leaf: hinged at fix_r[4] (lx = hinge_x)
        tip_lx = 12.0 - gap / 2.0
        mid_lx = 0.5 * (hinge_x + tip_lx)
        l_mid = add_node(wx(mid_lx), 0.0)
        l_tip = add_node(wx(tip_lx), 0.0)
        members.append([fix_r[4], l_mid, "road"])
        members.append([l_mid, l_tip, "road"])

        # Rigidifying upper triangle on leaf: peak at (mid_lx, leaf_h)
        l_top = add_node(wx(mid_lx), leaf_h)
        members.append([fix_r[4], l_top, "wood"])
        members.append([l_mid, l_top, "wood"])
        members.append([l_tip, l_top, "wood"])

        # Hydraulic from t_node to l_top!
        # Check length: dx = mid_lx - t_lx ≈ 10.3 - 6.6 = 3.7m, dy = leaf_h - tower_h ≈ -1.3m -> L ≈ 3.9m <= 5.0m!
        members.append([t_node, l_top, "hydraulic", "A"])

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

print("=== LEVEL 4 BASCULE TEST ===", flush=True)
best4 = None
for th in [2.2, 2.6, 3.0]:
    for lh in [1.0, 1.3]:
        for hr in [0.5, 0.55]:
            for od in [4.0, 5.0]:
                d = make_l4_bascule(8.7, 0.14, th, lh, hr, od, 16.3, 18.2, 1.0)
                ok, cost, pk, msgs = eval_design(4, d)
                if ok:
                    if best4 is None or cost < best4[0]:
                        best4 = (cost, d)
                        print(f"NEW BEST L4: {cost:.1f} (th={th} lh={lh} hr={hr} od={od}) pk={pk*100:.1f}%", flush=True)
                        save_if_better(4, d, SUB / "level4.json")
                elif th == 2.6 and lh == 1.3 and hr == 0.5 and od == 5.0:
                    print("Sample fail:", msgs)

if best4:
    print("\n=== BEST L4 ===")
    eval_design(4, best4[1], verbose=True)
