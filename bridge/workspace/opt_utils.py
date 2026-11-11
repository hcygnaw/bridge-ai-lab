#!/usr/bin/env python3
"""Helper utilities for testing, optimizing, and safely saving best passing designs."""
import json
import math
import os
import sys

WORKSPACE = os.path.dirname(os.path.abspath(__file__))
os.chdir(WORKSPACE)
if WORKSPACE not in sys.path:
    sys.path.insert(0, WORKSPACE)

import bridge as B
import saboteur as S

SUB_DIR = os.path.join(WORKSPACE, 'submission')
os.makedirs(SUB_DIR, exist_ok=True)


def eval_bridge(level_id, design, verbose=False):
    """Evaluate a bridge design on all official scenarios of level_id.
    Returns (passed_all, cost, max_peak, details_list).
    """
    lv = B.load_level(level_id)
    try:
        P = B.parse_design(lv, design)
    except B.DesignError as e:
        if verbose:
            print(f"[L{level_id}] INVALID: {e}")
        return False, float('inf'), float('inf'), [str(e)]

    scen_paths = B.sample_paths(lv)
    all_ok = True
    max_peak = 0.0
    details = []
    for sp in scen_paths:
        sc = B.load_json(sp)
        res, _ = B.simulate(lv, P, sc, replay=False)
        ok = bool(res.get('ok'))
        pk = max(res.get('peak_members', [0.0]) or [0.0])
        if pk > max_peak:
            max_peak = pk
        sm = B.summarize(res, P, sc)
        details.append((os.path.basename(sp), ok, pk, sm['text']))
        if not ok:
            all_ok = False
    if verbose:
        status = "PASS" if all_ok else "FAIL"
        print(f"[L{level_id}] {status} | cost={P['cost']:.2f}/{lv['budget']} | max_peak={max_peak*100:.1f}%")
        for name, ok, pk, txt in details:
            print(f"  - {name}: {'OK' if ok else 'FAIL'} (peak {pk*100:.1f}%)")
            if not ok:
                for line in txt.splitlines():
                    print("   ", line)
    return all_ok, P['cost'], max_peak, details


def save_if_best(level_id, design, verbose=True):
    """Verify design on all official scenarios and save to submission/ if valid, passing, and cheaper."""
    ok, cost, max_peak, details = eval_bridge(level_id, design, verbose=verbose)
    if not ok:
        return False, cost

    fname = 'final_bridge.json' if str(level_id) == 'final' else f'level{level_id}.json'
    fpath = os.path.join(SUB_DIR, fname)
    old_cost = float('inf')
    if os.path.isfile(fpath):
        try:
            old_ok, c, _, _ = eval_bridge(level_id, B.load_json(fpath), verbose=False)
            if old_ok:
                old_cost = c
        except Exception:
            pass

    if str(level_id) == 'final' or cost < old_cost - 1e-6 or not os.path.isfile(fpath):
        with open(fpath, 'w', encoding='utf-8') as f:
            json.dump(design, f, ensure_ascii=False, indent=1)
        print(f"*** SAVED {fname}: cost={cost:.2f} (prev={old_cost}) max_peak={max_peak*100:.1f}% ***")
        return True, cost
    return False, old_cost
