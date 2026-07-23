#!/usr/bin/env python3
"""
Pairwise hromada matching v6 — goals embeddings + KSE covariates.

Combines mean-centered sub-goal embeddings (v5 DF-weighting) with KSE enrichment:
  60% goals_cosine + 25% geo + 15% mss_network

Usage:
  python scripts/analysis/match.py
  python scripts/analysis/match.py --input data/releases/hromadas.json --out data/releases/matching-edges.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
from enrich_from_kse import geo_score, mss_network_score  # noqa: E402

KNOWN_PAIRS = {
    frozenset(["Ніжинська міська територіальна громада", "Козелецька селищна територіальна громада"]),
    frozenset(["Батуринська міська територіальна громада", "Козелецька селищна територіальна громада"]),
    frozenset(["Ніжинська міська територіальна громада", "Батуринська міська територіальна громада"]),
    frozenset(["Слобожанська селищна територіальна громада", "Обухівська селищна територіальна громада"]),
}

WEIGHT_GOALS = 0.60
WEIGHT_GEO = 0.25
WEIGHT_MSS = 0.15


def load_hromadas(path: Path) -> list[dict]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    rows = raw if isinstance(raw, list) else raw.get("list", [])
    return [
        r
        for r in rows
        if r.get("SourceQuality") in ("full-strategy", "partial", "proxy-info")
        and (r.get("Goals") or "").strip()
    ]


def build_records(hromadas: list[dict]) -> list[dict]:
    records = []
    for r in hromadas:
        goals = (r.get("Goals") or "").strip()
        lines = [l.strip(" \t-•\n") for l in re.split(r"\n", goals)]
        lines = [l for l in lines if len(l) > 15]
        records.append(
            {
                "name": r.get("Name") or "",
                "katottg": r.get("Katottg") or r.get("KATOTTG") or r.get("Koatuu / Katottg"),
                "oblast": r.get("Oblast"),
                "rayon": r.get("Rayon"),
                "goals": goals,
                "subgoals": lines,
            }
        )
    return records


def goals_similarity(records: list[dict], model: SentenceTransformer) -> np.ndarray:
    all_subgoals: list[str] = []
    subgoal_owner: list[int] = []
    for i, r in enumerate(records):
        sg = r["subgoals"] if r["subgoals"] else [r["goals"]]
        for s in sg:
            all_subgoals.append("query: " + s)
            subgoal_owner.append(i)

    sub_emb = model.encode(all_subgoals, show_progress_bar=False, normalize_embeddings=True, batch_size=64)
    mean_vec = sub_emb.mean(axis=0)
    centered = sub_emb - mean_vec
    centered = centered / np.clip(np.linalg.norm(centered, axis=1, keepdims=True), 1e-8, None)

    n = len(records)
    N = len(all_subgoals)
    owner_arr = np.array(subgoal_owner)
    sub_idx = {i: [] for i in range(n)}
    for k, owner in enumerate(subgoal_owner):
        sub_idx[owner].append(k)

    raw_sim = sub_emb @ sub_emb.T
    df = np.zeros(N, dtype=int)
    for k in range(N):
        owners_matched = set(owner_arr[raw_sim[k] > 0.90]) - {owner_arr[k]}
        df[k] = len(owners_matched)
    weight = 1.0 / (1.0 + np.log1p(np.maximum(df - 2, 0)))

    def pair_score(i: int, j: int) -> float:
        idx_i, idx_j = sub_idx[i], sub_idx[j]
        if not idx_i or not idx_j:
            return 0.0
        sims = centered[np.ix_(idx_i, idx_j)]
        wi, wj = weight[idx_i], weight[idx_j]
        best_i = sims.max(axis=1)
        best_j = sims.max(axis=0)
        return float((np.average(best_i, weights=wi) + np.average(best_j, weights=wj)) / 2)

    scores = np.zeros((n, n))
    for i in range(n):
        for j in range(i + 1, n):
            s = pair_score(i, j)
            scores[i, j] = scores[j, i] = s
    return scores


def match_all(records: list[dict], model: SentenceTransformer) -> list[dict]:
    n = len(records)
    goals_mat = goals_similarity(records, model)
    edges = []

    for i in range(n):
        for j in range(i + 1, n):
            g = float(goals_mat[i, j])
            geo = geo_score(
                records[i]["katottg"],
                records[j]["katottg"],
                records[i]["oblast"],
                records[j]["oblast"],
                records[i]["rayon"],
                records[j]["rayon"],
            )
            mss = mss_network_score(records[i]["katottg"], records[j]["katottg"])
            combined = WEIGHT_GOALS * g + WEIGHT_GEO * geo + WEIGHT_MSS * mss
            pk = frozenset([records[i]["name"], records[j]["name"]])
            edges.append(
                {
                    "a": records[i]["name"],
                    "b": records[j]["name"],
                    "score": round(combined, 3),
                    "goals_cosine": round(g, 3),
                    "geo_score": round(geo, 3),
                    "mss_network": round(mss, 3),
                    "known": pk in KNOWN_PAIRS,
                }
            )
    return sorted(edges, key=lambda e: -e["score"])


def default_input() -> Path:
    release = ROOT / "data" / "releases" / "hromadas.json"
    if release.exists():
        return release
    return ROOT / "data" / "research-log" / "hromadas_full54.json"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=default_input())
    parser.add_argument("--out", type=Path, default=ROOT / "data" / "releases" / "matching-edges.json")
    args = parser.parse_args()

    hromadas = load_hromadas(args.input)
    records = build_records(hromadas)
    print(f"Matching {len(records)} hromadas from {args.input}...")

    model = SentenceTransformer("intfloat/multilingual-e5-small")
    edges = match_all(records, model)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(edges, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(edges)} edges to {args.out}")

    print("\nTop 10:")
    for idx, e in enumerate(edges[:10], 1):
        tag = " KNOWN" if e["known"] else ""
        print(f"{idx:>2}. {e['score']:.3f} ({e['goals_cosine']}/{e['geo_score']}/{e['mss_network']}) {e['a'][:28]} <-> {e['b'][:28]}{tag}")


if __name__ == "__main__":
    main()
