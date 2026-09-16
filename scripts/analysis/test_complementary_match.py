#!/usr/bin/env python3
"""Kitchen-sink cap + named-deficit boost for complementary v3."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))

from complementary_match import complementary_score, pair_reasons_weighted  # noqa: E402


def _base(**kwargs):
    p = {
        "short": kwargs.get("short", "A"),
        "oblast": "Полтавська область",
        "challenges": "",
        "dream_sectors": [],
        "strength_sectors": [],
        "challenge_sectors": set(),
        "deficit_kinds": set(),
        "offer_kinds": set(),
        "health_known": False,
        "competence_known": False,
        "own_income_per_capita": 0,
        "dfrr_years": 0,
        "international_ties": False,
    }
    p.update(kwargs)
    return p


def test_kitchen_sink_alone_does_not_score() -> None:
    a = _base(
        short="А",
        dream_sectors=["Освіта", "Культура / спадщина", "Охорона здоров'я"],
        strength_sectors=["Підприємництво / МСБ"],
    )
    b = _base(
        short="Б",
        challenge_sectors={"Освіта", "Культура / спадщина", "Охорона здоров'я", "Підприємництво / МСБ"},
    )
    reasons, w = pair_reasons_weighted(a, b)
    assert w <= 0.5, w
    assert complementary_score(w, True) == 0.0
    assert any("шаблонних секторів" in r for r in reasons)


def test_named_water_deficit_scores() -> None:
    a = _base(short="А", offer_kinds={"water_infra"})
    b = _base(short="Б", deficit_kinds={"water_infra"}, challenge_sectors={"Вода / каналізація (ЖКГ)"})
    reasons, w = pair_reasons_weighted(a, b)
    assert w >= 1.6, w
    assert complementary_score(w, True) > 0
    assert any("водопостачання" in r for r in reasons)


def test_specific_sector_still_counts() -> None:
    a = _base(short="А", dream_sectors=["Вода / каналізація (ЖКГ)", "Довкілля / екологія"])
    b = _base(short="Б", challenge_sectors={"Вода / каналізація (ЖКГ)", "Довкілля / екологія"})
    _reasons, w = pair_reasons_weighted(a, b)
    assert w >= 2.0, w
    assert complementary_score(w, False) > 0


def main() -> None:
    test_kitchen_sink_alone_does_not_score()
    test_named_water_deficit_scores()
    test_specific_sector_still_counts()
    print("OK: complementary v3 checks passed")


if __name__ == "__main__":
    main()
