import copy
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bridge


def optimize_level(level_id, allow_delete=True):
    path = f"submission/level{level_id}.json"
    lv = bridge.load_level(str(level_id))
    scenarios = [bridge.load_json(p) for p in bridge.sample_paths(lv)]
    d = bridge.load_json(path)
    P = bridge.parse_design(lv, d)
    print(f"=== Level {level_id} start cost: {P['cost']:.1f} ===")

    def is_ok(cand):
        try:
            Pc = bridge.parse_design(lv, cand)
        except bridge.DesignError:
            return False, float("inf")
        if Pc["cost"] >= P["cost"] - 0.5:
            return False, Pc["cost"]
        for sc in scenarios:
            res, _ = bridge.simulate(lv, Pc, sc, replay=False)
            if not res["ok"]:
                return False, Pc["cost"]
        return True, Pc["cost"]

    changed = True
    while changed:
        changed = False
        # 1. Try downgrading steel -> wood / cable, cable -> wood
        for i in range(len(d["members"])):
            mat = d["members"][i][2]
            if mat in ("road", "hydraulic", "spring"):
                continue
            tries = ["wood", "cable"] if mat == "steel" else (["wood"] if mat == "cable" else [])
            for nm in tries:
                cand = copy.deepcopy(d)
                cand["members"][i][2] = nm
                ok, nc = is_ok(cand)
                if ok:
                    d = cand
                    P = bridge.parse_design(lv, d)
                    print(f"  L{level_id} downgrade [{i}] {mat}->{nm}: {nc:.1f}")
                    changed = True
                    break

        # 2. Try deleting non-road, non-hydraulic members
        if allow_delete:
            i = 0
            while i < len(d["members"]):
                mat = d["members"][i][2]
                if mat in ("road", "hydraulic"):
                    i += 1
                    continue
                cand = copy.deepcopy(d)
                cand["members"].pop(i)
                # Note: if sensors reference member index, skip if plate exists
                if any(s.get("type") == "plate" for s in cand.get("sensors", [])):
                    i += 1
                    continue
                ok, nc = is_ok(cand)
                if ok:
                    d = cand
                    P = bridge.parse_design(lv, d)
                    print(f"  L{level_id} delete [{i}] ({mat}): {nc:.1f}")
                    changed = True
                else:
                    i += 1

    with open(path, "w") as f:
        json.dump(d, f, indent=2)
    print(f"=== Level {level_id} final cost: {P['cost']:.1f} ===")


for lid in [1, 2, 3, 4]:
    optimize_level(lid)
