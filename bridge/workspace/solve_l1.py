import json
import subprocess
import sys

def make_truss_below(n_panels=6, depth=2.0):
    # n_panels = 6 -> 2.5m each
    dx = 15.0 / n_panels
    nodes = []
    members = []
    # top deck nodes: 0 .. n_panels-2 (at x = dx, 2*dx, ..., (n_panels-1)*dx)
    for i in range(1, n_panels):
        nodes.append([round(i * dx, 4), 0.0])
    # road segments
    for i in range(n_panels):
        u = "A0" if i == 0 else i - 1
        v = "A2" if i == n_panels - 1 else i
        members.append([u, v, "road"])
    
    # bottom chord nodes: at x = (i + 0.5) * dx, y = -depth
    b_start = len(nodes)
    for i in range(n_panels):
        nodes.append([round((i + 0.5) * dx, 4), round(-depth, 4)])
    
    # diagonals from top to bottom
    for i in range(n_panels):
        u = "A0" if i == 0 else i - 1
        v = "A2" if i == n_panels - 1 else i
        b = b_start + i
        members.append([u, b, "wood"])
        members.append([b, v, "wood"])
    
    # bottom chord horizontals
    for i in range(n_panels - 1):
        members.append([b_start + i, b_start + i + 1, "wood"])
    
    # connect ends to A1=(0,-2) and A3=(15,-2) if helpful
    members.append(["A1", b_start, "wood"])
    members.append([b_start + n_panels - 1, "A3", "wood"])
    
    return {"nodes": nodes, "members": members}

def test_design(design, level="1"):
    with open("tmp_test.json", "w") as f:
        json.dump(design, f)
    res = subprocess.run(
        [sys.executable, "bridge.py", "run", str(level), "tmp_test.json", "-q"],
        capture_output=True, text=True
    )
    return res.returncode == 0, res.stdout + res.stderr

if __name__ == "__main__":
    best_cost = 1e9
    best_design = None
    for depth in [1.2, 1.5, 1.8, 2.0, 2.2]:
        d = make_truss_below(6, depth)
        ok, out = test_design(d, 1)
        # parse cost from check
        chk = subprocess.run([sys.executable, "bridge.py", "check", "1", "tmp_test.json"], capture_output=True, text=True)
        cost = None
        for line in chk.stdout.splitlines():
            if "造价" in line or "cost" in line.lower():
                # extract number
                import re
                m = re.search(r"(\d+(?:\.\d+)?)", line)
                if m:
                    cost = float(m.group(1))
        print(f"depth={depth}: ok={ok}, cost={cost}")
        if ok and cost and cost < best_cost:
            best_cost = cost
            best_design = d
    if best_design:
        with open("submission/level1.json", "w") as f:
            json.dump(best_design, f, indent=2)
        print(f"Saved best Level 1 design with cost {best_cost}")
    else:
        print("Failed to find passing design")
