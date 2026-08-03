import json
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

hromadas = json.load(open('hromadas_full23.json'))['list']
sectors_by_id = {}
for line in open('hromada_sectors23.jsonl', encoding='utf-8'):
    d = json.loads(line)
    sectors_by_id[d['id']] = set(d['sectors'])

records = []
for r in hromadas:
    records.append({'id': r['Id'], 'name': r['Name'], 'oblast': r['Oblast'],
                     'goals': r['Goals'] or '', 'sectors': sectors_by_id[r['Id']]})

known_pairs = {
    frozenset(['Ніжинська міська територіальна громада', 'Козелецька селищна територіальна громада']),
    frozenset(['Батуринська міська територіальна громада', 'Козелецька селищна територіальна громада']),
    frozenset(['Ніжинська міська територіальна громада', 'Батуринська міська територіальна громада']),
    frozenset(['Слобожанська селищна територіальна громада', 'Обухівська селищна територіальна громада']),
}

goals_texts = [r['goals'] for r in records]
vec = TfidfVectorizer(token_pattern=r"(?u)\b\w\w+\b")
tfidf = vec.fit_transform(goals_texts)
sim = cosine_similarity(tfidf)

n = len(records)
edges = []
for i in range(n):
    for j in range(i+1, n):
        pair_key = frozenset([records[i]['name'], records[j]['name']])
        edges.append({
            'a': records[i]['name'], 'b': records[j]['name'],
            'goals_cosine': round(float(sim[i][j]), 3),
            'same_oblast': records[i]['oblast'] == records[j]['oblast'],
            'known': pair_key in known_pairs,
        })

edges.sort(key=lambda e: -e['goals_cosine'])
print(f"Total pairs: {len(edges)}\n")
print("=== TOP 20 ===")
for idx, e in enumerate(edges[:20], 1):
    tag = '✓ KNOWN МСС' if e['known'] else ''
    print(f"{idx:>2}. {e['a'][:30]:<30} <-> {e['b'][:30]:<30} {e['goals_cosine']:>6} {'SAME-OBLAST' if e['same_oblast'] else ''} {tag}")

print("\n=== Where do known pairs rank? ===")
for idx, e in enumerate(edges, 1):
    if e['known']:
        print(f"#{idx} of {len(edges)}: {e['a']} <-> {e['b']}  cosine={e['goals_cosine']}")

json.dump(edges, open('matching_edges23.json', 'w'), ensure_ascii=False, indent=2)
