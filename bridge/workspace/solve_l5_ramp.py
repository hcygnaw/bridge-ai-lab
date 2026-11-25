import json, math, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bridge

lv = bridge.load_level("5")
samples = [bridge.load_json(p) for p in bridge.sample_paths(lv)]
snames = [os.path.basename(p) for p in bridge.sample_paths(lv)]

def make_l5(pit_mode="ramp", river_sag=2.6, n_riv=11, n_cables=2):
    # Level 5 anchors:
    # A0=(0,0), A1=(0,-3), A2=(-11,0), A3=(-2,-3), A4=(-5,-3), A5=(-8,-3), A6=(-11,-3), A7=(24,0), A8=(24,-3)
    nodes = []
    members = []

    if pit_mode == "ramp":
        # Ramp down from A2=(-11,0) to A5=(-8,-3), drive on pit floor [-8,-2], ramp up from A3=(-2,-3) to A0=(0,0)
        p1 = len(nodes); nodes.append([-9.5, -1.5])
        members.append(["A2", p1, "road"])
        members.append([p1, "A5", "road"])
        p4 = len(nodes); nodes.append([-1.0, -1.5])
        members.append(["A3", p4, "road"])
        members.append([p4, "A0", "road"])
    else:
        # Gentler ramp: A2=(-11,0) -> (-9,-1.5) -> (-7,-2.9) [on A5], then (-4,-2.9) [on A3] -> (-2,-1.5) -> A0=(0,0)
        p1 = len(nodes); nodes.append([-9.0, -1.4])
        p2 = len(nodes); nodes.append([-7.0, -2.9])
        members.append(["A2", p1, "road"])
        members.append([p1, p2, "road"])
        members.append(["A5", p1, "steel"])
        p3 = len(nodes); nodes.append([-4.0, -2.9])
        p4 = len(nodes); nodes.append([-2.0, -1.4])
        members.append([p3, p4, "road"])
        members.append([p4, "A0", "road"])
        members.append(["A3", p4, "steel"])

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

    # Stressed-ribbon cable chain(s) along the river (skipping adjacent road nodes!)
    if n_cables >= 1:
        chain1 = ["A0", rnodes[1], rnodes[3], rnodes[5], rnodes[7], "A7"]
        for i in range(len(chain1) - 1):
            members.append([chain1[i], chain1[i + 1], "cable"])
    if n_cables >= 2:
        chain2 = ["A0", rnodes[2], rnodes[4], rnodes[6], rnodes[8], "A7"]
        for i in range(len(chain2) - 1):
            members.append([chain2[i], chain2[i + 1], "cable"])

    return {"nodes": nodes, "members": members}

for pit_mode in ("ramp", "flat"):
    for river_sag in (2.2, 2.6, 3.0):
        for n_cables in (1, 2):
            d = make_l5(pit_mode=pit_mode, river_sag=river_sag, n_cables=n_cables)
            try:
                P = bridge.parse_design(lv, d)
            except bridge.DesignError as e:
                print(f"{pit_mode} sag={river_sag} cab={n_cables}: ERR {e}")
                continue
            oks = []
            info = []
            for sc, sn in zip(samples, snames):
                res, _ = bridge.simulate(lv, P, sc)
                oks.append(res["ok"])
                br = sum(1 for e in res["events"] if "BREAK" in e)
                info.append(f"{sn}:{'OK' if res['ok'] else 'FAIL'}(br={br})")
            print(f"{pit_mode:4s} sag={river_sag} cab={n_cables}: cost={P['cost']:7.1f}  " + "  ".join(info))
            if all(oks) and P["cost"] <= 10000:
                with open("submission/level5.json", "w") as f:
                    json.dump(d, f)
                print("SAVED submission/level5.json!")
                sys.exit(0)
