import json
import math
import os
import sys
import copy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bridge
from opt_helper import eval_design, save_submission


def auto_upgrade_to_pass(level_id, design, max_iters=25):
    """Iteratively upgrade breaking wood members to steel until all scenarios pass."""
    d = copy.deepcopy(design)
    lv = bridge.load_level(str(level_id))
    samples = [bridge.load_json(sp) for sp in bridge.sample_paths(lv)]

    for it in range(max_iters):
        try:
            P = bridge.parse_design(lv, d)
        except bridge.DesignError as e:
            return False, 999999.0, d, f"INVALID: {e}"
        all_ok = True
        to_upgrade = set()
        for sc in samples:
            res, _ = bridge.simulate(lv, P, sc, replay=False)
            if not res["ok"]:
                all_ok = False
                # Find first 2 broken wood members
                nb = len(d["members"])
                broken = []
                for ev in res["events"]:
                    parts = ev.split()
                    if len(parts) >= 3 and parts[1] == "BREAK":
                        mi = int(parts[2])
                        if mi < nb and d["members"][mi][2] == "wood":
                            broken.append(mi)
                            if len(broken) >= 2:
                                break
                to_upgrade.update(broken)
        if all_ok:
            return True, P["cost"], d, f"PASS in {it} upgrades"
        if not to_upgrade:
            return False, P["cost"], d, "FAIL (no wood member broke first)"
        for mi in to_upgrade:
            d["members"][mi][2] = "steel"
    return False, 999999.0, d, "MAX ITERS"


def make_l2_truss(n_seg=14, bot_y=-2.2, use_cables=True):
    """Under-deck Warren truss + braced 2-segment towers with cables for Level 2 (0..30)."""
    nodes = []
    members = []
    dx = 30.0 / n_seg
    for i in range(1, n_seg):
        nodes.append([round(i * dx, 3), 0.0])
    for i in range(n_seg):
        u = "A0" if i == 0 else i - 1
        v = "A4" if i == n_seg - 1 else i
        members.append([u, v, "road"])

    bot_start = len(nodes)
    for i in range(n_seg):
        x = (i + 0.5) * dx
        nodes.append([round(x, 3), round(bot_y, 3)])

    for i in range(n_seg - 1):
        members.append([bot_start + i, bot_start + i + 1, "wood"])
    for i in range(n_seg):
        dl = "A0" if i == 0 else i - 1
        dr = "A4" if i == n_seg - 1 else i
        members.append([bot_start + i, dl, "wood"])
        members.append([bot_start + i, dr, "wood"])

    # End struts to A1=(0,-4) and A5=(30,-4)
    members.append(["A1", bot_start, "steel"])
    members.append(["A5", bot_start + n_seg - 1, "steel"])

    if use_cables:
        # 2-segment A-frame towers at x=0 and x=30 (height 5.5m, mid-brace at y=2.75)
        tl1 = len(nodes); nodes.append([0.0, 2.75])
        tl2 = len(nodes); nodes.append([0.0, 5.5])
        tr1 = len(nodes); nodes.append([30.0, 2.75])
        tr2 = len(nodes); nodes.append([30.0, 5.5])
        members.append(["A0", tl1, "steel"])
        members.append([tl1, tl2, "steel"])
        members.append(["A3", tl1, "cable"])
        members.append(["A3", tl2, "cable"])
        members.append(["A4", tr1, "steel"])
        members.append([tr1, tr2, "steel"])
        members.append(["A7", tr1, "cable"])
        members.append(["A7", tr2, "cable"])
        # Cables to deck
        for i in [2, 4, 6]:
            members.append([tl2, i, "cable"])
        for i in [n_seg - 4, n_seg - 6, n_seg - 8]:
            if i >= 0 and i < n_seg - 1:
                members.append([tr2, i, "cable"])

    return {"nodes": nodes, "members": members}


if __name__ == "__main__":
    import solve_l2_l3_v2 as s
    print("=== LEVEL 2 ===")
    d2 = make_l2_truss(n_seg=14, bot_y=-2.0, use_cables=True)
    ok, cost, d2_out, msg = auto_upgrade_to_pass(2, d2)
    print(f"L2: {ok} cost={cost:.1f} {msg}")
    if ok:
        save_submission("level2.json", d2_out)

    print("=== LEVEL 3 ===")
    d3 = s.make_l3_pier_truss(n_half=6, bot_y=-1.8)
    ok, cost, d3_out, msg = auto_upgrade_to_pass(3, d3)
    print(f"L3: {ok} cost={cost:.1f} {msg}")
    if ok:
        save_submission("level3.json", d3_out)
