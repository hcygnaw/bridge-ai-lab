import json, math, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bridge

lv = bridge.load_level("5")
samples = [bridge.load_json(p) for p in bridge.sample_paths(lv)]
snames = [os.path.basename(p) for p in bridge.sample_paths(lv)]

def make_l5_cat(pit_sag=1.5, river_sag=2.6, n_pit=5, n_riv=11, n_cables=2):
    nodes = []
    members = []

    # Pit [-11, 0]: n_pit road segments with parabolic sag (pure road catenary!)
    pnodes = []
    for i in range(1, n_pit):
        t = i / n_pit
        x = round(-11.0 + 11.0 * t, 3)
        y = round(-pit_sag * 4.0 * t * (1.0 - t), 3)
        pnodes.append(len(nodes))
        nodes.append([x, y])
    for i in range(n_pit):
        u = "A2" if i == 0 else pnodes[i - 1]
        v = "A0" if i == n_pit - 1 else pnodes[i]
        members.append([u, v, "road"])
    # Stressed-ribbon chord cable under the pit road: A2->p1->A0 (~$795 -> total ~$9,920!)
    members.append(["A2", pnodes[1], "cable"])
    members.append([pnodes[1], "A0", "cable"])

    # River [0, 24]: n_riv road segments with parabolic sag
    rnodes = []
    for i in range(1, n_riv):
        t = i / n_riv
        x = round(24.0 * t, 3)
        y = round(-river_sag * 4.0 * t * (1.0 - t), 3)
        rnodes.append(len(nodes))
        nodes.append([x, y])
    for i in range(n_riv):
        u = "A0" if i == 0 else rnodes[i - 1]
        v = "A7" if i == n_riv - 1 else rnodes[i]
        members.append([u, v, "road"])

    if n_cables >= 1:
        chain1 = ["A0", rnodes[1], rnodes[3], rnodes[5], rnodes[7], "A7"]
        for i in range(len(chain1) - 1):
            members.append([chain1[i], chain1[i + 1], "cable"])
    if n_cables >= 2:
        chain2 = ["A0", rnodes[2], rnodes[4], rnodes[6], rnodes[8], "A7"]
        for i in range(len(chain2) - 1):
            members.append([chain2[i], chain2[i + 1], "cable"])

    return {"nodes": nodes, "members": members}

for pit_sag in (1.75, 1.85, 1.92):
    for river_sag in (2.2, 2.5):
        d = make_l5_cat(pit_sag=pit_sag, river_sag=river_sag, n_cables=2)
        try:
            P = bridge.parse_design(lv, d)
        except bridge.DesignError as e:
            print(f"ps={pit_sag} rs={river_sag}: ERR {e}")
            continue
        oks = []
        info = []
        for sc, sn in zip(samples, snames):
            res, _ = bridge.simulate(lv, P, sc)
            oks.append(res["ok"])
            br = sum(1 for e in res["events"] if "BREAK" in e)
            info.append(f"{sn}:{'OK' if res['ok'] else 'FAIL'}(br={br}, ev={res['events'][:3]})")
        print(f"ps={pit_sag} rs={river_sag}: cost={P['cost']:7.1f}  " + "  ".join(info))
        if all(oks) and P["cost"] <= 10000:
            with open("submission/level5.json", "w") as f:
                json.dump(d, f)
            print("SAVED submission/level5.json!")
            sys.exit(0)
