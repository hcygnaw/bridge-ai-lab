"""Local design and full-scenario scoring helpers. Run from bridge/workspace."""
import json
import math
import os
from pathlib import Path

import bridge


SUB = Path("submission")


def target(k):
    return SUB / ("final_bridge.json" if k == "final" else f"level{k}.json")


def write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n")
    tmp.replace(path)


class Design:
    def __init__(self, k):
        self.lv = bridge.load_level(k)
        self.nodes = []
        self.members = []
        self.lights = []
        self.rules = []
        self.sensors = []
        self.lookup = {tuple(p): f"A{j}" for j, p in enumerate(self.lv["anchors"])}

    def n(self, x, y):
        pt = (round(x, 6), round(y, 6))
        if pt not in self.lookup:
            self.lookup[pt] = len(self.nodes)
            self.nodes.append(list(pt))
        return self.lookup[pt]

    def pos(self, n):
        return self.lv["anchors"][int(n[1:])] if isinstance(n, str) else self.nodes[n]

    def m(self, a, b, material="wood", group=None):
        self.members.append([a, b, material] + ([] if group is None else [group]))

    def span(self, a, b, sag, count, material="road", params=None, curve="parabola"):
        ax, ay = self.pos(a)
        bx, by = self.pos(b)
        ts = params if params is not None else [i / count for i in range(1, count)]
        ns = [a]
        for t in ts:
            f = 1 - abs(2*t-1) if curve == "v" else 4*t*(1-t)
            ns.append(self.n(ax+(bx-ax)*t, ay+(by-ay)*t-sag*f))
        ns.append(b)
        for i, (n1, n2) in enumerate(zip(ns, ns[1:])):
            self.m(n1, n2, material if isinstance(material, str) else material[i])
        return ns

    def raw(self):
        d = dict(nodes=self.nodes, members=self.members)
        for key in ("lights", "sensors", "rules"):
            if getattr(self, key):
                d[key] = getattr(self, key)
        return d


class Bench:
    def __init__(self, k, order=None):
        self.k = k
        self.lv = bridge.load_level(k)
        self.sc = [bridge.load_json(p) for p in bridge.sample_paths(self.lv)]
        self.order = list(range(len(self.sc))) if order is None else order

    def existing(self):
        path = target(self.k)
        return bridge.parse_design(self.lv, bridge.load_json(path))["cost"] if path.exists() else math.inf

    def test(self, raw, *, save=True, cheaper=True, verbose=False, tag=""):
        if isinstance(raw, Design):
            raw = raw.raw()
        try:
            p = bridge.parse_design(self.lv, raw)
        except bridge.DesignError as e:
            if verbose:
                print("illegal:", str(e).splitlines()[:3])
            return False
        cost = p["cost"]
        if cheaper and cost >= self.existing():
            return False
        for i in self.order:
            r, _ = bridge.simulate(self.lv, p, self.sc[i])
            if verbose:
                print(self.k, i+1, cost, r["ok"], r["anomaly"],
                      [(v["status"],v["reason"],v["t"]) for v in r["vehicles"]],
                      [e for e in r["events"] if "BREAK" in e][:4])
            if not r["ok"]:
                return False
        if save and (not cheaper or cost < self.existing()):
            write(target(self.k), raw)
            print("PASS", self.k, cost, tag, flush=True)
        return True


def chain(k, sag, count, *, pit=(1.1, 5), midpoint=0):
    d = Design(k)
    if k == 1:
        d.span("A0", "A2", sag, count)
    elif k == 2:
        d.span("A0", "A4", sag, count)
    elif k == 3:
        mid = d.n(14, midpoint)
        if mid != "A2":
            dist = midpoint+4
            if dist <= 3:
                d.m("A2", mid)
            else:
                d.m("A2", mid, "steel")
        d.span("A0", mid, sag, count)
        d.span(mid, "A3", sag, count)
    elif k == 5:
        d.span("A2", "A0", pit[0], pit[1])
        d.span("A0", "A7", sag, count)
    elif k == "final":
        d.span("A0", "A3", sag, count)
    return d


if __name__ == "__main__":
    for k, sag, n in [(1, 1.5, 7), (2, 3.3, 14), (3, 1.6, 7), (5, 2.8, 11)]:
        Bench(k).test(chain(k, sag, n, midpoint=-2.3), verbose=True)
