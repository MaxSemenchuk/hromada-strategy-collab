#!/usr/bin/env python3
"""Regression tests for goals_hierarchy.py — line classification and
hierarchy-index lookup that feed match.py's embedding input directly.
No model download needed.
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
from goals_hierarchy import (  # noqa: E402
    classify_line,
    find_mss_intents_in_text,
    load_hierarchy_index,
    parse_goals_text,
    record_subgoals,
    split_goal_lines,
)


def test_classify_line_operational_vs_strategic() -> None:
    assert classify_line("1.1. Модернізація доріг місцевого значення") == "operational"
    assert classify_line("Стратегічна ціль 1. Розвиток економіки громади") == "strategic"
    assert classify_line("Напрям 2. Комфортне середовище") == "strategic"


def test_classify_line_long_paragraph_falls_back_to_strategic() -> None:
    # No numbering/marker, but long SDG-style prose — treated as strategic, not dropped.
    long_line = (
        "Стимулювання підприємницької активності, залучення інвестицій, "
        "розвиток агропромислового комплексу та туристичного потенціалу громади"
    )
    assert len(long_line) > 80
    assert classify_line(long_line) == "strategic"


def test_classify_line_short_unmarked_is_other() -> None:
    line = "Це довільний текст без жодного маркера цілі"
    assert 15 < len(line) <= 80
    assert classify_line(line) == "other"


def test_split_goal_lines_filters_short_lines() -> None:
    lines = split_goal_lines("коротко\nСтратегічна ціль 1. Розвиток економіки громади")
    assert all(len(l) > 15 for l in lines)
    assert not any(l == "коротко" for l in lines)


def test_split_goal_lines_expands_combined_paragraph() -> None:
    combined = (
        "Стратегічна ціль 1: Конкурентоспроможна економіка громади з новими робочими місцями. "
        "Стратегічна ціль 2: Комфортна та безпечна інфраструктура громади для мешканців. "
        "Стратегічна ціль 3: Високі соціальні стандарти життя та якісні послуги для громади."
    )
    assert len(combined) > 120
    lines = split_goal_lines(combined)
    assert len(lines) == 3
    assert all(l.startswith("Стратегічна ціль") for l in lines)


def test_split_goal_lines_handles_bare_marker_without_prefix() -> None:
    # Bare "Ціль N" markers (no "Стратегічна" prefix) must still split correctly —
    # regression guard for the marker-collapse fix above.
    combined = (
        "Ціль 1: Конкурентоспроможна економіка громади з новими робочими місцями. "
        "Ціль 2: Комфортна та безпечна інфраструктура громади для мешканців. "
        "Ціль 3: Високі соціальні стандарти життя та якісні послуги для громади."
    )
    assert len(combined) > 120
    lines = split_goal_lines(combined)
    assert len(lines) == 3
    assert all(l.startswith("Ціль") for l in lines)


def test_parse_goals_text_extracts_ids() -> None:
    text = (
        "Стратегічна ціль 1. Розвиток економіки громади та залучення інвестицій\n"
        "1.1. Підтримка малого та середнього бізнесу в громаді"
    )
    parsed = parse_goals_text(text)
    assert len(parsed["strategic_goals"]) == 1
    assert parsed["strategic_goals"][0]["id"] == "1"
    assert len(parsed["operational_goals"]) == 1
    assert parsed["operational_goals"][0]["parent"] == "1"


def test_load_hierarchy_index_homonym_resolution() -> None:
    rows = [
        {"katottg": "UA001", "name": "Солотвинська", "strategic_goals": [{"text": "A"}]},
        {"katottg": "UA002", "name": "Солотвинська", "strategic_goals": [{"text": "B"}]},
        {"katottg": "UA003", "name": "Унікальна", "strategic_goals": [{"text": "C"}]},
    ]
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump({"hromadas": rows}, f, ensure_ascii=False)
        path = Path(f.name)
    try:
        index = load_hierarchy_index(path)
        # Both katottg-keyed entries present.
        assert index["UA001"]["name"] == "Солотвинська"
        assert index["UA002"]["name"] == "Солотвинська"
        # Ambiguous name must NOT resolve to either row.
        assert "Солотвинська" not in index
        # Unique name resolves.
        assert index["Унікальна"]["katottg"] == "UA003"
    finally:
        path.unlink()


def test_record_subgoals_prefers_hierarchy_over_parsing() -> None:
    hierarchy_index = {
        "UA001": {
            "strategic_goals": [{"text": "Стратегічна ціль 1. Розвиток туризму громади"}],
            "operational_goals": [{"text": "1.1. Модернізація водопостачання громади"}],
        }
    }
    strat, ops, all_lines = record_subgoals(
        "Тестова громада", "UA001", "ignored raw text", hierarchy_index
    )
    assert ops == ["1.1. Модернізація водопостачання громади"]
    assert strat == ["Стратегічна ціль 1. Розвиток туризму громади"]
    # Embedding order: operational first, then strategic.
    assert all_lines[0] == ops[0]


def test_record_subgoals_falls_back_to_parsing_when_no_hierarchy_match() -> None:
    strat, ops, all_lines = record_subgoals(
        "Невідома громада",
        "UA999",
        "Стратегічна ціль 1. Розвиток економіки громади та залучення інвестицій",
        hierarchy_index={},
    )
    assert strat
    assert all_lines


def test_find_mss_intents_detects_explicit_language() -> None:
    text = "Громада планує міжмуніципальне співробітництво з сусідніми громадами щодо водопостачання"
    intents = find_mss_intents_in_text(text, field="Goals")
    assert len(intents) == 1
    assert intents[0]["theme"] == "вода"


def test_find_mss_intents_skips_negated_language() -> None:
    text = "На сьогодні немає угод про міжмуніципальну співпрацю з сусідніми громадами"
    intents = find_mss_intents_in_text(text, field="Goals")
    assert intents == []


def main() -> None:
    test_classify_line_operational_vs_strategic()
    test_classify_line_long_paragraph_falls_back_to_strategic()
    test_classify_line_short_unmarked_is_other()
    test_split_goal_lines_filters_short_lines()
    test_split_goal_lines_expands_combined_paragraph()
    test_split_goal_lines_handles_bare_marker_without_prefix()
    test_parse_goals_text_extracts_ids()
    test_load_hierarchy_index_homonym_resolution()
    test_record_subgoals_prefers_hierarchy_over_parsing()
    test_record_subgoals_falls_back_to_parsing_when_no_hierarchy_match()
    test_find_mss_intents_detects_explicit_language()
    test_find_mss_intents_skips_negated_language()
    print("OK: goals_hierarchy checks passed")


if __name__ == "__main__":
    main()
