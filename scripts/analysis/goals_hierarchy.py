#!/usr/bin/env python3
"""Parse / classify strategy goal lines into strategic vs operational.

Used by match.py (v7) and build_goals_hierarchy.py.
Hierarchy may also come from goals-hierarchy.json (structured extractions).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HIERARCHY_RELEASE = ROOT / "data" / "releases" / "goals-hierarchy.json"

STRATEGIC_RE = re.compile(
    r"(?i)^(?:стратегічн\w*\s+ціль|ціль|напрям)\s*[.:]?\s*[0-9A-CА-Яа-я]|"
    r"^(?:\d+)\.\s+\S"
)
OPERATIONAL_RE = re.compile(
    r"(?i)^(?:оперативн\w*\s+ціль)|"
    r"^(?:\d+\.\d+)"
)
MSS_INTENT_RE = re.compile(
    r"(?i)(?:міжмуніцип|МСС|кооперац\w*\s+з\s+інш\w*\s+громад|"
    r"співпрац\w*\s+з\s+(?:сусідн|інш)\w*\s+громад|"
    r"спільн\w+\s+(?:з\s+громад|використан|проєкт|проект))"
)


def split_goal_lines(goals: str | list | None) -> list[str]:
    if not goals:
        return []
    if isinstance(goals, list):
        raw = [str(x).strip(" \t-•\n") for x in goals if str(x).strip()]
    else:
        raw = [l.strip(" \t-•\n") for l in re.split(r"\n", str(goals))]
    lines: list[str] = []
    for line in raw:
        if not line:
            continue
        lines.extend(_expand_long_goal_line(line))
    return [l for l in lines if len(l) > 15]


# Compressed "all priorities in one paragraph" extractions (common in partial /
# proxy rows). Splitting them is length/hub mitigation: otherwise two kitchen-sink
# blobs cosine-match as if they shared a focused profile.
_LONG_LINE_CHARS = 120
_GOAL_MARKER_SPLIT = re.compile(
    r"(?=(?:Стратегічн\w*\s+(?:ціль|напрям)|Основний напрям|Ціль)\s*[.:]?\s*[0-9A-CА-Яа-я0-9])",
    re.I,
)
_CLAUSE_SPLIT = re.compile(r"\s+[-–—]\s+|;\s+")


def _expand_long_goal_line(line: str) -> list[str]:
    if len(line) <= _LONG_LINE_CHARS:
        return [line]
    marked = [p.strip(" \t-•,") for p in _GOAL_MARKER_SPLIT.split(line) if p.strip()]
    if len(marked) > 1:
        out: list[str] = []
        for part in marked:
            out.extend(_expand_long_goal_line(part) if len(part) > _LONG_LINE_CHARS else [part])
        return out or [line]
    chunks = [c.strip(" \t-•,") for c in _CLAUSE_SPLIT.split(line)]
    chunks = [c for c in chunks if len(c) > 20]
    if len(chunks) >= 2:
        return chunks
    return [line]


def classify_line(line: str) -> str:
    """Return 'operational' | 'strategic' | 'other'."""
    if OPERATIONAL_RE.search(line):
        return "operational"
    if STRATEGIC_RE.search(line):
        return "strategic"
    # Long SDG-style paragraphs without numbering → treat as strategic
    if len(line) > 80:
        return "strategic"
    return "other"


def parse_goals_text(goals: str | list | None) -> dict:
    lines = split_goal_lines(goals)
    strategic: list[dict] = []
    operational: list[dict] = []
    other: list[str] = []
    for line in lines:
        kind = classify_line(line)
        if kind == "operational":
            parent = None
            m = re.match(r"^(\d+)\.\d+", line)
            if m:
                parent = m.group(1)
            operational.append({"text": line, "parent": parent})
        elif kind == "strategic":
            sid = None
            m = re.search(r"(?:ціль|напрям)\s*([0-9A-C])", line, re.I)
            if not m:
                m = re.match(r"^(\d+)\.", line)
            if m:
                sid = m.group(1)
            strategic.append({"id": sid, "text": line})
        else:
            other.append(line)
    return {
        "strategic_goals": strategic,
        "operational_goals": operational,
        "other_lines": other,
        "all_lines": lines,
    }


def load_hierarchy_index(path: Path | None = None) -> dict[str, dict]:
    """Index by Name and Katottg."""
    p = path or HIERARCHY_RELEASE
    if not p.exists():
        return {}
    raw = json.loads(p.read_text(encoding="utf-8"))
    rows = raw.get("hromadas") if isinstance(raw, dict) else raw
    index: dict[str, dict] = {}
    for row in rows or []:
        if row.get("name"):
            index[row["name"]] = row
        if row.get("katottg"):
            index[row["katottg"]] = row
    return index


def record_subgoals(
    name: str,
    katottg: str | None,
    goals_text: str,
    hierarchy_index: dict[str, dict] | None = None,
) -> tuple[list[str], list[str], list[str]]:
    """Return (strategic_texts, operational_texts, all_for_embedding).

    Prefer curated hierarchy release; else parse Goals text.
    Embedding list: operational first (higher weight applied in matcher),
    then strategic, then leftover lines.
    """
    hier = None
    if hierarchy_index:
        hier = hierarchy_index.get(name) or (hierarchy_index.get(katottg) if katottg else None)

    if hier and (hier.get("strategic_goals") or hier.get("operational_goals")):
        strat_raw = [
            (g.get("text") if isinstance(g, dict) else str(g)).strip()
            for g in (hier.get("strategic_goals") or [])
        ]
        ops_raw = [
            (g.get("text") if isinstance(g, dict) else str(g)).strip()
            for g in (hier.get("operational_goals") or [])
        ]
        strat: list[str] = []
        for s in strat_raw:
            strat.extend(x for x in _expand_long_goal_line(s) if len(x) > 15)
        ops: list[str] = []
        for s in ops_raw:
            ops.extend(x for x in _expand_long_goal_line(s) if len(x) > 15)
        all_lines = ops + strat
        if not all_lines:
            all_lines = split_goal_lines(goals_text)
        return strat, ops, all_lines

    parsed = parse_goals_text(goals_text)
    strat = [g["text"] for g in parsed["strategic_goals"]]
    ops = [g["text"] for g in parsed["operational_goals"]]
    other = parsed["other_lines"]
    if ops or strat:
        all_lines = ops + strat + other
    else:
        all_lines = parsed["all_lines"]
    return strat, ops, all_lines


def find_mss_intents_in_text(text: str, *, field: str) -> list[dict]:
    if not text or not MSS_INTENT_RE.search(text):
        return []
    intents: list[dict] = []
    # Prefer line-level hits; skip clear negations / absences
    neg = re.compile(
        r"(?i)(?:не\s+підтвердж|немає|не\s+має|жодної?\s+угод|відсутн|"
        r"лише\s+як|не\s+згаду|без\s+формальн)"
    )
    for line in re.split(r"[\n;•]", text):
        line = line.strip(" \t-•")
        if len(line) < 20:
            continue
        if not MSS_INTENT_RE.search(line):
            continue
        if neg.search(line):
            continue
        intents.append(
            {
                "quote": line[:400],
                "field": field,
                "theme": _guess_theme(line),
            }
        )
    if not intents and MSS_INTENT_RE.search(text) and not neg.search(text):
        # Single blob — take a window around first match
        m = MSS_INTENT_RE.search(text)
        start = max(0, m.start() - 80)
        end = min(len(text), m.end() + 200)
        window = text[start:end].strip()
        if not neg.search(window):
            intents.append(
                {
                    "quote": window[:400],
                    "field": field,
                    "theme": _guess_theme(window),
                }
            )
    return intents


def _guess_theme(text: str) -> str | None:
    themes = [
        ("вода", r"вод[оа]|річк|каналіз"),
        ("відходи", r"смітт|відход|ТПВ|полігон"),
        ("транспорт", r"транспорт|дорог|перевезен"),
        ("туризм", r"турист|спадщин"),
        ("ЦНАП", r"ЦНАП|адмінпослуг"),
        ("безпека", r"безпек|ЦЗ|пожеж"),
        ("енергія", r"енерг|тепло|ВДЕ"),
        ("медицина", r"мед|лікарн|здоров"),
        ("освіта", r"освіт|школ"),
    ]
    for label, pat in themes:
        if re.search(pat, text, re.I):
            return label
    return None
