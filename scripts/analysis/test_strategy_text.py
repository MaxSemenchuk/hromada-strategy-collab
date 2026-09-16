#!/usr/bin/env python3
"""Unit checks for strategy_text named objects / neighbours / deficits."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))

from strategy_text import (  # noqa: E402
    KITCHEN_SINK_SECTORS,
    build_name_index,
    deficit_kinds,
    find_assets,
    find_deficits,
    find_named_neighbours,
    offer_kinds,
    sector_hit_weight,
)


def test_nizhyn_oster_river() -> None:
    text = (
        "Кооперація з іншими громадами у спільному вирішенні проблеми "
        "розчищення річки Остер"
    )
    assets = find_assets(text, field="mss_agreements")
    rivers = [a for a in assets if a["kind"] == "river"]
    assert rivers, assets
    assert "остер" in rivers[0]["key"]
    assert rivers[0]["theme"] == "вода"
    assert not rivers[0]["common"]


def test_dnipro_is_common_hydronym() -> None:
    assets = find_assets("Розвиток рекреації на річці Дніпро", field="goals")
    assert assets
    assert assets[0]["common"] is True


def test_named_cluster() -> None:
    text = "Договір МСС «Створення туристичного кластеру «Місцями козацької сили»»"
    assets = find_assets(text, field="mss_agreements")
    clusters = [a for a in assets if a["kind"] == "cluster"]
    assert clusters
    assert "козацької" in clusters[0]["name"]


def test_cnap_without_name_is_not_shared_asset() -> None:
    assert find_assets("Модернізація ЦНАП та адмінпослуг", field="projects") == []


def test_water_deficit_not_generic_school() -> None:
    ch = "Зношений водогін; брак кваліфікованих кадрів; погане міжселищне сполучення."
    kinds = deficit_kinds(ch)
    assert "water_infra" in kinds
    assert "roads" in kinds
    school = find_deficits("Недостатній рівень освіти та якості шкільних послуг")
    assert school == []


def test_offer_waterkanal() -> None:
    kinds = offer_kinds("КП «Наш Дім Леськи»; централізоване водопостачання більшості НП")
    assert "water_infra" in kinds


def test_neighbour_kozelets_cluster() -> None:
    rows = [
        {
            "Name": "Козелецька селищна територіальна громада",
            "Katottg": "UA1",
            "Oblast": "Чернігівська область",
        },
        {
            "Name": "Ніжинська міська територіальна громада",
            "Katottg": "UA2",
            "Oblast": "Чернігівська область",
        },
        {
            "Name": "Батуринська міська територіальна громада",
            "Katottg": "UA3",
            "Oblast": "Чернігівська область",
        },
        {
            "Name": "Парафіївська селищна територіальна громада",
            "Katottg": "UA4",
            "Oblast": "Чернігівська область",
        },
        {
            "Name": "Ніжинська сільська територіальна громада",
            "Katottg": "UA5",
            "Oblast": "Львівська область",
        },
    ]
    index = build_name_index(rows)
    text = (
        "Договір МСС «Створення туристичного кластеру» з Ніжинською, "
        "Батуринською та Парафіївською громадами"
    )
    found = find_named_neighbours(
        text,
        speaker_name="Козелецька селищна територіальна громада",
        speaker_oblast="Чернігівська область",
        index=index,
    )
    shorts = {x["short"] for x in found}
    assert "Ніжинська" in shorts
    assert "Батуринська" in shorts
    assert "Парафіївська" in shorts
    nizhyn = next(x for x in found if x["short"] == "Ніжинська")
    assert nizhyn["katottg"] == "UA2"


def test_neighbour_list_after_gromady_word() -> None:
    rows = [
        {
            "Name": "Козелецька селищна територіальна громада",
            "Katottg": "UA0",
            "Oblast": "Чернігівська область",
        },
        {
            "Name": "Ніжинська міська територіальна громада",
            "Katottg": "UA2",
            "Oblast": "Чернігівська область",
        },
        {
            "Name": "Батуринська міська територіальна громада",
            "Katottg": "UA3",
            "Oblast": "Чернігівська область",
        },
        {
            "Name": "Парафіївська селищна територіальна громада",
            "Katottg": "UA4",
            "Oblast": "Чернігівська область",
        },
        {
            "Name": "Сухополов'янська сільська територіальна громада",
            "Katottg": "UA6",
            "Oblast": "Чернігівська область",
        },
    ]
    index = build_name_index(rows)
    text = (
        "Учасники: Козелецька, Ніжинська, Батуринська громади, "
        "Сухополов'янська та Парафіївська сільські/селищні ради."
    )
    found = find_named_neighbours(
        text,
        speaker_name="Козелецька селищна територіальна громада",
        speaker_oblast="Чернігівська область",
        index=index,
    )
    shorts = {x["short"] for x in found}
    assert "Ніжинська" in shorts
    assert "Батуринська" in shorts
    assert "Парафіївська" in shorts
    assert "Сухополов'янська" in shorts


def test_oblast_adjective_is_not_a_hromada() -> None:
    rows = [
        {
            "Name": "Київська міська територіальна громада",
            "Katottg": "UA800",
            "Oblast": "м. Київ",
        },
        {
            "Name": "Вишгородська міська територіальна громада",
            "Katottg": "UA9",
            "Oblast": "Київська область",
        },
    ]
    index = build_name_index(rows)
    found = find_named_neighbours(
        "Розвиток співпраці громад Київської області",
        speaker_name="Вишгородська міська територіальна громада",
        speaker_oblast="Київська область",
        index=index,
    )
    assert found == []


def test_kitchen_sink_weights() -> None:
    assert "Освіта" in KITCHEN_SINK_SECTORS
    assert sector_hit_weight("Освіта", source="DREAM") < sector_hit_weight(
        "Вода / каналізація (ЖКГ)", source="DREAM"
    )
    assert sector_hit_weight("Довкілля / екологія", source="Strengths") == 0.85


def test_strategic_tsil_is_not_a_river() -> None:
    assert find_assets("Стратегічна ціль 1. Розвиток економіки", field="goals") == []


def test_homonym_leftover_other_oblast_is_skipped() -> None:
    rows = [
        {
            "Name": "Олександрійська сільська територіальна громада",
            "Katottg": "UA-RV",
            "Oblast": "Рівненська область",
        },
        {
            "Name": "Олександрійська міська територіальна громада",
            "Katottg": "UA-KR",
            "Oblast": "Кіровоградська область",
        },
    ]
    index = build_name_index(rows)
    found = find_named_neighbours(
        "Співпраця з Олександрійською громадою сусіднього району",
        speaker_name="Олександрійська сільська територіальна громада",
        speaker_oblast="Рівненська область",
        index=index,
    )
    assert found == []


def test_ukrainskymy_and_ova_are_not_neighbours() -> None:
    rows = [
        {
            "Name": "Сумська міська територіальна громада",
            "Katottg": "UA-SM",
            "Oblast": "Сумська область",
        },
        {
            "Name": "Українська міська територіальна громада",
            "Katottg": "UA-UK",
            "Oblast": "Дніпропетровська область",
        },
    ]
    index = build_name_index(rows)
    found = find_named_neighbours(
        "Партнерство з українськими громадами та співпраця з Сумською ОВА",
        speaker_name="Конотопська міська територіальна громада",
        speaker_oblast="Сумська область",
        index=index,
    )
    assert found == []


def test_compound_speaker_does_not_match_own_tail() -> None:
    rows = [
        {
            "Name": "Новгород-Сіверська міська територіальна громада",
            "Katottg": "UA-NS",
            "Oblast": "Чернігівська область",
        },
        {
            "Name": "Сіверська міська територіальна громада",
            "Katottg": "UA-SV",
            "Oblast": "Донецька область",
        },
    ]
    index = build_name_index(rows)
    found = find_named_neighbours(
        "Співпраця з Сіверською громадою",
        speaker_name="Новгород-Сіверська міська територіальна громада",
        speaker_oblast="Чернігівська область",
        index=index,
    )
    assert found == []


def test_airport_is_common_without_coop() -> None:
    assets = find_assets("Розвиток аеропорту Івано-Франківськ", field="projects")
    assert assets
    assert assets[0]["kind"] == "airport"
    assert assets[0]["common"] is True


def test_year_abbreviation_is_not_a_river() -> None:
    assert find_assets("Відсутність стратегії до 2024 р. Водопостачання лише на 28%", field="challenges") == []
    assert find_assets("планується спільний енергетичний кластер. Формальної угоди немає", field="projects") == []


def test_airport_lowercase_continuation_is_skipped() -> None:
    assert find_assets("близькість аеропорту створює навантаження на мережу", field="strengths") == []
    assert find_assets("30 км від Івано-Франківська й аеропорту Історична спадщина князівства", field="strengths") == []


def test_negated_neighbour_is_skipped() -> None:
    rows = [
        {
            "Name": "Кам'янська міська територіальна громада",
            "Katottg": "UA-KM",
            "Oblast": "Дніпропетровська область",
        },
        {
            "Name": "Божедарівська селищна територіальна громада",
            "Katottg": "UA-BZ",
            "Oblast": "Дніпропетровська область",
        },
    ]
    index = build_name_index(rows)
    found = find_named_neighbours(
        "Прямого зв'язку з Кам'янською громадою (той же район) не знайдено.",
        speaker_name="Божедарівська селищна територіальна громада",
        speaker_oblast="Дніпропетровська область",
        index=index,
    )
    assert found == []


def test_plich_program_is_not_a_named_neighbour() -> None:
    rows = [
        {
            "Name": "Глухівська міська територіальна громада",
            "Katottg": "UA-GL",
            "Oblast": "Сумська область",
        }
    ]
    index = build_name_index(rows)
    found = find_named_neighbours(
        "Пліч-о-пліч з Глухівською громадою — національна програма згуртованості",
        speaker_name="Маневицька селищна територіальна громада",
        speaker_oblast="Волинська область",
        index=index,
    )
    assert found == []


def main() -> None:
    test_nizhyn_oster_river()
    test_dnipro_is_common_hydronym()
    test_named_cluster()
    test_cnap_without_name_is_not_shared_asset()
    test_water_deficit_not_generic_school()
    test_offer_waterkanal()
    test_neighbour_kozelets_cluster()
    test_neighbour_list_after_gromady_word()
    test_oblast_adjective_is_not_a_hromada()
    test_kitchen_sink_weights()
    test_strategic_tsil_is_not_a_river()
    test_homonym_leftover_other_oblast_is_skipped()
    test_ukrainskymy_and_ova_are_not_neighbours()
    test_compound_speaker_does_not_match_own_tail()
    test_airport_is_common_without_coop()
    test_year_abbreviation_is_not_a_river()
    test_airport_lowercase_continuation_is_skipped()
    test_negated_neighbour_is_skipped()
    test_plich_program_is_not_a_named_neighbour()
    print("OK: strategy_text checks passed")


if __name__ == "__main__":
    main()
