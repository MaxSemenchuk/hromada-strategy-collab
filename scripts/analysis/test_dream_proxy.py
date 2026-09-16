#!/usr/bin/env python3
"""Unit checks for DREAM-title priority proxy (no model download)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
from dream_priority import (  # noqa: E402
    DREAM_PROXY_DISCOUNT,
    GEO_MIXED_MIN,
    GEO_PROXY_MIN,
    SOURCE_DREAM,
    SOURCE_GOALS,
    SOURCE_MIXED,
    WEIGHT_DREAM_IN_GOALS,
    dream_priority_lines,
    has_usable_dream_proxy,
    keep_priority_edge,
    load_dream_lines_by_katottg,
    priority_channel,
)
from tracks import goals_percentile_threshold, thematic_slice  # noqa: E402


def test_titles_not_sector_labels() -> None:
    row = {
        "top_sectors": ["Освіта", "Відновлення / реконструкція"],
        "sample_titles": ["Капремонт школи №1 в селі"],
        "sector_samples": {
            "Освіта": [{"title": "Капітальний ремонт ліцею на 400 місць", "code": "a"}],
            "Вода / каналізація (ЖКГ)": [{"title": "Реконструкція очисних споруд", "code": "b"}],
        },
    }
    lines = dream_priority_lines(row)
    blob = " ".join(lines)
    assert "Капітальний ремонт ліцею" in blob
    assert "Реконструкція очисних споруд" in blob
    assert "Пріоритет DREAM" not in blob
    assert "Освіта" not in lines
    assert has_usable_dream_proxy(lines)


def test_round_robin_avoids_duplicate_reconstruction() -> None:
    row = {
        "sample_titles": [f"Капремонт будинку {i}" for i in range(5)],
        "sector_samples": {
            "Відновлення / реконструкція": [
                {"title": f"Капітальний ремонт ЖБ зруйнованого будинку {i}"} for i in range(8)
            ],
            "Освіта": [{"title": "Новий корпус опорного ліцею громади"}],
        },
    }
    lines = dream_priority_lines(row)
    assert any("ліцею" in t for t in lines)
    assert len(lines) >= 2


def test_priority_channel_goals_blend() -> None:
    p, src = priority_channel(
        goals_cosine=0.50, dream_cosine=0.20, has_goals_a=True, has_goals_b=True
    )
    assert src == SOURCE_GOALS
    expected = (1 - WEIGHT_DREAM_IN_GOALS) * 0.50 + WEIGHT_DREAM_IN_GOALS * 0.20
    assert abs(p - expected) < 1e-9


def test_priority_channel_proxy_discount() -> None:
    p, src = priority_channel(
        goals_cosine=0.0, dream_cosine=0.40, has_goals_a=False, has_goals_b=False
    )
    assert src == SOURCE_DREAM
    assert abs(p - DREAM_PROXY_DISCOUNT * 0.40) < 1e-9
    p2, src2 = priority_channel(
        goals_cosine=0.0, dream_cosine=0.40, has_goals_a=True, has_goals_b=False
    )
    assert src2 == SOURCE_MIXED
    assert abs(p2 - DREAM_PROXY_DISCOUNT * 0.40) < 1e-9


def test_keep_edge_gates() -> None:
    assert keep_priority_edge(SOURCE_GOALS, geo_score=0.0, mss_network=0.0)
    assert keep_priority_edge(SOURCE_DREAM, geo_score=GEO_PROXY_MIN, mss_network=0.0)
    assert keep_priority_edge(SOURCE_DREAM, geo_score=0.1, mss_network=1.0)
    assert not keep_priority_edge(SOURCE_DREAM, geo_score=0.4, mss_network=0.0)
    assert keep_priority_edge(SOURCE_MIXED, geo_score=GEO_MIXED_MIN, mss_network=0.0)
    assert not keep_priority_edge(SOURCE_MIXED, geo_score=0.4, mss_network=0.0)


def test_tracks_percentile_ignores_proxy_zeros() -> None:
    edges = [
        {"goals_cosine": 0.40, "priority_source": "goals"},
        {"goals_cosine": 0.20, "priority_source": "goals"},
        {"goals_cosine": 0.0, "priority_source": "dream_proxy"},
        {"goals_cosine": 0.0, "priority_source": "mixed"},
    ]
    floor = goals_percentile_threshold(edges, 50)
    assert floor >= 0.20
    # Proxy zeros must not pull p50 to 0.
    assert floor > 0.05


def test_thematic_slice_skips_proxy() -> None:
    edges = [
        {
            "a": "A",
            "b": "B",
            "track": "thematic",
            "goals_cosine": 0.5,
            "score": 0.4,
            "known": False,
            "template_collision": 0.0,
            "priority_source": "dream_proxy",
        },
        {
            "a": "C",
            "b": "D",
            "track": "thematic",
            "goals_cosine": 0.4,
            "score": 0.3,
            "known": False,
            "template_collision": 0.0,
            "priority_source": "goals",
        },
    ]
    out = thematic_slice(edges)
    pairs = [frozenset([e["a"], e["b"]]) for e in out]
    assert frozenset(["C", "D"]) in pairs
    assert frozenset(["A", "B"]) not in pairs


def test_release_dream_index_loads() -> None:
    idx = load_dream_lines_by_katottg()
    if not idx:
        print("SKIP: dream-priorities.json missing")
        return
    assert any(has_usable_dream_proxy(v) for v in idx.values())


def main() -> None:
    test_titles_not_sector_labels()
    test_round_robin_avoids_duplicate_reconstruction()
    test_priority_channel_goals_blend()
    test_priority_channel_proxy_discount()
    test_keep_edge_gates()
    test_tracks_percentile_ignores_proxy_zeros()
    test_thematic_slice_skips_proxy()
    test_release_dream_index_loads()
    print("OK: dream_priority proxy helpers")


if __name__ == "__main__":
    main()
