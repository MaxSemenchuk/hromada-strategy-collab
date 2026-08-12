#!/usr/bin/env python3
"""Regression: template-collision guardrail (no model download needed).

Motivating case (2026-08-09/10): Бабинська/Ободівська scored goals_cosine=1.0
on reordered, near-verbatim consulting-template boilerplate with zero shared
theme — see docs/project-history.md. Guards both the raw-text metric
(match.py) and its consequence (excluded from ranked slices, tracks.py).
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
from match import (  # noqa: E402
    build_records,
    default_input,
    load_hromadas,
    template_collision_fraction,
)
from tracks import TEMPLATE_COLLISION_MAX, thematic_slice  # noqa: E402

TEMPLATE_A = [
    "Стратегічна ціль 1. Створення умов для гармонійного розвитку жителів громади",
    "Стратегічна ціль 2. Економічний розвиток громади",
    "Стратегічна ціль 3. Створення комфортних та безпечних умов для проживання",
    "Розбудова та модернізація інфраструктури громади та благоустрій",
]
TEMPLATE_B_REORDERED = [
    "Стратегічна ціль 2. Економічний розвиток громади",
    "Розбудова та модернізація інфраструктури громади та благоустрій",
    "Стратегічна ціль 1. Створення умов для гармонійного розвитку жителів громади",
    "Стратегічна ціль 3. Створення комфортних та безпечних умов для проживання",
]
DISTINCT = [
    "Розвиток туристичної та рекреаційної інфраструктури вздовж річки",
    "Модернізація системи водопостачання та водовідведення",
    "Підтримка малого бізнесу у сфері ремісництва",
]
ONE_SHARED_BOILERPLATE = [
    "Залучення інвестицій у громаду",
    "Розвиток туристичної та рекреаційної інфраструктури вздовж річки",
    "Модернізація системи водопостачання та водовідведення",
]
ONE_SHARED_BOILERPLATE_OTHER_SIDE = [
    "Залучення інвестицій у громаду",
    "Підтримка малого бізнесу у сфері ремісництва",
    "Цифровізація адміністративних послуг населенню",
]


def test_reordered_template_flags_high() -> None:
    frac = template_collision_fraction(TEMPLATE_A, TEMPLATE_B_REORDERED)
    assert frac >= TEMPLATE_COLLISION_MAX, f"reordered near-verbatim template scored only {frac}"


def test_distinct_content_scores_low() -> None:
    frac = template_collision_fraction(DISTINCT, TEMPLATE_A)
    assert frac < TEMPLATE_COLLISION_MAX, f"unrelated docs falsely flagged at {frac}"


def test_one_shared_boilerplate_line_does_not_flag() -> None:
    """One recycled generic sentence among otherwise-distinct lines must NOT
    flag — that's a real partial-match signal (rewarded by goals_cosine's own
    bipartite scoring), not evidence of a shared document template."""
    frac = template_collision_fraction(ONE_SHARED_BOILERPLATE, ONE_SHARED_BOILERPLATE_OTHER_SIDE)
    assert frac < TEMPLATE_COLLISION_MAX, f"single shared line falsely flagged at {frac}"


def test_empty_lines_score_zero() -> None:
    assert template_collision_fraction([], TEMPLATE_A) == 0.0
    assert template_collision_fraction(TEMPLATE_A, []) == 0.0


def test_thematic_slice_excludes_flagged_pairs() -> None:
    edges = [
        {
            "a": "Flagged A",
            "b": "Flagged B",
            "track": "thematic",
            "goals_cosine": 1.0,
            "score": 0.6,
            "known": False,
            "template_collision": 1.0,
        },
        {
            "a": "Clean A",
            "b": "Clean B",
            "track": "thematic",
            "goals_cosine": 0.7,
            "score": 0.5,
            "known": False,
            "template_collision": 0.0,
        },
    ]
    out = thematic_slice(edges)
    pairs = [frozenset([e["a"], e["b"]]) for e in out]
    assert frozenset(["Flagged A", "Flagged B"]) not in pairs
    assert frozenset(["Clean A", "Clean B"]) in pairs


def test_real_corpus_babynska_obodivska() -> None:
    """Real-corpus regression for the case that motivated this guardrail."""
    hromadas = load_hromadas(default_input())
    records = build_records(hromadas)
    by_name = {r["name"]: r for r in records}
    a = by_name.get("Бабинська сільська територіальна громада")
    b = by_name.get("Ободівська сільська територіальна громада")
    if a is None or b is None:
        print("SKIP: Бабинська/Ободівська not in current corpus")
        return
    frac = template_collision_fraction(a["subgoals"], b["subgoals"])
    assert frac >= TEMPLATE_COLLISION_MAX, f"known collision pair scored only {frac}"


def main() -> None:
    test_reordered_template_flags_high()
    test_distinct_content_scores_low()
    test_one_shared_boilerplate_line_does_not_flag()
    test_empty_lines_score_zero()
    test_thematic_slice_excludes_flagged_pairs()
    test_real_corpus_babynska_obodivska()
    print("OK: template-collision guardrail checks passed")


if __name__ == "__main__":
    main()
