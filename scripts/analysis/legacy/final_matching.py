import json, re
import difflib
from collections import defaultdict

# Use the WORKING (v3, unweighted mean-centered) scores as the base
edges = json.load(open('embed_edges54.json'))

d = json.load(open('hromadas_full54.json'))
hromadas = [r for r in d['list'] if r['SourceQuality'] in ('full-strategy','partial') and r['Goals']]
subgoals_by_name = {}
for r in hromadas:
    goals = (r['Goals'] or '').strip()
    lines = [l.strip(' \t-•\n') for l in re.split(r'\n', goals)]
    lines = [l for l in lines if len(l) > 15]
    subgoals_by_name[r['Name']] = lines

def norm(s):
    s = s.lower()
    s = re.sub(r'[^\w\s]', '', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s

def template_collision(name_a, name_b):
    """Return the most similar line-pair if there's a near-verbatim duplicate (likely shared template, not real content match)."""
    lines_a = subgoals_by_name.get(name_a, [])
    lines_b = subgoals_by_name.get(name_b, [])
    best = None
    for la in lines_a:
        na = norm(la)
        if len(na) < 20:
            continue
        for lb in lines_b:
            nb = norm(lb)
            if len(nb) < 20:
                continue
            ratio = difflib.SequenceMatcher(None, na, nb).ratio()
            if ratio > 0.75 and (best is None or ratio > best[2]):
                best = (la, lb, ratio)
    return best

# Score every edge, flag template collisions
for e in edges:
    coll = template_collision(e['a'], e['b'])
    e['template_collision'] = coll[2] if coll else 0.0
    e['collision_sample'] = coll[:2] if coll else None

by_score = sorted(edges, key=lambda e: -e['score'])

known_pairs = {
    frozenset(['Ніжинська міська територіальна громада', 'Козелецька селищна територіальна громада']),
    frozenset(['Батуринська міська територіальна громада', 'Козелецька селищна територіальна громада']),
    frozenset(['Ніжинська міська територіальна громада', 'Батуринська міська територіальна громада']),
}

print("=== TOP 20 by score, with template-collision flag ===\n")
for idx, e in enumerate(by_score[:20], 1):
    pk = frozenset([e['a'], e['b']])
    tag = '✓ KNOWN' if pk in known_pairs else ''
    flag = f"⚠️ TEMPLATE ({e['template_collision']:.2f})" if e['template_collision'] > 0.75 else ''
    print(f"{idx:>2}. {e['a'][:30]:<30} <-> {e['b'][:30]:<30} {e['score']:.3f} {tag} {flag}")
    if e['template_collision'] > 0.75:
        print(f"      collision: '{e['collision_sample'][0][:60]}' ~ '{e['collision_sample'][1][:60]}'")

print("\n=== CLEAN top 15 (score-sorted, template collisions removed) ===\n")
clean = [e for e in by_score if e['template_collision'] <= 0.75]
for idx, e in enumerate(clean[:15], 1):
    pk = frozenset([e['a'], e['b']])
    tag = '✓ KNOWN' if pk in known_pairs else ''
    print(f"{idx:>2}. {e['a'][:32]:<32} <-> {e['b'][:32]:<32} {e['score']:.3f} {tag}")

json.dump(edges, open('embed_edges54_flagged.json','w'), ensure_ascii=False, indent=2)
