#!/usr/bin/env python3
"""Build PIN + matching overlay viz: full МСС network + Leaflet map / force graph.

Sources:
  - data/cache/kse/partnerships-hromadas-network.csv
  - data/cache/kse/geography.csv
  - data/releases/matching-edges.json
  - data/releases/hromadas.json  (PortalUrl / StrategyUrl / Goals)
  - docs/geo/ukraine-oblasts.geojson  (Natural Earth admin-1, simplified)
  - docs/geo/ukraine-basins-lev06.geojson  (HydroBASINS EU lev06 clipped/simplified)
  - data/research-log/hromada-basin-assignment.json  (optional basin_id on nodes)

Writes docs/mss-pin-matching-graph.html

Overlay policy (2026-07-24 / layers 2026-07-29 / basins 2026-08-03):
  Do NOT paint top-N by combined score — that collapses to geo neighbours in a
  sparse strategy corpus. Split tracks instead:

    thematic      — high goals_cosine  → «схожа стратегія» (default ON)
    operational   — high geo           → «зручний сусід»   (default OFF)
    complementary — resource/DREAM ↔ Challenges (default OFF)
    explicit_ask  — МСС language in strategy text (default OFF)
    twinning      — UA–EU sister cities from SKEW / strategy (node highlight, default OFF)
    plich_o_plich — domestic rear↔forpost pairs, text-mined from news (default OFF;
                    bilateral_confirmed edges only — see docs/plich-o-plich.md)
    basins        — HydroBASINS lev06 underlay (default OFF; not in score)
    universe      — all release hromadas with KSE lat/lon (metadata underlay)
"""

from __future__ import annotations

import csv
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
sys.path.insert(0, str(ROOT / "scripts" / "analysis" / "legacy"))
from edge_io import ensure_packages, load_matching_edges  # noqa: E402
from goal_overlap import explain_goal_overlap  # noqa: E402
from mss_suggest import (  # noqa: E402
    THEME_LABELS,
    THEME_LABELS_EN,
    classify_registry_theme,
    theme_label,
)
from tracks import operational_slice, thematic_slice  # noqa: E402

PIN = ROOT / "data/cache/kse/partnerships-hromadas-network.csv"
GEO = ROOT / "data/cache/kse/geography.csv"
MSS_REGISTRY = ROOT / "data/cache/mss/mss_registry.xlsx"
EDGES = ROOT / "data/releases/matching-edges.json"
COMPLEMENTARY = ROOT / "data/releases/matching-edges.complementary.json"
EXPLICIT_ASK = ROOT / "data/releases/matching-edges.explicit-ask.json"
TWINNING = ROOT / "data/releases/twinning-partners.json"
PLICH_O_PLICH = ROOT / "data/releases/plich-o-plich.json"
HROMADAS = ROOT / "data/releases/hromadas.json"
OBLASTS = ROOT / "docs/geo/ukraine-oblasts.geojson"
OUTLINE = ROOT / "docs/geo/ukraine-outline.geojson"
BASINS = ROOT / "docs/geo/ukraine-basins-lev06.geojson"
BASIN_ASSIGN = ROOT / "data/research-log/hromada-basin-assignment.json"
TEMPLATE = Path(__file__).with_name("mss_pin_matching_graph.template.html")
OUT = ROOT / "docs/mss-pin-matching-graph.html"

TOP_THEMATIC = 40
TOP_OPERATIONAL = 40
TOP_COMPLEMENTARY = 40
TOP_EXPLICIT_ASK = 40
MAX_AGREEMENTS_PER_EDGE = 6
AGREEMENT_TITLE_MAX = 140

COUNTRY_LABELS = {
    "DE": "Німеччина",
    "PL": "Польща",
    "SE": "Швеція",
    "BG": "Болгарія",
    "HU": "Угорщина",
    "RO": "Румунія",
    "SK": "Словаччина",
    "LT": "Литва",
    "CZ": "Чехія",
    "GE": "Грузія",
    "LV": "Латвія",
    "US": "США",
    "IT": "Італія",
    "FR": "Франція",
    "EE": "Естонія",
    "CN": "Китай",
    "MD": "Молдова",
    "TR": "Туреччина",
    "GR": "Греція",
    "CA": "Канада",
    "SI": "Словенія",
    "IL": "Ізраїль",
    "HR": "Хорватія",
    "MK": "Північна Македонія",
    "FI": "Фінляндія",
    "AT": "Австрія",
    "GB": "Велика Британія",
    "ES": "Іспанія",
    "PT": "Португалія",
    "AZ": "Азербайджан",
    "CH": "Швейцарія",
    "DK": "Данія",
    "AM": "Вірменія",
    "NL": "Нідерланди",
    "ZA": "Південно-Африканська Республіка",
    "CY": "Кіпр",
    "GT": "Ґватемала",
    "PE": "Перу",
    "KR": "Республіка Корея",
    "NO": "Норвегія",
    "BE": "Бельгія",
    "EG": "Єгипет",
    "IN": "Індія",
    "MA": "Марокко",
    "JP": "Японія",
    "MC": "Монако",
    "MX": "Мексика",
    "UZ": "Узбекистан",
}

# Registry titles are noisy: legal boilerplate, typos (теритріальн*), genitive forms.
_TITLE_BOILERPLATE = re.compile(
    r"^(?:"
    r"Договір\s+(?:про\s+)?співробітництв[оа]\s+"
    r")?"
    r"(?:терит\w*\s+громад(?:и)?\s+)?"
    r"(?:у\s+формі\s+)?"
    r"(?:в\s+частині\s+)?",
    re.IGNORECASE | re.UNICODE,
)
_QUOTED_NAME = re.compile(r"[«\"„]([^»\"“]{4,160})[»\"“]")
_GENERIC_JOINT_PROJECT = re.compile(
    r"^реалізаці[яї]\s+спільн\w*\s+про[еє]кт\w*"
    r"(?:,\s*що\s+передбачає.*)?$",
    re.IGNORECASE | re.UNICODE,
)
_GENERIC_JOINT_FINANCE = re.compile(
    r"^спільного\s+фінансування(?:\s*\(утримання\))?"
    r"(?:\s+суб.єктами\s+співробітництва)?"
    r"(?:\s+(?:підприємств|установ|організацій)"
    r"(?:\s+комунальної\s+форми\s+власності)?"
    r"(?:\s*[-–—,]?\s*інфраструктурних\s+об.єктів)?)?"
    r"$",
    re.IGNORECASE | re.UNICODE,
)
_GENERIC_DELEGATION = re.compile(
    r"^делегування\s+виконання\s+окремих\s+завдань"
    r"(?:\s+(?:з|що|через|у)\b.*)?$",
    re.IGNORECASE | re.UNICODE,
)

# Registry titles never record the project subject (only the legal form under
# 1508-VII ст.11 ч.2) — these three were identified via targeted web research
# (council decisions / regional grant coverage), 2026-08, for hub-node display.
KNOWN_AGREEMENT_SUBJECTS = {
    "320": "Соляна дорога",
    "527": "Словечансько-Овруцький кряж",
    "584": "Скейт-парк у Кам’янка-Бузькій",
}

# Multi-party hub nodes whose title collapses to one of these generic
# category labels get a register-number suffix so they're distinguishable
# on the graph (see KNOWN_AGREEMENT_SUBJECTS for the ones we could name).
_GENERIC_HUB_LABELS = {"Спільний проєкт"}


def _ukr_hromada_count(n: int) -> str:
    if n % 100 in (11, 12, 13, 14):
        return f"{n} громад"
    last = n % 10
    if last == 1:
        return f"{n} громада"
    if 2 <= last <= 4:
        return f"{n} громади"
    return f"{n} громад"


def load_geo() -> dict[str, dict]:
    out: dict[str, dict] = {}
    with GEO.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            code = row.get("hromada_code")
            try:
                lat = float(row["lat_center"])
                lon = float(row["lon_center"])
            except (KeyError, TypeError, ValueError):
                continue
            if not code:
                continue
            out[code] = {
                "lat": lat,
                "lon": lon,
                "oblast": row.get("oblast_name") or None,
                "name_short": row.get("hromada") or code,
            }
    return out


def _clip(text: str, limit: int = AGREEMENT_TITLE_MAX) -> str:
    text = re.sub(r"\s+", " ", text).strip(" .;")
    if len(text) <= limit:
        return text
    cut = text[: limit - 1].rsplit(" ", 1)[0]
    return (cut or text[: limit - 1]).rstrip(" ,;:") + "…"


def _cap(text: str) -> str:
    if not text:
        return text
    return text[0].upper() + text[1:] if text[0].islower() else text


def agreement_essence(title: str, form: str = "") -> str:
    """Readable subject of an IMC agreement for the detail card."""
    raw = (title or "").strip()
    form = (form or "").strip()
    blob = f"{raw} {form}"

    # Prefer a named object inside quotes when present.
    quoted = _QUOTED_NAME.search(raw) or _QUOTED_NAME.search(form)
    if quoted:
        name = _clip(quoted.group(1).strip(" ."), AGREEMENT_TITLE_MAX - 28)
        if re.search(r"про[еє]кт", blob, re.IGNORECASE):
            return _cap(f"Спільний проєкт «{name}»")
        if re.search(r"фінанс|утриман", blob, re.IGNORECASE):
            return _cap(f"Спільне фінансування «{name}»")
        if re.search(r"утворен", blob, re.IGNORECASE):
            return _cap(f"Утворення «{name}»")
        if re.search(r"делегуван", blob, re.IGNORECASE):
            return _cap(f"Делегування «{name}»")
        return _cap(f"«{name}»")

    short = _TITLE_BOILERPLATE.sub("", raw).strip(" .")
    short = re.sub(
        r"^Договір\s+про\s+(утворення|реалізацію|делегування)\s+",
        r"\1 ",
        short,
        flags=re.IGNORECASE,
    ).strip(" .")
    if not short:
        short = _TITLE_BOILERPLATE.sub("", form).strip(" .") or form or raw

    # Collapse pure legal generics to short category labels.
    if _GENERIC_JOINT_PROJECT.match(short) or _GENERIC_JOINT_PROJECT.match(form):
        return "Спільний проєкт"
    if _GENERIC_DELEGATION.match(short) and not re.search(
        r"[«\"„]|послуг|освіт|медич|пожеж|архів|відход|водо",
        short,
        re.IGNORECASE,
    ):
        return "Делегування окремих завдань"
    if _GENERIC_JOINT_FINANCE.match(short) and not re.search(
        r"[«\"„]|установ[аии]|підприємств|пожеж|освіт|медич|архів|школ|днз|амбулатор",
        short,
        re.IGNORECASE,
    ):
        return "Спільне фінансування / утримання"

    # If leftover text is mostly party geography, fall back to form / category.
    if short and not re.search(
        r"(про[еє]кт|фінанс|утриман|комунальн|пожеж|освіт|медич|соціальн|"
        r"водо|відход|доро|архів|підприємств|послуг|делегуван|утворен|"
        r"школ|днз|амбулатор|цнап|безпек)",
        short,
        re.IGNORECASE,
    ):
        form_short = _TITLE_BOILERPLATE.sub("", form).strip(" .") or form
        if _GENERIC_JOINT_PROJECT.match(form_short):
            return "Спільний проєкт"
        if form_short:
            short = form_short

    return _cap(_clip(short or form or raw or "Угода МСС"))


def load_mss_registry() -> dict[str, dict]:
    """register_number → {title, form} from MinRegion MSS registry XLSX."""
    if not MSS_REGISTRY.exists():
        return {}
    try:
        import openpyxl
    except ImportError as exc:
        raise SystemExit(
            "openpyxl required to attach agreement subjects "
            f"(pip install openpyxl). Missing while reading {MSS_REGISTRY}"
        ) from exc
    wb = openpyxl.load_workbook(MSS_REGISTRY, read_only=True, data_only=True)
    ws = wb.active
    out: dict[str, dict] = {}
    for i, row in enumerate(ws.iter_rows(values_only=True)):
        if i == 0 or not row or row[0] is None:
            continue
        num = row[0]
        if isinstance(num, float) and num.is_integer():
            key = str(int(num))
        else:
            key = str(num).strip()
        if not key:
            continue
        out[key] = {
            "title": str(row[1] or "").strip(),
            "form": str(row[6] or "").strip() if len(row) > 6 else "",
        }
    return out


def _agreement_item(num: str, registry: dict[str, dict]) -> tuple[dict, str]:
    """Registry lookup → detail-card item {n, title, theme_id, theme, form?}."""
    info = registry.get(num) or {}
    raw_title = info.get("title") or ""
    form = _clip(info.get("form") or "", 90)
    known = KNOWN_AGREEMENT_SUBJECTS.get(num)
    title = (
        _cap(f"Спільний проєкт «{known}»")
        if known
        else (agreement_essence(raw_title, form) or f"№{num}")
    )
    tid, _score = classify_registry_theme(raw_title, form, title)
    item: dict = {"n": num, "title": title, "theme_id": tid, "theme": theme_label(tid) or tid}
    if form and form.casefold() != title.casefold():
        item["form"] = form
    return item, tid


def load_pin(
    registry: dict[str, dict] | None = None,
) -> tuple[dict[str, dict], list[dict], dict[str, dict], set[tuple[str, str]]]:
    """PIN registry as a graph.

    2-party agreements become a direct hromada↔hromada edge (as before).
    Multi-party agreements (89 of 306 registry numbers span 3–22 hromadas)
    become a single hub node instead of a fully-expanded clique of pairwise
    edges — clique expansion is how the raw KSE CSV is shaped, and it alone
    accounts for ~80% of all raw PIN pairs, which is what made the "Граф"
    view unreadable.
    """
    registry = registry or {}
    nodes: dict[str, dict] = {}
    reg_parties: dict[str, set[str]] = defaultdict(set)
    pair_nums: dict[tuple[str, str], set[str]] = defaultdict(set)
    pair_keys: set[tuple[str, str]] = set()

    with PIN.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            a, b = row["hromada_code.x"], row["hromada_code.y"]
            if not a or not b or a == b:
                continue
            nodes[a] = {"id": a, "label": row["hromada_name.x"] or a}
            nodes[b] = {"id": b, "label": row["hromada_name.y"] or b}
            key = tuple(sorted((a, b)))
            pair_keys.add(key)
            num = (row.get("register_number") or "").strip()
            if num:
                reg_parties[num].add(a)
                reg_parties[num].add(b)
                pair_nums[key].add(num)
            else:
                pair_nums[key]  # ensure pair exists even without a number

    multi_nums = {num for num, codes in reg_parties.items() if len(codes) > 2}

    edges: list[dict] = []
    for (a, b), nums in sorted(pair_nums.items()):
        solo_nums = nums - multi_nums
        if not solo_nums and nums:
            continue  # tied only via a multi-party hub — no direct dyad
        edge: dict = {"a": a, "b": b, "kind": "pin"}
        agreements: list[dict] = []
        seen_titles: set[str] = set()
        for num in sorted(solo_nums, key=lambda x: int(x) if x.isdigit() else 0):
            item, _tid = _agreement_item(num, registry)
            key_t = item["title"].casefold()
            if key_t in seen_titles:
                continue
            seen_titles.add(key_t)
            agreements.append(item)
            if len(agreements) >= MAX_AGREEMENTS_PER_EDGE:
                break
        if agreements:
            edge["agreements"] = agreements
            edge["reasons"] = [x["title"] for x in agreements[:4]]
            theme_ids = []
            seen_t: set[str] = set()
            for agr in agreements:
                tid = agr.get("theme_id") or "other"
                if tid not in seen_t:
                    seen_t.add(tid)
                    theme_ids.append(tid)
            edge["theme_ids"] = theme_ids
            # Human labels for detail chips (not the legal-form string formerly stuffed in theme)
            edge["themes"] = [
                theme_label(t) or t for t in theme_ids if t != "other"
            ][:6]
            if len(agreements) == 1 and agreements[0].get("form"):
                edge["form"] = agreements[0]["form"]
        edges.append(edge)

    agreement_nodes: dict[str, dict] = {}
    for num in sorted(multi_nums, key=lambda x: int(x) if x.isdigit() else 0):
        codes = sorted(reg_parties[num])
        item, tid = _agreement_item(num, registry)
        hub_id = f"agreement:{num}"
        title = item["title"]
        full_name = title
        if title in _GENERIC_HUB_LABELS:
            title = f"{title} №{num}"
            full_name = f"{title} ({_ukr_hromada_count(len(codes))})"
        agreement_nodes[hub_id] = {
            "id": hub_id,
            "kind": "agreement",
            "label": _clip(title, 40),
            "full_name": full_name,
            "party_count": len(codes),
            "theme_id": tid,
            "theme": item.get("theme") if tid != "other" else None,
        }
        for code in codes:
            edges.append({
                "a": code,
                "b": hub_id,
                "kind": "pin_agreement",
                "theme_id": tid,
                "theme": item.get("theme"),
                "themes": [item["theme"]] if tid != "other" else [],
                "theme_ids": [tid],
                "agreements": [item],
                "reasons": [item["title"]],
            })

    return nodes, edges, agreement_nodes, pair_keys


def short_label(full: str) -> str:
    parts = full.replace("територіальна громада", "").strip().split()
    return " ".join(parts[:2]) if len(parts) >= 2 else full


def explain_fields(e: dict) -> dict:
    """Compact why-signal payload for the map/graph detail card."""
    out: dict = {}
    reasons = e.get("reasons")
    if isinstance(reasons, list):
        clipped = [str(r).strip() for r in reasons if r][:5]
        if clipped:
            out["reasons"] = clipped
    if e.get("theme"):
        out["theme"] = e["theme"]
    if e.get("form"):
        out["form"] = e["form"]
    themes = e.get("themes")
    if isinstance(themes, list) and themes:
        out["themes"] = [str(t).strip() for t in themes if t][:6]
    theme_ids = e.get("theme_ids")
    if isinstance(theme_ids, list) and theme_ids:
        out["theme_ids"] = [str(t).strip() for t in theme_ids if t][:8]
    for key in (
        "suggested_theme",
        "suggested_form",
        "suggest_confidence",
        "suggest_rationale",
        "suggest_caveat",
        "discovery_primary",
        "status",
    ):
        if e.get(key):
            out[key] = e[key]
    if e.get("package"):
        out["package"] = e["package"]
    if e.get("signals"):
        out["signals"] = e["signals"][:6]
    pairs = e.get("goal_pairs")
    if isinstance(pairs, list) and pairs:
        out["goal_pairs"] = pairs[:3]
    agreements = e.get("agreements")
    if isinstance(agreements, list) and agreements:
        out["agreements"] = agreements[:MAX_AGREEMENTS_PER_EDGE]
    for key in (
        "goals_cosine",
        "geo_score",
        "dream_overlap",
        "fiscal_similarity",
        "mss_network",
        "same_oblast",
    ):
        if e.get(key) is not None:
            out[key] = e[key]
    return out


def attach_goal_overlap(
    edge: dict,
    *,
    name_a: str,
    name_b: str,
    goals_by_name: dict[str, dict],
) -> None:
    """Mutate edge with thematic overlap reasons when Goals text is available."""
    ga = goals_by_name.get(name_a) or {}
    gb = goals_by_name.get(name_b) or {}
    if not (ga.get("goals") and gb.get("goals")):
        return
    overlap = explain_goal_overlap(
        name_a=name_a,
        name_b=name_b,
        katottg_a=ga.get("katottg"),
        katottg_b=gb.get("katottg"),
        goals_a=ga["goals"],
        goals_b=gb["goals"],
    )
    if not overlap:
        return
    # Prefer freshly computed overlap over any empty/generic reasons.
    for key in ("reasons", "themes", "goal_pairs", "theme"):
        if overlap.get(key):
            edge[key] = overlap[key]


def encode_overlay(
    rows: list[dict],
    *,
    kind: str,
    name_to_code: dict[str, str],
    pin_keys: set[tuple[str, str]],
    goals_by_name: dict[str, dict] | None = None,
) -> list[dict]:
    """Map matching-edge names → KATOTTG overlay edges; skip pairs already in PIN."""
    out: list[dict] = []
    for e in rows:
        ca, cb = name_to_code[e["a"]], name_to_code[e["b"]]
        if tuple(sorted((ca, cb))) in pin_keys:
            continue
        edge = {
            "a": ca,
            "b": cb,
            "kind": kind,
            "score": e["score"],
            "goals_cosine": e.get("goals_cosine"),
            "geo_score": e.get("geo_score"),
            "track": e.get("track"),
        }
        if goals_by_name is not None:
            attach_goal_overlap(
                edge, name_a=e["a"], name_b=e["b"], goals_by_name=goals_by_name
            )
        edge.update(explain_fields({**e, **edge}))
        out.append(edge)
    return out


def encode_named_overlay(
    rows: list[dict],
    *,
    kind: str,
    name_to_code: dict[str, str],
    score_key: str,
    limit: int,
    prefer_same_oblast: bool = False,
) -> list[dict]:
    """Map complementary / explicit-ask edges (name-keyed) onto KATOTTG codes."""
    ranked = list(rows)
    if prefer_same_oblast:
        ranked = sorted(
            ranked,
            key=lambda e: (
                -float(e.get(score_key) or 0),
                -int(bool(e.get("same_oblast"))),
            ),
        )
    else:
        ranked = sorted(ranked, key=lambda e: -float(e.get(score_key) or 0))
    out: list[dict] = []
    for e in ranked:
        ca = name_to_code.get(e.get("a") or "")
        cb = name_to_code.get(e.get("b") or "")
        if not ca or not cb or ca == cb:
            # try katottg fields when present
            ca = ca or e.get("a_katottg")
            cb = cb or e.get("b_katottg")
        if not ca or not cb or ca == cb:
            continue
        edge = {
            "a": ca,
            "b": cb,
            "kind": kind,
            "score": e.get(score_key),
            "track": e.get("track") or kind,
        }
        edge.update(explain_fields(e))
        out.append(edge)
        if len(out) >= limit:
            break
    return out


def build_payload() -> dict:
    geo = load_geo()
    mss_registry = load_mss_registry()
    pin_nodes, pin_edges, agreement_nodes, pin_pair_keys = load_pin(mss_registry)
    pin_participant_count = len(pin_nodes)

    # Theme catalog for PIN filter UI — unique registry agreements, not edge fan-out
    # (multi-party deals otherwise explode one title into dozens of pair edges).
    pin_theme_regs: dict[str, set[str]] = defaultdict(set)
    for e in pin_edges:
        agrs = e.get("agreements") or []
        if not agrs:
            pin_theme_regs["other"].add(f"edge:{e['a']}:{e['b']}")
            continue
        for agr in agrs:
            tid = agr.get("theme_id") or "other"
            pin_theme_regs[tid].add(str(agr.get("n") or agr.get("title") or id(agr)))
    pin_theme_counts = {tid: len(regs) for tid, regs in pin_theme_regs.items()}
    pin_themes = [
        {
            "id": tid,
            "label_uk": THEME_LABELS.get(tid, tid),
            "label_en": THEME_LABELS_EN.get(tid, tid),
            "n": pin_theme_counts[tid],
        }
        for tid in sorted(
            pin_theme_counts.keys(),
            key=lambda t: (-pin_theme_counts[t], THEME_LABELS.get(t, t)),
        )
    ]

    hromadas = json.loads(HROMADAS.read_text(encoding="utf-8"))
    # Full metadata index (1,469) — portals / names / corpus flags by KATOTTG
    by_code: dict[str, dict] = {}
    for r in hromadas:
        code = r.get("Katottg")
        if not code:
            continue
        by_code[code] = {
            "full_name": r.get("Name"),
            "portal_url": r.get("PortalUrl") or None,
            "strategy_url": r.get("StrategyUrl") or None,
            "in_corpus": bool(r.get("Goals")),
            "source_quality": r.get("SourceQuality"),
            "type": r.get("Type"),
            "population": r.get("Population"),
            "donor_programs": r.get("DonorsPrograms") or [],
        }

    corpus = [r for r in hromadas if r.get("Goals") and r.get("Katottg")]
    name_to_code = {r["Name"]: r["Katottg"] for r in corpus}
    code_to_full = {r["Katottg"]: r["Name"] for r in corpus}
    corpus_codes = set(name_to_code.values())
    # Expand name_to_code to all hromadas (intents/tags may cite non-Goals rows)
    all_name_to_code = {
        r["Name"]: r["Katottg"] for r in hromadas if r.get("Name") and r.get("Katottg")
    }
    goals_by_name = {
        r["Name"]: {
            "goals": (r.get("Goals") or "").strip(),
            "katottg": r.get("Katottg"),
        }
        for r in corpus
        if r.get("Name")
    }

    matching = load_matching_edges(prefer_rich_cache=True)
    corpus_matching = [
        e for e in matching if e["a"] in name_to_code and e["b"] in name_to_code
    ]
    thematic = thematic_slice(corpus_matching, limit=TOP_THEMATIC)
    operational = operational_slice(corpus_matching, limit=TOP_OPERATIONAL)
    # Slim release may lack package/signals — annotate only painted layers.
    ensure_packages(thematic + operational)

    # Includes pairs only tied via a multi-party agreement hub (no direct
    # dyadic "pin" edge for those), so overlay layers still skip them.
    pin_keys = pin_pair_keys

    thematic_edges = encode_overlay(
        thematic,
        kind="thematic",
        name_to_code=name_to_code,
        pin_keys=pin_keys,
        goals_by_name=goals_by_name,
    )
    operational_edges = encode_overlay(
        operational, kind="operational", name_to_code=name_to_code, pin_keys=pin_keys
    )

    complementary_edges: list[dict] = []
    if COMPLEMENTARY.exists():
        complementary_edges = encode_named_overlay(
            json.loads(COMPLEMENTARY.read_text(encoding="utf-8")),
            kind="complementary",
            name_to_code=name_to_code,
            score_key="complementary_score",
            limit=TOP_COMPLEMENTARY,
            prefer_same_oblast=True,
        )

    explicit_ask_edges: list[dict] = []
    if EXPLICIT_ASK.exists():
        explicit_ask_edges = encode_named_overlay(
            json.loads(EXPLICIT_ASK.read_text(encoding="utf-8")),
            kind="explicit_ask",
            name_to_code=all_name_to_code,
            score_key="explicit_ask_score",
            limit=TOP_EXPLICIT_ASK,
        )

    # Domestic Пліч-о-Пліч rear↔forpost pairs, text-mined from project news
    # (see docs/plich-o-plich.md). Only bilateral_confirmed edges — the
    # source release also carries co-mention-only edges from multi-hromada
    # roundup articles, which are a clique-of-everyone-mentioned, not a
    # claimed pairwise partnership, so those are deliberately left out here.
    plich_o_plich_edges: list[dict] = []
    if PLICH_O_PLICH.exists():
        plich_payload = json.loads(PLICH_O_PLICH.read_text(encoding="utf-8"))
        for e in plich_payload.get("edges") or []:
            if not e.get("bilateral_confirmed"):
                continue
            ca, cb = e.get("a_katottg"), e.get("b_katottg")
            if not ca or not cb or ca == cb:
                continue
            plich_o_plich_edges.append(
                {
                    "a": ca,
                    "b": cb,
                    "kind": "plich_o_plich",
                    "score": e.get("article_count"),
                    "article_count": e.get("article_count"),
                    "first_seen": e.get("first_seen"),
                    "last_seen": e.get("last_seen"),
                    "source_url": (e.get("source_urls") or [None])[0],
                }
            )

    for e in (
        thematic_edges
        + operational_edges
        + complementary_edges
        + explicit_ask_edges
        + plich_o_plich_edges
    ):
        for code in (e["a"], e["b"]):
            if code not in pin_nodes:
                pin_nodes[code] = {
                    "id": code,
                    "label": short_label(code_to_full.get(code) or by_code.get(code, {}).get("full_name") or code),
                }

    pin_member = {e["a"] for e in pin_edges} | {e["b"] for e in pin_edges}

    twinning_by_code: dict[str, list[dict]] = {}
    if TWINNING.exists():
        twin_payload = json.loads(TWINNING.read_text(encoding="utf-8"))
        for h in twin_payload.get("hromadas") or []:
            code = (h.get("katottg") or "").strip()
            if not code:
                continue
            partners = []
            for p in h.get("partners") or []:
                partners.append(
                    {
                        "name": p.get("partner_name"),
                        "country": p.get("partner_country"),
                        "region": p.get("partner_region"),
                        "type": p.get("type"),
                        "since": p.get("since"),
                        "source": p.get("source"),
                        "url": p.get("source_url"),
                    }
                )
            twinning_by_code[code] = {
                "partners": partners,
                "c4c_url": h.get("c4c_url"),
            }

    # Twinning countries as graph-only hub nodes (Граф view; no lat/lon, so
    # they never enter the Leaflet map layers, which all skip lat==None).
    country_nodes: dict[str, dict] = {}
    twinning_edges: list[dict] = []
    for code, twin in twinning_by_code.items():
        by_country: dict[str, int] = defaultdict(int)
        for p in twin.get("partners") or []:
            iso = p.get("country")
            if iso:
                by_country[iso] += 1
        for iso, count in by_country.items():
            node_id = f"country:{iso}"
            if node_id not in country_nodes:
                label = COUNTRY_LABELS.get(iso, iso)
                country_nodes[node_id] = {
                    "id": node_id,
                    "kind": "country",
                    "label": label,
                    "full_name": label,
                    "iso2": iso,
                    "degree": 0,
                }
            country_nodes[node_id]["degree"] += 1
            twinning_edges.append(
                {"a": code, "b": node_id, "kind": "twinning", "partner_count": count}
            )

    # Donor programs as graph-only hub nodes, from hromadas.json DonorsPrograms.
    donor_nodes: dict[str, dict] = {}
    donor_edges: list[dict] = []
    for r in hromadas:
        code = r.get("Katottg")
        programs = r.get("DonorsPrograms") or []
        if not code or not programs:
            continue
        for program in programs:
            node_id = f"donor:{program}"
            if node_id not in donor_nodes:
                donor_nodes[node_id] = {
                    "id": node_id,
                    "kind": "donor",
                    "label": program,
                    "full_name": program,
                    "degree": 0,
                }
            donor_nodes[node_id]["degree"] += 1
            donor_edges.append({"a": code, "b": node_id, "kind": "donor"})

    for e in twinning_edges + donor_edges:
        code = e["a"]
        if code not in pin_nodes:
            pin_nodes[code] = {
                "id": code,
                "label": short_label(code_to_full.get(code) or by_code.get(code, {}).get("full_name") or code),
            }

    degree: dict[str, int] = {c: 0 for c in pin_nodes}
    for e in pin_edges:
        degree[e["a"]] = degree.get(e["a"], 0) + 1
        degree[e["b"]] = degree.get(e["b"], 0) + 1

    basin_by_code: dict[str, int] = {}
    if BASIN_ASSIGN.exists():
        try:
            assign_payload = json.loads(BASIN_ASSIGN.read_text(encoding="utf-8"))
            for code, row in (assign_payload.get("assignments") or {}).items():
                bid = row.get("basin_id")
                if bid is not None:
                    basin_by_code[code] = int(bid)
        except (OSError, ValueError, TypeError) as exc:
            print(f"WARNING: basin assignment unreadable ({exc})")

    def enrich(code: str, label_fallback: str) -> dict:
        g = geo.get(code)
        meta = by_code.get(code) or {}
        lat = lon = oblast = None
        label = label_fallback
        if g:
            lat, lon = g["lat"], g["lon"]
            oblast = g["oblast"]
            label = g["name_short"] or label
        twin = twinning_by_code.get(code) or {}
        twin_partners = twin.get("partners") or []
        out = {
            "id": code,
            "label": label,
            "full_name": meta.get("full_name") or code_to_full.get(code),
            "katottg": code,
            "oblast": oblast,
            "lat": lat,
            "lon": lon,
            "degree": degree.get(code, 0),
            "in_corpus": code in corpus_codes or bool(meta.get("in_corpus")),
            "in_pin": code in pin_member,
            "portal_url": meta.get("portal_url"),
            "strategy_url": meta.get("strategy_url"),
            "c4c_url": twin.get("c4c_url"),
            "source_quality": meta.get("source_quality"),
            "type": meta.get("type"),
            "population": meta.get("population"),
            "twinning_count": len(twin_partners),
            "twinning_partners": twin_partners[:12],
            "donor_programs": meta.get("donor_programs") or [],
        }
        if code in basin_by_code:
            out["basin_id"] = basin_by_code[code]
        return out

    nodes = []
    with_geo = 0
    for code, base in sorted(pin_nodes.items(), key=lambda x: x[1]["label"]):
        n = enrich(code, base["label"])
        if n["lat"] is not None:
            with_geo += 1
        nodes.append(n)

    # Country / donor hub nodes — Граф view only (no katottg/lat/lon, so the
    # Leaflet map layers, which all skip lat==None, never render them).
    nodes.extend(sorted(country_nodes.values(), key=lambda n: n["label"]))
    nodes.extend(sorted(donor_nodes.values(), key=lambda n: n["label"]))

    # Multi-party agreement hubs get a synthetic position (centroid of their
    # geocoded participants) so the Мапа view can draw pin_agreement spokes —
    # otherwise every hromada whose only PIN ties are multi-party (44% of PIN
    # participants) shows its badge/degree but zero lines on the map.
    code_latlon = {n["id"]: (n["lat"], n["lon"]) for n in nodes if n.get("lat") is not None}
    hub_participants: dict[str, list[str]] = defaultdict(list)
    for e in pin_edges:
        if e["kind"] == "pin_agreement":
            hub_participants[e["b"]].append(e["a"])
    for hub_id, hub in agreement_nodes.items():
        pts = [code_latlon[c] for c in hub_participants.get(hub_id, []) if c in code_latlon]
        if pts:
            hub["lat"] = sum(p[0] for p in pts) / len(pts)
            hub["lon"] = sum(p[1] for p in pts) / len(pts)
        else:
            hub["lat"] = hub["lon"] = None
    nodes.extend(sorted(agreement_nodes.values(), key=lambda n: -n["party_count"]))

    # Universe layer: every release hromada with KSE lat/lon (≈ full mainland set)
    universe: list[dict] = []
    for code, meta in by_code.items():
        g = geo.get(code)
        if not g:
            continue
        twin = twinning_by_code.get(code) or {}
        twin_partners = twin.get("partners") or []
        u = {
            "id": code,
            "label": g.get("name_short") or short_label(meta.get("full_name") or code),
            "full_name": meta.get("full_name"),
            "katottg": code,
            "oblast": g.get("oblast"),
            "lat": g["lat"],
            "lon": g["lon"],
            "in_corpus": bool(meta.get("in_corpus")),
            "in_pin": code in pin_member,
            "portal_url": meta.get("portal_url"),
            "strategy_url": meta.get("strategy_url"),
            "c4c_url": twin.get("c4c_url"),
            "source_quality": meta.get("source_quality"),
            "type": meta.get("type"),
            "population": meta.get("population"),
            "twinning_count": len(twin_partners),
            "twinning_partners": twin_partners[:12],
        }
        if code in basin_by_code:
            u["basin_id"] = basin_by_code[code]
        universe.append(u)
    universe.sort(key=lambda n: n.get("full_name") or n["label"] or n["id"])

    if not OBLASTS.exists():
        raise SystemExit(f"Missing {OBLASTS}")
    if not OUTLINE.exists():
        raise SystemExit(f"Missing {OUTLINE}")
    oblasts = json.loads(OBLASTS.read_text(encoding="utf-8"))
    outline = json.loads(OUTLINE.read_text(encoding="utf-8"))
    basins = None
    if BASINS.exists():
        basins = json.loads(BASINS.read_text(encoding="utf-8"))
    else:
        print(f"WARNING: missing {BASINS}; basin underlay omitted")

    portal_on_map = sum(1 for n in universe if n.get("portal_url"))
    twinning_on_map = sum(1 for n in universe if n.get("twinning_count") or n.get("c4c_url"))

    return {
        "meta": {
            "corpus_size": len(corpus),
            "pin_edges": len(pin_edges),
            "pin_participants": pin_participant_count,
            "pin_nodes": len(nodes),
            "universe_nodes": len(universe),
            "universe_with_portal": portal_on_map,
            "twinning_hromadas": twinning_on_map,
            "twinning_partners": sum(len(v.get("partners") or []) for v in twinning_by_code.values()),
            "cities4cities_listed": sum(1 for v in twinning_by_code.values() if v.get("c4c_url")),
            "twinning_countries": len(country_nodes),
            "twinning_edges": len(twinning_edges),
            "donor_programs_count": len(donor_nodes),
            "donor_edges": len(donor_edges),
            "pin_agreement_hubs": len(agreement_nodes),
            "pin_agreement_edges": sum(1 for e in pin_edges if e["kind"] == "pin_agreement"),
            "thematic_edges": len(thematic_edges),
            "operational_edges": len(operational_edges),
            "complementary_edges": len(complementary_edges),
            "explicit_ask_edges": len(explicit_ask_edges),
            "plich_o_plich_edges": len(plich_o_plich_edges),
            # legacy alias: thematic only (combined-score hyp layer removed)
            "hypothesis_edges": len(thematic_edges),
            "nodes_with_geo": with_geo,
            "oblasts": len(oblasts.get("features", [])),
            "basins": len((basins or {}).get("features", [])),
            "basins_assigned": len(basin_by_code),
            "pin_source": "KSE-Loc-Data-Hub partnerships-hromadas-network.csv",
            "mss_registry_source": (
                "data/cache/mss/mss_registry.xlsx (Назва договору / Форма)"
                if mss_registry
                else None
            ),
            "pin_agreements_enriched": sum(
                1 for e in pin_edges if e.get("agreements")
            ),
            "pin_themes_tagged": sum(
                v for k, v in pin_theme_counts.items() if k != "other"
            ),
            "pin_themes_other": pin_theme_counts.get("other", 0),
            "geo_source": "KSE-Loc-Data-Hub geography.csv (lat_center/lon_center)",
            "oblasts_source": "Natural Earth admin-1 → docs/geo/ukraine-oblasts.geojson",
            "outline_source": "docs/geo/ukraine-outline.geojson (mask outside UA)",
            "basins_source": (
                "HydroBASINS EU lev06 → docs/geo/ukraine-basins-lev06.geojson "
                "(hydrological catchments, not legal DAVR RBDs)"
                if basins
                else None
            ),
            "matching_source": "data/releases/matching-edges.json",
            "hromadas_source": "data/releases/hromadas.json (PortalUrl/StrategyUrl)",
            "twinning_source": (
                "data/releases/twinning-partners.json (SKEW + strategy)"
                if twinning_by_code
                else None
            ),
            "plich_o_plich_source": (
                "data/releases/plich-o-plich.json (news text-mining; "
                "bilateral_confirmed edges only)"
                if plich_o_plich_edges
                else None
            ),
            "top_thematic": TOP_THEMATIC,
            "top_operational": TOP_OPERATIONAL,
            "top_complementary": TOP_COMPLEMENTARY,
            "top_explicit_ask": TOP_EXPLICIT_ASK,
            "overlay_policy": (
                "thematic=goals_cosine track; operational=geo neighbours; "
                "complementary=resource/DREAM↔Challenges; explicit_ask=МСС language; "
                "twinning=UA–EU sister cities (node highlight); "
                "plich_o_plich=domestic rear↔forpost pairs, bilateral_confirmed only; "
                "basins=HydroBASINS lev06 underlay (not in score); "
                "pin theme filter=mss_suggest on registry title/form; "
                "no combined-score hyp layer; "
                "universe=all release rows with KSE geo (metadata layer)"
            ),
        },
        "pin_themes": pin_themes,
        "oblasts": oblasts,
        "ukraine_outline": outline,
        "basins": basins,
        "nodes": nodes,
        "universe": universe,
        "edges": (
            pin_edges
            + thematic_edges
            + operational_edges
            + complementary_edges
            + explicit_ask_edges
            + plich_o_plich_edges
            + twinning_edges
            + donor_edges
        ),
    }


def main() -> None:
    for path in (PIN, GEO, TEMPLATE):
        if not path.exists():
            raise SystemExit(f"Missing {path}")
    payload = build_payload()
    html = TEMPLATE.read_text(encoding="utf-8").replace(
        "__DATA__", json.dumps(payload, ensure_ascii=False)
    )
    OUT.write_text(html, encoding="utf-8")
    m = payload["meta"]
    print(
        f"Wrote {OUT.relative_to(ROOT)} — "
        f"PIN {m['pin_participants']}participants/{m['pin_edges']}e "
        f"(graph {m['pin_nodes']}n all layers) "
        f"(subjects={m.get('pin_agreements_enriched', 0)}) · "
        f"universe={m['universe_nodes']} (portal={m['universe_with_portal']}) · "
        f"oblasts={m['oblasts']} · basins={m.get('basins', 0)} · "
        f"thematic={m['thematic_edges']} operational={m['operational_edges']} "
        f"complementary={m['complementary_edges']} explicit_ask={m['explicit_ask_edges']} "
        f"twinning={m.get('twinning_hromadas', 0)} "
        f"(countries={m.get('twinning_countries', 0)}/{m.get('twinning_edges', 0)}e) "
        f"donors={m.get('donor_programs_count', 0)}/{m.get('donor_edges', 0)}e "
        f"pin_agreement_hubs={m.get('pin_agreement_hubs', 0)}/{m.get('pin_agreement_edges', 0)}e"
    )


if __name__ == "__main__":
    main()
