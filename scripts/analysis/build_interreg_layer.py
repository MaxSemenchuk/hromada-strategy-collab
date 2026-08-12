#!/usr/bin/env python3
"""UA–EU Interreg partnership layer (separate from domestic МСС matching).

Source: keep.eu (Interact/EU public database of Interreg/ETC projects and
partner organisations). Uses keep.eu's public browse API — POST
/api/search/projects/ for project lists, GET /api/project/<id>/ for detail
(partner org names, towns, budgets) — which works without an API key. This is
distinct from keep.eu's registered-key Open Data bulk export documented at
https://keep.eu/faq/api-how-to-access-data-in-open-data-format/ (see
internal/eu-transfer-one-pager.md for that path).

Scope (first pass): the five 2021-2027 Interreg NEXT/B programmes bordering
or covering Ukraine — Poland-Ukraine, Hungary-Slovakia-Romania-Ukraine,
Romania-Ukraine, Danube, Black Sea Basin (PROGRAMMES_CURRENT below).
Historical periods (2014-2020 ENI CBC, 2007-2013 ENPI CBC, 2000-2006 — same
country pairs, ~1,100 more projects total) are known programme IDs
(PROGRAMMES_HISTORICAL) but not fetched by default — pass --historical to
include them.

Does NOT fold into v7 combined `score`. Does NOT set known=true (that flag is
for curated domestic registry МСС only).

Usage:
  yarn interreg                 # fetch + build release (current period only)
  yarn interreg --historical    # also fetch 2000-2020 programmes
  yarn interreg --offline       # build from cache only, no network
  yarn fetch-interreg           # refresh data/cache/interreg/ only
"""

from __future__ import annotations

import argparse
import json
import re
import ssl
import time
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / "data" / "cache" / "interreg"
CACHE_PROJECTS_DIR = CACHE / "projects"
CACHE_LIST = CACHE / "project-list.json"
HROMADAS = ROOT / "data" / "releases" / "hromadas.json"
OUT = ROOT / "data" / "releases" / "interreg-partners.json"
MANIFEST = ROOT / "data" / "releases" / "interreg-partners.manifest.json"
PREVIEW = ROOT / "docs" / "assets" / "interreg-preview.json"

API_BASE = "https://keep.eu/api"
SEARCH_PROJECTS = f"{API_BASE}/search/projects/"
PROJECT_DETAIL = f"{API_BASE}/project/{{id}}/"
PROJECT_PAGE = "https://keep.eu/projects/{seo_name}/"

UA_HDR = (
    "hromada-strategy-collab/0.1 "
    "(+https://github.com/MaxSemenchuk/hromada-strategy-collab; research cache)"
)

# 2021-2027 Interreg NEXT/B programmes bordering or covering Ukraine.
PROGRAMMES_CURRENT = {
    335: "2021 - 2027 Interreg VI-A NEXT Poland - Ukraine",
    337: "2021 - 2027 Interreg VI-A NEXT Hungary - Slovakia - Romania - Ukraine",
    341: "2021 - 2027 Interreg VI-A NEXT Romania - Ukraine",
    369: "2021 - 2027 Interreg VI-B Danube",
    387: "2021 - 2027 Interreg VI-B NEXT Black Sea Basin",
}

# Same country pairs, earlier programming periods. Not fetched unless
# --historical is passed (~1,100 additional projects, most without UA
# partners since Ukraine joined some of these programmes only in later
# calls — expect a lower hit rate than PROGRAMMES_CURRENT).
PROGRAMMES_HISTORICAL = {
    76: "2014 - 2020 Poland - Belarus - Ukraine ENI CBC",
    93: "2014 - 2020 Romania - Ukraine ENI CBC",
    96: "2014 - 2020 Hungary - Slovakia - Romania - Ukraine ENI CBC",
    63: "2014 - 2020 INTERREG VB Danube",
    64: "2014 - 2020 Black Sea Basin ENI CBC",
    173: "2007 - 2013 Poland-Belarus-Ukraine ENPI CBC",
    137: "2007 - 2013 Romania-Ukraine-Moldova ENPI CBC",
    117: "2007 - 2013 Hungary-Slovakia-Romania-Ukraine ENPI CBC",
    153: "2007 - 2013 Black Sea Basin ENPI CBC",
    259: "2000 - 2006 Poland - Ukraine - Belarus (PL-UA-BY)",
    232: "2000 - 2006 Hungary - Slovakia - Ukraine (HU-SK-UA)",
}

REQUEST_TEMPLATE = {
    "projects": {
        "status": None,
        "prizes": False,
        "only_projects_with_documents": False,
        "project_details": {"start": [], "without_start": False, "end": [], "without_end": False},
        "project_budget": {"range": [], "without_budget": False},
        "themes": {"list": [], "type": "or"},
        "macro_regional_strategies": [],
        "only_infrastructure_financed": False,
    },
    "programmes": {"type": [], "period": [], "available": []},
    "partners": {
        "status": [],
        "type": [],
        "nuts_lead": [],
        "nuts_partner": [],
        "nuts_search_type": "both",
        "selectedAreas": {},
    },
    "contribution_2014_2020": {
        "specific_objectives": {"thematic_objectives": [], "thematic_priorities": []},
        "thematic_objectives_eni": [],
    },
    "contribution_2021_2027": {
        "specific_objectives": [],
        "intervention": [],
        "common_output_indicators": [],
        "common_result_indicators": [],
    },
    "search": {
        "list": [],
        "type": None,
        "fields": [
            "name__unaccent__contains",
            "acronym__unaccent__contains",
            "description__unaccent__contains",
            "expected_results__unaccent__contains",
            "achievements__unaccent__contains",
            "expected_achievements__unaccent__contains",
            "actual_achievements__unaccent__contains",
            "expected_outputs__unaccent__contains",
            "delivered_outputs__unaccent__contains",
            "partner__name__unaccent__exact",
            "partner__name_translated__unaccent__contains",
        ],
        "rawSearchString": "",
    },
    "documents": {"document_lang": [], "languages": [], "types": [], "name": "", "search": ""},
    "project_lang": [],
    "project_desc_lang": [],
    "languages": [],
    "translation_languages": [],
    "thematic_objectives_eni": [],
    "location": None,
}

EN_OBLAST_TO_UA = {
    "vinnytsia": "Вінницька область",
    "volyn": "Волинська область",
    "dnipropetrovsk": "Дніпропетровська область",
    "donetsk": "Донецька область",
    "zhytomyr": "Житомирська область",
    "zakarpattia": "Закарпатська область",
    "transcarpathia": "Закарпатська область",
    "zaporizhzhia": "Запорізька область",
    "ivano-frankivsk": "Івано-Франківська область",
    "kyiv": "Київська область",
    "kyivska": "Київська область",
    "kirovohrad": "Кіровоградська область",
    "luhansk": "Луганська область",
    "lviv": "Львівська область",
    "mykolaiv": "Миколаївська область",
    "odesa": "Одеська область",
    "odessa": "Одеська область",
    "poltava": "Полтавська область",
    "rivne": "Рівненська область",
    "sumy": "Сумська область",
    "ternopil": "Тернопільська область",
    "kharkiv": "Харківська область",
    "kherson": "Херсонська область",
    "khmelnytskyi": "Хмельницька область",
    "khmelnytsky": "Хмельницька область",
    "cherkasy": "Черкаська область",
    "chernivtsi": "Чернівецька область",
    "chernihiv": "Чернігівська область",
}

ADJ_SUFFIXES = ("ської", "зької", "цької", "ької", "ська", "зька", "цька", "ька")

# Adjective immediately before a council/hromada noun, nominative or
# genitive ("Верховинська сільська рада" / "...Верховинської Сільської Ради").
COUNCIL_ADJ = re.compile(
    r"([А-ЯІЇЄҐ][а-яіїєґ'’\-]+?)(?:" + "|".join(ADJ_SUFFIXES) + r")\s+"
    r"(?:сільськ\w*|селищн\w*|міськ\w*)\s+"
    r"(?:рад\w*|територіальн\w*\s+громад\w*)",
    re.I,
)


def _ssl_context() -> ssl.SSLContext:
    try:
        import certifi  # type: ignore

        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        ctx = ssl.create_default_context()
        try:
            ctx.load_default_certs()
        except Exception:
            pass
        return ctx


def http_post_json(url: str, body: dict) -> dict:
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"User-Agent": UA_HDR, "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, context=_ssl_context(), timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def http_get_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": UA_HDR})
    with urllib.request.urlopen(req, context=_ssl_context(), timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_project_list(programme_ids: list[int]) -> list[dict]:
    body = json.loads(json.dumps(REQUEST_TEMPLATE))
    body["programmes"]["available"] = [{"id": i} for i in programme_ids]
    results: list[dict] = []
    page = 1
    while True:
        payload = http_post_json(f"{SEARCH_PROJECTS}?page={page}", body)
        batch = payload.get("results") or []
        results.extend(batch)
        total_pages = payload.get("total_pages") or 1
        if page == 1:
            print(f"  {payload.get('count')} projects across {total_pages} pages")
        if page >= total_pages or not batch:
            break
        page += 1
        time.sleep(0.15)
    return results


def fetch_project_detail(project_id: int, force: bool = False) -> dict:
    CACHE_PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
    cache_file = CACHE_PROJECTS_DIR / f"{project_id}.json"
    if not force and cache_file.exists():
        return json.loads(cache_file.read_text(encoding="utf-8"))
    detail = http_get_json(PROJECT_DETAIL.format(id=project_id))
    cache_file.write_text(json.dumps(detail, ensure_ascii=False) + "\n", encoding="utf-8")
    time.sleep(0.15)
    return detail


def fetch_all(programme_ids: list[int], force: bool = False) -> list[dict]:
    CACHE.mkdir(parents=True, exist_ok=True)
    if not force and CACHE_LIST.exists():
        cached = json.loads(CACHE_LIST.read_text(encoding="utf-8"))
        if set(cached.get("programme_ids") or []) >= set(programme_ids):
            print(f"Using cached {CACHE_LIST.relative_to(ROOT)}")
            projects = cached["projects"]
        else:
            projects = None
    else:
        projects = None

    if projects is None:
        print(f"Fetching project list for {len(programme_ids)} programmes")
        projects = fetch_project_list(programme_ids)
        CACHE_LIST.write_text(
            json.dumps(
                {
                    "fetched_at": datetime.now(timezone.utc).isoformat(),
                    "programme_ids": programme_ids,
                    "project_count": len(projects),
                    "projects": projects,
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    details: list[dict] = []
    for i, p in enumerate(projects, 1):
        pid = p["id"]
        try:
            detail = fetch_project_detail(pid, force=force)
        except Exception as exc:
            print(f"  WARN project {pid} fetch failed: {exc}")
            continue
        details.append(detail)
        if i % 50 == 0:
            print(f"  fetched detail {i}/{len(projects)}")
    return details


def norm_apos(s: str) -> str:
    return (s or "").replace("'", "’").replace("ʼ", "’").replace("`", "’")


def short_name(name: str) -> str:
    for suffix in (
        " міська територіальна громада",
        " селищна територіальна громада",
        " сільська територіальна громада",
        " територіальна громада",
    ):
        if name.endswith(suffix):
            return name[: -len(suffix)]
    return name


def adj_stem(word: str) -> str | None:
    w = norm_apos(word).lower()
    for suf in ADJ_SUFFIXES:
        if w.endswith(suf) and len(w) > len(suf) + 2:
            return w[: -len(suf)]
    return None


def hromada_stem(name: str) -> str | None:
    short = short_name(norm_apos(name))
    first = short.split(" ", 1)[0] if short else ""
    return adj_stem(first)


def partner_stem(partner_name: str) -> str | None:
    m = COUNCIL_ADJ.search(norm_apos(partner_name or ""))
    if not m:
        return None
    return m.group(1).lower()


UA_TO_LAT = {
    "а": "a", "б": "b", "в": "v", "г": "h", "ґ": "g", "д": "d", "е": "e",
    "є": "ie", "ж": "zh", "з": "z", "и": "y", "і": "i", "ї": "i", "й": "i",
    "к": "k", "л": "l", "м": "m", "н": "n", "о": "o", "п": "p", "р": "r",
    "с": "s", "т": "t", "у": "u", "ф": "f", "х": "kh", "ц": "ts", "ч": "ch",
    "ш": "sh", "щ": "shch", "ь": "", "ю": "iu", "я": "ia",
}


def to_lat(s: str) -> str:
    s = norm_apos(s).lower()
    out: list[str] = []
    for ch in s:
        if ch in UA_TO_LAT:
            out.append(UA_TO_LAT[ch])
        elif "a" <= ch <= "z":
            out.append(ch)
    return "".join(out)


def norm_town(s: str) -> str:
    return re.sub(r"[^a-z]", "", (s or "").lower())


def load_hromada_index() -> tuple[dict[str, dict], dict[str, list[dict]], dict[str, list[dict]]]:
    rows = json.loads(HROMADAS.read_text(encoding="utf-8"))
    by_name: dict[str, dict] = {}
    by_stem: dict[str, list[dict]] = defaultdict(list)
    by_town: dict[str, list[dict]] = defaultdict(list)

    def richness(r: dict) -> int:
        return sum(1 for f in ("PartnersMentioned", "Projects", "Goals", "MSSAgreements") if (r.get(f) or "").strip())

    for r in rows:
        name = norm_apos((r.get("Name") or "").strip())
        if not name:
            continue
        r = {**r, "Name": name}
        prev = by_name.get(name)
        if prev is None or richness(r) > richness(prev):
            by_name[name] = r
        st = hromada_stem(name)
        if st:
            by_stem[st].append(by_name[name])
        short = short_name(name)
        first = short.split(" ", 1)[0] if short else ""
        town_key = norm_town(to_lat(adj_stem(first) or first))
        if town_key:
            by_town[town_key].append(by_name[name])
    return by_name, by_stem, by_town


def match_partner(
    partner_name: str,
    town: str | None,
    oblast_hint: str | None,
    by_stem: dict[str, list[dict]],
    by_town: dict[str, list[dict]],
) -> tuple[dict | None, str]:
    def pick(hits: list[dict]) -> dict | None:
        uniq: dict[str, dict] = {}
        for h in hits:
            uniq[h.get("Katottg") or h["Name"]] = h
        hits = list(uniq.values())
        if oblast_hint:
            narrowed = [h for h in hits if h.get("Oblast") == oblast_hint]
            if len(narrowed) == 1:
                return narrowed[0]
            if narrowed:
                hits = narrowed
        if len(hits) == 1:
            return hits[0]
        if len(hits) > 1:
            city = [h for h in hits if "міська" in (h.get("Name") or "")]
            if len(city) == 1:
                return city[0]
        return None

    st = partner_stem(partner_name)
    if st and by_stem.get(st):
        row = pick(by_stem[st])
        if row:
            return row, "name_stem"

    if town:
        tk = norm_town(town)
        hits: list[dict] = []
        for st, hlist in by_town.items():
            if not st or len(st) < 4:
                continue
            if tk == st or tk.startswith(st) or st.startswith(tk):
                hits.extend(hlist)
        if hits:
            row = pick(hits)
            if row:
                return row, "town"
    return None, "unmatched"


def oblast_from_address(address: str | None) -> str | None:
    if not address:
        return None
    m = re.search(r",\s*([A-Za-z\-]+)\s+Oblast\s*,", address)
    if not m:
        return None
    return EN_OBLAST_TO_UA.get(m.group(1).strip().lower())


def build_release(details: list[dict], programme_ids: list[int]) -> None:
    by_name, by_stem, by_town = load_hromada_index()

    by_hromada: dict[str, dict] = {}
    stats: dict[str, int] = defaultdict(int)
    unmatched: list[dict] = []
    seen_project_partner: set[tuple[int, int]] = set()

    for proj in details:
        pid = proj.get("id")
        acronym = proj.get("acronym")
        seo_name = proj.get("seo_name")
        programme = proj.get("programme") or {}
        translations = proj.get("translations") or {}
        proj_name = ((translations.get("en") or {}).get("name")) or acronym
        source_url = PROJECT_PAGE.format(seo_name=seo_name) if seo_name else None
        for ship in proj.get("partnerships") or []:
            partner = ship.get("partner") or {}
            country = (partner.get("country") or {}).get("title")
            if country != "Ukraine":
                continue
            partner_id = partner.get("id")
            if partner_id is not None and (pid, partner_id) in seen_project_partner:
                continue
            if partner_id is not None:
                seen_project_partner.add((pid, partner_id))
            partner_name = partner.get("name") or ""
            partner_name_en = ((partner.get("translations") or {}).get("en") or {}).get(
                "name_translated"
            )
            town = ship.get("town")
            oblast_hint = oblast_from_address(ship.get("location_address"))
            row, how = match_partner(partner_name, town, oblast_hint, by_stem, by_town)
            stats[how] += 1
            org_type = ship.get("organisation_type")
            prog_id = programme.get("id")
            entry_common = {
                "project_id": pid,
                "project_acronym": acronym,
                "project_name_en": proj_name,
                "programme": programme.get("title"),
                "programme_id": prog_id,
                # keep.eu's own organisation_type is null on every 2000-2020 record
                # observed so far (2021-2027 records have it) — period tells readers
                # why is_local_authority can't be trusted as a negative for those rows.
                "period": "current" if prog_id in PROGRAMMES_CURRENT else "historical",
                "organisation_type": org_type,
                # True only for keep.eu's own "Local public authority" tag — i.e. the
                # partner plausibly *is* the hromada council itself, not merely an
                # oblast/national/sectoral body headquartered in the hromada's town
                # (which is what a plain town-match otherwise conflates). Read this
                # as a lower bound: some genuine hromada departments are tagged
                # "Other" by keep.eu and won't get this flag.
                "is_local_authority": org_type == "Local public authority",
                "town": town,
                "partner_name": partner_name,
                "partner_name_en": partner_name_en,
                "budget_eur": ship.get("total_budget"),
                "source": "keep.eu",
                "source_url": source_url,
                "confidence": "registry",
                "match": how,
            }
            if not row:
                unmatched.append({**entry_common, "oblast_hint": oblast_hint})
                continue
            code = (row.get("Katottg") or row["Name"]).strip()
            hentry = by_hromada.setdefault(
                code,
                {
                    "name": row["Name"],
                    "short": short_name(row["Name"]),
                    "katottg": row.get("Katottg"),
                    "oblast": row.get("Oblast"),
                    "partners": [],
                },
            )
            key = (pid, partner_id or partner_name)
            existing = {(p["project_id"], p.get("_dedupe_key")) for p in hentry["partners"]}
            if key not in existing:
                hentry["partners"].append({**entry_common, "_dedupe_key": partner_id or partner_name})

    for h in by_hromada.values():
        for p in h["partners"]:
            p.pop("_dedupe_key", None)

    hromadas = sorted(
        by_hromada.values(),
        key=lambda h: (-len(h["partners"]), h["short"]),
    )
    for h in hromadas:
        h["partner_count"] = len(h["partners"])
        h["local_authority_partner_count"] = sum(
            1 for p in h["partners"] if p.get("is_local_authority")
        )

    matched_partnerships = sum(len(h["partners"]) for h in hromadas)
    local_authority_count = sum(
        1 for h in hromadas for p in h["partners"] if p.get("is_local_authority")
    )
    org_type_breakdown: dict[str, int] = defaultdict(int)
    period_breakdown: dict[str, int] = defaultdict(int)
    for h in hromadas:
        for p in h["partners"]:
            org_type_breakdown[p.get("organisation_type") or "unspecified"] += 1
            period_breakdown[p.get("period") or "unknown"] += 1
    hromadas_with_local_authority = sum(
        1 for h in hromadas if h["local_authority_partner_count"] > 0
    )

    generated = datetime.now(timezone.utc).isoformat()
    payload = {
        "generatedAt": generated,
        "warning": (
            "UA-EU Interreg partnership layer — separate from domestic МСС and from "
            "the SKEW/Cities4Cities twinning layer (twinning-partners.json). Sourced "
            "from keep.eu (Interact-EU), the official Interreg/ETC project database. "
            "IMPORTANT: matching a partner org to a hromada by its registered town "
            "does NOT mean that hromada's council has a cooperation tie the way SKEW "
            "twinning does — most matched partners are oblast/national/sectoral bodies "
            "(regional development agencies, universities, hospitals, NGOs, even a "
            "National Guard unit) that merely have a mailing address in that hromada's "
            "town, not the hromada government itself. Only "
            f"{local_authority_count}/{matched_partnerships} matched partnerships "
            "(organisation_type == 'Local public authority') plausibly ARE the "
            "hromada council or a direct department of it — treat coverage.org_type_"
            "breakdown as the honest picture, not hromadas_with_partners. SECOND "
            "CAVEAT: organisation_type is null on every 2000-2020 ('historical') "
            "record observed so far — keep.eu simply didn't capture it for older "
            "programming periods — so is_local_authority is a hard false there, not "
            "evidence of absence. All 57 confirmed local-authority partnerships come "
            "from the 2021-2027 ('current') period; period_breakdown below shows how "
            "much of the total is from the less-classified historical periods. Not "
            "folded into matching score."
        ),
        "sources": [
            {
                "id": "keep.eu",
                "name": "keep.eu — Interact-EU Interreg/ETC project database",
                "url": "https://keep.eu",
                "programmes": [
                    {"id": pid, "title": PROGRAMMES_CURRENT.get(pid) or PROGRAMMES_HISTORICAL.get(pid)}
                    for pid in programme_ids
                ],
            }
        ],
        "coverage": {
            "programme_ids": programme_ids,
            "projects_scanned": len(details),
            "hromadas_with_partners": len(hromadas),
            "hromadas_with_local_authority_partner": hromadas_with_local_authority,
            "matched_partnerships": matched_partnerships,
            "local_authority_partnerships": local_authority_count,
            "unmatched_partnerships": len(unmatched),
            "resolve_stats": dict(stats),
            "org_type_breakdown": dict(
                sorted(org_type_breakdown.items(), key=lambda kv: -kv[1])
            ),
            "period_breakdown": dict(period_breakdown),
        },
        "hromadas": hromadas,
        "unmatched": unmatched[:300],
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    MANIFEST.write_text(
        json.dumps(
            {
                "generatedAt": generated,
                "hromadasWithPartners": len(hromadas),
                "hromadasWithLocalAuthorityPartner": hromadas_with_local_authority,
                "projectsScanned": len(details),
                "matchedPartnerships": matched_partnerships,
                "localAuthorityPartnerships": local_authority_count,
                "periodBreakdown": dict(period_breakdown),
                "unmatchedPartnerships": len(unmatched),
                "programmeIds": programme_ids,
                "method": "keep.eu public search+detail API; name-stem + town matching, no API key required",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    PREVIEW.write_text(
        json.dumps(
            {
                "generatedAt": generated,
                "caveat": (
                    "UA-EU Interreg partnerships (keep.eu) — separate from domestic МСС "
                    "and SKEW/C4C twinning. Most matches are oblast/national bodies "
                    "headquartered in the hromada's town, not the hromada council "
                    "itself — see local_authority_partner_count per hromada."
                ),
                "hromadaCount": len(hromadas),
                "localAuthorityPartnerships": local_authority_count,
                "projectsScanned": len(details),
                "top": [
                    {
                        "short": h["short"],
                        "oblast": h.get("oblast"),
                        "partner_count": h["partner_count"],
                        "local_authority_partner_count": h["local_authority_partner_count"],
                        "projects": sorted(
                            {p["project_acronym"] for p in h["partners"] if p.get("project_acronym")}
                        )[:5],
                    }
                    for h in hromadas[:25]
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(
        f"Wrote {OUT.relative_to(ROOT)} — {len(hromadas)} hromadas from "
        f"{len(details)} projects scanned; unmatched={len(unmatched)}; "
        f"resolve_stats={dict(stats)}"
    )


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--offline", action="store_true", help="Build from cache only, no network")
    ap.add_argument("--fetch-only", action="store_true", help="Only refresh cache")
    ap.add_argument("--force-fetch", action="store_true", help="Re-download even if cache exists")
    ap.add_argument(
        "--historical", action="store_true", help="Also fetch 2000-2020 programmes"
    )
    args = ap.parse_args()

    programme_ids = list(PROGRAMMES_CURRENT)
    if args.historical:
        programme_ids += list(PROGRAMMES_HISTORICAL)

    if args.offline:
        if not CACHE_LIST.exists():
            raise SystemExit(
                "No cached project list under data/cache/interreg/ — run without --offline first"
            )
        cached = json.loads(CACHE_LIST.read_text(encoding="utf-8"))
        projects = cached["projects"]
        details = []
        for p in projects:
            f = CACHE_PROJECTS_DIR / f"{p['id']}.json"
            if f.exists():
                details.append(json.loads(f.read_text(encoding="utf-8")))
    else:
        details = fetch_all(programme_ids, force=args.force_fetch)

    if args.fetch_only:
        return
    build_release(details, programme_ids)


if __name__ == "__main__":
    main()
