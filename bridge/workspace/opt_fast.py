import json, copy, math, time, bridge as B, opt_lib as O

def optimize_design(lid, d, max_sec=25.0):
    t0 = time.time()
    lv = B.load_level(lid)
    mats = set(lv.get('allowed_materials', lv.get('materials', ['road','wood','steel','cable','spring','hydraulic'])))
    best_d = copy.deepcopy(d)
    ok, best_c, best_pk, _ = O.eval_level(lid, best_d)
    if not ok:
        return False, best_c, best_d
    O.save_if_best(lid, best_d)

    # Phase 1: Greedy member pruning + steel->wood/cable + wood->cable downgrades (sorted by cost savings!)
    P = B.parse_design(lv, best_d)
    # Identify non-road members sorted by length*unit_cost descending
    unit = {'road': 200, 'wood': 100, 'steel': 260, 'cable': 30, 'spring': 180, 'hydraulic': 400}
    improved = True
    while improved and time.time() - t0 < max_sec * 0.65:
        improved = False
        # Recompute member lengths/costs
        P = B.parse_design(lv, best_d)
        order = []
        for idx, m in enumerate(best_d['members']):
            mat = m[2]
            if mat == 'road': continue
            a, b = m[0], m[1]
            pa = lv['anchors'][int(a[1:])] if isinstance(a, str) else best_d['nodes'][a]
            pb = lv['anchors'][int(b[1:])] if isinstance(b, str) else best_d['nodes'][b]
            L = math.hypot(pa[0]-pb[0], pa[1]-pb[1])
            order.append((L * unit.get(mat, 0), idx))
        order.sort(reverse=True)

        # Try symmetric pairs or single members
        tried = set()
        for _, idx in order:
            if time.time() - t0 >= max_sec * 0.65: break
            if idx in tried or idx >= len(best_d['members']): continue
            m = best_d['members'][idx]
            mat = m[2]
            if mat == 'road': continue
            # Try removing first, then cable, then wood
            actions = ['REMOVE']
            if mat == 'steel':
                if 'cable' in mats: actions.append('cable')
                if 'wood' in mats: actions.append('wood')
            elif mat == 'wood':
                if 'cable' in mats: actions.append('cable')
            elif mat == 'spring':
                if 'cable' in mats: actions.append('cable')
                if 'wood' in mats: actions.append('wood')
            for act in actions:
                cand = copy.deepcopy(best_d)
                if act == 'REMOVE':
                    cand['members'].pop(idx)
                else:
                    cand['members'][idx][2] = act
                    if len(cand['members'][idx]) > 3:
                        cand['members'][idx] = cand['members'][idx][:3]
                ok2, c2, pk2, _ = O.eval_level(lid, cand)
                if ok2 and c2 < best_c - 0.5:
                    best_d, best_c, best_pk = cand, c2, pk2
                    O.save_if_best(lid, best_d)
                    improved = True
                    break
            if improved:
                break

    # Remove unused free nodes (keep indexing clean)
    used = set()
    for m in best_d['members']:
        for e in (m[0], m[1]):
            if isinstance(e, int): used.add(e)
    if len(used) < len(best_d['nodes']):
        nmap = {}
        new_nodes = []
        for i, pt in enumerate(best_d['nodes']):
            if i in used:
                nmap[i] = len(new_nodes); new_nodes.append(pt)
        cand = copy.deepcopy(best_d)
        cand['nodes'] = new_nodes
        for m in cand['members']:
            if isinstance(m[0], int): m[0] = nmap[m[0]]
            if isinstance(m[1], int): m[1] = nmap[m[1]]
        ok2, c2, pk2, _ = O.eval_level(lid, cand)
        if ok2:
            best_d, best_c, best_pk = cand, c2, pk2
            O.save_if_best(lid, best_d)

    # Phase 2: Coordinate descent on non-deck free nodes (y then x) to shrink bar lengths
    deck_nodes = set()
    for m in best_d['members']:
        if m[2] == 'road':
            if isinstance(m[0], int): deck_nodes.add(m[0])
            if isinstance(m[1], int): deck_nodes.add(m[1])
    free_struct = [i for i in range(len(best_d['nodes'])) if i not in deck_nodes]
    for step in [0.6, 0.3]:
        if time.time() - t0 >= max_sec: break
        for i in free_struct:
            if time.time() - t0 >= max_sec: break
            for axis in [1, 0]:
                for delta in [-step, step]:
                    cand = copy.deepcopy(best_d)
                    cand['nodes'][i][axis] = round(cand['nodes'][i][axis] + delta, 3)
                    ok2, c2, pk2, _ = O.eval_level(lid, cand)
                    if ok2 and c2 < best_c - 1.0:
                        best_d, best_c, best_pk = cand, c2, pk2
                        O.save_if_best(lid, best_d)
                        break
    return True, best_c, best_d

for lid in [4, 2, 3, 5, 1]:
    d = json.load(open(f'submission/level{lid}.json'))
    ok0, c0, pk0, _ = O.eval_level(lid, d)
    ok1, c1, _ = optimize_design(lid, d, max_sec=28.0)
    print(f'L{lid}: {c0:8.2f} -> {c1:8.2f} (saved {c0-c1:7.2f})', flush=True)
