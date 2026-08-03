import json
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

hromadas = json.load(open('hromadas_full13.json'))['list']
sectors_by_id = {}
for line in open('hromada_sectors13.jsonl', encoding='utf-8'):
    d = json.loads(line)
    sectors_by_id[d['id']] = set(d['sectors'])

records = []
for r in hromadas:
    records.append({
        'id': r['Id'], 'name': r['Name'], 'oblast': r['Oblast'],
        'goals': r['Goals'] or '', 'sectors': sectors_by_id[r['Id']],
    })

def jaccard(a, b):
    return len(a & b) / len(a | b) if (a | b) else 0

goals_texts = [r['goals'] for r in records]
vec = TfidfVectorizer(token_pattern=r"(?u)\b\w\w+\b")
tfidf = vec.fit_transform(goals_texts)
sim = cosine_similarity(tfidf)

# known/confirmed pairs (already validated ground truth) - exclude from "new match" spotlight
known_pairs = {
    frozenset(['Ніжинська міська територіальна громада', 'Козелецька селищна територіальна громада']),
    frozenset(['Батуринська міська територіальна громада', 'Козелецька селищна територіальна громада']),
    frozenset(['Ніжинська міська територіальна громада', 'Батуринська міська територіальна громада']),
}

n = len(records)
edges = []
for i in range(n):
    for j in range(i+1, n):
        jac = jaccard(records[i]['sectors'], records[j]['sectors'])
        cos = sim[i][j]
        pair_key = frozenset([records[i]['name'], records[j]['name']])
        edges.append({
            'a': records[i]['name'], 'b': records[j]['name'],
            'sector_jaccard': round(jac, 3), 'goals_cosine': round(float(cos), 3),
            'same_oblast': records[i]['oblast'] == records[j]['oblast'],
            'known': pair_key in known_pairs,
        })

edges.sort(key=lambda e: -e['goals_cosine'])
print(f"{'#':<3}{'Pair':<66} {'Cosine':>7} {'Jaccard':>8}  {'Oblast':<6} {'Known'}")
for idx, e in enumerate(edges, 1):
    pair = f"{e['a'][:32]:<32} <-> {e['b'][:32]}"
    print(f"{idx:<3}{pair:<66} {e['goals_cosine']:>7} {e['sector_jaccard']:>8}  {'SAME' if e['same_oblast'] else '':<6} {'✓ known МСС' if e['known'] else ''}")

json.dump(edges, open('matching_edges13.json', 'w'), ensure_ascii=False, indent=2)

print("\n=== TOP 10 NEW (unconfirmed) CANDIDATE MATCHES ===")
new_candidates = [e for e in edges if not e['known']]
for idx, e in enumerate(new_candidates[:10], 1):
    print(f"{idx}. {e['a']} <-> {e['b']}  cosine={e['goals_cosine']}  {'(same oblast)' if e['same_oblast'] else ''}")
