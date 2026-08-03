import json
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

hromadas = json.load(open('hromadas_full.json'))['list']
sectors_by_id = {}
for line in open('hromada_sectors.jsonl', encoding='utf-8'):
    d = json.loads(line)
    sectors_by_id[d['id']] = set(d['sectors'])

records = []
for r in hromadas:
    records.append({
        'id': r['Id'],
        'name': r['Name'],
        'oblast': r['Oblast'],
        'goals': r['Goals'] or '',
        'challenges': r['Challenges'] or '',
        'strengths': r['Strengths'] or '',
        'sectors': sectors_by_id[r['Id']],
    })

# --- Sector Jaccard (baseline, expected to be flat/uninformative) ---
def jaccard(a, b):
    return len(a & b) / len(a | b) if (a | b) else 0

# --- TF-IDF cosine on Goals text (the real discriminative signal) ---
goals_texts = [r['goals'] for r in records]
vec = TfidfVectorizer(token_pattern=r"(?u)\b\w\w+\b")
tfidf = vec.fit_transform(goals_texts)
sim = cosine_similarity(tfidf)

n = len(records)
edges = []
for i in range(n):
    for j in range(i+1, n):
        jac = jaccard(records[i]['sectors'], records[j]['sectors'])
        cos = sim[i][j]
        same_oblast = records[i]['oblast'] == records[j]['oblast']
        edges.append({
            'a': records[i]['name'],
            'b': records[j]['name'],
            'sector_jaccard': round(jac, 3),
            'goals_cosine': round(float(cos), 3),
            'same_oblast': same_oblast,
        })

edges.sort(key=lambda e: -e['goals_cosine'])
print(f"{'Pair':<70} {'Jaccard':>8} {'Cosine':>8} {'Oblast'}")
for e in edges:
    pair = f"{e['a'][:30]} <-> {e['b'][:30]}"
    print(f"{pair:<70} {e['sector_jaccard']:>8} {e['goals_cosine']:>8} {'SAME' if e['same_oblast'] else ''}")

json.dump(edges, open('matching_edges.json', 'w'), ensure_ascii=False, indent=2)
