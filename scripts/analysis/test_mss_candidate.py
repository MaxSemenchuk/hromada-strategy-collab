#!/usr/bin/env python3
"""Unit checks for mss_candidate package/signals normalization."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
from mss_candidate import (  # noqa: E402
    annotate_candidate,
    build_signals,
    discovery_primary_for,
    package_from_edge,
    write_candidates_sidecar,
)


def test_package_label() -> None:
    e = {
        "suggested_theme": "ЦНАП / адмінпослуги",
        "suggested_theme_id": "cnap",
        "suggested_form": "делегування",
        "suggested_form_id": "delegation",
        "suggest_confidence": "high",
        "suggest_rationale": "тест",
    }
    pkg = package_from_edge(e)
    assert pkg["theme_id"] == "cnap"
    assert pkg["form_id"] == "delegation"
    assert pkg["label_uk"] == "ЦНАП / адмінпослуги — делегування"


def test_signals_and_primary() -> None:
    thematic = {
        "track": "thematic",
        "goals_cosine": 0.15,
        "geo_score": 0.2,
        "mss_network": 0,
        "known": False,
        "suggested_theme": "Туризм / кластер",
        "suggested_theme_id": "tourism",
        "suggested_form": "спільний проєкт",
        "suggested_form_id": "joint_project",
        "suggest_confidence": "medium",
    }
    annotate_candidate(thematic)
    assert thematic["kind"] == "mss_candidate"
    assert thematic["status"] == "hypothesis"
    assert thematic["discovery_primary"] == "strategy_goals"
    ids = {s["id"] for s in thematic["signals"]}
    assert "strategy_goals" in ids
    assert thematic["package"]["label_uk"].startswith("Туризм")

    operational = {
        "track": "operational",
        "goals_cosine": 0.02,
        "geo_score": 0.95,
        "mss_network": 0,
        "fiscal_similarity": 0.7,
        "dream_overlap": 0.5,
        "operational_score": 0.8,
        "known": False,
        "suggested_theme": "ЦНАП / адмінпослуги",
        "suggested_theme_id": "cnap",
        "suggested_form": "делегування",
        "suggested_form_id": "delegation",
        "suggest_confidence": "medium",
    }
    annotate_candidate(operational)
    assert operational["discovery_primary"] == "geo"
    assert any(s["id"] == "geo" for s in operational["signals"])
    assert any(s["id"] == "structural" for s in operational["signals"])

    known = {
        "track": "mixed",
        "goals_cosine": 0.1,
        "geo_score": 0.5,
        "mss_network": 1.0,
        "known": True,
        "suggested_theme": "Туризм / кластер",
        "suggested_theme_id": "tourism",
        "suggested_form": "спільний проєкт",
        "suggested_form_id": "joint_project",
        "suggest_confidence": "high",
    }
    annotate_candidate(known)
    assert known["status"] == "registry_known"
    assert any(s["id"] == "network" for s in known["signals"])


def test_complementary_explicit() -> None:
    comp = {
        "track": "complementary",
        "complementary_score": 0.9,
        "known": False,
        "suggested_theme": "Освіта",
        "suggested_theme_id": "education",
        "suggested_form": "спільне утримання",
        "suggested_form_id": "joint_finance",
        "suggest_confidence": "high",
    }
    sigs = build_signals(comp)
    assert discovery_primary_for(comp, sigs) == "complementary"
    assert any(s["id"] == "complementary" for s in sigs)

    ask = {
        "track": "explicit-ask",
        "explicit_ask_score": 0.95,
        "known": False,
        "suggested_theme": "ЦНАП / адмінпослуги",
        "suggested_theme_id": "cnap",
        "suggested_form": "делегування",
        "suggested_form_id": "delegation",
        "suggest_confidence": "high",
    }
    annotate_candidate(ask)
    assert ask["discovery_primary"] == "explicit_ask"


def test_sidecar_smoke(tmp_path: Path | None = None) -> None:
    from pathlib import Path as P

    out_dir = P(tmp_path) if tmp_path else ROOT / "data" / "releases"
    # Use in-memory tiny sets — do not rewrite production on unit test
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        td_path = P(td)
        edges = [
            {
                "a": "A громада",
                "b": "B громада",
                "track": "thematic",
                "goals_cosine": 0.2,
                "geo_score": 0.1,
                "mss_network": 0,
                "known": True,
                "suggested_theme": "Туризм / кластер",
                "suggested_theme_id": "tourism",
                "suggested_form": "спільний проєкт",
                "suggested_form_id": "joint_project",
                "suggest_confidence": "high",
            },
            {
                "a": "C громада",
                "b": "D громада",
                "track": "thematic",
                "goals_cosine": 0.18,
                "geo_score": 0.1,
                "mss_network": 0,
                "known": False,
                "suggested_theme": "Туризм / кластер",
                "suggested_theme_id": "tourism",
                "suggested_form": "спільний проєкт",
                "suggested_form_id": "joint_project",
                "suggest_confidence": "medium",
            },
        ]
        for e in edges:
            annotate_candidate(e)
        result = write_candidates_sidecar(
            matching_edges=edges,
            thematic=[edges[1]],
            operational=[],
            complementary=[],
            explicit_ask=[],
            top_n_per_slice=10,
            out_path=td_path / "mss-candidates.json",
            manifest_path=td_path / "mss-candidates.manifest.json",
        )
        assert result["registry_known"] == 1
        assert result["hypotheses"] == 1
        payload = __import__("json").loads(
            (td_path / "mss-candidates.json").read_text(encoding="utf-8")
        )
        assert payload["registry_known"][0]["package"]["form_id"] == "joint_project"
        assert payload["hypotheses"][0]["signal_chips"]


def main() -> None:
    test_package_label()
    test_signals_and_primary()
    test_complementary_explicit()
    test_sidecar_smoke()
    print("test_mss_candidate: OK")


if __name__ == "__main__":
    main()
