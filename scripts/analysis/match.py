#!/usr/bin/env python3
"""
Pairwise hromada matching v7.1 — hierarchy-aware goals + KSE covariates.

Combines mean-centered sub-goal embeddings (v5 DF-weighting) with KSE enrichment:
  60% goals_cosine + 25% geo + 15% mss_network

v7 goals_cosine: when both sides have operational lines (from goals-hierarchy.json
or parsed Goals text), blend 0.65×operational_sim + 0.35×strategic_sim; else
fall back to all lines (v6 behaviour). Combined score weights unchanged.

v7.1 length / hub mitigation (Poltava–Zhytomyr-type risk): each pairwise
goals similarity blends
  0.65 × bipartite soft-alignment (DF-weighted avg of best line matches)
  0.35 × DF-weighted document-centroid cosine (mean-centered subgoals)
Also restores true pairwise cosine (``A @ B.T``); v4–v7 used a broken
``np.ix_`` embedding-coordinate slice. Comprehensive long strategies average
toward the corpus mean after centering, so centroid sim stays low unless the
*profile* matches — not merely many mediocre line overlaps.

Each edge also gets a dual-track label (scoring weights unchanged):
  thematic    — high goals, low geo  → cold-start vision partners
  operational — high geo             → convenient service co-sharers
  mixed       — otherwise

After `yarn match`, run `yarn export-matching-edges` to attach operational
boost + suggested_theme / suggested_form (mss_suggest) and write slices.

Usage:
  python scripts/analysis/match.py
  python scripts/analysis/match.py --input data/releases/hromadas.json --out data/releases/matching-edges.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
from enrich_from_kse import geo_score, mss_network_score  # noqa: E402
from goals_hierarchy import load_hierarchy_index, record_subgoals  # noqa: E402
from tracks import assign_tracks  # noqa: E402

# Curated registry-confirmed pairs (hard regression). Expanded 2026-08-04
# from IMC∩Goals shortlist — see internal/known-curation-review.md.
KNOWN_PAIRS = {
    # Original core (tourism triangle + CNAP)
    frozenset(["Ніжинська міська територіальна громада", "Козелецька селищна територіальна громада"]),
    frozenset(["Батуринська міська територіальна громада", "Козелецька селищна територіальна громада"]),
    frozenset(["Ніжинська міська територіальна громада", "Батуринська міська територіальна громада"]),
    frozenset(["Слобожанська селищна територіальна громада", "Обухівська селищна територіальна громада"]),
    # Approved shortlist (registry theme·form proofs)
    frozenset(["Галицька міська територіальна громада", "Дубовецька сільська територіальна громада"]),
    frozenset(["Рукшинська сільська територіальна громада", "Хотинська міська територіальна громада"]),
    frozenset(["Вашковецька сільська територіальна громада", "Сокирянська міська територіальна громада"]),
    frozenset(["Клішковецька сільська територіальна громада", "Хотинська міська територіальна громада"]),
    frozenset(["Верховинська селищна територіальна громада", "Кутська селищна територіальна громада"]),
    frozenset(["Львівська міська територіальна громада", "Жовківська міська територіальна громада"]),
    frozenset(["Тернопільська міська територіальна громада", "Байковецька сільська територіальна громада"]),
    frozenset(["Клішковецька сільська територіальна громада", "Рукшинська сільська територіальна громада"]),
}

WEIGHT_GOALS = 0.60
WEIGHT_GEO = 0.25
WEIGHT_MSS = 0.15
# When both sides have operational goals
WEIGHT_OPS_IN_GOALS = 0.65
WEIGHT_STRAT_IN_GOALS = 0.35
# Length / hub mitigation inside goals similarity
WEIGHT_BIPARTITE = 0.65
WEIGHT_CENTROID = 0.35


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
    hierarchy = load_hierarchy_index()
    records = []
    for r in hromadas:
        goals = (r.get("Goals") or "").strip()
        name = r.get("Name") or ""
        katottg = r.get("Katottg") or r.get("KATOTTG") or r.get("Koatuu / Katottg")
        strat, ops, all_lines = record_subgoals(name, katottg, goals, hierarchy)
        records.append(
            {
                "name": name,
                "katottg": katottg,
                "oblast": r.get("Oblast"),
                "rayon": r.get("Rayon"),
                "goals": goals,
                "strategic": strat,
                "operational": ops,
                "subgoals": all_lines if all_lines else [goals],
            }
        )
    return records


def _blend_bipartite_centroid(
    centered: np.ndarray,
    weight: np.ndarray,
    idx_i: list[int],
    idx_j: list[int],
) -> float:
    """DF-weighted bipartite soft-align blended with document-centroid cosine.

    Centroid term dampens comprehensive long-document hubs: diverse subgoal
    sets collapse toward the corpus mean after centering, so only shared
    *profiles* score high. Bipartite keeps credit for specific shared lines.

    For length-imbalanced pairs, each side's directional average only keeps the
    top ``min(n_i, n_j)`` best line matches — a long doc cannot pad its score
    with dozens of mediocre overlaps against a short focused partner.

    Note: v4–v7 incorrectly used ``centered[np.ix_(idx_i, idx_j)]`` (embedding
    coordinate slices). v7.1 restores true pairwise cosine
    ``centered[idx_i] @ centered[idx_j].T``.
    """
    if not idx_i or not idx_j:
        return 0.0
    sims = centered[idx_i] @ centered[idx_j].T
    wi = np.asarray(weight[idx_i], dtype=float)
    wj = np.asarray(weight[idx_j], dtype=float)
    best_i = sims.max(axis=1)
    best_j = sims.max(axis=0)
    k = min(len(best_i), len(best_j))
    bipartite = float((_capped_avg(best_i, wi, k) + _capped_avg(best_j, wj, k)) / 2)

    ci = np.average(centered[idx_i], axis=0, weights=wi)
    cj = np.average(centered[idx_j], axis=0, weights=wj)
    ni = float(np.linalg.norm(ci))
    nj = float(np.linalg.norm(cj))
    if ni < 1e-8 or nj < 1e-8:
        centroid = 0.0
    else:
        centroid = float((ci / ni) @ (cj / nj))

    blended = WEIGHT_BIPARTITE * bipartite + WEIGHT_CENTROID * centroid
    return float(max(0.0, blended))


def _capped_avg(best: np.ndarray, weights: np.ndarray, k: int) -> float:
    """Average of the top-k best line matches (length-normalized soft alignment)."""
    if k <= 0 or len(best) == 0:
        return 0.0
    if len(best) <= k:
        return float(np.average(best, weights=weights))
    top = np.argpartition(best, -k)[-k:]
    return float(np.average(best[top], weights=weights[top]))


def _indexed_similarity(
    records: list[dict],
    model: SentenceTransformer,
    line_key: str,
) -> np.ndarray:
    """Pairwise DF-weighted mean-centered similarity over record[line_key] lines."""
    all_subgoals: list[str] = []
    subgoal_owner: list[int] = []
    for i, r in enumerate(records):
        sg = r.get(line_key) or []
        if not sg:
            continue
        for s in sg:
            all_subgoals.append("query: " + s)
            subgoal_owner.append(i)

    n = len(records)
    scores = np.zeros((n, n))
    if not all_subgoals:
        return scores

    sub_emb = model.encode(all_subgoals, show_progress_bar=False, normalize_embeddings=True, batch_size=64)
    mean_vec = sub_emb.mean(axis=0)
    centered = sub_emb - mean_vec
    centered = centered / np.clip(np.linalg.norm(centered, axis=1, keepdims=True), 1e-8, None)

    N = len(all_subgoals)
    owner_arr = np.array(subgoal_owner)
    sub_idx: dict[int, list[int]] = {i: [] for i in range(n)}
    for k, owner in enumerate(subgoal_owner):
        sub_idx[owner].append(k)

    raw_sim = sub_emb @ sub_emb.T
    df = np.zeros(N, dtype=int)
    for k in range(N):
        owners_matched = set(owner_arr[raw_sim[k] > 0.90]) - {owner_arr[k]}
        df[k] = len(owners_matched)
    weight = 1.0 / (1.0 + np.log1p(np.maximum(df - 2, 0)))

    for i in range(n):
        for j in range(i + 1, n):
            s = _blend_bipartite_centroid(centered, weight, sub_idx[i], sub_idx[j])
            scores[i, j] = scores[j, i] = s
    return scores


def goals_similarity(records: list[dict], model: SentenceTransformer) -> np.ndarray:
    all_mat = _indexed_similarity(records, model, "subgoals")
    ops_mat = _indexed_similarity(records, model, "operational")
    strat_mat = _indexed_similarity(records, model, "strategic")

    n = len(records)
    scores = np.zeros((n, n))
    for i in range(n):
        for j in range(i + 1, n):
            has_ops = bool(records[i]["operational"] and records[j]["operational"])
            has_strat = bool(records[i]["strategic"] and records[j]["strategic"])
            if has_ops and has_strat:
                s = WEIGHT_OPS_IN_GOALS * float(ops_mat[i, j]) + WEIGHT_STRAT_IN_GOALS * float(
                    strat_mat[i, j]
                )
            elif has_ops:
                s = float(ops_mat[i, j])
            else:
                s = float(all_mat[i, j])
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
    meta = assign_tracks(edges)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(edges, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(edges)} edges to {args.out}")
    print(
        f"Tracks: thematic={meta['counts']['thematic']} "
        f"operational={meta['counts']['operational']} "
        f"mixed={meta['counts']['mixed']} "
        f"(goals p{meta['goalsPercentile']} floor={meta['goalsFloor']})"
    )

    print("\nTop 10 (by combined score — not a pure strategy match):")
    for idx, e in enumerate(edges[:10], 1):
        tag = " KNOWN" if e["known"] else ""
        print(
            f"{idx:>2}. {e['score']:.3f} [{e['track']}] "
            f"({e['goals_cosine']}/{e['geo_score']}/{e['mss_network']}) "
            f"{e['a'][:28]} <-> {e['b'][:28]}{tag}"
        )


if __name__ == "__main__":
    main()
