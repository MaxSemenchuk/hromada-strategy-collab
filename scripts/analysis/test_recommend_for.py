#!/usr/bin/env python3
"""Unit checks for agent-centric recommend_for policies."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))

from recommend_for import (  # noqa: E402
    MOTIVATIONS,
    agent_rank,
    card_from_edge,
    merge_complementary,
    recommend_for,
    resolve_seed,
    index_hromadas,
    weights_without_goals,
)


def _edge(**kwargs):
    base = {
        "a": "Галицька міська територіальна громада",
        "b": "Дубовецька сільська територіальна громада",
        "goals_cosine": 0.05,
        "geo_score": 0.9,
        "mss_network": 0.0,
        "known": False,
        "track": "operational",
        "suggested_theme": "ЦНАП / адмінпослуги",
        "suggested_theme_id": "cnap",
        "suggested_form": "делегування",
        "suggested_form_id": "delegation",
        "package": {
            "theme": "ЦНАП / адмінпослуги",
            "theme_id": "cnap",
            "form": "делегування",
            "form_id": "delegation",
            "label_uk": "ЦНАП / адмінпослуги — делегування",
        },
        "signals": [
            {"id": "geo", "label_uk": "зручний сусід", "strength": "high"},
        ],
        "signal_chips": [
            {"id": "geo", "label_uk": "зручний сусід", "strength": "high"},
        ],
        "discovery_primary": "geo",
        "status": "hypothesis",
    }
    base.update(kwargs)
    return base


def test_policy_cut_costs_prefers_geo_cnap() -> None:
    near_cnap = _edge(geo_score=0.95, goals_cosine=0.02)
    far_tourism = _edge(
        b="Далека міська територіальна громада",
        geo_score=0.1,
        goals_cosine=0.4,
        suggested_theme="Туризм / кластер",
        suggested_theme_id="tourism",
        suggested_form="спільний проєкт",
        suggested_form_id="joint_project",
        package={
            "theme": "Туризм / кластер",
            "theme_id": "tourism",
            "form": "спільний проєкт",
            "form_id": "joint_project",
            "label_uk": "Туризм / кластер — спільний проєкт",
        },
    )
    assert agent_rank(near_cnap, "cut_costs_service") > agent_rank(
        far_tourism, "cut_costs_service"
    )


def test_policy_tourism_prefers_goals() -> None:
    near_cnap = _edge(geo_score=0.95, goals_cosine=0.02)
    far_tourism = _edge(
        b="Далека міська територіальна громада",
        geo_score=0.1,
        goals_cosine=0.4,
        suggested_theme="Туризм / кластер",
        suggested_theme_id="tourism",
        suggested_form="спільний проєкт",
        suggested_form_id="joint_project",
        package={
            "theme": "Туризм / кластер",
            "theme_id": "tourism",
            "form": "спільний проєкт",
            "form_id": "joint_project",
            "label_uk": "Туризм / кластер — спільний проєкт",
        },
    )
    assert agent_rank(far_tourism, "tourism_cluster") > agent_rank(
        near_cnap, "tourism_cluster"
    )


def test_card_has_why_not_score_pitch() -> None:
    e = _edge()
    card = card_from_edge(
        e,
        seed_name="Галицька міська територіальна громада",
        motivation="cut_costs_service",
        rank_value=0.5,
    )
    assert card["partner_short"] == "Дубовецька"
    assert "package" in card
    assert card["why_helps_you_uk"]
    assert "score" not in card["why_helps_you_uk"].lower()
    assert "high score" not in card["why_helps_you_en"].lower()
    assert card["kind"] == "mss_agent_recommendation"


def test_merge_complementary_attaches_score() -> None:
    edges = [_edge()]
    comp = [
        {
            "a": "Галицька міська територіальна громада",
            "b": "Дубовецька сільська територіальна громада",
            "complementary_score": 0.8,
            "reasons": ["DREAM вода ↔ виклик"],
            "track": "complementary",
        }
    ]
    merged = merge_complementary(edges, comp)
    assert len(merged) == 1
    assert merged[0]["complementary_score"] == 0.8


def test_recommend_for_orders_by_policy() -> None:
    seed = "Галицька міська територіальна громада"
    edges = [
        _edge(b="Сусідська сільська територіальна громада", geo_score=0.9, goals_cosine=0.01),
        _edge(
            b="Кластерна міська територіальна громада",
            geo_score=0.1,
            goals_cosine=0.35,
            suggested_theme="Туризм / кластер",
            suggested_theme_id="tourism",
            suggested_form="спільний проєкт",
            suggested_form_id="joint_project",
            package={
                "theme": "Туризм / кластер",
                "theme_id": "tourism",
                "form": "спільний проєкт",
                "form_id": "joint_project",
                "label_uk": "Туризм / кластер — спільний проєкт",
            },
        ),
    ]
    cut = recommend_for(seed, motivation="cut_costs_service", k=2, edges=edges, complementary=[])
    tour = recommend_for(seed, motivation="tourism_cluster", k=2, edges=edges, complementary=[])
    assert cut[0]["partner_short"] == "Сусідська"
    assert tour[0]["partner_short"] == "Кластерна"


def test_resolve_seed_by_substring() -> None:
    rows = [
        {
            "Name": "Галицька міська територіальна громада",
            "Katottg": "UA26020030000088465",
            "Oblast": "Івано-Франківська",
            "Goals": "1. вода",
        },
        {
            "Name": "Ніжинська міська територіальна громада",
            "Katottg": "UA74040250000063494",
            "Oblast": "Чернігівська",
            "Goals": "1. туризм",
        },
    ]
    index = index_hromadas(rows)
    s = resolve_seed(seed="Галицька", katottg=None, index=index)
    assert s["katottg"] == "UA26020030000088465"


def test_motivations_cover_mvp() -> None:
    for mid in ("cut_costs_service", "water_basin", "tourism_cluster", "general"):
        assert mid in MOTIVATIONS
        assert "weights" in MOTIVATIONS[mid]


def test_weights_without_goals_redistributes_and_sums_to_one() -> None:
    for mid in MOTIVATIONS:
        w = weights_without_goals(mid)
        assert set(w) == {"geo", "network", "complementary"}
        assert abs(sum(w.values()) - 1.0) < 1e-9
        orig = MOTIVATIONS[mid]["weights"]
        # ratios between geo/network/complementary stay unchanged
        if orig.get("network"):
            assert abs(
                w["geo"] / w["network"] - orig.get("geo", 0) / orig["network"]
            ) < 1e-9


def test_agent_rank_ignores_goals_when_unavailable() -> None:
    high_goals_no_signal = _edge(goals_cosine=0.9, geo_score=0.0, mss_network=0.0)
    unavailable = dict(high_goals_no_signal, goals_available=False, geo_score=0.5)
    # goals_cosine=0.9 is ignored entirely, not scored as present
    assert agent_rank(unavailable, "general") == agent_rank(
        dict(high_goals_no_signal, goals_available=False, goals_cosine=0.0, geo_score=0.5),
        "general",
    )
    # and the redistributed geo weight actually applies (> plain geo*0.25)
    plain_weight_only = MOTIVATIONS["general"]["weights"]["geo"] * 0.5
    assert agent_rank(unavailable, "general") > plain_weight_only


def main() -> None:
    test_policy_cut_costs_prefers_geo_cnap()
    test_policy_tourism_prefers_goals()
    test_card_has_why_not_score_pitch()
    test_merge_complementary_attaches_score()
    test_recommend_for_orders_by_policy()
    test_resolve_seed_by_substring()
    test_motivations_cover_mvp()
    test_weights_without_goals_redistributes_and_sums_to_one()
    test_agent_rank_ignores_goals_when_unavailable()
    print("test_recommend_for: ok")


if __name__ == "__main__":
    main()
