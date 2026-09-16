#!/usr/bin/env python3
"""Unit checks for UA–EU international theme tagging and 3668 helpers."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
from build_intl_agreements import country_iso, kind_id, ua_level  # noqa: E402
from intl_theme import classify_intl_themes, names_overlap  # noqa: E402


def test_themes() -> None:
    culture = classify_intl_themes(
        "торговельно-економічне і культурне співробітництво",
        "культура, освіта, спорт",
    )
    assert "culture" in culture, culture
    assert "education" in culture, culture
    assert "economy" in culture, culture

    health_en = classify_intl_themes(
        "Ensuring accessibility of health care services to patients"
    )
    assert "health" in health_en, health_en

    water_en = classify_intl_themes(
        "Development of sewerage infrastructure and improvement of sewage management"
    )
    assert "water" in water_en, water_en

    border = classify_intl_themes(
        "Joint actions for the opening of the international BCP Yablunivka-Remeta"
    )
    assert "borders" in border, border

    empty = classify_intl_themes("Договір про партнерство і співробітництво")
    assert empty == [] or "economy" not in empty


def test_kind_and_country() -> None:
    assert kind_id("транскордонне та міжтериторіальне співробітництво") == "cbc_interterritorial"
    assert kind_id("міжтериторіальне співробітництво") == "interterritorial"
    assert kind_id("транскордонне співробітництво") == "cbc"
    assert kind_id("") == "unspecified"
    assert country_iso("Республіка Польща") == "PL"
    assert country_iso("Федеративна Республіка Німеччина") == "DE"
    assert country_iso("Французька Республіка") == "FR"
    assert country_iso("Королівство Норвегія") == "NO"
    assert country_iso("Сполучене Королівство Великої Британії та Північної Ірландії") == "GB"


def test_ua_level() -> None:
    assert ua_level("Вінницька міська рада (21050, м. Вінниця)") == "hromada"
    assert ua_level(
        "Вінницька обласна державна адміністрація (21050 м. Вінниця вул.Соборна 70)"
    ) == "oblast"
    assert ua_level("Ямницька сільська рада (Ямницька територіальна громада)") == "hromada"


def test_name_overlap() -> None:
    assert names_overlap("Ґміна Грубешів", "Грубешів")
    assert names_overlap("гміна Седліще", "Седліще")
    assert not names_overlap("Люблін", "Варшава")


def main() -> None:
    test_themes()
    test_kind_and_country()
    test_ua_level()
    test_name_overlap()
    print("test_intl_theme: OK")


if __name__ == "__main__":
    main()
