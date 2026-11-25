import json
import math
import os
import sys

import bridge as B


def eval_design(level_id, design, quiet=True):
    """Validate and simulate design on all official scenarios of level_id.
    Returns (ok, cost, max_peak, details_list).
    """
    lv = B.load_level(level_id)
    try:
        P = B.parse_design(lv, design)
    except B.DesignError as e:
        if not quiet:
            print(f"L{level_id} DesignError: {e}")
        return False, float("inf"), float("inf"), [str(e)]

    samples = B.sample_paths(lv)
    all_ok = True
    max_peak = 0.0
    details = []
    for sp in samples:
        sc = B.load_json(sp)
        res, _ = B.simulate(lv, P, sc, replay=False)
        ok = bool(res.get("ok"))
        all_ok = all_ok and ok
        pk = max(res.get("peak_members", [0.0]) or [0.0])
        if pk > max_peak:
            max_peak = pk
        details.append((os.path.basename(sp), ok, res.get("anomaly", 0), res.get("shiphit", False), res.get("broken", 0), pk))
        if not quiet:
            print(f"  [{ 'PASS' if ok else 'FAIL' }] {os.path.basename(sp)} peak={pk*100:.1f}% broken={res.get('broken',0)}")
            if not ok:
                print(B.summarize(res, P, sc)["text"])
    return all_ok, P["cost"], max_peak, details


def save_if_best(level_id, design, sub_dir="submission"):
    ok, cost, max_peak, details = eval_design(level_id, design, quiet=True)
    if not ok:
        return False, cost, max_peak
    os.makedirs(sub_dir, exist_ok=True)
    fn = "final_bridge.json" if str(level_id) == "final" else f"level{level_id}.json"
    path = os.path.join(sub_dir, fn)
    if os.path.exists(path):
        try:
            old = B.load_json(path)
            old_ok, old_cost, _, _ = eval_design(level_id, old, quiet=True)
            if old_ok and old_cost <= cost + 1e-6:
                return True, old_cost, max_peak
        except Exception:
            pass
    with open(path, "w", encoding="utf-8") as f:
        json.dump(design, f, ensure_ascii=False, indent=1)
    print(f"Saved NEW BEST for L{level_id}: cost={cost:.2f}, max_peak={max_peak*100:.1f}% -> {path}")
    return True, cost, max_peak
