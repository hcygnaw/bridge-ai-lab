"""Reduce a passing bridge's cost using only the stock checker and simulator.

Example (from bridge/workspace):
    python trim_bridge.py 2 submission/level2.json trimmed.json --seconds 60
"""

import argparse
import copy
import json
import math
import os
from pathlib import Path
import random
import tempfile
import time

import bridge


def compact(design):
    members = design["members"]
    used = sorted({n for m in members for n in m[:2] if isinstance(n, int)})
    remap = {old: new for new, old in enumerate(used)}
    design["nodes"] = [design["nodes"][old] for old in used]
    for m in members:
        m[:2] = [remap.get(n, n) for n in m[:2]]


def candidate(best, level, rng):
    d = copy.deepcopy(best)
    m = rng.choice(d["members"])
    nodes = d["nodes"]

    def pos(k):
        return nodes[k] if isinstance(k, int) else level["anchors"][int(k[1:])]

    move = rng.random()
    if move < .22 and m[2] not in ("road", "hydraulic"):
        m[2] = rng.choice(["wood", "cable", "spring", "steel"])
    elif move < .35 and m[2] not in ("road", "hydraulic"):
        index = d["members"].index(m)
        d["members"].pop(index)
        for sensor in d.get("sensors", []):
            if sensor["type"] == "plate" and sensor["member"] > index:
                sensor["member"] -= 1
        compact(d)
    elif move < .44 and m[2] != "road" and len(m) == 3:
        i = rng.randrange(2)
        x, y = pos(m[i])
        options = [k for k in [*range(len(nodes)), *(f"A{j}" for j in range(len(level["anchors"])))]
                   if k not in m[:2] and math.dist((x, y), pos(k)) <= 3]
        if options:
            m[i] = rng.choice(options)
            compact(d)
    elif nodes:
        j = rng.randrange(len(nodes))
        here = nodes[j]
        attached = [pos(e[1] if e[0] == j else e[0]) for e in d["members"] if j in e[:2]]
        if rng.random() < .45 and attached:
            frac = rng.uniform(.015, .40)
            for axis in (0, 1):
                here[axis] += frac * (sum(p[axis] for p in attached) / len(attached) - here[axis])
        else:
            step = rng.choice([.025, .09, .28, .55])
            here[0] += rng.gauss(0, step)
            here[1] += rng.gauss(0, step)
        nodes[j] = [round(v, 5) for v in here]
    return d


def store(path, design):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", dir=path.parent, delete=False, encoding="utf-8") as f:
        json.dump(design, f, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
        f.write("\n")
    os.replace(f.name, path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("level", type=int, choices=range(1, 7))
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--seconds", type=float, default=60)
    parser.add_argument("--seed", type=int, default=1)
    args = parser.parse_args()
    if args.seconds <= 0 or not math.isfinite(args.seconds):
        parser.error("--seconds must be finite and positive")
    lv = bridge.load_level(args.level)
    scenarios = [bridge.load_json(path) for path in bridge.sample_paths(lv)]

    def passes(parsed):
        return all(bridge.simulate(lv, parsed, sc)[0]["ok"] for sc in scenarios)

    best = bridge.load_json(args.input)
    p = bridge.parse_design(lv, best)
    if not passes(p):
        parser.error("input did not pass all official scenarios")
    price = p["cost"]
    if args.output.exists() and args.output.resolve() != args.input.resolve():
        parser.error("output already exists; use a new file, or optimize the input in place")
    if args.output.resolve() != args.input.resolve():
        store(args.output, best)
    rng = random.Random(args.seed)
    stop = time.monotonic() + args.seconds
    print(f"Starting cost: {price:.2f}", flush=True)
    while time.monotonic() < stop:
        d = candidate(best, lv, rng)
        try:
            p = bridge.parse_design(lv, d)
        except bridge.DesignError:
            continue
        if p["cost"] < price and passes(p):
            best, price = d, p["cost"]
            store(args.output, best)
            print(f"Passed all scenarios: {price:.2f}", flush=True)


if __name__ == "__main__":
    main()
