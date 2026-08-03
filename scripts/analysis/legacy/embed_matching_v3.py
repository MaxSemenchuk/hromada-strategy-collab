import json, re
import numpy as np
from sentence_transformers import SentenceTransformer

d = json.load(open('hromadas_full54.json'))
hromadas = [r for r in d['list'] if r['SourceQuality'] in ('full-strategy','partial') and r['Goals']]
print(f"Matching-eligible hromadas: {len(hromadas)}")

model = SentenceTransformer('intfloat/multilingual-e5-small')

records = []
for r in hromadas:
    goals = (r['Goals'] or '').strip()
    lines = [l.strip(' \t-•\n') for l in re.split(r'\n', goals)]
    lines = [l for l in lines if len(l) > 15]
    records.append({'id': r['Id'], 'name': r['Name'], 'oblast': r['Oblast'], 'goals': goals, 'subgoals': lines})

all_subgoals, subgoal_owner = [], []
for i, r in enumerate(records):
    sg = r['subgoals'] if r['subgoals'] else ([r['goals']] if r['goals'] else [])
    for s in sg:
        all_subgoals.append("query: " + s)
        subgoal_owner.append(i)

sub_emb = model.encode(all_subgoals, show_progress_bar=False, normalize_embeddings=True, batch_size=64)
mean_vec = sub_emb.mean(axis=0)
centered = sub_emb - mean_vec
norms = np.linalg.norm(centered, axis=1, keepdims=True)
centered = centered / np.clip(norms, 1e-8, None)

n = len(records)
sub_idx = {i: [] for i in range(n)}
for k, owner in enumerate(subgoal_owner):
    sub_idx[owner].append(k)

def best_match(i, j):
    idx_i, idx_j = sub_idx[i], sub_idx[j]
    if not idx_i or not idx_j:
        return 0.0
    sims = centered[idx_i] @ centered[idx_j].T
    return float((sims.max(axis=1).mean() + sims.max(axis=0).mean()) / 2)

known_pairs = {
    frozenset(['Ніжинська міська територіальна громада', 'Козелецька селищна територіальна громада']),
    frozenset(['Батуринська міська територіальна громада', 'Козелецька селищна територіальна громада']),
    frozenset(['Ніжинська міська територіальна громада', 'Батуринська міська територіальна громада']),
    frozenset(['Слобожанська селищна територіальна громада', 'Обухівська селищна територіальна громада']),
}
already_discussed = {
    frozenset(['Ужгородська міська територіальна громада', 'Мукачівська міська територіальна громада']),
    frozenset(['Дніпровська міська територіальна громада', 'Львівська міська територіальна громада']),
    frozenset(['Новомосковська міська територіальна громада', 'Запорізька міська територіальна громада']),
}

edges = []
for i in range(n):
    for j in range(i+1, n):
        pk = frozenset([records[i]['name'], records[j]['name']])
        edges.append({'a': records[i]['name'], 'b': records[j]['name'],
                       'score': round(best_match(i,j), 3),
                       'known': pk in known_pairs, 'discussed': pk in already_discussed})

by_score = sorted(edges, key=lambda e: -e['score'])
print(f"\nTotal pairs: {len(edges)}\n")
print("=== TOP 20 overall ===")
for idx, e in enumerate(by_score[:20], 1):
    tag = '✓ KNOWN' if e['known'] else ('· already discussed' if e['discussed'] else '')
    print(f"{idx:>2}. {e['a'][:32]:<32} <-> {e['b'][:32]:<32} {e['score']:.3f} {tag}")

print("\n=== TOP 15 NEW (excluding known + already-discussed) ===")
new_edges = [e for e in by_score if not e['known'] and not e['discussed']]
for idx, e in enumerate(new_edges[:15], 1):
    print(f"{idx:>2}. {e['a'][:32]:<32} <-> {e['b'][:32]:<32} {e['score']:.3f}")

json.dump(edges, open('embed_edges54.json','w'), ensure_ascii=False, indent=2)
