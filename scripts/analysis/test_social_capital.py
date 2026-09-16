#!/usr/bin/env python3
"""Unit + light integration checks for social_capital (v7.3 0.15 slot)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))

from social_capital import (  # noqa: E402
    W_COINTENT,
    W_NAMED,
    W_SHARED_DONOR,
    W_TWINNING_BOTH,
    combine_social_capital,
    parse_programs,
    social_capital_score,
)
from enrich_from_kse import mss_network_score  # noqa: E402
from dream_priority import WEIGHT_SOCIAL, combined_match_score, priority_from_edge  # noqa: E402

KREMENCHUK = "UA53020110000092487"
OKHTYRKA = "UA59040110000026694"
ODESA = "UA51100270000073549"


def test_combine_weights() -> None:
    sc, parts = combine_social_capital(mss_network=1.0)
    assert sc == 1.0
    assert "kse_or_plich" in parts["flags"]

    sc, _ = combine_social_capital(named=True)
    assert sc == W_NAMED

    sc, _ = combine_social_capital(cointent=True)
    assert sc == W_COINTENT

    sc, _ = combine_social_capital(twinning_both=True)
    assert sc == W_TWINNING_BOTH

    sc, _ = combine_social_capital(shared_donor=True)
    assert sc == W_SHARED_DONOR

    # Direct takes max, not sum, of KSE vs named.
    sc, _ = combine_social_capital(mss_network=0.5, named=True)
    assert sc == W_NAMED

    # Named + both twinning hits the cap.
    sc, _ = combine_social_capital(named=True, twinning_both=True)
    assert sc == 1.0

    # Cap
    sc, _ = combine_social_capital(
        mss_network=1.0, twinning_both=True, shared_donor=True
    )
    assert sc == 1.0


def test_methodology_programs_excluded() -> None:
    assert parse_programs(["DOBRE", "STRATEGY LAB", "Ре:Форм"]) == ["DOBRE"]


def test_priority_from_edge_v71_goals() -> None:
    p = priority_from_edge({"goals_cosine": 0.4, "geo_score": 0.2, "mss_network": 0})
    assert abs(p - 0.4) < 1e-9


def test_combined_slot_weight() -> None:
    # Changing only the 0.15 slot by 1.0 moves combined score by 0.15.
    assert abs(combined_match_score(0, 0, 1.0) - WEIGHT_SOCIAL) < 1e-9


def test_plich_pair_still_full() -> None:
    mss = mss_network_score(KREMENCHUK, OKHTYRKA)
    sc, parts = social_capital_score(KREMENCHUK, OKHTYRKA, mss_network=mss)
    assert mss == 1.0
    assert sc == 1.0
    assert "kse_or_plich" in parts["flags"]


def test_unconnected_zero_without_affiliations() -> None:
    fake_a, fake_b = "UA0000000000000000000", "UA1111111111111111111"
    assert mss_network_score(fake_a, fake_b) == 0.0
    sc, parts = social_capital_score(fake_a, fake_b, mss_network=0.0)
    assert sc == 0.0
    assert parts["flags"] == []


def test_named_neighbour_from_explicit_ask() -> None:
    # Козелецька names Парафіївська in the tourism-cluster agreement quote.
    edges = json.loads(
        (ROOT / "data/releases/matching-edges.explicit-ask.json").read_text(encoding="utf-8")
    )
    named = next(
        e
        for e in edges
        if e.get("explicit_ask_score") == 0.95
        and "Козелецька" in (e.get("a") or "")
        and "Парафіївська" in (e.get("b") or "")
    )
    sc, parts = social_capital_score(
        named.get("a_katottg"),
        named.get("b_katottg"),
        name_a=named["a"],
        name_b=named["b"],
        mss_network=0.0,
    )
    assert sc >= W_NAMED
    assert "named" in parts["flags"]


def test_twinning_is_not_mss_network() -> None:
    payload = json.loads(
        (ROOT / "data/releases/twinning-partners.json").read_text(encoding="utf-8")
    )
    registry = [
        row["katottg"]
        for row in payload.get("hromadas") or []
        if row.get("katottg")
        and any(p.get("confidence") == "registry" for p in row.get("partners") or [])
    ]
    other = next(k for k in registry if k != ODESA)
    mss = mss_network_score(ODESA, other)
    sc, parts = social_capital_score(ODESA, other, mss_network=mss)
    assert "twinning_both" in parts["flags"]
    assert sc >= W_TWINNING_BOTH
    # Twinning alone must not look like a domestic IMC edge.
    if mss <= 0:
        assert sc < 1.0


def test_one_sided_twinning_is_not_a_pair_signal() -> None:
    sc, parts = social_capital_score(ODESA, "UA1111111111111111111", mss_network=0.0)
    assert "twinning_both" not in parts["flags"]
    assert sc == 0.0


def test_shared_donor_from_tags() -> None:
    rows = json.loads((ROOT / "data/releases/hromadas.json").read_text(encoding="utf-8"))
    dobre = [
        r
        for r in rows
        if "DOBRE" in (r.get("DonorsPrograms") or [])
        and (r.get("Katottg") or "").strip()
    ]
    assert len(dobre) >= 2
    a, b = dobre[0], dobre[1]
    sc, parts = social_capital_score(
        a["Katottg"],
        b["Katottg"],
        name_a=a["Name"],
        name_b=b["Name"],
        mss_network=0.0,
    )
    assert "shared_donor" in parts["flags"]
    assert sc >= W_SHARED_DONOR


def test_mss_candidate_chips_from_parts() -> None:
    from mss_candidate import build_signals

    e = {
        "track": "mixed",
        "goals_cosine": 0.05,
        "geo_score": 0.2,
        "mss_network": 0.0,
        "social_capital": 0.55,
        "social_capital_parts": {"flags": ["twinning_both", "shared_donor"]},
    }
    ids = {s["id"] for s in build_signals(e)}
    assert "twinning" in ids
    assert "donor" in ids
    assert "network" not in ids


def main() -> None:
    test_combine_weights()
    test_methodology_programs_excluded()
    test_priority_from_edge_v71_goals()
    test_combined_slot_weight()
    test_plich_pair_still_full()
    test_unconnected_zero_without_affiliations()
    test_named_neighbour_from_explicit_ask()
    test_twinning_is_not_mss_network()
    test_one_sided_twinning_is_not_a_pair_signal()
    test_shared_donor_from_tags()
    test_mss_candidate_chips_from_parts()
    print("test_social_capital: ok")


if __name__ == "__main__":
    main()
