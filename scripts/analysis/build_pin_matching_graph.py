#!/usr/bin/env python3
"""Build PIN + matching overlay viz: full МСС network + Leaflet map / force graph.

Sources:
  - data/cache/kse/partnerships-hromadas-network.csv
  - data/cache/kse/geography.csv
  - data/releases/matching-edges.json
  - data/releases/hromadas.json  (PortalUrl / StrategyUrl / Goals)
  - docs/geo/ukraine-oblasts.geojson  (Natural Earth admin-1, simplified)

Writes docs/mss-pin-matching-graph.html

Overlay policy (2026-07-24 / layers 2026-07-29):
  Do NOT paint top-N by combined score — that collapses to geo neighbours in a
  sparse strategy corpus. Split tracks instead:

    thematic      — high goals_cosine  → «схожа стратегія» (default ON)
    operational   — high geo           → «зручний сусід»   (default OFF)
    complementary — resource/DREAM ↔ Challenges (default OFF)
    explicit_ask  — МСС language in strategy text (default OFF)
    twinning      — UA–EU sister cities from SKEW / strategy (node highlight, default OFF)
    known         — curated registry validation pairs
    pin_corpus    — broader KSE PIN ∩ Goals corpus (mss_network>0, not known)
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
from goal_overlap import explain_goal_overlap  # noqa: E402
from tracks import operational_slice, thematic_slice  # noqa: E402

PIN = ROOT / "data/cache/kse/partnerships-hromadas-network.csv"
GEO = ROOT / "data/cache/kse/geography.csv"
MSS_REGISTRY = ROOT / "data/cache/mss/mss_registry.xlsx"
EDGES = ROOT / "data/releases/matching-edges.json"
COMPLEMENTARY = ROOT / "data/releases/matching-edges.complementary.json"
EXPLICIT_ASK = ROOT / "data/releases/matching-edges.explicit-ask.json"
TWINNING = ROOT / "data/releases/twinning-partners.json"
HROMADAS = ROOT / "data/releases/hromadas.json"
OBLASTS = ROOT / "docs/geo/ukraine-oblasts.geojson"
OUTLINE = ROOT / "docs/geo/ukraine-outline.geojson"
TEMPLATE = Path(__file__).with_name("mss_pin_matching_graph.template.html")
OUT = ROOT / "docs/mss-pin-matching-graph.html"

TOP_THEMATIC = 40
TOP_OPERATIONAL = 40
TOP_COMPLEMENTARY = 40
TOP_EXPLICIT_ASK = 40
MAX_AGREEMENTS_PER_EDGE = 6
AGREEMENT_TITLE_MAX = 140

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


def load_pin(registry: dict[str, dict] | None = None) -> tuple[dict[str, dict], list[dict]]:
    """PIN undirected edges, enriched with agreement subjects when registry is present."""
    registry = registry or {}
    nodes: dict[str, dict] = {}
    pair_regs: dict[tuple[str, str], set[str]] = defaultdict(set)
    with PIN.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            a, b = row["hromada_code.x"], row["hromada_code.y"]
            if not a or not b or a == b:
                continue
            nodes[a] = {"id": a, "label": row["hromada_name.x"] or a}
            nodes[b] = {"id": b, "label": row["hromada_name.y"] or b}
            key = tuple(sorted((a, b)))
            num = (row.get("register_number") or "").strip()
            if num:
                pair_regs[key].add(num)
            else:
                pair_regs[key]  # ensure pair exists even without number

    edges: list[dict] = []
    for (a, b), nums in sorted(pair_regs.items()):
        edge: dict = {"a": a, "b": b, "kind": "pin"}
        agreements: list[dict] = []
        seen_titles: set[str] = set()
        for num in sorted(nums, key=lambda x: int(x) if x.isdigit() else 0):
            info = registry.get(num) or {}
            title = agreement_essence(info.get("title") or "", info.get("form") or "")
            if not title:
                title = f"№{num}"
            # Dedupe near-identical subjects across multi-agreement pairs.
            key_t = title.casefold()
            if key_t in seen_titles:
                continue
            seen_titles.add(key_t)
            item: dict = {"n": num, "title": title}
            form = _clip(info.get("form") or "", 90)
            if form and form.casefold() != title.casefold():
                item["form"] = form
            agreements.append(item)
            if len(agreements) >= MAX_AGREEMENTS_PER_EDGE:
                break
        if agreements:
            edge["agreements"] = agreements
            edge["reasons"] = [x["title"] for x in agreements[:4]]
            if len(agreements) == 1 and agreements[0].get("form"):
                edge["theme"] = agreements[0]["form"]
        edges.append(edge)
    return nodes, edges


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
    themes = e.get("themes")
    if isinstance(themes, list) and themes:
        out["themes"] = [str(t).strip() for t in themes if t][:6]
    for key in (
        "suggested_theme",
        "suggested_form",
        "suggest_confidence",
        "suggest_rationale",
        "suggest_caveat",
    ):
        if e.get(key):
            out[key] = e[key]
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


def pin_corpus_overlay(
    corpus_matching: list[dict],
    *,
    name_to_code: dict[str, str],
    known_code_keys: set[tuple[str, str]],
    goals_by_name: dict[str, dict] | None = None,
) -> list[dict]:
    """Broader KSE check: mss_network>0 but not curated known (dedupe by KATOTTG)."""
    by_codes: dict[tuple[str, str], dict] = {}
    for e in corpus_matching:
        if e.get("known") or float(e.get("mss_network") or 0) <= 0:
            continue
        ca, cb = name_to_code[e["a"]], name_to_code[e["b"]]
        if ca == cb:
            continue
        key = tuple(sorted((ca, cb)))
        if key in known_code_keys:
            continue
        prev = by_codes.get(key)
        if prev is None or float(e["score"]) > float(prev["score"]):
            by_codes[key] = e
    out: list[dict] = []
    for key, e in sorted(by_codes.items()):
        edge = {
            "a": key[0],
            "b": key[1],
            "kind": "pin_corpus",
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
    pin_nodes, pin_edges = load_pin(mss_registry)

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
        }

    corpus = [r for r in hromadas if r.get("Goals") and r.get("Katottg")]
    name_to_code = {r["Name"]: r["Katottg"] for r in corpus}
    code_to_full = {r["Katottg"]: r["Name"] for r in corpus}
    corpus_codes = set(name_to_code.values())
    goals_by_name = {
        r["Name"]: {
            "goals": (r.get("Goals") or "").strip(),
            "katottg": r.get("Katottg"),
        }
        for r in corpus
        if r.get("Name")
    }

    matching = json.loads(EDGES.read_text(encoding="utf-8"))
    corpus_matching = [
        e for e in matching if e["a"] in name_to_code and e["b"] in name_to_code
    ]
    known = [e for e in corpus_matching if e.get("known")]
    thematic = thematic_slice(corpus_matching, limit=TOP_THEMATIC)
    operational = operational_slice(corpus_matching, limit=TOP_OPERATIONAL)

    pin_keys = {tuple(sorted((e["a"], e["b"]))) for e in pin_edges}
    known_code_keys = {
        tuple(sorted((name_to_code[e["a"]], name_to_code[e["b"]]))) for e in known
    }

    known_edges = []
    for e in known:
        edge = {
            "a": name_to_code[e["a"]],
            "b": name_to_code[e["b"]],
            "kind": "known",
            "score": e["score"],
            "goals_cosine": e.get("goals_cosine"),
            "geo_score": e.get("geo_score"),
            "track": e.get("track"),
        }
        attach_goal_overlap(
            edge, name_a=e["a"], name_b=e["b"], goals_by_name=goals_by_name
        )
        edge.update(explain_fields({**e, **edge}))
        known_edges.append(edge)
    pin_corpus_edges = pin_corpus_overlay(
        corpus_matching,
        name_to_code=name_to_code,
        known_code_keys=known_code_keys,
        goals_by_name=goals_by_name,
    )
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
        # Expand name_to_code to all hromadas (intents may cite non-Goals rows)
        all_name_to_code = {
            r["Name"]: r["Katottg"]
            for r in hromadas
            if r.get("Name") and r.get("Katottg")
        }
        explicit_ask_edges = encode_named_overlay(
            json.loads(EXPLICIT_ASK.read_text(encoding="utf-8")),
            kind="explicit_ask",
            name_to_code=all_name_to_code,
            score_key="explicit_ask_score",
            limit=TOP_EXPLICIT_ASK,
        )

    for e in (
        known_edges
        + pin_corpus_edges
        + thematic_edges
        + operational_edges
        + complementary_edges
        + explicit_ask_edges
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

    degree: dict[str, int] = {c: 0 for c in pin_nodes}
    for e in pin_edges:
        degree[e["a"]] = degree.get(e["a"], 0) + 1
        degree[e["b"]] = degree.get(e["b"], 0) + 1

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
        return {
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
        }

    nodes = []
    with_geo = 0
    for code, base in sorted(pin_nodes.items(), key=lambda x: x[1]["label"]):
        n = enrich(code, base["label"])
        if n["lat"] is not None:
            with_geo += 1
        nodes.append(n)

    # Universe layer: every release hromada with KSE lat/lon (≈ full mainland set)
    universe: list[dict] = []
    for code, meta in by_code.items():
        g = geo.get(code)
        if not g:
            continue
        twin = twinning_by_code.get(code) or {}
        twin_partners = twin.get("partners") or []
        universe.append(
            {
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
        )
    universe.sort(key=lambda n: n.get("full_name") or n["label"] or n["id"])

    if not OBLASTS.exists():
        raise SystemExit(f"Missing {OBLASTS}")
    if not OUTLINE.exists():
        raise SystemExit(f"Missing {OUTLINE}")
    oblasts = json.loads(OBLASTS.read_text(encoding="utf-8"))
    outline = json.loads(OUTLINE.read_text(encoding="utf-8"))

    portal_on_map = sum(1 for n in universe if n.get("portal_url"))
    twinning_on_map = sum(1 for n in universe if n.get("twinning_count") or n.get("c4c_url"))

    return {
        "meta": {
            "corpus_size": len(corpus),
            "pin_edges": len(pin_edges),
            "pin_nodes": len(nodes),
            "universe_nodes": len(universe),
            "universe_with_portal": portal_on_map,
            "twinning_hromadas": twinning_on_map,
            "twinning_partners": sum(len(v.get("partners") or []) for v in twinning_by_code.values()),
            "cities4cities_listed": sum(1 for v in twinning_by_code.values() if v.get("c4c_url")),
            "thematic_edges": len(thematic_edges),
            "operational_edges": len(operational_edges),
            "complementary_edges": len(complementary_edges),
            "explicit_ask_edges": len(explicit_ask_edges),
            "known_edges": len(known_edges),
            "pin_corpus_edges": len(pin_corpus_edges),
            # legacy alias: thematic only (combined-score hyp layer removed)
            "hypothesis_edges": len(thematic_edges),
            "nodes_with_geo": with_geo,
            "oblasts": len(oblasts.get("features", [])),
            "pin_source": "KSE-Loc-Data-Hub partnerships-hromadas-network.csv",
            "mss_registry_source": (
                "data/cache/mss/mss_registry.xlsx (Назва договору / Форма)"
                if mss_registry
                else None
            ),
            "pin_agreements_enriched": sum(
                1 for e in pin_edges if e.get("agreements")
            ),
            "geo_source": "KSE-Loc-Data-Hub geography.csv (lat_center/lon_center)",
            "oblasts_source": "Natural Earth admin-1 → docs/geo/ukraine-oblasts.geojson",
            "outline_source": "docs/geo/ukraine-outline.geojson (mask outside UA)",
            "matching_source": "data/releases/matching-edges.json",
            "hromadas_source": "data/releases/hromadas.json (PortalUrl/StrategyUrl)",
            "twinning_source": (
                "data/releases/twinning-partners.json (SKEW + strategy)"
                if twinning_by_code
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
                "pin_corpus=mss_network>0 not known; no combined-score hyp layer; "
                "universe=all release rows with KSE geo (metadata layer)"
            ),
        },
        "oblasts": oblasts,
        "ukraine_outline": outline,
        "nodes": nodes,
        "universe": universe,
        "edges": (
            pin_edges
            + known_edges
            + pin_corpus_edges
            + thematic_edges
            + operational_edges
            + complementary_edges
            + explicit_ask_edges
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
        f"PIN {m['pin_nodes']}n/{m['pin_edges']}e "
        f"(subjects={m.get('pin_agreements_enriched', 0)}) · "
        f"universe={m['universe_nodes']} (portal={m['universe_with_portal']}) · "
        f"oblasts={m['oblasts']} · "
        f"known={m['known_edges']} pin∩corpus={m['pin_corpus_edges']} "
        f"thematic={m['thematic_edges']} operational={m['operational_edges']} "
        f"complementary={m['complementary_edges']} explicit_ask={m['explicit_ask_edges']} "
        f"twinning={m.get('twinning_hromadas', 0)}"
    )


if __name__ == "__main__":
    main()
