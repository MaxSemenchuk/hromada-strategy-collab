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

N = len(all_subgoals)
full_sim = centered @ centered.T  # N x N

# --- Distinctiveness weight: how similar is subgoal k to subgoals of OTHER hromadas (not its own)? ---
# High avg similarity to others => boilerplate/templated => low distinctiveness weight
owner_arr = np.array(subgoal_owner)
distinct_w = np.zeros(N)
for k in range(N):
    mask = owner_arr != owner_arr[k]
    avg_sim_to_others = full_sim[k][mask].mean()
    distinct_w[k] = avg_sim_to_others

print("\nDistinctiveness raw score distribution (avg sim to other hromadas' subgoals):")
print(f"  min={distinct_w.min():.3f} max={distinct_w.max():.3f} mean={distinct_w.mean():.3f} std={distinct_w.std():.3f}")

# Convert to a weight: penalize high-boilerplate (high avg-sim-to-others) subgoals.
# Use rank-based percentile so it's robust to distribution shape, then invert.
ranks = distinct_w.argsort().argsort() / (N - 1)  # 0=most distinctive(lowest avg sim), 1=most boilerplate
weight = (1 - ranks) ** 2  # sharpen: boilerplate lines get strongly downweighted

# show the most boilerplate and most distinctive lines
order = np.argsort(-distinct_w)
print("\nMost BOILERPLATE subgoals (highest avg similarity to other hromadas):")
for k in order[:5]:
    print(f"  [{records[owner_arr[k]]['name'][:20]}] {all_subgoals[k][7:80]}  (avgsim={distinct_w[k]:.3f})")
print("\nMost DISTINCTIVE subgoals (lowest avg similarity to other hromadas):")
for k in order[-5:]:
    print(f"  [{records[owner_arr[k]]['name'][:20]}] {all_subgoals[k][7:80]}  (avgsim={distinct_w[k]:.3f})")

def weighted_best_match(i, j):
    idx_i, idx_j = sub_idx[i], sub_idx[j]
    if not idx_i or not idx_j:
        return 0.0
    sims = centered[np.ix_(idx_i, idx_j)]
    wi = weight[idx_i]; wj = weight[idx_j]
    best_for_i = sims.max(axis=1)  # best match score for each subgoal in i
    best_for_j = sims.max(axis=0)
    score_i = np.average(best_for_i, weights=wi)
    score_j = np.average(best_for_j, weights=wj)
    return float((score_i + score_j) / 2)

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

print(f"\n=== TOP 20 with DISTINCTIVENESS-WEIGHTED matching ===")
for idx, e in enumerate(by_score[:20], 1):
    tag = '✓ KNOWN' if e['known'] else ''
    print(f"{idx:>2}. {e['a'][:32]:<32} <-> {e['b'][:32]:<32} {e['score']:.3f} {tag}")

print("\n=== Known pairs rank ===")
for e in edges:
    if e['known']:
        k = frozenset([e['a'],e['b']])
        print(f"{e['a'][:28]:<28} <-> {e['b'][:28]:<28} rank=#{rank[k]} score={e['score']:.3f}")

print("\n=== Check: did Ганнівська-Тульчинська drop? ===")
for e in edges:
    if {'Ганнівська' in e['a'] or 'Ганнівська' in e['b']} and ('Тульчинська' in e['a'] or 'Тульчинська' in e['b']):
        k = frozenset([e['a'],e['b']])
        print(f"rank=#{rank[k]} score={e['score']:.3f}")

print("\n=== Check: Галицька-Дубовецька (real named project) ===")
for e in edges:
    if ('Галицька' in e['a'] and 'Дубовецька' in e['b']) or ('Галицька' in e['b'] and 'Дубовецька' in e['a']):
        k = frozenset([e['a'],e['b']])
        print(f"rank=#{rank[k]} score={e['score']:.3f}")

json.dump(edges, open('embed_edges54_weighted.json','w'), ensure_ascii=False, indent=2)
