import json
import networkx as nx
from collections import defaultdict, Counter

data = json.load(open('mss_graph_mvp_data.json'))
raw_edges = data['edges']

# Dedupe: aggregate by unordered (a,b) pair
agg = defaultdict(lambda: {'categories': set(), 'dates': set(), 'count': 0})
for e in raw_edges:
    key = tuple(sorted([e['a'], e['b']]))
    agg[key]['categories'].add(e['category'])
    agg[key]['dates'].add(e['date'])
    agg[key]['count'] += 1

print(f"Unique (a,b) pairs after dedup: {len(agg)}")

G = nx.Graph()
for (a, b), info in agg.items():
    G.add_edge(a, b, categories=list(info['categories']), n=info['count'])

print(f"Nodes: {G.number_of_nodes()}, Edges: {G.number_of_edges()}")
degrees = dict(G.degree())
deg_dist = Counter(degrees.values())
print("Degree distribution (top):", sorted(deg_dist.items())[:10])

# For a clean MVP visual: take nodes with degree >= 2 (actively multi-connected hromadas)
core_nodes = [n for n, d in degrees.items() if d >= 2]
print(f"\nNodes with degree >= 2: {len(core_nodes)}")

H = G.subgraph(core_nodes).copy()
# keep only the largest few connected components for a clean visual
components = sorted(nx.connected_components(H), key=len, reverse=True)
print(f"Connected components in degree>=2 subgraph: {len(components)}, sizes: {[len(c) for c in components[:10]]}")

# Take top components until we have ~50-60 nodes for a readable visual
chosen = set()
for comp in components:
    if len(chosen) + len(comp) > 70:
        break
    chosen |= comp
if not chosen:
    chosen = components[0]

V = H.subgraph(chosen).copy()
print(f"\nFinal visual subgraph: {V.number_of_nodes()} nodes, {V.number_of_edges()} edges")

pos = nx.spring_layout(V, k=0.9, iterations=200, seed=42)
# scale to canvas coords
xs = [p[0] for p in pos.values()]; ys = [p[1] for p in pos.values()]
minx, maxx, miny, maxy = min(xs), max(xs), min(ys), max(ys)
W, H_ = 720, 520
margin = 50
def scalex(x): return margin + (x - minx) / (maxx - minx + 1e-9) * (W - 2*margin)
def scaley(y): return margin + (y - miny) / (maxy - miny + 1e-9) * (H_ - 2*margin)

nodes_out = [{'id': n, 'x': round(scalex(pos[n][0]),1), 'y': round(scaley(pos[n][1]),1), 'degree': V.degree(n)} for n in V.nodes()]
edges_out = [{'a': a, 'b': b, 'categories': d['categories'], 'n': d['n']} for a,b,d in V.edges(data=True)]

json.dump({'nodes': nodes_out, 'edges': edges_out,
           'full_stats': {'total_nodes': G.number_of_nodes(), 'total_edges': G.number_of_edges(),
                           'category_counts': dict(Counter(cat for e in raw_edges for cat in [e['category']]))}},
          open('mss_graph_viz.json','w'), ensure_ascii=False, indent=2)
print("\nSaved mss_graph_viz.json")
