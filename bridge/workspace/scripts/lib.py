"""Bridge design helpers. Run from bridge/workspace."""
import json, math, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import bridge

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(HERE)

def dump(design, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(design, f, ensure_ascii=False, indent=1)
    return path

def check(level, design):
    lv = bridge.load_level(str(level))
    P = bridge.parse_design(lv, design)
    return P

def run(level, design, quiet=False):
    lv = bridge.load_level(str(level))
    P = bridge.parse_design(lv, design)
    ok = True
    reports = []
    for sp in bridge.sample_paths(lv):
        scenario = json.loads(open(sp, encoding="utf-8").read())
        res, _ = bridge.simulate(lv, P, scenario)
        summ = bridge.summarize(res, P, scenario)
        peaks = bridge.peak_report(res, P, top=6)
        reports.append((os.path.basename(sp), summ, peaks, res))
        if not summ["ok"]:
            ok = False
    if not quiet:
        print(f"LEVEL {level} cost={P['cost']:.1f} budget={lv['budget']} {'PASS' if ok else 'FAIL'}")
        print("  detail", P.get("cost_detail"))
        for name, summ, peaks, res in reports:
            print(f"  {name}: {'OK' if summ['ok'] else 'FAIL'}")
            print(summ["text"])
            for line in peaks:
                print("   ", line)
    return ok, P["cost"], reports

class B:
    def __init__(self):
        self.nodes = []
        self.members = []
        self.sensors = []
        self.lights = []
        self.rules = []
        self._idx = {}

    def node(self, x, y, key=None):
        x, y = round(float(x), 4), round(float(y), 4)
        k = key if key is not None else (x, y)
        if k in self._idx:
            return self._idx[k]
        # merge very close
        for i, (px, py) in enumerate(self.nodes):
            if abs(px - x) < 0.05 and abs(py - y) < 0.05:
                self._idx[k] = i
                return i
        i = len(self.nodes)
        self.nodes.append([x, y])
        self._idx[k] = i
        return i

    def mem(self, a, b, mat, group=None):
        if isinstance(a, str) or isinstance(b, str):
            pass
        else:
            if a == b:
                return
        key = (str(a), str(b), mat) if str(a) < str(b) else (str(b), str(a), mat)
        # duplicate pair check
        pair = tuple(sorted([str(a), str(b)]))
        if not hasattr(self, "_pairs"):
            self._pairs = set()
        if pair in self._pairs:
            return
        self._pairs.add(pair)
        if mat == "hydraulic":
            self.members.append([a, b, mat, group or "A"])
        else:
            self.members.append([a, b, mat])

    def design(self):
        d = {"nodes": self.nodes, "members": self.members}
        if self.sensors:
            d["sensors"] = self.sensors
        if self.lights:
            d["lights"] = self.lights
        if self.rules:
            d["rules"] = self.rules
        return d
