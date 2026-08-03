import json, re
import numpy as np
from sentence_transformers import SentenceTransformer

hromadas = json.load(open('hromadas_full46.json'))['list']
model = SentenceTransformer('intfloat/multilingual-e5-small')

records = []
for r in hromadas:
    goals = (r['Goals'] or '').strip()
    lines = [l.strip(' \t-•\n') for l in re.split(r'\n', goals)]
    lines = [l for l in lines if len(l) > 15]
    records.append({'id': r['Id'], 'name': r['Name'], 'goals': goals, 'subgoals': lines})

all_subgoals, subgoal_owner = [], []
for i, r in enumerate(records):
    sg = r['subgoals'] if r['subgoals'] else ([r['goals']] if r['goals'] else [])
    for s in sg:
        all_subgoals.append("query: " + s)
        subgoal_owner.append(i)

sub_emb = model.encode(all_subgoals, show_progress_bar=False, normalize_embeddings=True, batch_size=64)

# MEAN-CENTER: subtract corpus-mean sub-goal vector, then re-normalize
mean_vec = sub_emb.mean(axis=0)
centered = sub_emb - mean_vec
norms = np.linalg.norm(centered, axis=1, keepdims=True)
centered = centered / np.clip(norms, 1e-8, None)

n = len(records)
sub_idx_by_hromada = {i: [] for i in range(n)}
for k, owner in enumerate(subgoal_owner):
    sub_idx_by_hromada[owner].append(k)

def bipartite_best_match(i, j, emb):
    idx_i, idx_j = sub_idx_by_hromada[i], sub_idx_by_hromada[j]
    if not idx_i or not idx_j:
        return 0.0
    sims = emb[idx_i] @ emb[idx_j].T
    return float((sims.max(axis=1).mean() + sims.max(axis=0).mean()) / 2)

known_pairs = {
    frozenset(['Ніжинська міська територіальна громада', 'Козелецька селищна територіальна громада']),
    frozenset(['Батуринська міська територіальна громада', 'Козелецька селищна територіальна громада']),
    frozenset(['Ніжинська міська територіальна громада', 'Батуринська міська територіальна громада']),
    frozenset(['Слобожанська селищна територіальна громада', 'Обухівська селищна територіальна громада']),
}

edges = []
for i in range(n):
    for j in range(i+1, n):
        pk = frozenset([records[i]['name'], records[j]['name']])
        edges.append({'a': records[i]['name'], 'b': records[j]['name'],
                       'centered_best': round(bipartite_best_match(i,j,centered), 3),
                       'known': pk in known_pairs})

by_c = sorted(edges, key=lambda e: -e['centered_best'])
c_rank = {frozenset([e['a'],e['b']]): i+1 for i,e in enumerate(by_c)}

print("=== TOP 15 by MEAN-CENTERED sub-goal best-match ===")
for idx, e in enumerate(by_c[:15], 1):
    tag = '✓ KNOWN' if e['known'] else ''
    print(f"{idx:>2}. {e['a'][:30]:<30} <-> {e['b'][:30]:<30} score={e['centered_best']:.3f} {tag}")

print("\n=== Known pairs rank (centered) ===")
for e in edges:
    if e['known']:
        k = frozenset([e['a'],e['b']])
        print(f"{e['a'][:28]:<28} <-> {e['b'][:28]:<28} rank=#{c_rank[k]} of {len(edges)} score={e['centered_best']:.3f}")

print("\n=== Poltava-Zhytomyr (centered) ===")
for e in edges:
    if {'Полтавська' in e['a'] or 'Полтавська' in e['b']} and ('Житомирська' in e['a'] or 'Житомирська' in e['b']):
        if ('Полтавська' in e['a'] and 'Житомирська' in e['b']) or ('Полтавська' in e['b'] and 'Житомирська' in e['a']):
            k = frozenset([e['a'],e['b']])
            print(f"rank=#{c_rank[k]} of {len(edges)} score={e['centered_best']:.3f}")

print("\n=== Uzhhorod-Mukachevo (centered) ===")
for e in edges:
    if ('Ужгородська' in e['a'] and 'Мукачівська' in e['b']) or ('Ужгородська' in e['b'] and 'Мукачівська' in e['a']):
        k = frozenset([e['a'],e['b']])
        print(f"rank=#{c_rank[k]} of {len(edges)} score={e['centered_best']:.3f}")
