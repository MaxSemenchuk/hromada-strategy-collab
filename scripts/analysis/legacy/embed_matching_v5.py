import json, re
import numpy as np
from sentence_transformers import SentenceTransformer

d = json.load(open('hromadas_full54.json'))
hromadas = [r for r in d['list'] if r['SourceQuality'] in ('full-strategy','partial') and r['Goals']]
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

sub_emb = model.encode(all_subgoals, show_progress_bar=False, normalize_embeddings=True, batch_size=64)  # RAW, uncentered
mean_vec = sub_emb.mean(axis=0)
centered = sub_emb - mean_vec
centered = centered / np.clip(np.linalg.norm(centered, axis=1, keepdims=True), 1e-8, None)

n = len(records)
N = len(all_subgoals)
owner_arr = np.array(subgoal_owner)
sub_idx = {i: [] for i in range(n)}
for k, owner in enumerate(subgoal_owner):
    sub_idx[owner].append(k)

# --- Document-frequency style weight: how many DISTINCT hromadas have a near-duplicate of subgoal k? ---
raw_sim = sub_emb @ sub_emb.T  # RAW similarity (not centered) - near-verbatim duplicates show up here as very high
THRESH = 0.90
df = np.zeros(N, dtype=int)
for k in range(N):
    owners_matched = set(owner_arr[raw_sim[k] > THRESH]) - {owner_arr[k]}
    df[k] = len(owners_matched)

print("DF (distinct-hromadas-with-near-duplicate) distribution:")
vals, counts = np.unique(df, return_counts=True)
for v, c in zip(vals, counts):
    print(f"  DF={v}: {c} subgoals")

order = np.argsort(-df)
print("\nHighest-DF (most templated/boilerplate) lines:")
for k in order[:6]:
    print(f"  DF={df[k]:>2} [{records[owner_arr[k]]['name'][:20]}] {all_subgoals[k][7:75]}")

# IDF-style weight: heavily penalize only near-universal duplicates (DF >= 5), leave everything else alone
weight = 1.0 / (1.0 + np.log1p(np.maximum(df - 2, 0)))  # DF<=2 -> weight=1.0 (untouched); grows harsher after that

def weighted_best_match(i, j):
    idx_i, idx_j = sub_idx[i], sub_idx[j]
    if not idx_i or not idx_j:
        return 0.0
    sims = centered[np.ix_(idx_i, idx_j)]
    wi, wj = weight[idx_i], weight[idx_j]
    best_i = sims.max(axis=1); best_j = sims.max(axis=0)
    return float((np.average(best_i, weights=wi) + np.average(best_j, weights=wj)) / 2)

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
                       'score': round(weighted_best_match(i,j), 3), 'known': pk in known_pairs})

by_score = sorted(edges, key=lambda e: -e['score'])
rank = {frozenset([e['a'],e['b']]): idx+1 for idx,e in enumerate(by_score)}

print(f"\n=== TOP 20 (DF-weighted) ===")
for idx, e in enumerate(by_score[:20], 1):
    tag = '✓ KNOWN' if e['known'] else ''
    print(f"{idx:>2}. {e['a'][:32]:<32} <-> {e['b'][:32]:<32} {e['score']:.3f} {tag}")

print("\n=== Sanity checks ===")
for e in edges:
    if e['known']:
        k = frozenset([e['a'],e['b']])
        print(f"KNOWN: {e['a'][:25]:<25}<->{e['b'][:25]:<25} rank=#{rank[k]} score={e['score']:.3f}")
for e in edges:
    if ('Ганнівська' in e['a'] and 'Тульчинська' in e['b']) or ('Ганнівська' in e['b'] and 'Тульчинська' in e['a']):
        k = frozenset([e['a'],e['b']]); print(f"Ганнівська-Тульчинська: rank=#{rank[k]} score={e['score']:.3f}")
for e in edges:
    if ('Галицька' in e['a'] and 'Дубовецька' in e['b']) or ('Галицька' in e['b'] and 'Дубовецька' in e['a']):
        k = frozenset([e['a'],e['b']]); print(f"Галицька-Дубовецька: rank=#{rank[k]} score={e['score']:.3f}")
for e in edges:
    if ('Новомосковська' in e['a'] and 'Запорізька' in e['b']) or ('Новомосковська' in e['b'] and 'Запорізька' in e['a']):
        k = frozenset([e['a'],e['b']]); print(f"Новомосковськ-Запоріжжя: rank=#{rank[k]} score={e['score']:.3f}")
for e in edges:
    if ('Ужгородська' in e['a'] and 'Мукачівська' in e['b']) or ('Ужгородська' in e['b'] and 'Мукачівська' in e['a']):
        k = frozenset([e['a'],e['b']]); print(f"Ужгород-Мукачево: rank=#{rank[k]} score={e['score']:.3f}")

json.dump(edges, open('embed_edges54_final.json','w'), ensure_ascii=False, indent=2)
