import json
import math
import os
import sys
import copy
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bridge


def eval_design(level_id, design, quiet=True):
    """Validate and run all public scenarios for level_id.
    Returns (ok, cost, max_stress_pct, details_str).
    """
    lv = bridge.load_level(str(level_id))
    try:
        P = bridge.parse_design(lv, design)
    except bridge.DesignError as e:
        return False, 999999.0, 999.0, f"INVALID: {e}"
    cost = P["cost"]
    all_ok = True
    worst_stress = 0.0
    reasons = []
    for sp in bridge.sample_paths(lv):
        sc = bridge.load_json(sp)
        res, _ = bridge.simulate(lv, P, sc, replay=False)
        if not res["ok"]:
            all_ok = False
            reasons.append(f"{os.path.basename(sp)}: {res.get('reason', 'fail')}")
        peaks = res.get("peak_members", [])
        if peaks:
            ms = max(peaks)
            if ms > worst_stress:
                worst_stress = ms
    return all_ok, cost, worst_stress, "; ".join(reasons)


def save_submission(filename, design):
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "submission", filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(design, f, indent=2)
    return path


def make_level1_truss(n_seg=7, arch_y=-1.8, use_bottom_chord=True, mat="wood", deck_y=0.0):
    """Simple under-deck truss/arch for Level 1 (span 0..15, anchors A0=(0,0), A1=(0,-2), A2=(15,0), A3=(15,-2))."""
    nodes = []
    members = []
    dx = 15.0 / n_seg
    # Deck nodes: 0 .. n_seg-2
    for i in range(1, n_seg):
        x = i * dx
        # Slight camber if deck_y != 0
        t = x / 15.0
        y = 4.0 * deck_y * t * (1.0 - t)
        nodes.append([round(x, 3), round(y, 3)])
    # Road members
    for i in range(n_seg):
        u = "A0" if i == 0 else i - 1
        v = "A2" if i == n_seg - 1 else i
        members.append([u, v, "road"])

    # Bottom nodes
    n_bot = n_seg - 1
    bot_start = len(nodes)
    for i in range(1, n_seg):
        x = i * dx
        t = x / 15.0
        # parabolic arch or flat
        y = arch_y * (0.6 + 0.4 * 4.0 * t * (1.0 - t)) if arch_y < 0 else arch_y
        nodes.append([round(x, 3), round(y, 3)])

    # Verticals
    for i in range(n_bot):
        members.append([i, bot_start + i, mat])

    # Bottom chord
    if use_bottom_chord:
        members.append(["A1", bot_start, mat])
        for i in range(n_bot - 1):
            members.append([bot_start + i, bot_start + i + 1, mat])
        members.append([bot_start + n_bot - 1, "A3", mat])

    # Diagonals
    members.append(["A0", bot_start, mat])
    members.append(["A2", bot_start + n_bot - 1, mat])
    for i in range(n_bot - 1):
        if i < (n_bot - 1) // 2:
            members.append([i, bot_start + i + 1, mat])
        else:
            members.append([bot_start + i, i + 1, mat])

    return {"nodes": nodes, "members": members}


if __name__ == "__main__":
    best = None
    for n_seg in [6, 7]:
        for arch_y in [-1.5, -2.0, -2.5, -3.0]:
            for deck_y in [0.0, 0.3, 0.6]:
                d = make_level1_truss(n_seg=n_seg, arch_y=arch_y, deck_y=deck_y)
                ok, cost, stress, msg = eval_design(1, d)
                if ok:
                    print(f"PASS n={n_seg} arch_y={arch_y} deck_y={deck_y} cost={cost:.1f} stress={stress:.2f}")
                    if best is None or cost < best[0]:
                        best = (cost, d)
                else:
                    print(f"FAIL n={n_seg} arch_y={arch_y} deck_y={deck_y} cost={cost:.1f} {msg}")
    if best:
        save_submission("level1.json", best[1])
        print(f"Saved best level1.json with cost {best[0]:.1f}")
