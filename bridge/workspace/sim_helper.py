#!/usr/bin/env python3
"""Helper utilities for evaluating, optimizing, and safely saving bridge designs."""
import json
import math
import os
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import bridge as B
import saboteur as S

SUB_DIR = os.path.join(HERE, 'submission')
os.makedirs(SUB_DIR, exist_ok=True)

_LEVEL_CACHE = {}


def get_level_and_samples(level_id):
    key = str(level_id)
    if key not in _LEVEL_CACHE:
        lv = B.load_level(key)
        samples = [( os.path.basename(p), B.load_json(p) ) for p in B.sample_paths(lv)]
        _LEVEL_CACHE[key] = (lv, samples)
    return _LEVEL_CACHE[key]


def round_design(d, ndigits=3):
    """Round node coordinates cleanly to avoid ugly float representations and keep JSON compact."""
    out = dict(d)
    if 'nodes' in out:
        out['nodes'] = [[round(float(x), ndigits), round(float(y), ndigits)] for x, y in out['nodes']]
    return out


def evaluate_design(level_id, design_dict, stop_on_fail=True, no_archive=True):
    """Evaluate a design on all official scenarios of level_id.
    Returns dict(valid, ok, cost, max_peak, broken_total, details, err).
    """
    lv, samples = get_level_and_samples(level_id)
    try:
        P = B.parse_design(lv, design_dict)
    except B.DesignError as e:
        return dict(valid=False, ok=False, cost=1e18, max_peak=99.0, broken_total=999, details=[], err=str(e))

    prev_env = os.environ.get('BRIDGE_NO_ARCHIVE')
    if no_archive:
        os.environ['BRIDGE_NO_ARCHIVE'] = '1'
    try:
        all_ok = True
        max_peak = 0.0
        broken_total = 0
        details = []
        for sname, sc in samples:
            res, _ = B.simulate(lv, P, sc, replay=False)
            ok = bool(res.get('ok'))
            pk = max(res.get('peak_members', [0.0]) or [0.0])
            br = res.get('bridge_broken', 0)
            max_peak = max(max_peak, pk)
            broken_total += br
            details.append((sname, ok, pk, br, res))
            if not ok:
                all_ok = False
                if stop_on_fail:
                    break
        return dict(valid=True, ok=all_ok, cost=P['cost'], max_peak=max_peak,
                    broken_total=broken_total, details=details, err='')
    finally:
        if no_archive:
            if prev_env is None:
                os.environ.pop('BRIDGE_NO_ARCHIVE', None)
            else:
                os.environ['BRIDGE_NO_ARCHIVE'] = prev_env


def current_best_cost(level_id):
    fname = 'final_bridge.json' if str(level_id) == 'final' else f'level{level_id}.json'
    fpath = os.path.join(SUB_DIR, fname)
    if not os.path.isfile(fpath):
        return None
    lv, _ = get_level_and_samples(level_id)
    try:
        P = B.parse_design(lv, B.load_json(fpath))
        return P['cost']
    except Exception:
        return None


def verify_and_save(level_id, design_dict, force=False):
    """Run official `python3 bridge.py run <level> <tmp>` (with archive ON!) and only overwrite
    submission/level<N>.json if all scenarios pass AND (force or cost < current_best_cost).
    """
    design_dict = round_design(design_dict, 3)
    fname = 'final_bridge.json' if str(level_id) == 'final' else f'level{level_id}.json'
    target = os.path.join(SUB_DIR, fname)
    tmp_cand = os.path.join(HERE, f'_cand_{fname}')
    with open(tmp_cand, 'w', encoding='utf-8') as f:
        json.dump(design_dict, f, ensure_ascii=False, indent=2)

    lv, _ = get_level_and_samples(level_id)
    try:
        P = B.parse_design(lv, B.load_json(tmp_cand))
    except B.DesignError as e:
        print(f'[REJECT L{level_id}] Invalid design: {e}')
        if os.path.exists(tmp_cand):
            os.remove(tmp_cand)
        return False

    best = current_best_cost(level_id)
    if not force and best is not None and P['cost'] >= best - 1e-6:
        print(f'[SKIP L{level_id}] Cost {P["cost"]:.2f} >= current best {best:.2f}')
        if os.path.exists(tmp_cand):
            os.remove(tmp_cand)
        return False

    env = dict(os.environ)
    env.pop('BRIDGE_NO_ARCHIVE', None)
    r = subprocess.run([sys.executable, os.path.join(HERE, 'bridge.py'), 'run', str(level_id), tmp_cand],
                       cwd=HERE, env=env, capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        print(f'[FAIL L{level_id}] Official run failed (rc={r.returncode}):\n{r.stdout}\n{r.stderr}')
        if os.path.exists(tmp_cand):
            os.remove(tmp_cand)
        return False

    shutil.move(tmp_cand, target)
    prev_str = f' (was {best:.2f})' if best is not None else ' (initial pass)'
    print(f'[SAVED L{level_id}] {target} -> Cost {P["cost"]:.2f}{prev_str}')
    return True
