import json, math, sys
from pathlib import Path

WS = Path(__file__).resolve().parent
sys.path.insert(0, str(WS))
import bridge
from opt_util import eval_design, save_if_better

SUB = WS / "submission"
SUB.mkdir(exist_ok=True)

def dist(a, b):
    return math.hypot(a[0]-b[0], a[1]-b[1])

def topo_inverted_warren(n_seg, y_bot_mid, y_bot_end, road_camber=0.0, bot_mat="wood", tie_anchors=True):
    nodes = []
    members = []
    for i in range(1, n_seg):
        t = i / n_seg
        x = 15.0 * t
        y = 4.0 * road_camber * t * (1.0 - t)
        nodes.append([round(x, 4), round(y, 4)])
    for i in range(n_seg):
        u = "A0" if i == 0 else i - 1
        v = "A2" if i == n_seg - 1 else i
        members.append([u, v, "road"])
    bot_start = len(nodes)
    for i in range(n_seg):
        t = (i + 0.5) / n_seg
        x = 15.0 * t
        y = y_bot_end + (y_bot_mid - y_bot_end) * 4.0 * t * (1.0 - t)
        nodes.append([round(x, 4), round(y, 4)])
    for i in range(n_seg):
        u = "A0" if i == 0 else i - 1
        v = "A2" if i == n_seg - 1 else i
        b = bot_start + i
        members.append([u, b, "wood"])
        members.append([v, b, "wood"])
        if i + 1 < n_seg:
            members.append([b, b + 1, bot_mat])
    if tie_anchors:
        members.append(["A1", bot_start, bot_mat])
        members.append(["A3", bot_start + n_seg - 1, bot_mat])
    return {"nodes": nodes, "members": members}

def topo_inverted_truss(n_seg, y_bot_mid, y_bot_end, road_camber=0.0, bot_mat="wood", diag_mat="wood"):
    nodes = []
    members = []
    for i in range(1, n_seg):
        t = i / n_seg
        x = 15.0 * t
        y = 4.0 * road_camber * t * (1.0 - t)
        nodes.append([round(x, 4), round(y, 4)])
    for i in range(n_seg):
        u = "A0" if i == 0 else i - 1
        v = "A2" if i == n_seg - 1 else i
        members.append([u, v, "road"])
    bot_start = len(nodes)
    for i in range(1, n_seg):
        t = i / n_seg
        x = 15.0 * t
        y = y_bot_end + (y_bot_mid - y_bot_end) * 4.0 * t * (1.0 - t)
        nodes.append([round(x, 4), round(y, 4)])
    for i in range(n_seg):
        u = "A1" if i == 0 else bot_start + i - 1
        v = "A3" if i == n_seg - 1 else bot_start + i
        members.append([u, v, bot_mat])
    for i in range(n_seg - 1):
        members.append([i, bot_start + i, "wood"])
    for i in range(n_seg):
        u_top = "A0" if i == 0 else i - 1
        v_top = "A2" if i == n_seg - 1 else i
        u_bot = "A1" if i == 0 else bot_start + i - 1
        v_bot = "A3" if i == n_seg - 1 else bot_start + i
        if i + 0.5 < n_seg / 2.0:
            if diag_mat == "cable":
                members.append([u_top, v_bot, "cable"])
            else:
                members.append([u_bot, v_top, diag_mat])
        elif i + 0.5 > n_seg / 2.0:
            if diag_mat == "cable":
                members.append([v_top, u_bot, "cable"])
            else:
                members.append([v_bot, u_top, diag_mat])
        else:
            members.append([u_top, v_bot, diag_mat])
            members.append([v_top, u_bot, diag_mat])
    return {"nodes": nodes, "members": members}

def topo_kingpost(n_seg, post_x_list, post_y_list, road_camber=0.0):
    nodes = []
    members = []
    for i in range(1, n_seg):
        t = i / n_seg
        x = 15.0 * t
        y = 4.0 * road_camber * t * (1.0 - t)
        nodes.append([round(x, 4), round(y, 4)])
    for i in range(n_seg):
        u = "A0" if i == 0 else i - 1
        v = "A2" if i == n_seg - 1 else i
        members.append([u, v, "road"])
    bot_ids = []
    for rx_idx, py in zip(post_x_list, post_y_list):
        x = nodes[rx_idx][0]
        bid = len(nodes)
        nodes.append([x, py])
        bot_ids.append((rx_idx, bid))
        members.append([rx_idx, bid, "wood"])
        for adj in [rx_idx - 1, rx_idx + 1]:
            if 0 <= adj < n_seg - 1:
                if dist(nodes[adj], nodes[bid]) <= 3.0:
                    members.append([adj, bid, "wood"])
    prev = "A0"
    for _, bid in bot_ids:
        members.append([prev, bid, "cable"])
        prev = bid
    members.append([prev, "A2", "cable"])
    return {"nodes": nodes, "members": members}

best = None
def try_d(label, d):
    global best
    ok, cost, pk, _ = eval_design(1, d)
    if ok:
        if best is None or cost < best[0]:
            best = (cost, label, pk, d)
            print(f"NEW BEST L1: {cost:.1f} ({label}) peak={pk*100:.1f}%", flush=True)
            save_if_better(1, d, SUB / "level1.json")

print("=== Testing Inverted Warren ===", flush=True)
for n_seg in [6, 7]:
    for y_end in [-2.0, -1.6, -1.3, -1.0]:
        for y_mid in [-2.5, -2.0, -1.5, -1.0]:
            for rc in [-0.2, 0.0, 0.3, 0.6]:
                for bm in ["wood", "cable"]:
                    for ta in [False, True]:
                        try_d(f"invW_n{n_seg}_ye{y_end}_ym{y_mid}_rc{rc}_{bm}_ta{int(ta)}",
                              topo_inverted_warren(n_seg, y_mid, y_end, rc, bm, ta))

print("=== Testing Inverted Truss ===", flush=True)
for n_seg in [6, 7]:
    for y_mid in [-2.5, -2.0, -1.5]:
        for rc in [0.0, 0.3, 0.6]:
            for bm in ["wood", "cable"]:
                for dm in ["wood", "cable"]:
                    try_d(f"invT_n{n_seg}_ym{y_mid}_rc{rc}_{bm}_{dm}",
                          topo_inverted_truss(n_seg, y_mid, -2.0, rc, bm, dm))

print("=== Testing Kingpost / Queenpost ===", flush=True)
for n_seg in [6, 7]:
    if n_seg == 6:
        configs = [([1, 3], -2.0), ([1, 3], -2.5), ([1, 2, 3], -2.0), ([1, 2, 3], -2.5)]
    else:
        configs = [([1, 4], -2.0), ([1, 4], -2.5), ([1, 2, 4], -2.0), ([1, 3, 4], -2.0), ([1, 2, 3, 4], -2.0)]
    for idxs, py in configs:
        for rc in [-0.3, 0.0, 0.3, 0.6]:
            try_d(f"kp_n{n_seg}_{idxs}_py{py}_rc{rc}",
                  topo_kingpost(n_seg, idxs, [py]*len(idxs), rc))

if best:
    print("\n=== BEST L1 ===")
    eval_design(1, best[3], verbose=True)
