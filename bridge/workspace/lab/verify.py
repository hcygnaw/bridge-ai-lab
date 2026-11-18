"""Recheck the submitted files with the unmodified contestant simulator."""
import json
import os
from pathlib import Path
import sys

WORKSPACE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKSPACE))
import bridge
import saboteur


def verify():
    os.chdir(WORKSPACE)
    report = {}
    success = True
    for level in (*range(1, 7), "final"):
        filename = "final_bridge.json" if level == "final" else f"level{level}.json"
        lv = bridge.load_level(level)
        design = bridge.parse_design(lv, bridge.load_json(Path("submission") / filename))
        samples = []
        for path in bridge.sample_paths(lv):
            res, _ = bridge.simulate(lv, design, bridge.load_json(path))
            samples.append({
                "sample": Path(path).stem,
                "ok": res["ok"],
                "arrivals": [v["t"] if v["status"] == 2 else None for v in res["vehicles"]],
                "bridge_breaks": res["bridge_broken"],
                "anomaly": res["anomaly"],
                "ship_hit": res["shiphit"],
            })
            success = success and res["ok"]
        report[str(level)] = {"cost": design["cost"], "samples": samples}
        if level == "final":
            vehicle = saboteur.parse_sab(lv, bridge.load_json("submission/saboteur.json"))
            game, _ = saboteur.duel(lv, design, vehicle)
            report["local_duel"] = {
                "sab_cost": vehicle["cost"], "sab_mass": vehicle["mass"],
                "sab_arrived": game["sab_arrived"], "sab_time": game["res"]["sab"]["t"],
                "convoy_ok": game["convoy_ok"], "bridge_win": game["bridge_win"],
                "bridge_breaks": game["res"]["bridge_broken"], "anomaly": game["anomaly"],
            }
    return report, success


if __name__ == "__main__":
    result, passed = verify()
    print(json.dumps(result, indent=2, ensure_ascii=False))
    sys.exit(0 if passed else 1)
