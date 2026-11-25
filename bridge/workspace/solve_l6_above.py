import json, math, os, subprocess, sys

with open("levels/level6.json") as f:
    L6 = json.load(f)

SAMPLES = ["levels/level6/sample1.json", "levels/level6/sample2.json", "levels/level6/sample3.json"]

def run_sim(path, scen):
    res = subprocess.run([sys.executable, "bridge.py", "run", "6", path, scen], capture_output=True, text=True)
    out = res.stdout + res.stderr
    return res.returncode == 0, out

def run_sim_raw(path, scen):
    # Use bridge.py to check/run; for raw events call bridge_sim.exe via bridge.py's format
    cmd = ["./bridge_sim.exe", "levels/level6.json", path, scen]
    res = subprocess.run(cmd, capture_output=True, text=True)
    return res.stdout

def build_above_deck(top_y=2.4, piv_x=13.5, l1_x=15.7, l2_x=17.9):
    nodes = [list(a) for a in L6["anchors"]]
    # Anchors: 0:(0,0), 1:(0,-2), 2:(36,0), 3:(36,-2), 4:(12,-2), 5:(24,-2)
    members = []

    def add_side(sign):
        x0 = 0.0 if sign == 1 else 36.0
        a_deck = 0 if sign == 1 else 2
        a_pier = 4 if sign == 1 else 5

        # Deck from 0 to 12.0 in 5 segments of 2.4m, plus cantilever to piv_x (13.5)
        xs = [2.4, 4.8, 7.2, 9.6, 12.0, piv_x]
        s_deck = []
        for x in xs:
            idx = len(nodes)
            nodes.append([round(x0 + sign * x, 3), 0.0])
            s_deck.append(idx)
        for i in range(len(s_deck)):
            u = a_deck if i == 0 else s_deck[i - 1]
            v = s_deck[i]
            members.append([u, v, "road"])

        # Above-deck Warren truss from 0 to 12: top nodes at x=1.2, 3.6, 6.0, 8.4, 10.8, 12.5
        s_top = []
        for i in range(5):
            idx = len(nodes)
            nodes.append([round(x0 + sign * (2.4 * i + 1.2), 3), top_y])
            s_top.append(idx)
            dl = a_deck if i == 0 else s_deck[i - 1]
            dr = s_deck[i]
            members.append([idx, dl, "wood"])
            members.append([idx, dr, "wood"])
        for i in range(4):
            members.append([s_top[i], s_top[i + 1], "wood"])

        # Pier A4=(12,-2) supports s_deck[4]=(12,0) and piv=(13.5,0)
        members.append([a_pier, s_deck[4], "steel"])
        members.append([a_pier, s_deck[5], "steel"])

        # Hydraulic anchor at (12.8, top_y) connected to s_top[4]=(10.8,top_y), s_deck[4]=(12,0), piv=(13.5,0)
        h_anc = len(nodes)
        nodes.append([round(x0 + sign * 12.8, 3), top_y])
        members.append([s_top[4], h_anc, "steel"])   # (10.8,2.4)-(12.8,2.4) L=2.0m
        members.append([s_deck[4], h_anc, "steel"])  # (12.0,0)-(12.8,2.4) L=2.53m
        members.append([s_deck[5], h_anc, "steel"])  # (13.5,0)-(12.8,2.4) L=2.50m

        # Bascule leaf: pivots at s_deck[5] (piv_x=13.5) to l2_x=17.9
        piv = s_deck[5]
        l1 = len(nodes); nodes.append([round(x0 + sign * l1_x, 3), 0.0])
        l2 = len(nodes); nodes.append([round(x0 + sign * l2_x, 3), 0.0])
        members.append([piv, l1, "road"])
        members.append([l1, l2, "road"])

        l_top = len(nodes); nodes.append([round(x0 + sign * l1_x, 3), 0.9])
        members.append([piv, l_top, "wood"])
        members.append([l1, l_top, "wood"])
        members.append([l2, l_top, "wood"])

        # Hydraulic from h_anc (12.8, 2.4) to l1 (15.7, 0.0) -> L = 3.76m <= 5.0m!
        members.append([h_anc, l1, "hydraulic", "A"])

    add_side(1)
    add_side(-1)

    return {
        "nodes": nodes,
        "members": members,
        "hydraulics": {"A": {"ratio": 0.5, "speed": 1.0, "trigger": "ship"}}
    }

def calc_cost(d):
    prices = {"road": 160, "wood": 50, "steel": 150, "cable": 70, "hydraulic": 400}
    c = 0.0
    for m in d["members"]:
        x1, y1 = d["nodes"][m[0]]
        x2, y2 = d["nodes"][m[1]]
        c += math.hypot(x2 - x1, y2 - y1) * prices[m[2]]
    return c

def auto_upgrade(d, max_iters=25):
    tmp = "tmp_l6_above.json"
    for it in range(max_iters):
        with open(tmp, "w") as f:
            json.dump(d, f)
        all_ok = True
        earliest_break = None
        for sc in SAMPLES:
            raw = run_sim_raw(tmp, sc)
            if "FAIL" in raw or "ERR" in raw:
                all_ok = False
                for line in raw.splitlines():
                    if "BREAK" in line:
                        parts = line.split()
                        t = float(parts[0])
                        idx = int(parts[2])
                        force = float(parts[3])
                        if d["members"][idx][2] in ("wood", "cable"):
                            if earliest_break is None or t < earliest_break[0]:
                                earliest_break = (t, idx, force, sc)
                            break
        if all_ok:
            return True, calc_cost(d), d
        if earliest_break is None:
            print(f"Stopped at iter {it}, cost={calc_cost(d):.1f}")
            for sc in SAMPLES:
                ok, out = run_sim(tmp, sc)
                raw = run_sim_raw(tmp, sc)
                ev = [l for l in raw.splitlines() if any(k in l for k in ("BREAK", "FAIL", "SHIPHIT"))]
                print(os.path.basename(sc), ok, "Events:", ev[:8])
            return False, calc_cost(d), d
        t, idx, force, sc = earliest_break
        old_mat = d["members"][idx][2]
        if old_mat == "wood" and force > 0:
            new_mat = "cable"
        else:
            new_mat = "steel"
        print(f"iter {it}: cost={calc_cost(d):.1f}, {old_mat} m[{idx}] (f={force:.0f}) -> {new_mat} at t={t:.2f}s in {os.path.basename(sc)}")
        d["members"][idx][2] = new_mat
    return False, calc_cost(d), d

d = build_above_deck(top_y=2.4)
print(f"Initial cost: {calc_cost(d):.1f}")
ok, cost, d = auto_upgrade(d)
print(f"Result: ok={ok}, cost={cost:.1f}")
if ok and cost <= 20000:
    with open("submission/level6.json", "w") as f:
        json.dump(d, f)
    print("SAVED submission/level6.json!")
