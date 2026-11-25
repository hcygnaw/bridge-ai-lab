#!/usr/bin/env python3
"""Helper utilities for evaluating and optimizing bridge designs."""
import json
import math
import os
import sys

WS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, WS)
import bridge as B
import saboteur as S

SUB_DIR = os.path.join(WS, "submission")
os.makedirs(SUB_DIR, exist_ok=True)


def eval_level(level_id, design, verbose=False):
    """Parse and run all public samples for a level.
    Returns (ok, cost, max_peak, details) or (False, None, None, err_str).
    """
    lv = B.load_level(level_id)
    try:
        P = B.parse_design(lv, design)
    except B.DesignError as e:
        if verbose:
            print(f"[L{level_id}] INVALID: {e}")
        return False, None, None, str(e)

    cost = P["cost"]
    all_ok = True
    max_peak = 0.0
    details = []
    for sp in B.sample_paths(lv):
        sc = B.load_json(sp)
        res, _ = B.simulate(lv, P, sc)
        ok = bool(res["ok"])
        all_ok = all_ok and ok
        # peak stresses on bridge members only
        nm = len(P["members"])
        peaks = res["peak"][:nm]
        mp = max(peaks) if peaks else 0.0
        max_peak = max(max_peak, mp)
        summ = B.summarize(res, P, sc)
        details.append((sc.get("name", os.path.basename(sp)), ok, mp, res, summ["text"]))
        if verbose:
            print(f"[L{level_id}] cost={cost:.1f} | {sc.get('name')}: {'PASS' if ok else 'FAIL'} (peak={mp*100:.1f}%, broken={res['broken']}, anom={res['anomaly']})")
            if not ok:
                print(summ["text"])
    return all_ok, cost, max_peak, details


def save_if_best(level_id, design, filename=None):
    """Evaluate and save to submission/ only if valid, passing, and cheaper than existing."""
    if filename is None:
        filename = f"level{level_id}.json" if level_id != "final" else "final_bridge.json"
    out_path = os.path.join(SUB_DIR, filename)

    ok, cost, mp, details = eval_level(level_id, design, verbose=False)
    if not ok:
        return False, cost, mp, details

    old_cost = float("inf")
    if os.path.isfile(out_path):
        try:
            lv = B.load_level(level_id)
            old_d = B.load_json(out_path)
            old_P = B.parse_design(lv, old_d)
            old_cost = old_P["cost"]
        except Exception:
            old_cost = float("inf")

    if cost < old_cost - 1e-6:
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(design, f, indent=2)
        print(f"*** NEW BEST [L{level_id}]: {cost:.2f} (was {old_cost:.2f}), peak={mp*100:.1f}% -> {filename}")
        return True, cost, mp, details
    return True, cost, mp, details


def make_ribbon(x0, x1, n_seg, sag, a_left, a_right, extra_nodes=None, extra_members=None):
    """Create a parabolic hanging ribbon (sag > 0 -> downward, sag < 0 -> upward arch) of road segments."""
    nodes = []
    for i in range(1, n_seg):
        u = i / n_seg
        x = x0 + u * (x1 - x0)
        y = -4.0 * sag * u * (1.0 - u)
        nodes.append([round(x, 4), round(y, 4)])
    members = []
    for i in range(n_seg):
        p0 = a_left if i == 0 else i - 1
        p1 = a_right if i == n_seg - 1 else i
        members.append([p0, p1, "road"])
    if extra_nodes:
        nodes.extend(extra_nodes)
    if extra_members:
        members.extend(extra_members)
    return {"nodes": nodes, "members": members}
