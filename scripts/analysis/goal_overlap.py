#!/usr/bin/env python3
"""Explain thematic similarity: shared sector themes + closest goal-line pairs.

Lightweight (no embeddings) — used by the PIN matching map detail card so
«схожа стратегія» shows *what* overlaps, not only goals_cosine.
"""

from __future__ import annotations

import re
from functools import lru_cache

# Reuse complementary sector stems — same controlled vocabulary stakeholders see.
from complementary_match import SECTOR_PATTERNS, sectors_in_text  # noqa: E402
from goals_hierarchy import load_hierarchy_index, record_subgoals  # noqa: E402

_GOAL_PREFIX = re.compile(
    r"^(?:Стратегічн\w*\s+ціль|Оперативн\w*\s+ціль|Ціль|Напрям)"
    r"\s*[0-9A-CА-Яа-я.]*\.?\s*",
    re.IGNORECASE | re.UNICODE,
)
_NUM_PREFIX = re.compile(r"^\d+(?:\.\d+)*\.?\s*")
_STOP = {
    "громад",
    "розвит",
    "створен",
    "покращен",
    "забезпеч",
    "підвищен",
    "умови",
    "умов",
    "якість",
    "якісн",
    "ефективн",
    "систем",
    "населен",
    "територ",
    "міськ",
    "сільськ",
    "селищн",
    "через",
    "також",
    "шляхом",
    "основі",
    "рівень",
    "рівня",
    "сфери",
    "галуз",
    "людин",
    "потенц",
    "комфор",
    "інфраст",
    "послуг",
    "доступ",
    "сучасн",
    "наближ",
    "формува",
    "реаліза",
}


def clean_goal_line(line: str, limit: int = 96) -> str:
    text = _GOAL_PREFIX.sub("", (line or "").strip())
    text = _NUM_PREFIX.sub("", text).strip(" .;:-")
    text = re.sub(r"\s+", " ", text)
    if len(text) <= limit:
        return text
    cut = text[: limit - 1].rsplit(" ", 1)[0]
    return (cut or text[: limit - 1]).rstrip(" ,;:") + "…"


def _stems(text: str) -> set[str]:
    words = re.findall(r"[А-Яа-яЇїІіЄєҐґA-Za-z]{4,}", (text or "").lower())
    out: set[str] = set()
    for w in words:
        stem = w[:6]
        if stem in _STOP or any(stem.startswith(s) for s in _STOP):
            continue
        out.add(stem)
    return out


def shared_goal_themes(*texts: str) -> list[str]:
    """Sector labels present in every non-empty text (intersection)."""
    sets = [sectors_in_text(t) for t in texts if (t or "").strip()]
    if len(sets) < 2:
        return []
    shared = sets[0].intersection(*sets[1:])
    # Stable order matching SECTOR_PATTERNS declaration
    order = list(SECTOR_PATTERNS.keys())
    return [s for s in order if s in shared]


def closest_goal_pairs(
    lines_a: list[str],
    lines_b: list[str],
    *,
    top: int = 3,
    min_shared_stems: int = 3,
    min_jaccard: float = 0.18,
) -> list[dict]:
    """Top goal-line pairs by stem Jaccard (explainability, not the scorer)."""
    scored: list[tuple[float, int, str, str]] = []
    prep_a = [(_stems(ln), clean_goal_line(ln)) for ln in lines_a if ln]
    prep_b = [(_stems(ln), clean_goal_line(ln)) for ln in lines_b if ln]
    seen: set[tuple[str, str]] = set()
    for ta, ca in prep_a:
        if len(ta) < min_shared_stems or not ca:
            continue
        for tb, cb in prep_b:
            if len(tb) < min_shared_stems or not cb:
                continue
            inter = ta & tb
            if len(inter) < min_shared_stems:
                continue
            key = tuple(sorted((ca.casefold(), cb.casefold())))
            if key in seen:
                continue
            seen.add(key)
            identical = ca.casefold() == cb.casefold()
            jac = 1.0 if identical else len(inter) / len(ta | tb)
            if not identical and jac < min_jaccard:
                continue
            sector_bonus = 0.05 if shared_goal_themes(ca, cb) else 0.0
            scored.append((jac + sector_bonus, len(inter), ca, cb))
    scored.sort(key=lambda x: (-x[0], -x[1], x[2]))
    out: list[dict] = []
    for jac, _n, ca, cb in scored[:top]:
        if ca.casefold() == cb.casefold():
            out.append({"text": ca, "score": round(min(jac, 1.0), 3)})
        else:
            out.append({"a": ca, "b": cb, "score": round(min(jac, 1.0), 3)})
    return out


@lru_cache(maxsize=1)
def _hierarchy():
    return load_hierarchy_index()


def goal_lines_for(name: str, katottg: str | None, goals_text: str) -> list[str]:
    strat, ops, all_lines = record_subgoals(name, katottg, goals_text, _hierarchy())
    # Prefer operational + strategic; fall back to all parsed lines
    preferred = ops + strat
    return preferred if preferred else all_lines


def explain_goal_overlap(
    *,
    name_a: str,
    name_b: str,
    katottg_a: str | None,
    katottg_b: str | None,
    goals_a: str,
    goals_b: str,
    top_pairs: int = 3,
) -> dict:
    """Payload for map/graph detail card on thematic / known edges."""
    lines_a = goal_lines_for(name_a, katottg_a, goals_a)
    lines_b = goal_lines_for(name_b, katottg_b, goals_b)
    themes = shared_goal_themes(goals_a, goals_b)
    if not themes:
        # Fall back to themes from structured lines only
        themes = shared_goal_themes("\n".join(lines_a), "\n".join(lines_b))
    pairs = closest_goal_pairs(lines_a, lines_b, top=top_pairs)
    reasons: list[str] = []
    if themes:
        reasons.append("Спільні теми: " + ", ".join(themes[:5]))
    for p in pairs:
        if "text" in p:
            reasons.append(f"спільна ціль: «{p['text']}»")
        else:
            reasons.append(f"«{p['a']}» ≈ «{p['b']}»")
    out: dict = {}
    if themes:
        out["themes"] = themes[:4]
    if pairs:
        out["goal_pairs"] = pairs
    if reasons:
        out["reasons"] = reasons[:5]
    if themes:
        out["theme"] = ", ".join(themes[:3])
    return out
