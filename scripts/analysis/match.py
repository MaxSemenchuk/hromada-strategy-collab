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
boost, write slim `matching-edges.json` (core scores; compact), rich slices /
mss-candidates, and an optional rich cache under data/cache/matching/.

Usage:
  python scripts/analysis/match.py
  python scripts/analysis/match.py --input data/releases/hromadas.json --out data/releases/matching-edges.json
"""

from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
from edge_io import write_release_edges, write_rich_cache  # noqa: E402
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
) -> tuple[float, tuple[int, int, float] | None]:
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

    Returns ``(score, evidence)`` where ``evidence`` is the single best-matching
    line pair as ``(global_idx_a, global_idx_b, similarity)`` — the strongest
    concrete overlap driving this pair's score, for UI display.
    """
    if not idx_i or not idx_j:
        return 0.0, None
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
    flat = int(np.argmax(sims))
    li, lj = divmod(flat, sims.shape[1])
    evidence = (idx_i[li], idx_j[lj], float(sims[li, lj]))
    return float(max(0.0, blended)), evidence


def _capped_avg(best: np.ndarray, weights: np.ndarray, k: int) -> float:
    """Average of the top-k best line matches (length-normalized soft alignment)."""
    if k <= 0 or len(best) == 0:
        return 0.0
    if len(best) <= k:
        return float(np.average(best, weights=weights))
    top = np.argpartition(best, -k)[-k:]
    return float(np.average(best[top], weights=weights[top]))


Evidence = dict[tuple[int, int], tuple[str, str, float]]


def _indexed_similarity(
    records: list[dict],
    model: SentenceTransformer,
    line_key: str,
) -> tuple[np.ndarray, Evidence]:
    """Pairwise DF-weighted mean-centered similarity over record[line_key] lines.

    Also returns, per pair, the single best-matching line pair (stripped of the
    "query: " e5 prefix, when applied) as evidence for why the score is what it is.

    The "query: " prefix is an e5-specific training convention (asymmetric
    query/passage encoding) — meaningless for other models, so it's only
    applied when ``model.uses_query_prefix`` is set (see ``main``).
    """
    prefix = "query: " if getattr(model, "uses_query_prefix", False) else ""
    all_subgoals: list[str] = []
    subgoal_owner: list[int] = []
    for i, r in enumerate(records):
        sg = r.get(line_key) or []
        if not sg:
            continue
        for s in sg:
            all_subgoals.append(prefix + s)
            subgoal_owner.append(i)

    n = len(records)
    scores = np.zeros((n, n))
    evidence: Evidence = {}
    if not all_subgoals:
        return scores, evidence

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
            s, ev = _blend_bipartite_centroid(centered, weight, sub_idx[i], sub_idx[j])
            scores[i, j] = scores[j, i] = s
            if ev is not None:
                gi, gj, sim = ev
                evidence[(i, j)] = (
                    all_subgoals[gi][len(prefix) :],
                    all_subgoals[gj][len(prefix) :],
                    sim,
                )
    return scores, evidence


def goals_similarity(records: list[dict], model: SentenceTransformer) -> tuple[np.ndarray, Evidence]:
    all_mat, all_ev = _indexed_similarity(records, model, "subgoals")
    ops_mat, ops_ev = _indexed_similarity(records, model, "operational")
    strat_mat, strat_ev = _indexed_similarity(records, model, "strategic")

    n = len(records)
    scores = np.zeros((n, n))
    evidence: Evidence = {}
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
            # Prefer operational evidence (more concrete/actionable), then strategic, then any line.
            ev = ops_ev.get((i, j)) or strat_ev.get((i, j)) or all_ev.get((i, j))
            if ev is not None:
                evidence[(i, j)] = ev
    return scores, evidence


def _short_name(full: str | None) -> str:
    """First adjective token — «Солотвинська селищна …» → «Солотвинська»."""
    if not full:
        return ""
    parts = full.replace("територіальна громада", "").strip().split()
    return parts[0] if parts else full


def _is_homonym_pair(a: dict, b: dict) -> bool:
    """Drop twin / corrupt pairs that should never rank as IMC candidates.

    - Same Katottg (duplicate rows — e.g. Обухівська селищна vs міська
      sharing one code) → skip.
    - Same official Name or same short name, different Katottg
      (Солотвинська Закарпаття vs ІФ) → skip.
    """
    ka, kb = a.get("katottg"), b.get("katottg")
    if ka and kb and ka == kb:
        return True
    if not ka or not kb or ka == kb:
        return False
    if a.get("name") and a["name"] == b.get("name"):
        return True
    sa, sb = _short_name(a.get("name")), _short_name(b.get("name"))
    return bool(sa and sa == sb)


def _norm_line(s: str) -> str:
    s = s.lower()
    s = re.sub(r"[^\w\s]", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def template_collision(lines_a: list[str], lines_b: list[str]) -> tuple[str, str, float] | None:
    """Best near-verbatim subgoal-line match between two records, if any.

    Ported from Pass 5 (`legacy/final_matching.py`) — never made it into v6/v7.
    NOTE: on the current 294-record corpus, "best single line" is too noisy —
    common boilerplate sentences (e.g. "Залучення інвестицій у громаду") match
    near-verbatim across many unrelated pairs. Use `template_collision_fraction`
    for the actual guardrail decision; this is kept for the sample-line display.
    """
    best: tuple[str, str, float] | None = None
    for la in lines_a:
        na = _norm_line(la)
        if len(na) < 20:
            continue
        for lb in lines_b:
            nb = _norm_line(lb)
            if len(nb) < 20:
                continue
            ratio = difflib.SequenceMatcher(None, na, nb).ratio()
            if best is None or ratio > best[2]:
                best = (la, lb, ratio)
    return best


def template_collision_fraction(
    lines_a: list[str], lines_b: list[str], line_ratio_thresh: float = 0.9
) -> float:
    """Fraction of each side's lines with a near-verbatim match on the other side.

    Returns min(frac_a, frac_b) — both directions must show substantial
    line-level duplication for this to indicate a shared document template,
    not just one recycled boilerplate sentence.
    """
    na_lines = [l for l in lines_a if len(_norm_line(l)) >= 20]
    nb_lines = [l for l in lines_b if len(_norm_line(l)) >= 20]
    if not na_lines or not nb_lines:
        return 0.0
    normed_b = [_norm_line(l) for l in nb_lines]

    def frac(src: list[str], others: list[str]) -> float:
        matched = 0
        for l in src:
            nl = _norm_line(l)
            best = max(
                (difflib.SequenceMatcher(None, nl, ol).ratio() for ol in others),
                default=0.0,
            )
            if best >= line_ratio_thresh:
                matched += 1
        return matched / len(src)

    normed_a = [_norm_line(l) for l in na_lines]
    return min(frac(na_lines, normed_b), frac(nb_lines, normed_a))


def match_all(records: list[dict], model: SentenceTransformer) -> list[dict]:
    n = len(records)
    goals_mat, goals_evidence = goals_similarity(records, model)
    edges = []

    for i in range(n):
        for j in range(i + 1, n):
            if _is_homonym_pair(records[i], records[j]):
                continue
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
            collision = template_collision_fraction(records[i]["subgoals"], records[j]["subgoals"])
            edge = {
                "a": records[i]["name"],
                "b": records[j]["name"],
                "a_katottg": records[i]["katottg"],
                "b_katottg": records[j]["katottg"],
                "score": round(combined, 3),
                "goals_cosine": round(g, 3),
                "geo_score": round(geo, 3),
                "mss_network": round(mss, 3),
                "known": pk in KNOWN_PAIRS,
                "template_collision": round(collision, 3),
            }
            ev = goals_evidence.get((i, j))
            if ev is not None:
                edge["goals_evidence"] = {"a": ev[0], "b": ev[1], "similarity": round(ev[2], 3)}
            edges.append(edge)
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

    from sentence_transformers import models as st_models

    _word_embedding_model = st_models.Transformer("lang-uk/ukr-paraphrase-multilingual-mpnet-base")
    _pooling_model = st_models.Pooling(
        _word_embedding_model.get_word_embedding_dimension(), pooling_mode="mean"
    )
    model = SentenceTransformer(modules=[_word_embedding_model, _pooling_model])
    model.uses_query_prefix = False  # e5-specific convention, not applicable here
    edges = match_all(records, model)
    meta = assign_tracks(edges)

    # Rich cache first (goals_evidence + full fields) — export_edges.py picks
    # this up via load_matching_edges(prefer_rich_cache=True) since the public
    # release matrix below is slimmed to RELEASE_CORE_KEYS.
    rich_path = write_rich_cache(edges)
    write_release_edges(edges, args.out)
    print(f"Wrote {len(edges)} slim edges to {args.out}")
    print(f"Wrote {len(edges)} rich edges to {rich_path}")
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
