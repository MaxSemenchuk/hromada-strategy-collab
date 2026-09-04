#!/usr/bin/env python3
"""Regression: Пліч-о-пліч feeds mss_network_score; EU-twinning/donor
experience feeds complementary_score as a resource offer (not a pairwise
network tie — see docs discussion in aim-cc-field-experiment-prereg.md)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))

import complementary_match as cm  # noqa: E402
from enrich_from_kse import mss_network_score, plich_o_plich_pairs  # noqa: E402

# Kremenchuk <-> Okhtyrka: bilateral_confirmed=true in plich-o-plich.json
# (a signed memorandum article), not in the KSE academic snapshot.
KREMENCHUK = "UA53020110000092487"
OKHTYRKA = "UA59040110000026694"


def test_plich_o_plich_loads_pairs() -> None:
    pairs = plich_o_plich_pairs()
    assert len(pairs) > 0


def test_mss_network_score_recognizes_plich_bilateral_pair() -> None:
    assert mss_network_score(KREMENCHUK, OKHTYRKA) == 1.0


def test_mss_network_score_zero_for_unconnected_pair() -> None:
    assert mss_network_score("UA0000000000000000000", "UA1111111111111111111") == 0.0


def test_international_ties_offer_from_donors_or_eu_twin() -> None:
    profiles = cm.load_profiles()
    # Одеська: EU-twinning registry rows (SKEW + decentralization_ua)
    odesa = profiles.get("UA51100270000073549")
    assert odesa is not None
    assert odesa["international_ties"] is True
    assert "international_ties" in cm.resource_offers(odesa)


def test_international_need_pattern_matches_donor_grant_language() -> None:
    pattern = dict((key, pat) for key, pat, _need in cm.RESOURCE_NEED_PATTERNS)["international"]
    assert pattern.search("Потреба залучення донорської підтримки та грантів")
    assert not pattern.search("Потреба ремонту доріг та освітлення вулиць")


def main() -> None:
    test_plich_o_plich_loads_pairs()
    test_mss_network_score_recognizes_plich_bilateral_pair()
    test_mss_network_score_zero_for_unconnected_pair()
    test_international_ties_offer_from_donors_or_eu_twin()
    test_international_need_pattern_matches_donor_grant_language()
    print("test_network_signal_sources: ok")


if __name__ == "__main__":
    main()
