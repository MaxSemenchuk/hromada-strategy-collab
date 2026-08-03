import json
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from scipy.cluster.hierarchy import linkage, fcluster
from scipy.spatial.distance import squareform
from itertools import combinations

hromadas = json.load(open('hromadas_full30.json'))['list']
sectors_by_id = {}
for line in open('hromada_sectors30.jsonl', encoding='utf-8'):
    d = json.loads(line)
    sectors_by_id[d['id']] = set(d['sectors'])

records = []
for r in hromadas:
    records.append({'id': r['Id'], 'name': r['Name'], 'oblast': r['Oblast'],
                     'goals': r['Goals'] or '', 'sectors': sectors_by_id[r['Id']]})

n = len(records)
names = [r['name'] for r in records]

goals_texts = [r['goals'] for r in records]
vec = TfidfVectorizer(token_pattern=r"(?u)\b\w\w+\b")
tfidf = vec.fit_transform(goals_texts)
sim = cosine_similarity(tfidf)

# --- 1. Hierarchical clustering (average linkage) to find natural multi-member groups ---
dist = 1 - sim
np.fill_diagonal(dist, 0)
dist = (dist + dist.T) / 2  # symmetrize (float rounding)
condensed = squareform(dist, checks=False)
Z = linkage(condensed, method='average')

print("=== HIERARCHICAL CLUSTERS (cut at several thresholds) ===\n")
for k in [6, 8, 10]:
    labels = fcluster(Z, k, criterion='maxclust')
    print(f"--- {k} clusters ---")
    groups = {}
    for name, lab in zip(names, labels):
        groups.setdefault(lab, []).append(name)
    for lab, members in sorted(groups.items()):
        if len(members) > 1:
            print(f"  Cluster {lab}: {', '.join(m[:24] for m in members)}")
    print()

# --- 2. Clique detection: groups where ALL pairwise cosine >= threshold ---
print("=== TIGHT CLIQUES (all pairwise cosine >= 0.20) ===\n")
THRESH = 0.20
adj = sim >= THRESH
np.fill_diagonal(adj, False)

def find_cliques(adj, names, min_size=3):
    n = len(names)
    cliques = []
    # simple approach: check all combinations of size 3 and 4 (n=30 manageable)
    for size in [4, 3]:
        for combo in combinations(range(n), size):
            if all(adj[i][j] for i, j in combinations(combo, 2)):
                cliques.append(combo)
        # remove combos that are subsets of already-found larger cliques
    # dedupe: keep only maximal (not subset of another found clique)
    maximal = []
    for c in cliques:
        cs = set(c)
        if not any(cs < set(other) for other in cliques if other != c):
            maximal.append(c)
    # dedupe identical
    seen = set()
    result = []
    for c in maximal:
        key = tuple(sorted(c))
        if key not in seen:
            seen.add(key)
            result.append(c)
    return result

cliques = find_cliques(adj, names)
for c in cliques:
    members = [names[i] for i in c]
    # print avg pairwise cosine
    pairs = list(combinations(c, 2))
    avg = np.mean([sim[i][j] for i,j in pairs])
    print(f"  {{{', '.join(m[:26] for m in members)}}}  avg_cosine={avg:.3f}")

# --- 3. Digitalization / innovation-economy focused subgroup ---
print("\n=== DIGITALIZATION / INNOVATION-ECONOMY LENS ===\n")
digi_sectors = {"IT / цифровізація", "Е-врядування"}
digi_hromadas = [r for r in records if len(r['sectors'] & digi_sectors) == 2]
print(f"Hromadas with BOTH IT/digitalization AND E-governance sectors: {len(digi_hromadas)}")
for r in digi_hromadas:
    print(f"  - {r['name']}")

digi_idx = [i for i,r in enumerate(records) if r in digi_hromadas]
print(f"\nPairwise cosine among these {len(digi_idx)} digitally-focused hromadas (>=0.15 shown):")
for i, j in combinations(digi_idx, 2):
    if sim[i][j] >= 0.15:
        print(f"  {names[i][:28]:<28} <-> {names[j][:28]:<28} cosine={sim[i][j]:.3f}")
