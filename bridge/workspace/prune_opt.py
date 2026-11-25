import copy
import json
import math
import bridge as B
from opt_utils import eval_design, save_if_best


def prune_level(level_id, allow_node_opt=False):
    fn = f"submission/level{level_id}.json"
    best = B.load_json(fn)
    ok, best_cost, pk, _ = eval_design(level_id, best, quiet=True)
    assert ok, f"L{level_id} baseline not ok!"
    print(f"L{level_id} start: cost={best_cost:.2f}, pk={pk*100:.1f}%, members={len(best['members'])}")

    lv = B.load_level(level_id)
    anchors = [tuple(map(float, a)) for a in lv["anchors"]]

    def pos(d, u):
        if isinstance(u, str):
            return anchors[int(u[1:])]
        return d["nodes"][u]

    # Phase 1: Try downgrading steel -> wood/cable, cable -> wood, or removing non-road members!
    improved = True
    while improved:
        improved = False
        m_count = len(best["members"])
        # Order: most expensive members first
        idxs = list(range(m_count))
        idxs.sort(key=lambda i: -B.MATERIALS[best["members"][i][2]]["cost_m"] * math.hypot(
            pos(best, best["members"][i][0])[0] - pos(best, best["members"][i][1])[0],
            pos(best, best["members"][i][0])[1] - pos(best, best["members"][i][1])[1],
        ))
        for i in idxs:
            if i >= len(best["members"]):
                continue
            m = best["members"][i]
            mat = m[2]
            if mat in ("road", "hydraulic"):
                continue
            L = math.hypot(pos(best, m[0])[0] - pos(best, m[1])[0], pos(best, m[0])[1] - pos(best, m[1])[1])
            cands = []
            # Try removing member
            cands.append(("remove", None))
            if mat == "steel":
                if L <= 2.999:
                    cands.append(("wood", "wood"))
                cands.append(("cable", "cable"))
            elif mat == "cable":
                if L <= 2.999:
                    cands.append(("wood", "wood"))

            for label, new_mat in cands:
                cand = copy.deepcopy(best)
                if new_mat is None:
                    cand["members"].pop(i)
                else:
                    cand["members"][i][2] = new_mat
                ok, cost, pk2, _ = eval_design(level_id, cand, quiet=True)
                if ok and cost < best_cost - 1e-3:
                    best = cand
                    best_cost = cost
                    improved = True
                    print(f"  L{level_id} {label} m[{i}] ({mat}) -> cost={best_cost:.2f} (pk={pk2*100:.1f}%)")
                    save_if_best(level_id, best)
                    break
            if improved:
                break

    # Phase 2: Coordinate descent on y (and x for non-road nodes) to save length/cost
    if allow_node_opt:
        for step in [0.3, 0.15]:
            for ni in range(len(best["nodes"])):
                for dx, dy in [(0, step), (0, -step), (step, 0), (-step, 0)]:
                    cand = copy.deepcopy(best)
                    cand["nodes"][ni][0] = round(cand["nodes"][ni][0] + dx, 4)
                    cand["nodes"][ni][1] = round(cand["nodes"][ni][1] + dy, 4)
                    ok, cost, pk2, _ = eval_design(level_id, cand, quiet=True)
                    if ok and cost < best_cost - 1.0:
                        best = cand
                        best_cost = cost
                        print(f"  L{level_id} move node[{ni}] ({dx},{dy}) -> cost={best_cost:.2f}")
                        save_if_best(level_id, best)

    print(f"L{level_id} final: cost={best_cost:.2f}")


if __name__ == "__main__":
    for lid in [1, 3, 2, 4]:
        prune_level(lid, allow_node_opt=(lid in (1, 3)))
