"""Extract named objects, neighbours, and concrete deficits from strategy prose.

Discovery layer only — never folded into v7 combined `score`, never known=true.
Used by extract_strategy_entities.py, extract_mss_intents.py, complementary_match.py.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# --- names -----------------------------------------------------------------

SUFFIXES = (
    " міська територіальна громада",
    " селищна територіальна громада",
    " сільська територіальна громада",
    " територіальна громада",
)

STOP_ADJ = {
    "місцева",
    "місцеві",
    "прифронтова",
    "прифронтові",
    "тилова",
    "тилові",
    "наша",
    "наші",
    "ця",
    "ці",
    "така",
    "такі",
    "кожна",
    "кожні",
    "обидві",
    "обидва",
    "деякі",
    "інша",
    "інші",
    "усі",
    "всі",
    "партнерська",
    "партнерські",
    "українська",
    "українські",
    "згуртована",
    "згуртовані",
    "нова",
    "нові",
    "одна",
    "приймаюча",
    "територіальна",
    "обєднана",
    "об'єднана",
    "спроможна",
    "сільська",
    "міська",
    "селищна",
    "базова",
    "опорна",
    "сусідня",
    "сусідні",
    "інших",
    "іншими",
    "українськими",
    "українською",
}

ADJ = r"[А-ЯЇЄҐІ][а-яіїєґ'’ʼ\-]{2,}"
ADJ_CHAIN_GROMADA_RE = re.compile(
    rf"((?:{ADJ}(?:\s*,\s*|\s+та\s+|\s+і\s+))*{ADJ})\s+"
    rf"громад(?:а|и|у|ою|і|ах|ами)\b"
)
CHAIN_SPLIT_RE = re.compile(r"\s*,\s*|\s+та\s+|\s+і\s+")
GROMADA_TRAIL_RE = re.compile(
    rf"громад(?:а|и|ами|ах)\s*(?:,\s*|\s+та\s+|\s+і\s+)"
    rf"((?:{ADJ}(?:\s*,\s*|\s+та\s+|\s+і\s+)*)*{ADJ})"
    rf"(?=\s+(?:сільськ|селищн|міськ|ТГ|рад)|[;.\)]|$)",
)
ADJ_SUFFIX_MARKER_RE = re.compile(r"(ськ|зьк|цьк|ьк)")
OBLAST_SKIP_RE = re.compile(
    rf"({ADJ})\s+(?:област\w*|район\w*|р-н\w*|обл\.)",
    re.I,
)
COOP_PREP_RE = re.compile(
    rf"(?:спільно\s+з|разом\s+з|угод[аиу]?\s+з|співпрац\w*\s+з|"
    rf"партнерств\w*\s+з|кооперац\w*\s+з)\s+"
    rf"({ADJ}(?:ською|зькою|цькою|ою)?)\b"
    rf"(?!\s*(?:ОВА|ОДА|РДА|обласн|та\s+міжнародн))",
    re.I,
)
COOP_CTX_RE = re.compile(
    r"сусідн|міжмуніцип|\bМСС\b|спільно\s+з|разом\s+з|кооперац|"
    r"партнерств|угод[аиу]?\s+з",
    re.I,
)

# Rivers too common to pair unless both sides also talk IMC / cleaning.
COMMON_HYDRONYMS = {
    "дніпро",
    "дністер",
    "дунай",
    "десна",
    "прип'ять",
    "припять",
    "буг",
    "донець",
    "чорнеморе",
    "азов",
    "південнийбуг",
    "західнийбуг",
    "сіверськийдонець",
}

RIVER_STOP = {
    "стратегічн",
    "оперативн",
    "територіальн",
    "місцев",
    "формальн",
    "водопостачанн",
    "управлінськ",
    "памятк",
    "інш",
}
RIVER_STOP_PREFIXES = (
    "стратегіч",
    "оперативн",
    "формальн",
    "водопостач",
    "управлінськ",
    "памятк",
    "інш",
)
AIRPORT_STOP = {
    "історичн",
    "створю",
    "високий",
    "високи",
    "міжнародн",
    "місцев",
    "нови",
    "цивільн",
}

NEG_NEIGHBOUR_RE = re.compile(
    r"не\s+знайден|не\s+підтверд|не підтверд|артефакт|шаблон|"
    r"пліч[- ]о[- ]пліч",
    re.I,
)

ASSET_HINT_RE = re.compile(
    r"річк|басейн|полігон|ТПВ|ЦНАП|сміттєсортув|водоканал|аеропорт|"
    r"кластер|маршрут",
    re.I,
)

KITCHEN_SINK_SECTORS = frozenset(
    {
        "Освіта",
        "Культура / спадщина",
        "Охорона здоров'я",
        "Підприємництво / МСБ",
        "Соціальні послуги",
    }
)
KITCHEN_SINK_CAP = 0.5
KITCHEN_SINK_WEIGHT = 0.2


def short_name(name: str) -> str:
    for suffix in SUFFIXES:
        if name.endswith(suffix):
            return name[: -len(suffix)]
    return name


def norm_apos(s: str) -> str:
    return s.replace("'", "’").replace("ʼ", "’").replace("`", "’")


def adj_stem(word: str) -> str:
    """Stem past ськ/зьк/цьк/ьк so case endings drop (same idea as Пліч)."""
    w = norm_apos(word).lower().replace("’", "")
    matches = list(ADJ_SUFFIX_MARKER_RE.finditer(w))
    if matches:
        return w[: matches[-1].end()]
    if len(w) > 4 and w[-1] in "аиіуюоеїй":
        return w[:-1]
    return w


def _clip_quote(text: str, start: int, end: int, radius: int = 80) -> str:
    a = max(0, start - radius)
    b = min(len(text), end + radius)
    return re.sub(r"\s+", " ", text[a:b]).strip()[:280]


# --- assets ----------------------------------------------------------------

_RIVER_RE = re.compile(
    r"(?:річ(?:ка|ки|ці|ку|кою|ок)|(?<![А-Яа-яІіЇїЄєҐґA-Za-z])(?<!\d )р\.)\s+"
    r"([А-ЯІЇЄҐ][А-Яа-яІіЇїЄєҐґ'’\-]{2,}(?:\s+[А-ЯІЇЄҐ][А-Яа-яІіЇїЄєҐґ'’\-]{2,})?)",
)
_CLUSTER_RE = re.compile(
    r"кластер[уа]?\s+[«\"“]([^»\"”]{3,80})[»\"”]",
    re.I,
)
_LANDFILL_NAMED_RE = re.compile(
    r"полігон(?:у|а|і)?(?:\s+ТПВ)?\s+[«\"“]([^»\"”]{3,60})[»\"”]",
    re.I,
)
_AIRPORT_RE = re.compile(
    r"(?i:аеропорт(?:у|а|і)?)(?:\s+[«\"“]?([А-ЯІЇЄҐ][А-Яа-яІіЇїЄєҐґ'’\-]{2,}"
    r"(?:\s+[А-ЯІЇЄҐ][А-Яа-яІіЇїЄєҐґ'’\-]{2,})?)[»\"”]?)?",
)
_ROUTE_RE = re.compile(
    r"(?:велопішохідн\w*|туристичн\w*)\s+маршрут\w*(?:\s+[«\"“]([^»\"”]{3,80})[»\"”])?",
    re.I,
)


def norm_hydronym(name: str) -> str:
    w = norm_apos(name).lower().replace("’", "")
    w = re.sub(r"^(річ(?:ка|ки|ці|ку|кою|ок)|р\.)\s+", "", w)
    w = re.sub(r"[^а-яіїєґa-z0-9]+", "", w)
    if w in COMMON_HYDRONYMS:
        return w
    if len(w) > 4 and w[-1] in "аиіуюоеїй":
        stemmed = w[:-1]
        if stemmed in COMMON_HYDRONYMS:
            return stemmed
        return stemmed
    return w


def find_assets(text: str, *, field: str) -> list[dict]:
    """Named shared-object candidates. Generic ЦНАП/полігон without a name skipped."""
    if not text:
        return []
    out: list[dict] = []

    def add(kind: str, key: str, display: str, theme: str | None, m: re.Match) -> None:
        key = (key or "").strip()
        if len(key) < 3:
            return
        if kind == "river" and (
            key in RIVER_STOP or any(key.startswith(p) for p in RIVER_STOP_PREFIXES)
        ):
            return
        out.append(
            {
                "kind": kind,
                "key": key,
                "name": display.strip(),
                "theme": theme,
                "field": field,
                "quote": _clip_quote(text, m.start(), m.end()),
                "common": (kind == "river" and key in COMMON_HYDRONYMS) or kind == "airport",
            }
        )

    for m in _RIVER_RE.finditer(text):
        display = m.group(1)
        add("river", norm_hydronym(display), display, "вода", m)
    for m in _CLUSTER_RE.finditer(text):
        raw = m.group(1)
        add("cluster", re.sub(r"\s+", " ", raw.lower())[:80], raw, "туризм", m)
    for m in _LANDFILL_NAMED_RE.finditer(text):
        raw = m.group(1)
        add("landfill", re.sub(r"\s+", " ", raw.lower())[:60], raw, "відходи", m)
    for m in _AIRPORT_RE.finditer(text):
        raw = (m.group(1) or "").strip()
        if not raw or raw.lower() in {"аеропорт", "аеропорту", "аеропорта"}:
            continue
        if len(raw) <= 4 and raw.isupper():
            continue
        first = adj_stem(raw.split()[0])
        if any(first.startswith(s) for s in AIRPORT_STOP):
            continue
        add("airport", adj_stem(raw), raw, "транспорт", m)
    for m in _ROUTE_RE.finditer(text):
        raw = m.group(1)
        if not raw:
            continue
        add("route", re.sub(r"\s+", " ", raw.lower())[:80], raw, "туризм", m)

    # de-dupe by kind+key
    seen: set[tuple[str, str]] = set()
    uniq: list[dict] = []
    for item in out:
        sig = (item["kind"], item["key"])
        if sig in seen:
            continue
        seen.add(sig)
        uniq.append(item)
    return uniq


# --- deficits / offers -----------------------------------------------------

DEFICIT_SPECS: list[tuple[str, re.Pattern[str], str | None]] = [
    (
        "water_infra",
        re.compile(
            r"зношен\w*.{0,24}вод|аварійн\w*.{0,24}вод|відсутн\w*.{0,28}водопост|"
            r"немає.{0,24}централізован\w*\s+водо|немає.{0,20}водовідвед",
            re.I,
        ),
        "вода",
    ),
    (
        "waste",
        re.compile(
            r"відсутн\w*.{0,24}полігон|немає.{0,24}полігон|"
            r"проблем\w*.{0,24}(?:ТПВ|смітт)|несанкціонован\w*\s+звалищ",
            re.I,
        ),
        "відходи",
    ),
    (
        "roads",
        re.compile(
            r"(?:поган|аварійн|зношен)\w*.{0,24}дор[оі]г|міжселищн\w*.{0,28}сполучен",
            re.I,
        ),
        "транспорт",
    ),
    (
        "cnap",
        re.compile(r"(?:відсутн|немає).{0,24}ЦНАП|немає.{0,28}адмінпослуг", re.I),
        "ЦНАП",
    ),
    (
        "energy",
        re.compile(
            r"зношен\w*.{0,24}(?:котельн|тепломереж)|відсутн\w*.{0,24}газ",
            re.I,
        ),
        "енергія",
    ),
    (
        "fire",
        re.compile(r"(?:відсутн|немає).{0,28}пожеж", re.I),
        "безпека",
    ),
]

OFFER_SPECS: list[tuple[str, re.Pattern[str]]] = [
    ("water_infra", re.compile(r"водоканал|водогін|централізован\w*\s+водопостач", re.I)),
    ("waste", re.compile(r"сміттєсортув|полігон\s+ТПВ|кластер.{0,24}відход", re.I)),
    ("roads", re.compile(r"дорожн\w*\s+(?:служб|підприєм)|ремонт.{0,18}дор[оі]г", re.I)),
    ("cnap", re.compile(r"\bЦНАП\b")),
    ("energy", re.compile(r"сонячн\w*\s+панел|\bВДЕ\b|котельн\w*.{0,16}щеп", re.I)),
    ("fire", re.compile(r"пожежн\w*\s+команд|місцев\w*\s+пожеж", re.I)),
]

OFFER_LABELS = {
    "water_infra": "водопостачання / водоканал",
    "waste": "ТПВ / полігон",
    "roads": "дороги",
    "cnap": "ЦНАП",
    "energy": "енергетика / ВДЕ",
    "fire": "пожежна команда",
}


def find_deficits(text: str, *, field: str = "challenges") -> list[dict]:
    if not text:
        return []
    out: list[dict] = []
    for kind, pat, theme in DEFICIT_SPECS:
        m = pat.search(text)
        if not m:
            continue
        out.append(
            {
                "kind": kind,
                "theme": theme,
                "field": field,
                "quote": _clip_quote(text, m.start(), m.end(), radius=60),
            }
        )
    return out


def find_offers(text: str, *, field: str = "strengths") -> list[dict]:
    if not text:
        return []
    out: list[dict] = []
    for kind, pat in OFFER_SPECS:
        m = pat.search(text)
        if not m:
            continue
        out.append(
            {
                "kind": kind,
                "field": field,
                "quote": _clip_quote(text, m.start(), m.end(), radius=50),
            }
        )
    return out


def deficit_kinds(text: str) -> set[str]:
    return {d["kind"] for d in find_deficits(text)}


def offer_kinds(*texts: str) -> set[str]:
    found: set[str] = set()
    for t in texts:
        found |= {o["kind"] for o in find_offers(t or "")}
    return found


# --- neighbours ------------------------------------------------------------

@dataclass
class NameIndex:
    by_stem: dict[str, list[dict]] = field(default_factory=dict)


def build_name_index(rows: list[dict]) -> NameIndex:
    by_stem: dict[str, list[dict]] = {}
    for r in rows:
        name = (r.get("Name") or "").strip()
        if not name:
            continue
        rec = {
            "Name": name,
            "Katottg": (r.get("Katottg") or r.get("KATOTTG") or "").strip(),
            "Oblast": r.get("Oblast") or "",
            "short": short_name(name),
        }
        stem = adj_stem(rec["short"])
        if len(stem) < 4:
            continue
        by_stem.setdefault(stem, []).append(rec)
    return NameIndex(by_stem=by_stem)


def _masked_oblast_spans(text: str) -> str:
    """Blank out «X область / район» so those adjectives are not hromadas."""
    return OBLAST_SKIP_RE.sub(" " * 8, text)


def resolve_stem(
    stem: str,
    index: NameIndex,
    *,
    speaker_name: str,
    speaker_oblast: str,
) -> dict | None:
    all_hits = index.by_stem.get(stem) or []
    uniq_all: dict[str, dict] = {h["Katottg"] or h["Name"]: h for h in all_hits}
    uniq: dict[str, dict] = {}
    for h in all_hits:
        if h["Name"] == speaker_name:
            continue
        uniq[h["Katottg"] or h["Name"]] = h
    hits = list(uniq.values())
    if not hits:
        return None
    homonym = len(uniq_all) > 1
    obl = (speaker_oblast or "").strip()
    if homonym:
        same = [h for h in hits if (h.get("Oblast") or "").strip() == obl]
        if len(same) == 1:
            return same[0]
        return None
    if len(hits) == 1:
        return hits[0]
    if obl:
        same = [h for h in hits if (h.get("Oblast") or "").strip() == obl]
        if len(same) == 1:
            return same[0]
    return None


def find_named_neighbours(
    text: str,
    *,
    speaker_name: str,
    speaker_oblast: str,
    index: NameIndex,
) -> list[dict]:
    """Resolve named peer hromadas. Homonyms require same oblast; else skip."""
    if not text:
        return []
    masked = _masked_oblast_spans(text)
    found: dict[str, dict] = {}
    speaker_stem = adj_stem(short_name(speaker_name))
    stop_stems = {adj_stem(x) for x in STOP_ADJ}

    def consider(raw: str, evidence: str) -> None:
        adj = raw.strip(" «»\"'’,;.")
        if not adj or adj.lower() in STOP_ADJ:
            return
        stem = adj_stem(adj)
        if len(stem) < 4 or stem in stop_stems:
            return
        if speaker_stem and "-" in speaker_stem and stem == speaker_stem.split("-")[-1]:
            return
        if re.search(r"конкуренц", evidence, re.I) or NEG_NEIGHBOUR_RE.search(evidence):
            return
        hit = resolve_stem(
            stem, index, speaker_name=speaker_name, speaker_oblast=speaker_oblast
        )
        if not hit:
            return
        prev = found.get(hit["Name"])
        if prev is None:
            found[hit["Name"]] = {
                "name": hit["Name"],
                "katottg": hit["Katottg"] or None,
                "short": hit["short"],
                "evidence": evidence[:220],
            }

    for m in ADJ_CHAIN_GROMADA_RE.finditer(masked):
        for part in CHAIN_SPLIT_RE.split(m.group(1)):
            consider(part, _clip_quote(text, m.start(), m.end()))
    for m in GROMADA_TRAIL_RE.finditer(masked):
        for part in CHAIN_SPLIT_RE.split(m.group(1)):
            consider(part, _clip_quote(text, m.start(), m.end()))
    for m in COOP_PREP_RE.finditer(masked):
        consider(m.group(1), _clip_quote(text, m.start(), m.end()))
    return sorted(found.values(), key=lambda x: x["short"])


def sector_hit_weight(sector: str, *, source: str) -> float:
    """Anti-kitchen-sink: generic sectors are cheap; water/waste/CNAP stay dear.

    `source` is DREAM or Strengths — DREAM kitchen-sink is even cheaper.
    Caller must still cap total kitchen-sink contribution at KITCHEN_SINK_CAP.
    """
    if sector in KITCHEN_SINK_SECTORS:
        return 0.12 if source == "DREAM" else KITCHEN_SINK_WEIGHT
    if source == "DREAM":
        return 1.0
    return 0.85
