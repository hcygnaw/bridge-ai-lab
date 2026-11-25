import json, math, sys
from pathlib import Path

WS = Path(__file__).resolve().parent
sys.path.insert(0, str(WS))
import bridge
from opt_util import eval_design, save_if_better

SUB = WS / "submission"
SUB.mkdir(exist_ok=True)

def make_l5_dj(
    pit_rx=-6.2, pit_ry=0.9,
    pit_lx=-2.4, pit_ly=-0.8,
    lx_end=6.8, ry=1.4,
    rx_start=14.8, ly=-2.8,
    th_l=3.6,
    pit_n_r=2,
    use_pit_landing_2=False,
):
    nodes, members = [], []
    def add(x, y):
        nodes.append([round(x, 4), round(y, 4)])
        return len(nodes) - 1

    tl = add(0.0, th_l)
    members += [["A0", tl, "steel"], ["A5", tl, "cable"]]

    # Pit left ramp: A2=(-11,0) -> (pit_rx, pit_ry)
    n_pr = max(2, math.ceil(math.hypot(pit_rx + 11.0, pit_ry) / 2.4))
    pr = ["A2"]
    for i in range(1, n_pr + 1):
        t = i / n_pr
        pr.append(add(-11.0 + (pit_rx + 11.0)*t, pit_ry * (t ** 1.1)))
    for i in range(n_pr):
        members.append([pr[i], pr[i+1], "road"])
    for i in range(1, n_pr + 1):
        members.append([tl, pr[i], "cable"])

    # Pit right landing: (pit_lx, pit_ly) -> A0=(0,0)
    if use_pit_landing_2:
        pm = add(0.5*pit_lx, 0.5*pit_ly)
        p3 = add(pit_lx, pit_ly)
        members += [[p3, pm, "road"], [pm, "A0", "road"], [tl, p3, "cable"], [tl, pm, "cable"]]
    else:
        p3 = add(pit_lx, pit_ly)
        members += [[p3, "A0", "road"], [tl, p3, "cable"]]

    # River left ramp: A0=(0,0) -> (lx_end, ry)
    n_l = max(2, math.ceil(math.hypot(lx_end, ry) / 2.4))
    l_r = ["A0"]
    for i in range(1, n_l + 1):
        t = i / n_l
        l_r.append(add(lx_end * t, ry * (t ** 1.15)))
    for i in range(n_l):
        members.append([l_r[i], l_r[i+1], "road"])
    members.append(["A1", l_r[1], "steel"])
    for i in range(2, n_l + 1):
        members.append([tl, l_r[i], "cable"])

    # River right landing: (rx_start, ly) -> A7=(24,0), NO RIGHT TOWER!
    span_r = 24.0 - rx_start
    n_r = max(2, math.ceil(math.hypot(span_r, -ly) / 2.4))
    r_r = []
    for i in range(n_r):
        t = i / n_r
        r_r.append(add(rx_start + span_r * t, ly * (1.0 - t)))
    r_r.append("A7")
    for i in range(n_r):
        members.append([r_r[i], r_r[i+1], "road"])
    members.append(["A8", r_r[n_r - 1], "steel"])
    for i in range(0, n_r - 1):
        members.append(["A7", r_r[i], "cable"])

    return {"nodes": nodes, "members": members}

# First check WHERE car/van land in pit AND river separately!
lv = bridge.load_level("5")
sc1 = json.loads(open(bridge.sample_paths(lv)[0]).read())
sc2 = json.loads(open(bridge.sample_paths(lv)[1]).read())

def sim_times(d):
    try:
        P = bridge.parse_design(lv, d)
    except Exception:
        return None, None
    res1, _ = bridge.simulate(lv, P, sc1, replay=False)
    res2, _ = bridge.simulate(lv, P, sc2, replay=False)
    return P["cost"], (res1, res2)

print("=== STEP 1: TUNE PIT JUMP FIRST ===", flush=True)
for pit_rx in [-6.3, -6.5]:
    for pit_ry in [0.7, 1.0, 1.3]:
        for pit_lx in [-2.4, -3.5, -4.0]:
            for pit_ly in [-0.6, -1.0, -1.4]:
                use2 = abs(pit_lx) > 2.3
                d = make_l5_dj(pit_rx, pit_ry, pit_lx, pit_ly, 6.8, 1.4, 15.0, -2.8, 3.6, 2, use2)
                cost, res = sim_times(d)
                if cost is None: continue
                ev1 = [e for e in res[0]["events"] if "VFAIL" in e or "VARRIVE" in e]
                ev2 = [e for e in res[1]["events"] if "VFAIL" in e or "VARRIVE" in e]
                # Failure time > 5.0 means car crossed the pit AND reached river!
                t1 = float(ev1[0].split()[0]) if ev1 else 0
                t2 = float(ev2[0].split()[0]) if ev2 else 0
                if t1 > 4.5 and t2 > 4.5:
                    print(f"PIT OK! cost={cost:.1f} prx={pit_rx} pry={pit_ry} plx={pit_lx} ply={pit_ly} | ev1={ev1[:2]} ev2={ev2[:2]}", flush=True)
                    break
            else:
                continue
            break
