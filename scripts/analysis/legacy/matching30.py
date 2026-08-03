import json
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

hromadas = json.load(open('hromadas_full30.json'))['list']
sectors_by_id = {}
for line in open('hromada_sectors30.jsonl', encoding='utf-8'):
    d = json.loads(line)
    sectors_by_id[d['id']] = set(d['sectors'])

ADJ = {
    "Чернігівська область": {"Київська область", "Сумська область", "Полтавська область"},
    "Сумська область": {"Чернігівська область", "Полтавська область", "Харківська область"},
    "Харківська область": {"Сумська область", "Полтавська область", "Дніпропетровська область", "Донецька область", "Луганська область"},
    "Полтавська область": {"Чернігівська область", "Сумська область", "Харківська область", "Дніпропетровська область", "Кіровоградська область", "Черкаська область", "Київська область"},
    "Дніпропетровська область": {"Полтавська область", "Харківська область", "Донецька область", "Запорізька область", "Херсонська область", "Кіровоградська область"},
    "Запорізька область": {"Дніпропетровська область", "Донецька область", "Херсонська область"},
    "Херсонська область": {"Дніпропетровська область", "Запорізька область", "Миколаївська область", "Автономна Республіка Крим"},
    "Миколаївська область": {"Херсонська область", "Одеська область", "Кіровоградська область"},
    "Одеська область": {"Миколаївська область", "Кіровоградська область", "Вінницька область"},
    "Кіровоградська область": {"Полтавська область", "Дніпропетровська область", "Миколаївська область", "Одеська область", "Черкаська область", "Вінницька область"},
    "Черкаська область": {"Полтавська область", "Кіровоградська область", "Київська область", "Вінницька область"},
    "Київська область": {"Чернігівська область", "Полтавська область", "Черкаська область", "Житомирська область"},
    "Вінницька область": {"Одеська область", "Кіровоградська область", "Черкаська область", "Житомирська область", "Хмельницька область"},
    "Житомирська область": {"Київська область", "Вінницька область", "Хмельницька область", "Рівненська область"},
    "Хмельницька область": {"Вінницька область", "Житомирська область", "Рівненська область", "Тернопільська область", "Чернівецька область"},
    "Рівненська область": {"Житомирська область", "Хмельницька область", "Тернопільська область", "Львівська область", "Волинська область"},
    "Волинська область": {"Рівненська область", "Львівська область"},
    "Львівська область": {"Волинська область", "Рівненська область", "Тернопільська область", "Івано-Франківська область", "Закарпатська область"},
    "Тернопільська область": {"Рівненська область", "Хмельницька область", "Чернівецька область", "Івано-Франківська область", "Львівська область"},
    "Чернівецька область": {"Хмельницька область", "Тернопільська область", "Івано-Франківська область"},
    "Івано-Франківська область": {"Львівська область", "Тернопільська область", "Чернівецька область", "Закарпатська область"},
    "Закарпатська область": {"Львівська область", "Івано-Франківська область"},
    "Донецька область": {"Харківська область", "Дніпропетровська область", "Запорізька область", "Луганська область"},
    "Луганська область": {"Харківська область", "Донецька область"},
    "Автономна Республіка Крим": {"Херсонська область"},
}

def norm_rayon(r):
    return r.split("(")[0].strip() if r else None

def proximity(a, b):
    if a['oblast'] == b['oblast']:
        ra, rb = norm_rayon(a['rayon']), norm_rayon(b['rayon'])
        if ra and rb and ra == rb:
            return 1.0
        return 0.7
    if b['oblast'] in ADJ.get(a['oblast'], set()):
        return 0.3
    return 0.0

records = []
for r in hromadas:
    records.append({'id': r['Id'], 'name': r['Name'], 'oblast': r['Oblast'], 'rayon': r['Rayon'],
                     'goals': r['Goals'] or '', 'sectors': sectors_by_id[r['Id']]})

known_pairs = {
    frozenset(['Ніжинська міська територіальна громада', 'Козелецька селищна територіальна громада']),
    frozenset(['Батуринська міська територіальна громада', 'Козелецька селищна територіальна громада']),
    frozenset(['Ніжинська міська територіальна громада', 'Батуринська міська територіальна громада']),
    frozenset(['Слобожанська селищна територіальна громада', 'Обухівська селищна територіальна громада']),
}
# hromadas known to be substantively DIFFERENT tourism (mountain/nature) - discrimination check
mountain_tourism = {'Яремчанська міська територіальна громада', 'Вижницька міська територіальна громада'}

goals_texts = [r['goals'] for r in records]
vec = TfidfVectorizer(token_pattern=r"(?u)\b\w\w+\b")
tfidf = vec.fit_transform(goals_texts)
sim = cosine_similarity(tfidf)

n = len(records)
edges = []
W_COSINE, W_PROX = 0.6, 0.4
for i in range(n):
    for j in range(i+1, n):
        cos = round(float(sim[i][j]), 3)
        prox = proximity(records[i], records[j])
        combined = round(W_COSINE*cos + W_PROX*prox, 3)
        pair_key = frozenset([records[i]['name'], records[j]['name']])
        edges.append({'a': records[i]['name'], 'b': records[j]['name'],
                      'cosine': cos, 'proximity': prox, 'combined': combined,
                      'known': pair_key in known_pairs})

print(f"Total pairs: {len(edges)}\n")
by_cosine = sorted(edges, key=lambda e: -e['cosine'])
cosine_rank = {frozenset([e['a'],e['b']]): i+1 for i,e in enumerate(by_cosine)}

print("=== TOP 15 by pure goals cosine ===")
for idx, e in enumerate(by_cosine[:15], 1):
    tag = '✓ KNOWN' if e['known'] else ''
    print(f"{idx:>2}. {e['a'][:30]:<30} <-> {e['b'][:30]:<30} cos={e['cosine']:.3f} {tag}")

print("\n=== Discrimination check: mountain-tourism hromadas vs Cossack-heritage cluster ===")
cluster = {'Ніжинська міська територіальна громада','Батуринська міська територіальна громада','Козелецька селищна територіальна громада'}
for e in edges:
    if (e['a'] in mountain_tourism and e['b'] in cluster) or (e['b'] in mountain_tourism and e['a'] in cluster):
        key = frozenset([e['a'],e['b']])
        print(f"{e['a'][:28]:<28} <-> {e['b'][:28]:<28} cosine={e['cosine']:.3f} (rank #{cosine_rank[key]} of {len(edges)})")

print("\n=== Known pairs: cosine-only rank ===")
for e in edges:
    if e['known']:
        key = frozenset([e['a'],e['b']])
        print(f"{e['a'][:28]:<28} <-> {e['b'][:28]:<28} cosine={e['cosine']:.3f} rank=#{cosine_rank[key]} of {len(edges)}")

by_combined = sorted(edges, key=lambda e: -e['combined'])
combined_rank = {frozenset([e['a'],e['b']]): i+1 for i,e in enumerate(by_combined)}
print("\n=== Known pairs: combined rank ===")
for e in edges:
    if e['known']:
        key = frozenset([e['a'],e['b']])
        print(f"{e['a'][:28]:<28} <-> {e['b'][:28]:<28} combined=#{combined_rank[key]} of {len(edges)}")

print(f"\n=== TOP 15 NEW candidates by pure cosine (excluding known pairs) ===")
new_c = [e for e in by_cosine if not e['known']]
for idx, e in enumerate(new_c[:15], 1):
    print(f"{idx:>2}. {e['a'][:30]:<30} <-> {e['b'][:30]:<30} cos={e['cosine']:.3f}")

json.dump(edges, open('matching_edges30.json', 'w'), ensure_ascii=False, indent=2)
