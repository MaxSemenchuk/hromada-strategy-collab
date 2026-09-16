"""DREAM project-title similarity as a *proxy* for the v7 goals channel.

Not complementary matching (resource/DREAM ↔ Challenges) and not sector-tag
Jaccard (`dream_overlap` on operational_score). This compares project *titles*
with the same mean-centered bipartite+centroid machinery as Goals.

Used in combined `score` when at least one side has no parsed strategy:
  score = 0.60 × priority + 0.25 × geo + 0.15 × social_capital
  priority = goals_cosine                         if both have Goals
           | 0.90×goals + 0.10×dream_cosine       if both have Goals and DREAM
           | 0.90 × dream_or_cross_cosine         otherwise (proxy / mixed)
  social_capital = readiness / social-capital blend (KSE/Пліч floor, plus
                   named/explicit-ask, twinning, shared donors — see
                   social_capital.py). `mss_network` stays the domestic-tie
                   field for PIN reports; it is the floor of this slot.

Never sets known=true. Sector labels are not injected as matching lines.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DREAM_PATH = ROOT / "data" / "releases" / "dream-priorities.json"

# Small blend so revealed DREAM priorities nudge Goals–Goals scores without
# taking over the known-pair regression (still 90% strategy text).
WEIGHT_DREAM_IN_GOALS = 0.10
DREAM_PROXY_DISCOUNT = 0.90
# DREAM-only ↔ DREAM-only: operational neighbours (same as tracks.GEO_OPERATIONAL_MIN).
GEO_PROXY_MIN = 0.85
# Strategy text vs DREAM-only: allow a slightly wider ring (~80 km / geo 0.6).
GEO_MIXED_MIN = 0.6
MIN_DREAM_LINES = 2
MAX_DREAM_LINES = 16

SOURCE_GOALS = "goals"
SOURCE_MIXED = "mixed"
SOURCE_DREAM = "dream_proxy"

# Combined-score weights (v7.3 slot meanings; weights unchanged from v6).
WEIGHT_GOALS = 0.60
WEIGHT_GEO = 0.25
WEIGHT_SOCIAL = 0.15


def combined_match_score(priority: float, geo: float, social_capital: float) -> float:
    return WEIGHT_GOALS * float(priority) + WEIGHT_GEO * float(geo) + WEIGHT_SOCIAL * float(
        social_capital
    )


def priority_from_edge(edge: dict) -> float:
    """Rebuild the 0.60-slot value from stored edge fields (no embeddings)."""
    src = edge.get("priority_source") or SOURCE_GOALS
    g = float(edge.get("goals_cosine") or 0.0)
    raw_d = edge.get("dream_cosine")
    dream = None if raw_d is None else float(raw_d)
    if src == SOURCE_GOALS:
        p, _ = priority_channel(
            goals_cosine=g, dream_cosine=dream, has_goals_a=True, has_goals_b=True
        )
        return p
    p, _ = priority_channel(
        goals_cosine=g,
        dream_cosine=dream,
        has_goals_a=src == SOURCE_MIXED,
        has_goals_b=False,
    )
    return p


def dream_priority_lines(row: dict | None) -> list[str]:
    """Unique DREAM project titles for one hromada aggregate row.

    Prefers ``sector_samples`` (titles spread across sectors) over the first-N
    ``sample_titles`` which are often near-duplicate reconstruction lines.
    Does **not** add sector names — those would be tag-overlap matching.
    """
    if not row:
        return []
    titles: list[str] = []
    seen: set[str] = set()

    def add(raw: str | None) -> None:
        text = " ".join((raw or "").split())
        if len(text) < 12:
            return
        key = text.casefold()
        if key in seen:
            return
        seen.add(key)
        titles.append(text)

    samples = row.get("sector_samples") or {}
    if isinstance(samples, dict):
        # Round-robin across sectors so one dense sector cannot fill the cap.
        buckets: list[list[str]] = []
        for items in samples.values():
            bucket: list[str] = []
            for it in items or []:
                if isinstance(it, dict):
                    bucket.append(it.get("title") or "")
                elif isinstance(it, str):
                    bucket.append(it)
            if bucket:
                buckets.append(bucket)
        depth = max((len(b) for b in buckets), default=0)
        for k in range(depth):
            for bucket in buckets:
                if k < len(bucket):
                    add(bucket[k])
                    if len(titles) >= MAX_DREAM_LINES:
                        return titles

    if len(titles) < MIN_DREAM_LINES:
        for t in row.get("sample_titles") or []:
            add(t if isinstance(t, str) else None)
            if len(titles) >= MAX_DREAM_LINES:
                break
    return titles


@lru_cache(maxsize=1)
def load_dream_lines_by_katottg(path: str | None = None) -> dict[str, list[str]]:
    p = Path(path) if path else DREAM_PATH
    if not p.exists():
        return {}
    payload = json.loads(p.read_text(encoding="utf-8"))
    out: dict[str, list[str]] = {}
    for row in payload.get("hromadas") or []:
        kat = (row.get("katottg") or "").strip()
        if not kat:
            continue
        lines = dream_priority_lines(row)
        if lines:
            out[kat] = lines
    return out


def has_usable_dream_proxy(lines: list[str] | None) -> bool:
    return len(lines or []) >= MIN_DREAM_LINES


def priority_channel(
    *,
    goals_cosine: float,
    dream_cosine: float | None,
    has_goals_a: bool,
    has_goals_b: bool,
) -> tuple[float, str]:
    """Value that occupies the 0.60 slot, plus a source label for tracks/UI."""
    both_goals = bool(has_goals_a and has_goals_b)
    if both_goals:
        if dream_cosine is None:
            return float(goals_cosine), SOURCE_GOALS
        p = (1.0 - WEIGHT_DREAM_IN_GOALS) * float(goals_cosine) + WEIGHT_DREAM_IN_GOALS * float(
            dream_cosine
        )
        return float(p), SOURCE_GOALS
    if dream_cosine is None:
        return 0.0, SOURCE_DREAM if not (has_goals_a or has_goals_b) else SOURCE_MIXED
    src = SOURCE_MIXED if (has_goals_a or has_goals_b) else SOURCE_DREAM
    return float(DREAM_PROXY_DISCOUNT * float(dream_cosine)), src


def keep_priority_edge(
    source: str,
    *,
    geo_score: float,
    mss_network: float,
) -> bool:
    """Always keep Goals–Goals; DREAM-proxy only when PIN-linked or nearby.

    Full DREAM↔DREAM pairwise (~500k) is too large and too templated
    (капремонт школи) to dump into matching-edges.json.
    """
    if source == SOURCE_GOALS:
        return True
    if float(mss_network) > 0:
        return True
    if source == SOURCE_MIXED and float(geo_score) >= GEO_MIXED_MIN:
        return True
    if float(geo_score) >= GEO_PROXY_MIN:
        return True
    return False
