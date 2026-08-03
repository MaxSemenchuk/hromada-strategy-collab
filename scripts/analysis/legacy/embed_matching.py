import json, re
import numpy as np
from sentence_transformers import SentenceTransformer

hromadas = json.load(open('hromadas_full46.json'))['list']
model = SentenceTransformer('intfloat/multilingual-e5-small')

records = []
for r in hromadas:
    goals = (r['Goals'] or '').strip()
    # split into sub-goals: lines, filter noise
    lines = [l.strip(' \t-•\n') for l in re.split(r'\n', goals)]
    lines = [l for l in lines if len(l) > 15]  # drop empty/tiny fragments
    records.append({'id': r['Id'], 'name': r['Name'], 'oblast': r['Oblast'],
                     'sq': r['SourceQuality'], 'goals': goals, 'subgoals': lines})

# Document-level embeddings
doc_texts = ["query: " + (r['goals'] if r['goals'] else "немає даних") for r in records]
doc_emb = model.encode(doc_texts, show_progress_bar=False, normalize_embeddings=True)

# Sub-goal embeddings (flattened, with back-reference to hromada index)
all_subgoals = []
subgoal_owner = []
for i, r in enumerate(records):
    sg = r['subgoals'] if r['subgoals'] else [r['goals']] if r['goals'] else []
    for s in sg:
        all_subgoals.append("query: " + s)
        subgoal_owner.append(i)

print(f"Total sub-goals across {len(records)} hromadas: {len(all_subgoals)}")
sub_emb = model.encode(all_subgoals, show_progress_bar=False, normalize_embeddings=True, batch_size=64)

n = len(records)
sub_idx_by_hromada = {i: [] for i in range(n)}
for k, owner in enumerate(subgoal_owner):
    sub_idx_by_hromada[owner].append(k)

def doc_cosine(i, j):
    return float(np.dot(doc_emb[i], doc_emb[j]))

def bipartite_best_match(i, j):
    idx_i, idx_j = sub_idx_by_hromada[i], sub_idx_by_hromada[j]
    if not idx_i or not idx_j:
        return 0.0
    sims = sub_emb[idx_i] @ sub_emb[idx_j].T  # (len_i, len_j)
    # symmetric best-match: avg(max over j for each i, max over i for each j)
    best_i = sims.max(axis=1).mean()
    best_j = sims.max(axis=0).mean()
    return float((best_i + best_j) / 2)

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
        edges.append({
            'a': records[i]['name'], 'b': records[j]['name'],
            'doc_emb_cos': round(doc_cosine(i,j), 3),
            'subgoal_best': round(bipartite_best_match(i,j), 3),
            'known': pk in known_pairs,
        })

json.dump(edges, open('embed_edges46.json','w'), ensure_ascii=False, indent=2)

print("\n=== TOP 15 by SUB-GOAL BEST-MATCH (new method) ===")
by_sub = sorted(edges, key=lambda e: -e['subgoal_best'])
for idx, e in enumerate(by_sub[:15], 1):
    tag = '✓ KNOWN' if e['known'] else ''
    print(f"{idx:>2}. {e['a'][:30]:<30} <-> {e['b'][:30]:<30} subgoal={e['subgoal_best']:.3f} doc={e['doc_emb_cos']:.3f} {tag}")

print("\n=== Known pairs: doc-embedding vs sub-goal-best rank ===")
sub_rank = {frozenset([e['a'],e['b']]): i+1 for i,e in enumerate(by_sub)}
by_doc = sorted(edges, key=lambda e: -e['doc_emb_cos'])
doc_rank = {frozenset([e['a'],e['b']]): i+1 for i,e in enumerate(by_doc)}
for e in edges:
    if e['known']:
        k = frozenset([e['a'],e['b']])
        print(f"{e['a'][:28]:<28} <-> {e['b'][:28]:<28} doc_rank=#{doc_rank[k]} subgoal_rank=#{sub_rank[k]} of {len(edges)}")

print("\n=== Poltava-Zhytomyr check (was #1 false-positive risk with TF-IDF) ===")
for e in edges:
    if {'Полтавська міська територіальна громада','Житомирська міська територіальна громада'} <= {e['a'],e['b']} or \
       (e['a'].startswith('Полтавська') and e['b'].startswith('Житомирська')) or (e['b'].startswith('Полтавська') and e['a'].startswith('Житомирська')):
        k = frozenset([e['a'],e['b']])
        print(f"doc_rank=#{doc_rank[k]} subgoal_rank=#{sub_rank[k]} of {len(edges)}  doc_cos={e['doc_emb_cos']:.3f} subgoal_best={e['subgoal_best']:.3f}")

print("\n=== Vinnytsia's best matches (was isolated under TF-IDF) ===")
vin_edges = [e for e in edges if 'Вінницька' in e['a'] or 'Вінницька' in e['b']]
vin_edges.sort(key=lambda e: -e['subgoal_best'])
for e in vin_edges[:8]:
    k = frozenset([e['a'],e['b']])
    other = e['b'] if 'Вінницька' in e['a'] else e['a']
    print(f"Вінниця <-> {other[:30]:<30} subgoal_best={e['subgoal_best']:.3f} (rank #{sub_rank[k]})")

print("\n=== Uzhhorod-Mukachevo check ===")
for e in edges:
    if {'Ужгородська' in e['a'] or 'Ужгородська' in e['b']} and ('Мукачівська' in e['a'] or 'Мукачівська' in e['b']):
        if ('Ужгородська' in e['a'] and 'Мукачівська' in e['b']) or ('Ужгородська' in e['b'] and 'Мукачівська' in e['a']):
            k = frozenset([e['a'],e['b']])
            print(f"doc_rank=#{doc_rank[k]} subgoal_rank=#{sub_rank[k]} of {len(edges)}  subgoal_best={e['subgoal_best']:.3f}")
