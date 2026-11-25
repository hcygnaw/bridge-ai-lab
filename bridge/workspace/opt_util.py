import json, math, os, sys
from pathlib import Path

WS = Path(__file__).resolve().parent
sys.path.insert(0, str(WS))
import bridge

def eval_design(level_id, design, verbose=False):
    lv = bridge.load_level(str(level_id))
    try:
        P = bridge.parse_design(lv, design)
    except Exception as e:
        if verbose:
            print(f"INVALID: {e}")
        return False, None, 0.0, [str(e)]
    cost = P['cost']
    samples = bridge.sample_paths(lv)
    all_ok = True
    max_ratio = 0.0
    msgs = []
    for sp in samples:
        sc = bridge.load_json(sp)
        res, _ = bridge.simulate(lv, P, sc, replay=False)
        ok = bool(res.get('ok'))
        pk = max((r for r in res.get('peak_members', []) if r is not None), default=0.0)
        if pk > max_ratio:
            max_ratio = pk
        if not ok:
            all_ok = False
            msgs.append(f"{Path(sp).name}: {bridge.summarize(res, P, sc)} (peak={pk*100:.1f}%)")
        else:
            msgs.append(f"{Path(sp).name}: PASS (peak={pk*100:.1f}%)")
    if verbose:
        print(f"Level {level_id} | cost={cost:.1f}/{lv['budget']} | {'PASS' if all_ok else 'FAIL'} | max_peak={max_ratio*100:.1f}%")
        for m in msgs:
            print("  ", m)
    return all_ok, cost, max_ratio, msgs

def save_if_better(level_id, design, out_path):
    out_path = Path(out_path)
    ok, cost, pk, msgs = eval_design(level_id, design, verbose=False)
    if not ok:
        return False, cost, pk, msgs
    if out_path.exists():
        try:
            old = json.loads(out_path.read_text(encoding='utf-8'))
            old_ok, old_cost, _, _ = eval_design(level_id, old, verbose=False)
            if old_ok and old_cost is not None and old_cost <= cost + 1e-6:
                return False, cost, pk, msgs
        except Exception:
            pass
    out_path.write_text(json.dumps(design, separators=(',', ':')), encoding='utf-8')
    return True, cost, pk, msgs
