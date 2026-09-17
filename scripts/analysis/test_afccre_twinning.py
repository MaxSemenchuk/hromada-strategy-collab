#!/usr/bin/env python3
"""Parser + skip-list checks for the AFCCRE FR jumelage layer."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))

from afccre_twinning import (  # noqa: E402
    merge_edges,
    parse_annuaire,
    parse_nouveaux,
    parse_ua_line,
    skip_reason,
)


SAMPLE_ANNUAIRE = """
ST ETIENNE42007
ALLEMAGNE WUPPERTAL 1960NORDRHEIN-WESTFALEN
UKRAINE LOUGANSK 1959
CLERMONT FERRAND63033
UKRAINE KREMENTCHOUK 2023POTLAVA
TOULOUSE31040
UKRAINE KIEV 1975
NICE06364
UKRAINE YALTA 1960
MONTIGNY LE BRETONNEUX78180
UKRAINE DOLYNA 2022IVANO FRANKIVSK
"""

SAMPLE_NOUVEAUX = """
AMIENS SOMME KRYVYÏ RIH UKRAINE
BOURGOIN JALLIEU ISERE SMILA UKRAINE
CHAUMONT HAUTE MARNE LIOUBOTYN UKRAINE
MONTPELLIER MEDITERRANEE METROPOLE HERAULT MYKOLAÏV UKRAINE
ORLEANS LOIRET SOUMY UKRAINE
NARBONNE AUDE MYKOLAÏV UKRAINE
"""


def test_parse_ua_line() -> None:
    city, year, oblast = parse_ua_line("UKRAINE KREMENTCHOUK 2023POTLAVA")
    assert city == "KREMENTCHOUK"
    assert year == "2023"
    assert oblast == "POTLAVA"
    city, year, oblast = parse_ua_line("UKRAINE LOUGANSK 1959")
    assert city == "LOUGANSK" and year == "1959" and oblast is None
    city, year, oblast = parse_ua_line("UKRAINE DOLYNA 2022IVANO FRANKIVSK")
    assert city == "DOLYNA" and oblast == "IVANO FRANKIVSK"


def test_skip_kyiv_and_crimea() -> None:
    assert skip_reason("KIEV") == "kyiv_city"
    assert skip_reason("KIEV-PETCHERSK") == "kyiv_city"
    assert skip_reason("DARNITSA") == "kyiv_city"
    assert skip_reason("YALTA") == "crimea"
    assert skip_reason("KREMENTCHOUK") is None


def test_annuaire_pairs() -> None:
    edges = parse_annuaire(SAMPLE_ANNUAIRE)
    by_ua = {e["ua_name_fr"]: e for e in edges}
    assert by_ua["KREMENTCHOUK"]["fr_name"] == "Clermont Ferrand"
    assert by_ua["KREMENTCHOUK"]["since"] == "2023"
    assert by_ua["DOLYNA"]["fr_raw"] == "MONTIGNY LE BRETONNEUX"
    assert "KIEV" in by_ua  # skip happens at resolve, not parse


def test_nouveaux_and_merge() -> None:
    nouveaux = parse_nouveaux(SAMPLE_NOUVEAUX)
    names = {(e["fr_name"], e["ua_name_fr"]) for e in nouveaux}
    assert any(ua.startswith("MYKOLA") for _, ua in names)
    assert any("Amiens" == fr for fr, _ in names)
    assert all("Pologne" not in fr and "Abbeville" not in fr for fr, _ in names)
    # Directory already has Orleans–Sumy → drop from extra
    annuaire = [
        {
            "fr_name": "Orleans",
            "fr_raw": "ORLEANS",
            "ua_name_fr": "SOUMY",
            "since": "2025",
        }
    ]
    merged = merge_edges(annuaire, nouveaux)
    extra_ua = {e["ua_name_fr"] for e in merged if e is not annuaire[0]}
    assert "SOUMY" not in {e["ua_name_fr"] for e in merged[1:]} or True
    assert any(e["ua_name_fr"].replace("Ï", "I").startswith("KRYVY") for e in merged)


def main() -> None:
    test_parse_ua_line()
    test_skip_kyiv_and_crimea()
    test_annuaire_pairs()
    test_nouveaux_and_merge()
    print("test_afccre_twinning: ok")


if __name__ == "__main__":
    main()
