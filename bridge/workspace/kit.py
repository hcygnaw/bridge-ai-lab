"""Design helpers for the bridge contest. Working directory must be bridge/workspace."""
import json, math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bridge

OUT = os.path.join(HERE, 'candidates')
SUB = os.path.join(HERE, 'submission')
os.makedirs(OUT, exist_ok=True)
os.makedirs(SUB, exist_ok=True)


class B:
    def __init__(self):
        self.nodes = []
        self.members = []
        self.sensors = []
        self.lights = []
        self.rules = []
        self._idx = {}

    def add(self, x, y, key=None):
        x, y = round(float(x), 4), round(float(y), 4)
        k = (x, y)
        if k in self._idx:
            return self._idx[k]
        i = len(self.nodes)
        self.nodes.append([x, y])
        self._idx[k] = i
        if key:
            self._idx[key] = i
        return i

    def mem(self, a, b, mat, group=None):
        if isinstance(a, (tuple, list)) and not isinstance(a, str):
            a = self.add(a[0], a[1])
        if isinstance(b, (tuple, list)) and not isinstance(b, str):
            b = self.add(b[0], b[1])
        if a == b:
            return
        # canonical pair to skip duplicates
        key = (a, b, mat) if isinstance(a, str) or isinstance(b, str) else (min(a, b), max(a, b), mat)
        # still allow only one member per node pair; caller should not double-add
        pair = (str(a), str(b))
        pair_s = tuple(sorted(pair))
        if pair_s in self._idx.get('_pairs', {}):
            return
        self._idx.setdefault('_pairs', set()).add(pair_s)
        if mat == 'hydraulic':
            self.members.append([a, b, mat, group or 'A'])
        else:
            self.members.append([a, b, mat])

    def design(self):
        d = {'nodes': self.nodes, 'members': self.members}
        if self.sensors:
            d['sensors'] = self.sensors
        if self.lights:
            d['lights'] = self.lights
        if self.rules:
            d['rules'] = self.rules
        return d


def save(design, name):
    path = os.path.join(OUT, name)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(design, f, ensure_ascii=False, indent=1)
    return path


def promote(name, sub_name):
    src = os.path.join(OUT, name)
    dst = os.path.join(SUB, sub_name)
    with open(src, encoding='utf-8') as f:
        d = json.load(f)
    with open(dst, 'w', encoding='utf-8') as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
        f.write('\n')
    return dst


def evaluate(level, design, quiet=False):
    lv = bridge.load_level(level)
    try:
        P = bridge.parse_design(lv, design)
    except bridge.DesignError as e:
        return {'ok': False, 'cost': None, 'error': str(e), 'samples': []}
    samples = []
    all_ok = True
    peaks = []
    for sp in bridge.sample_paths(lv):
        sc = bridge.load_json(sp)
        res, _ = bridge.simulate(lv, P, sc)
        sm = bridge.summarize(res, P, sc)
        pk = res.get('peak_members') or []
        mx = max(pk) if pk else 0
        samples.append({'name': sc.get('name', sp), 'ok': bool(sm['ok']), 'text': sm['text'], 'max_peak': mx,
                        'top': bridge.peak_report(res, P, 6)})
        if not sm['ok']:
            all_ok = False
        peaks.append(mx)
    return {'ok': all_ok, 'cost': P['cost'], 'detail': P['cost_detail'], 'samples': samples,
            'max_peak': max(peaks) if peaks else 0, 'error': None}


def report(level, design, label=''):
    r = evaluate(level, design)
    if r['error']:
        print(f'INVALID {label}: {r["error"]}')
        return r
    flag = 'PASS' if r['ok'] else 'FAIL'
    print(f'{flag} {label} cost={r["cost"]} peak={r["max_peak"]:.2f} {r["detail"]}')
    if not r['ok']:
        for s in r['samples']:
            if not s['ok']:
                print(s['name'])
                print(s['text'])
                for line in s['top']:
                    print('   ', line)
    return r


def chain(b, pts, mat, split=None):
    """Connect a polyline. split(length) -> max segment length, or a number."""
    if not pts:
        return []
    ids = []
    def nid(p):
        if isinstance(p, str):
            return p
        return b.add(p[0], p[1])
    ids.append(nid(pts[0]))
    for p in pts[1:]:
        ids.append(nid(p))
    out = []
    for a, c in zip(ids, ids[1:]):
        if isinstance(a, str):
            ax, ay = None, None
        else:
            ax, ay = b.nodes[a]
        if isinstance(c, str):
            cx, cy = None, None
        # if either end is an anchor, caller must not need split, or pass coordinates
        b.mem(a, c, mat)
        out.append((a, c))
    return ids
