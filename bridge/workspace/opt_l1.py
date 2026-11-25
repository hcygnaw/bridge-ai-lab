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

# Topology A: Catenary road + wood diagonal struts from A1=(0,-2) and A3=(15,-2) + optional under-cable
def topo_catenary_braced(n_seg, sag, use_end_struts=True, use_cable_tie=False, tie_span=(1, -1)):
    nodes = []
    members = []
    for i in range(1, n_seg):
        t = i / n_seg
        x = 15.0 * t
        y = -4.0 * sag * t * (1.0 - t)
        nodes.append([round(x, 4), round(y, 4)])
    for i in range(n_seg):
        u = "A0" if i == 0 else i - 1
        v = "A2" if i == n_seg - 1 else i
        members.append([u, v, "road"])
    if use_end_struts:
        # A1=(0,-2) to node 0, A3=(15,-2) to node n_seg-2
        if dist((0,-2), nodes[0]) <= 3.0:
            members.append(["A1", 0, "wood"])
        if dist((15,-2), nodes[-1]) <= 3.0:
            members.append(["A3", len(nodes)-1, "wood"])
    if use_cable_tie:
        # Cable from A0 to node k and A2 to node n-1-k, or A1 to node k
        a, b = tie_span
        members.append(["A0", a, "cable"])
        members.append(["A2", len(nodes)-1-a, "cable"])
        if b is not None:
            members.append([a, len(nodes)-1-a, "cable"])
    return {"nodes": nodes, "members": members}

# Topology B: Minimal wood under-arch / under-truss (using A1=(0,-2) and A3=(15,-2))
def topo_under_truss(n_seg, arch_y_mid, road_sag=0.0, use_bottom_chord=True):
    # Road has n_seg segments, n_seg-1 interior nodes (0 .. n_seg-2)
    # Bottom chord has n_seg-2 interior nodes (or n_seg-1 nodes aligned with road)
    nodes = []
    members = []
    for i in range(1, n_seg):
        t = i / n_seg
        x = 15.0 * t
        y = -4.0 * road_sag * t * (1.0 - t)
        nodes.append([round(x, 4), round(y, 4)])
    for i in range(n_seg):
        u = "A0" if i == 0 else i - 1
        v = "A2" if i == n_seg - 1 else i
        members.append([u, v, "road"])
    # Bottom nodes shifted by half segment: x = 15*(i+0.5)/n_seg for i=1..n_seg-2
    bot_start = len(nodes)
    n_bot = n_seg - 2
    for i in range(n_bot):
        t = (i + 1.5) / n_seg
        x = 15.0 * t
        y = -2.0 + (arch_y_mid - (-2.0)) * 4.0 * t * (1.0 - t)
        nodes.append([round(x, 4), round(y, 4)])
    # Connect A1=(0,-2) to road[0] and bot[0]
    members.append(["A1", 0, "wood"])
    members.append(["A3", n_seg-2, "wood"])
    if n_bot > 0:
        members.append(["A1", bot_start, "wood"])
        members.append(["A3", bot_start + n_bot - 1, "wood"])
        for i in range(n_bot):
            b = bot_start + i
            members.append([b, i, "wood"])
            members.append([b, i + 1, "wood"])
            if use_bottom_chord and i + 1 < n_bot:
                members.append([b, b + 1, "wood"])
    return {"nodes": nodes, "members": members}

# Topology C: Wood arch (compression arch from A1 to A3 supporting road)
def topo_arch_bridge(n_seg, arch_h, road_sag=0.0, mat="wood"):
    # Simple 5- or 6-segment arch from A1=(0,-2) to A3=(15,-2) peaking at y=arch_h
    nodes = []
    members = []
    for i in range(1, n_seg):
        t = i / n_seg
        x = 15.0 * t
        y = -4.0 * road_sag * t * (1.0 - t)
        nodes.append([round(x, 4), round(y, 4)])
    for i in range(n_seg):
        u = "A0" if i == 0 else i - 1
        v = "A2" if i == n_seg - 1 else i
        members.append([u, v, "road"])
    # Arch nodes directly below/above road nodes? No, at road x positions!
    # Wait: if arch is below road (arch_h <= -0.5), connect A1 -> arch[0] -> ... -> arch[n_seg-2] -> A3
    arch_start = len(nodes)
    for i in range(1, n_seg):
        t = i / n_seg
        x = 15.0 * t
        y = -2.0 + (arch_h - (-2.0)) * 4.0 * t * (1.0 - t)
        nodes.append([round(x, 4), round(y, 4)])
    for i in range(n_seg):
        u = "A1" if i == 0 else arch_start + i - 1
        v = "A3" if i == n_seg - 1 else arch_start + i
        members.append([u, v, mat])
    for i in range(n_seg - 1):
        members.append([i, arch_start + i, "wood"])
        # Add diagonals for shear stiffness
        if i < (n_seg - 1) // 2:
            members.append([arch_start + i, i + 1, "wood"])
        elif i > (n_seg - 1) // 2:
            members.append([arch_start + i, i - 1, "wood"])
    return {"nodes": nodes, "members": members}

# Topology D: Pure road catenary + just a few strategic cables from A0/A2 or A1/A3
def topo_cable_catenary(n_seg, sag, extra_cables):
    nodes = []
    members = []
    for i in range(1, n_seg):
        t = i / n_seg
        x = 15.0 * t
        y = -4.0 * sag * t * (1.0 - t)
        nodes.append([round(x, 4), round(y, 4)])
    for i in range(n_seg):
        u = "A0" if i == 0 else i - 1
        v = "A2" if i == n_seg - 1 else i
        members.append([u, v, "road"])
    for u, v, m in extra_cables:
        members.append([u, v, m])
    return {"nodes": nodes, "members": members}

# Topology E: Upper Warren truss (wood)
def topo_upper_warren(n_seg, h_mid, h_end, road_sag=0.0):
    nodes = []
    members = []
    for i in range(1, n_seg):
        t = i / n_seg
        x = 15.0 * t
        y = -4.0 * road_sag * t * (1.0 - t)
        nodes.append([round(x, 4), round(y, 4)])
    for i in range(n_seg):
        u = "A0" if i == 0 else i - 1
        v = "A2" if i == n_seg - 1 else i
        members.append([u, v, "road"])
    top_start = len(nodes)
    for i in range(n_seg):
        t = (i + 0.5) / n_seg
        x = 15.0 * t
        y = h_end + (h_mid - h_end) * 4.0 * t * (1.0 - t)
        nodes.append([round(x, 4), round(y, 4)])
    for i in range(n_seg):
        u = "A0" if i == 0 else i - 1
        v = "A2" if i == n_seg - 1 else i
        t_node = top_start + i
        members.append([u, t_node, "wood"])
        members.append([v, t_node, "wood"])
        if i + 1 < n_seg:
            members.append([t_node, t_node + 1, "wood"])
    return {"nodes": nodes, "members": members}

best = None
def try_d(label, d):
    global best
    ok, cost, pk, _ = eval_design(1, d)
    if ok:
        if best is None or cost < best[0]:
            best = (cost, label, pk, d)
            print(f"NEW BEST L1: {cost:.1f} ({label}) peak={pk*100:.1f}%")
            save_if_better(1, d, SUB / "level1.json")

# 1. Test braced catenary with minimal wood/cables
for n_seg in [7, 8]:
    for sag in [0.8, 1.0, 1.2, 1.4, 1.6, 1.8, 2.0]:
        try_d(f"cat_end_n{n_seg}_s{sag}", topo_catenary_braced(n_seg, sag, True, False))
        for k in [1, 2]:
            try_d(f"cat_cab_n{n_seg}_s{sag}_k{k}", topo_catenary_braced(n_seg, sag, True, True, (k, None)))
            try_d(f"cat_cab2_n{n_seg}_s{sag}_k{k}", topo_catenary_braced(n_seg, sag, True, True, (k, 1)))
            try_d(f"cat_cabonly_n{n_seg}_s{sag}_k{k}", topo_catenary_braced(n_seg, sag, False, True, (k, 1)))

# 2. Test under-truss
for n_seg in [7, 8]:
    for arch_y in [-2.5, -2.0, -1.5, -1.0]:
        for rsag in [-0.3, 0.0, 0.3, 0.6]:
            for bc in [True, False]:
                try_d(f"under_n{n_seg}_ay{arch_y}_rs{rsag}_bc{int(bc)}", topo_under_truss(n_seg, arch_y, rsag, bc))

# 3. Test upper Warren truss
for n_seg in [7]:
    for h_mid in [1.2, 1.6, 2.0, 2.4]:
        for h_end in [1.0, 1.4, 1.8]:
            try_d(f"warren_n{n_seg}_hm{h_mid}_he{h_end}", topo_upper_warren(n_seg, h_mid, h_end))

if best:
    print("\n=== BEST L1 SO FAR ===")
    eval_design(1, best[3], verbose=True)
