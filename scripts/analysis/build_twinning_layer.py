#!/usr/bin/env python3
"""UA–EU municipal twinning layer (separate from domestic МСС matching).

Primary source: SKEW (Engagement Global) German–Ukrainian municipal partnership
list + map (HTML; ~250–300 links). Secondary: Cities4Cities news titles naming
signed UA–EU pairs + markers.json profile URLs. Tertiary: named foreign city
partners in strategy extractions (PartnersMentioned / Projects / MSSAgreements).

Does NOT fold into v7 combined `score`. Does NOT set known=true (that flag is
for curated domestic registry МСС only).

Usage:
  yarn twinning                 # fetch SKEW if cache stale/missing + build release
  yarn twinning --offline       # build from cache + strategies only
  yarn twinning --fetch-only    # refresh data/cache/twinning/ only
  yarn fetch-twinning           # alias for --fetch-only
"""

from __future__ import annotations

import argparse
import json
import re
import ssl
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from html import unescape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / "data" / "cache" / "twinning"
CACHE_MAP = CACHE / "skew-map.html"
CACHE_LIST = CACHE / "skew-list.html"
CACHE_EDGES = CACHE / "skew-edges.json"
CACHE_C4C_MARKERS = CACHE / "cities4cities-markers.json"
CACHE_C4C_NEWS = CACHE / "cities4cities-news.json"
HROMADAS = ROOT / "data" / "releases" / "hromadas.json"
ALIASES = ROOT / "data" / "sources" / "twinning-name-aliases.json"
PARTNERSHIP_MAP = ROOT / "data" / "releases" / "partnership-map.json"
DE_DUPLICATE_PAIRS = ROOT / "data" / "sources" / "twinning-de-duplicate-pairs.json"
OUT = ROOT / "data" / "releases" / "twinning-partners.json"
MANIFEST = ROOT / "data" / "releases" / "twinning-partners.manifest.json"
PREVIEW = ROOT / "docs" / "assets" / "twinning-preview.json"

SKEW_MAP_URL = (
    "https://skew.engagement-global.de/"
    "landkarte-deutsch-ukrainischer-kommunalbeziehungen.html"
)
SKEW_LIST_URL = (
    "https://skew.engagement-global.de/"
    "Liste-deutsch-ukrainischer-kommunalbeziehungen.html"
    "?stateDe=&stateUa=&type="
)
C4C_MARKERS_URL = (
    "https://cities4cities.eu/wp-content/themes/"
    "%5B2.0%5D%20sitegist-theme/markers/markers.json"
)
C4C_NEWS_API = "https://cities4cities.eu/wp-json/wp/v2/posts"
C4C_SITE = "https://cities4cities.eu/"
UA_HDR = (
    "hromada-strategy-collab/0.1 "
    "(+https://github.com/MaxSemenchuk/hromada-strategy-collab; research cache)"
)

CYR_TO_DE = {
    "а": "a",
    "б": "b",
    "в": "w",
    "г": "h",
    "ґ": "g",
    "д": "d",
    "е": "e",
    "є": "je",
    "ж": "sch",
    "з": "s",
    "и": "y",
    "і": "i",
    "ї": "ji",
    "й": "j",
    "к": "k",
    "л": "l",
    "м": "m",
    "н": "n",
    "о": "o",
    "п": "p",
    "р": "r",
    "с": "s",
    "т": "t",
    "у": "u",
    "ф": "f",
    "х": "ch",
    "ц": "z",
    "ч": "tsch",
    "ш": "sch",
    "щ": "schtsch",
    "ь": "",
    "ю": "ju",
    "я": "ja",
}

OBLAST_LAT_TO_UA = {
    "Lwiwska": "Львівська область",
    "Sakarpatska": "Закарпатська область",
    "Wolynska": "Волинська область",
    "Tscherkasska": "Черкаська область",
    "Saporiska": "Запорізька область",
    "Charkiwska": "Харківська область",
    "Chersonska": "Херсонська область",
    "Chmelnyzka": "Хмельницька область",
    "Chmelnytska": "Хмельницька область",
    "Tschernihiwska": "Чернігівська область",
    "Tscherniwezka": "Чернівецька область",
    "Tschernivezka": "Чернівецька область",
    "Dnipropetrowska": "Дніпропетровська область",
    "Donezka": "Донецька область",
    "Iwano-Frankiwska": "Івано-Франківська область",
    "Kyjiwska": "Київська область",
    "Kiyivska": "Київська область",
    "Kirowohradska": "Кіровоградська область",
    "Kirovohradska": "Кіровоградська область",
    "Luhanska": "Луганська область",
    "Mykolajiwska": "Миколаївська область",
    "Odeska": "Одеська область",
    "Poltawska": "Полтавська область",
    "Riwenska": "Рівненська область",
    "Riwnenska": "Рівненська область",
    "Sumska": "Сумська область",
    "Sumy": "Сумська область",
    "Ternopilska": "Тернопільська область",
    "Winnyzka": "Вінницька область",
    "Schytomyrska": "Житомирська область",
    "Kyjiw (Stadt)": None,  # city of Kyiv — not a hromada row
    "Autonome Republik Krim": None,
    "missing": None,
}

# Strategy-text patterns: «м. X, Country» / «місто X (Country)» / sister cues
STRATEGY_PARTNER = re.compile(
    r"(?:"
    r"(?:^|[\s,;«\"(])м(?:істо|\.)\s+([A-ZА-ЯІЇЄҐ][A-Za-zА-Яа-яІіЇїЄєҐґ'’\-]{2,})"
    r"(?:\s*\(([^)]{2,60})\))?"
    r"|"
    r"побратим(?:ство|и|ів)?\s+(?:з\s+|із\s+)?(?:м(?:істо|\.)\s+)?"
    r"([A-ZА-ЯІЇЄҐ][A-Za-zА-Яа-яІіЇїЄєҐґ'’\-]{2,})"
    r"(?:\s*\(([^)]{2,60})\))?"
    r"|"
    r"([A-ZА-ЯІЇЄҐ][A-Za-zА-Яа-яІіЇїЄєҐґ'’\-]{2,})\s*\((?:Німеччина|Польща|Швеція|"
    r"Болгарія|Данія|Франція|Італія|Нідерланди|Чехія|Словаччина|Румунія|"
    r"Литва|Латвія|Естонія|Австрія|Бельгія|Іспанія|Фінляндія|Угорщина|"
    r"Germany|Poland|Sweden|Bulgaria|Denmark|France|Italy|Netherlands)(?:,[^)]*)?\)"
    r")",
    re.I | re.M,
)

STRATEGY_STOP = {
    "дніпро",
    "львів",
    "київ",
    "одеса",
    "харків",
    "україна",
    "програма",
    "international",
    "vng",
    "союз",
    "мережа",
    "рада",
    "єс",
    "giz",
    "undp",
    "unicef",
    "юнісеф",
    "nefco",
    "проон",
    "метінвест",
    "works",
    "cowi",
    "one",
    "help",
    "euaci",
    "polaris",
}

# Well-known non-DE twin cities mentioned in strategies (when country paren missing)
KNOWN_CITY_COUNTRY = {
    "калмар": "SE",
    "kalmar": "SE",
    "велико-тирново": "BG",
    "великотирново": "BG",
    "veliko tarnovo": "BG",
    "ловіч": "PL",
    "łowicz": "PL",
    "lowicz": "PL",
    "вупперталь": "DE",
    "wuppertal": "DE",
    "бидгощ": "PL",
    "bydgoszcz": "PL",
}

COUNTRY_HINTS = {
    "німеччина": "DE",
    "germany": "DE",
    "польща": "PL",
    "poland": "PL",
    "швеція": "SE",
    "sweden": "SE",
    "болгарія": "BG",
    "bulgaria": "BG",
    "данія": "DK",
    "denmark": "DK",
    "франція": "FR",
    "france": "FR",
    "італія": "IT",
    "italy": "IT",
    "нідерланди": "NL",
    "netherlands": "NL",
    "чехія": "CZ",
    "словаччина": "SK",
    "румунія": "RO",
    "угорщина": "HU",
    "литва": "LT",
    "латвія": "LV",
    "естонія": "EE",
    "австрія": "AT",
    "бельгія": "BE",
    "іспанія": "ES",
    "фінляндія": "FI",
    "skew": "DE",
}


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


def norm_apos(s: str) -> str:
    return s.replace("'", "’").replace("ʼ", "’").replace("`", "’")


def norm_key(s: str) -> str:
    s = unescape(s).lower().replace("’", "").replace("'", "").replace("`", "")
    s = re.sub(r"\s*\([^)]*\)\s*", " ", s)
    return re.sub(r"[^a-zа-яіїєґ0-9]", "", s)


def to_de(s: str) -> str:
    s = norm_apos(s).lower()
    out: list[str] = []
    for ch in s:
        if ch in CYR_TO_DE:
            out.append(CYR_TO_DE[ch])
        elif "a" <= ch <= "z":
            out.append(ch)
    return "".join(out)


def _ssl_context() -> ssl.SSLContext:
    try:
        import certifi  # type: ignore

        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        ctx = ssl.create_default_context()
        # macOS Python.org builds often lack system CAs; curl still works.
        try:
            ctx.load_default_certs()
        except Exception:
            pass
        return ctx


def http_get(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA_HDR})
    try:
        with urllib.request.urlopen(req, context=_ssl_context(), timeout=90) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception as exc:
        # Fallback: system curl (same path as manual research fetches)
        import subprocess

        try:
            out = subprocess.check_output(
                ["curl", "-sL", "-A", UA_HDR, url],
                timeout=90,
            )
            return out.decode("utf-8", errors="replace")
        except Exception as curl_exc:
            raise RuntimeError(f"fetch failed ({exc}); curl fallback: {curl_exc}") from exc


# News-title patterns that name an UA↔foreign municipal pair.
# Do NOT use global IGNORECASE — it makes [A-Z] match lowercase junk ("brings").
C4C_PAIR_TITLE = re.compile(
    r"^\s*"
    r"(?:"
    # Swedish Kristianstad and Ukrainian Uman …
    r"(?i:swedish|french|german|polish|italian|danish|dutch|finnish|norwegian|austrian)\s+"
    r"(?P<f1>[A-ZÀ-ÖØ-Þ][\w’'\-]+(?:[\s\-][A-ZÀ-ÖØ-Þ][\w’'\-]+)?)"
    r".{0,50}?(?i:ukrainian)\s+(?P<u1>[A-ZА-ЯІЇЄҐ][\w’'\-]+)"
    r"|"
    # Swedish Ronneby … to Ternopil, its partner city
    r"(?i:swedish|french|german|polish|italian|danish|dutch|finnish|norwegian|austrian)\s+"
    r"(?P<f1b>[A-ZÀ-ÖØ-Þ][\w’'\-]+(?:[\s\-][A-ZÀ-ÖØ-Þ][\w’'\-]+)?)"
    r".{0,80}?\b(?i:to|with)\s+(?P<u1b>[A-ZА-ЯІЇЄҐ][\w’'\-]+)"
    r"|"
    # Bilohorodka and Bures-sur-Yvette have signed …
    r"(?P<a>[A-ZÀ-ÖØ-ÞА-ЯІЇЄҐ][\w’'\-]+(?:[\s\-][A-ZÀ-ÖØ-ÞА-ЯІЇЄҐ][\w’'\-]+)?)"
    r"\s+(?i:and)\s+"
    r"(?:(?i:the)\s+(?i:swedish|french|german|polish)\s+(?i:city)\s+(?i:of)\s+)?"
    r"(?P<b>[A-ZÀ-ÖØ-ÞА-ЯІЇЄҐ][\w’'\-]+(?:[\s\-][A-ZÀ-ÖØ-ÞА-ЯІЇЄҐ][\w’'\-]+)?)"
    r".{0,80}?(?i:signed|partnership|twin|cooperation|partner|deepen|become|sister)"
    r"|"
    # Delegation from Kassel visited Zhytomyr
    r"(?i:delegation)\s+(?i:from)\s+(?P<f3>[A-ZÀ-ÖØ-Þ][\w’'\-]+)"
    r".{0,40}?(?i:visited)\s+(?P<u3>[A-ZА-ЯІЇЄҐ][\w’'\-]+)"
    r")"
)

# UA place names that appear as the foreign slot in noisy titles — reject.
C4C_UA_STOP = {
    "ukraine",
    "ukrainian",
    "cities4cities",
    "municipal",
    "partnership",
    "partnerships",
    "cooperation",
    "agreement",
    "forum",
    "network",
    "entrepreneurship",
    "born",
    "new",
    "the",
}

C4C_TRAILING_JUNK = re.compile(
    r"\s+(?:have|has|had|are|is|become|became|deepen|deepens|signed|sign|and|–|-|:).*$",
    re.I,
)


def fetch_cities4cities(force: bool = False) -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
    if force or not CACHE_C4C_MARKERS.exists():
        print(f"Fetching {C4C_MARKERS_URL}")
        CACHE_C4C_MARKERS.write_text(http_get(C4C_MARKERS_URL), encoding="utf-8")
    else:
        print(f"Using cached {CACHE_C4C_MARKERS.relative_to(ROOT)}")
    if force or not CACHE_C4C_NEWS.exists():
        posts: list[dict] = []
        for page in range(1, 8):
            url = f"{C4C_NEWS_API}?per_page=20&page={page}&_fields=id,date,title,link"
            print(f"Fetching C4C news page {page}")
            try:
                raw = http_get(url)
                batch = json.loads(raw)
            except Exception as exc:
                print(f"  stop at page {page}: {exc}")
                break
            if not isinstance(batch, list) or not batch:
                break
            posts.extend(batch)
            if len(batch) < 20:
                break
        CACHE_C4C_NEWS.write_text(
            json.dumps(
                {
                    "fetched_at": datetime.now(timezone.utc).isoformat(),
                    "source": C4C_NEWS_API,
                    "post_count": len(posts),
                    "posts": posts,
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    else:
        print(f"Using cached {CACHE_C4C_NEWS.relative_to(ROOT)}")


def strip_html(s: str) -> str:
    s = re.sub(r"<[^>]+>", " ", s or "")
    return re.sub(r"\s+", " ", s).strip()


def parse_c4c_news_pairs() -> list[dict]:
    if not CACHE_C4C_NEWS.exists():
        return []
    payload = json.loads(CACHE_C4C_NEWS.read_text(encoding="utf-8"))
    out: list[dict] = []
    for post in payload.get("posts") or []:
        title = strip_html((post.get("title") or {}).get("rendered") or "")
        if not title:
            continue
        m = C4C_PAIR_TITLE.search(title)
        if not m:
            continue
        gd = m.groupdict()

        def clean(name: str | None) -> str | None:
            if not name:
                return None
            name = C4C_TRAILING_JUNK.sub("", name).strip(" –—-,:")
            if not name or name.lower() in C4C_UA_STOP:
                return None
            return name

        ua_name = foreign = None
        if gd.get("u1") and gd.get("f1"):
            ua_name, foreign = clean(gd["u1"]), clean(gd["f1"])
        elif gd.get("u1b") and gd.get("f1b"):
            ua_name, foreign = clean(gd["u1b"]), clean(gd["f1b"])
        elif gd.get("u3") and gd.get("f3"):
            ua_name, foreign = clean(gd["u3"]), clean(gd["f3"])
        elif gd.get("a") and gd.get("b"):
            a, b = clean(gd["a"]), clean(gd["b"])
            if not a or not b:
                continue
            # Decide which side is UA later in build via resolve; keep both candidates
            # Prefer left-as-UA for "X and Y signed" (common C4C style).
            ua_name, foreign = a, b
            # Special-case foreign-first titles: Franconville and Slavutych
            # Resolved in build by trying both sides.
        else:
            continue
        if not ua_name or not foreign:
            continue
        out.append(
            {
                "ua_name_en": ua_name,
                "partner_name": foreign,
                "alt_ua_name_en": foreign if gd.get("a") and gd.get("b") else None,
                "alt_partner_name": ua_name if gd.get("a") and gd.get("b") else None,
                "title": title,
                "date": (post.get("date") or "")[:10] or None,
                "source_url": post.get("link"),
                "source": "cities4cities",
                "confidence": "news_mention",
                "type": "Cities4Cities partnership",
            }
        )
    return out


def load_c4c_markers() -> list[dict]:
    if not CACHE_C4C_MARKERS.exists():
        return []
    data = json.loads(CACHE_C4C_MARKERS.read_text(encoding="utf-8"))
    return data if isinstance(data, list) else []


def resolve_latin_title(
    title: str,
    aliases: dict[str, dict],
    by_stem: dict[str, list[dict]],
    by_katottg: dict[str, dict],
) -> tuple[dict | None, str]:
    """Resolve Cities4Cities English title / news UA name to a hromada row."""
    key = norm_key(title)
    # drop boilerplate words
    key = key.replace("territorialcommunity", "").replace("municipality", "")
    key = key.replace("urbancouncil", "").replace("settlement", "").replace("rural", "")
    if not key:
        return None, "empty"
    alias = aliases.get(key)
    if alias:
        if "_katottg" in alias:
            row = by_katottg.get(alias["_katottg"])
            return (row, "alias") if row else (None, "alias_miss")
        return alias, "alias"
    # try stems / containment against transliterated UA shorts
    hits: list[dict] = []
    for st, rows in by_stem.items():
        if not st or len(st) < 4:
            continue
        if key == st or key.startswith(st) or st.startswith(key):
            hits.extend(rows)
        elif len(key) >= 5 and key in st:
            hits.extend(rows)
    uniq: dict[str, dict] = {}
    for h in hits:
        uniq[h.get("Katottg") or h["Name"]] = h
    hits = list(uniq.values())
    if len(hits) == 1:
        return hits[0], "latin"
    if len(hits) > 1:
        city = [h for h in hits if "міська" in (h.get("Name") or "")]
        if len(city) == 1:
            return city[0], "latin_city"
        return None, "multi"
    return None, "unmatched"


def fetch_skew(force: bool = False) -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
    if force or not CACHE_MAP.exists():
        print(f"Fetching {SKEW_MAP_URL}")
        CACHE_MAP.write_text(http_get(SKEW_MAP_URL), encoding="utf-8")
    else:
        print(f"Using cached {CACHE_MAP.relative_to(ROOT)}")
    if force or not CACHE_LIST.exists():
        print(f"Fetching {SKEW_LIST_URL}")
        CACHE_LIST.write_text(http_get(SKEW_LIST_URL), encoding="utf-8")
    else:
        print(f"Using cached {CACHE_LIST.relative_to(ROOT)}")


def parse_mapdata(html: str) -> dict:
    m = re.search(r"MAPDATA\s*=\s*", html)
    if not m:
        raise RuntimeError("MAPDATA not found in SKEW map HTML")
    start = m.end()
    if html[start] != "{":
        raise RuntimeError("MAPDATA does not start with '{'")
    depth = 0
    end = start
    for i in range(start, len(html)):
        ch = html[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    return json.loads(html[start:end])


def parse_list_types(html: str) -> dict[tuple[str, str], str]:
    """(de_name, ua_name) → partnership type from list table."""
    out: dict[tuple[str, str], str] = {}
    pat = re.compile(
        r'<td><a href="/Liste-deutsch-ukrainischer-kommunalbeziehungen\.html\?partner=\d+">'
        r"([^<]+)</a>\s*</td>\s*<td>([^<]*)</td>\s*<td>([^<]*)</td>\s*<td>([^<]*)</td>\s*"
        r'<td><a href="/Liste-deutsch-ukrainischer-kommunalbeziehungen\.html\?partner=\d+">'
        r"([^<]+)</a>",
        re.I,
    )
    for m in pat.finditer(html):
        de_name = unescape(m.group(1)).strip()
        ptype = unescape(m.group(3)).strip()
        ua_name = unescape(m.group(5)).strip()
        out[(de_name, ua_name)] = ptype
    return out


def extract_skew_edges() -> list[dict]:
    map_html = CACHE_MAP.read_text(encoding="utf-8")
    list_html = CACHE_LIST.read_text(encoding="utf-8")
    data = parse_mapdata(map_html)
    types = parse_list_types(list_html)
    edges: list[dict] = []
    for p in data.get("points") or []:
        if p.get("country") != "de":
            continue
        layer = p.get("layer") or ""
        mde = re.search(
            r'layer-partner">\s*<a href="[^"]*partner=(\d+)[^"]*">([^<]+)</a>'
            r"\s*<br>\s*([^<]+?)\s*</div>",
            layer,
            re.S,
        )
        if not mde:
            continue
        de_id, de_name, de_state = mde.groups()
        de_name = unescape(de_name).strip()
        de_state = unescape(de_state).strip()
        # Skip if the "German" card is actually non-DE (Poland etc. on map)
        if de_state in {"Polen", "Republik Moldau"} or "(Polen)" in de_name:
            continue
        for li in re.finditer(
            r'<li><a href="[^"]*partner=(\d+)[^"]*">([^<]+)</a>\s*\(seit\s*(\d+)\)'
            r"\s*<br>\s*([^<]+)</li>",
            layer,
        ):
            ua_id, ua_name, since, ua_ob = li.groups()
            ua_name = unescape(ua_name).strip()
            ua_ob = unescape(ua_ob).strip()
            # Triangle / utility noise on UA side
            if any(
                x in ua_name.lower()
                for x in ("vodokanal", "stadtwerke", "entwässerung", "wasserbetrieb")
            ):
                continue
            if ua_ob in {
                "Bayern",
                "Berlin",
                "Baden-Württemberg",
                "Nordrhein-Westfalen",
                "Sachsen",
                "Thüringen",
                "Polen",
                "Republik Moldau",
            }:
                continue
            ptype = types.get((de_name, ua_name)) or "Kommunalpartnerschaft"
            edges.append(
                {
                    "de_partner_id": int(de_id),
                    "de_name": de_name,
                    "de_state": de_state,
                    "ua_partner_id": int(ua_id),
                    "ua_name_de": ua_name,
                    "ua_oblast_lat": ua_ob,
                    "since": since,
                    "type": ptype,
                    "source": "skew",
                    "source_url": (
                        "https://skew.engagement-global.de/"
                        f"Liste-deutsch-ukrainischer-kommunalbeziehungen.html"
                        f"?partner={ua_id}"
                    ),
                }
            )
    CACHE_EDGES.write_text(
        json.dumps(
            {
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "map_url": SKEW_MAP_URL,
                "list_url": SKEW_LIST_URL,
                "edge_count": len(edges),
                "edges": edges,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return edges


def load_hromada_index() -> tuple[dict[str, dict], dict[str, dict], dict[str, list[dict]]]:
    rows = json.loads(HROMADAS.read_text(encoding="utf-8"))
    by_name: dict[str, dict] = {}
    by_katottg: dict[str, dict] = {}
    by_stem: dict[str, list[dict]] = defaultdict(list)

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
        code = (r.get("Katottg") or "").strip()
        if code:
            prev_c = by_katottg.get(code)
            if prev_c is None or richness(r) > richness(prev_c):
                by_katottg[code] = r
        short = short_name(name)
        stems = {to_de(short)}
        for suf in ("ська", "зька", "цька", "ька"):
            if short.endswith(suf) and len(short) > len(suf) + 2:
                stems.add(to_de(short[: -len(suf)]))
                break
        for st in stems:
            if st:
                by_stem[st].append(by_name[name])
    return by_name, by_katottg, by_stem


def load_aliases(by_name: dict[str, dict]) -> dict[str, dict]:
    raw = json.loads(ALIASES.read_text(encoding="utf-8"))
    out: dict[str, dict] = {}
    for k, v in raw.items():
        if k.startswith("_"):
            continue
        key = norm_key(k)
        if isinstance(v, dict):
            name = v.get("name")
            code = v.get("katottg")
            row = by_name.get(norm_apos(name or "")) if name else None
            if row is None and code:
                # resolve later via katottg in caller
                out[key] = {"_katottg": code}
            elif row:
                out[key] = row
            else:
                print(f"WARN alias miss: {k} → {v}")
        else:
            row = by_name.get(norm_apos(str(v)))
            if row:
                out[key] = row
            else:
                print(f"WARN alias miss: {k} → {v}")
    return out


def is_skip_ua_name(ua_name: str) -> str | None:
    low = ua_name.lower()
    if "(rajon)" in low or low.endswith("rajon") or ", rajon" in low:
        return "rajon"
    if any(x in low for x in ("vodokanal", "stadtwerke", "entwässerung", "wasserbetrieb")):
        return "non_hromada"
    if low.startswith("kyjiw-") or low.startswith("kijiw-") or low.startswith("kyiv-"):
        return "non_hromada"
    if "industrialnyj" in low:
        return "non_hromada"
    if low in {"kyjiw", "kiew", "kyiv"}:
        return "kyiv_city"
    return None


def resolve_ua(
    ua_name: str,
    oblast_lat: str | None,
    aliases: dict[str, dict],
    by_stem: dict[str, list[dict]],
    by_katottg: dict[str, dict],
) -> tuple[dict | None, str]:
    skip = is_skip_ua_name(ua_name)
    if skip:
        return None, skip

    key = norm_key(ua_name)
    alias = aliases.get(key)
    if alias:
        if "_katottg" in alias:
            row = by_katottg.get(alias["_katottg"])
            return (row, "alias") if row else (None, "alias_miss")
        return alias, "alias"

    ob_ua = OBLAST_LAT_TO_UA.get(oblast_lat or "") if oblast_lat else None
    stems = {key}
    if key.endswith("a") and len(key) > 4:
        stems.add(key[:-1])
    stems.add(key.replace("yj", "y"))
    stems.add(key.replace("ij", "yj"))

    hits: list[dict] = []
    for st in stems:
        for row in by_stem.get(st, []):
            if ob_ua and row.get("Oblast") != ob_ua:
                continue
            hits.append(row)
    if not hits and ob_ua:
        for st in stems:
            hits.extend(by_stem.get(st, []))

    uniq: dict[str, dict] = {}
    for h in hits:
        uniq[h.get("Katottg") or h["Name"]] = h
    hits = list(uniq.values())
    if len(hits) == 1:
        return hits[0], "translit"
    if len(hits) > 1:
        # Prefer міська
        city = [h for h in hits if "міська" in (h.get("Name") or "")]
        if len(city) == 1:
            return city[0], "translit_city"
        return None, "multi"
    return None, "unmatched"


def country_from_hint(text: str | None) -> str | None:
    if not text:
        return None
    low = text.lower()
    for k, code in COUNTRY_HINTS.items():
        if k in low:
            return code
    return None


def extract_strategy_partners(rows: list[dict]) -> dict[str, list[dict]]:
    """katottg/name → partner dicts from strategy free text."""
    out: dict[str, list[dict]] = defaultdict(list)
    fields = ("PartnersMentioned", "Projects", "MSSAgreements", "Strengths")
    for r in rows:
        name = norm_apos((r.get("Name") or "").strip())
        code = (r.get("Katottg") or "").strip() or name
        blob = "\n".join((r.get(f) or "") for f in fields)
        if not blob.strip():
            continue
        # count sister mentions even without named city
        if re.search(r"побратим|cities4cities|skew", blob, re.I):
            pass
        for m in STRATEGY_PARTNER.finditer(blob):
            city = (m.group(1) or m.group(3) or m.group(5) or "").strip()
            hint = m.group(2) or m.group(4) or ""
            if not city or len(city) < 3:
                continue
            if city.lower() in STRATEGY_STOP:
                continue
            # skip Ukrainian neighbour cues
            if re.search(r"громад|район|област|рда\b", hint, re.I):
                continue
            country = country_from_hint(hint) or country_from_hint(
                # only the match span + short paren — not a wide window (avoids
                # stealing DE from neighbouring SKEW/donor mentions)
                m.group(0)
            )
            if not country:
                country = KNOWN_CITY_COUNTRY.get(city.lower()) or KNOWN_CITY_COUNTRY.get(
                    city.lower().replace(" ", "")
                )
            if not country and not re.search(
                r"побратим|міжнарод|зарубіж|єс\b|eu\b|skew|cities4cities",
                m.group(0),
                re.I,
            ):
                window = blob[max(0, m.start() - 40) : m.end() + 40]
                if not re.search(
                    r"побратим|міжнарод|партнер|skew|cities4cities|меморандум",
                    window,
                    re.I,
                ):
                    continue
                country = country_from_hint(window)
            out[code].append(
                {
                    "partner_name": city,
                    "partner_country": country,
                    "partner_region": hint.strip() or None,
                    "type": "strategy_mention",
                    "since": None,
                    "source": "strategy",
                    "source_url": r.get("StrategyUrl"),
                    "confidence": "strategy_mention",
                    "quote": m.group(0)[:160],
                }
            )
    return out


def build_release(edges: list[dict]) -> None:
    by_name, by_katottg, by_stem = load_hromada_index()
    aliases = load_aliases(by_name)
    rows = list(by_name.values())

    stats: dict[str, int] = defaultdict(int)
    by_hromada: dict[str, dict] = {}
    unmatched: list[dict] = []

    for e in edges:
        row, how = resolve_ua(
            e["ua_name_de"],
            e.get("ua_oblast_lat"),
            aliases,
            by_stem,
            by_katottg,
        )
        stats[how] += 1
        if not row:
            unmatched.append(
                {
                    "ua_name_de": e["ua_name_de"],
                    "ua_oblast_lat": e.get("ua_oblast_lat"),
                    "de_name": e["de_name"],
                    "reason": how,
                }
            )
            continue
        code = (row.get("Katottg") or row["Name"]).strip()
        entry = by_hromada.setdefault(
            code,
            {
                "name": row["Name"],
                "short": short_name(row["Name"]),
                "katottg": row.get("Katottg"),
                "oblast": row.get("Oblast"),
                "partners": [],
            },
        )
        partner = {
            "partner_name": e["de_name"],
            "partner_country": "DE",
            "partner_region": e.get("de_state"),
            "type": e.get("type") or "Kommunalpartnerschaft",
            "since": e.get("since"),
            "source": "skew",
            "source_url": e.get("source_url"),
            "confidence": "registry",
            "ua_name_de": e["ua_name_de"],
            "match": how,
        }
        # de-dupe by partner_name + since
        key = (partner["partner_name"], partner["since"], partner["type"])
        existing = {
            (p["partner_name"], p.get("since"), p.get("type")) for p in entry["partners"]
        }
        if key not in existing:
            entry["partners"].append(partner)

    # Strategy mentions (non-DE + DE named in text)
    strategy = extract_strategy_partners(rows)
    strategy_added = 0
    for code, partners in strategy.items():
        row = by_katottg.get(code) or by_name.get(norm_apos(code))
        if not row:
            # code may already be name
            continue
        hcode = (row.get("Katottg") or row["Name"]).strip()
        entry = by_hromada.setdefault(
            hcode,
            {
                "name": row["Name"],
                "short": short_name(row["Name"]),
                "katottg": row.get("Katottg"),
                "oblast": row.get("Oblast"),
                "partners": [],
            },
        )
        have = {(p["partner_name"].lower(), p.get("partner_country")) for p in entry["partners"]}
        for p in partners:
            k = (p["partner_name"].lower(), p.get("partner_country"))
            # skip if same DE city already from SKEW
            if any(
                p["partner_name"].lower() == existing["partner_name"].lower()
                for existing in entry["partners"]
            ):
                continue
            if k in have:
                continue
            entry["partners"].append(p)
            have.add(k)
            strategy_added += 1

    # Cities4Cities: news-title pairs + markers profile URLs
    c4c_pairs = parse_c4c_news_pairs()
    c4c_added = 0
    c4c_unmatched: list[dict] = []
    for pair in c4c_pairs:
        row, how = resolve_latin_title(
            pair["ua_name_en"], aliases, by_stem, by_katottg
        )
        partner_name = pair["partner_name"]
        if not row and pair.get("alt_ua_name_en"):
            row, how = resolve_latin_title(
                pair["alt_ua_name_en"], aliases, by_stem, by_katottg
            )
            if row:
                partner_name = pair.get("alt_partner_name") or pair["ua_name_en"]
        if not row:
            c4c_unmatched.append({**pair, "reason": how})
            continue
        hcode = (row.get("Katottg") or row["Name"]).strip()
        entry = by_hromada.setdefault(
            hcode,
            {
                "name": row["Name"],
                "short": short_name(row["Name"]),
                "katottg": row.get("Katottg"),
                "oblast": row.get("Oblast"),
                "partners": [],
            },
        )
        partner = {
            "partner_name": partner_name,
            "partner_country": None,
            "partner_region": None,
            "type": pair.get("type") or "Cities4Cities partnership",
            "since": (pair.get("date") or "")[:4] or None,
            "source": "cities4cities",
            "source_url": pair.get("source_url"),
            "confidence": "news_mention",
            "quote": pair.get("title"),
            "match": how,
        }
        if any(
            p["partner_name"].lower() == partner["partner_name"].lower()
            for p in entry["partners"]
        ):
            # Prefer upgrading source_url / keep existing; mark also on c4c
            continue
        entry["partners"].append(partner)
        c4c_added += 1

    c4c_listed = 0
    for marker in load_c4c_markers():
        title = marker.get("title") or ""
        link = marker.get("link")
        row, how = resolve_latin_title(title, aliases, by_stem, by_katottg)
        if not row:
            continue
        hcode = (row.get("Katottg") or row["Name"]).strip()
        entry = by_hromada.setdefault(
            hcode,
            {
                "name": row["Name"],
                "short": short_name(row["Name"]),
                "katottg": row.get("Katottg"),
                "oblast": row.get("Oblast"),
                "partners": [],
            },
        )
        if link and not entry.get("c4c_url"):
            entry["c4c_url"] = link
            c4c_listed += 1
        elif link:
            entry.setdefault("c4c_url", link)

    # decentralization.ua Ministry partnership map (yarn partnership-map) —
    # merged additively. SKEW's German partner names are Latin/German-spelled;
    # decentralization.ua's are Cyrillic transliterations of ALL countries —
    # cross-alphabet string matching isn't reliable enough to auto-dedupe, so
    # for the DE subset specifically (the only country where both sources
    # can legitimately name the SAME city) we use a small manually-curated
    # pair list (data/sources/twinning-de-duplicate-pairs.json, 38 pairs
    # verified 2026-09-02) to tag `duplicate_of_skew` rather than either
    # blindly merging or blindly keeping both as distinct. Everything outside
    # that curated list (all non-DE countries, and DE rows not in the list)
    # is treated as genuinely additional. See docs/ua-eu-twinning.md for the
    # full caveat and the Poltava↔Kalmar counter-example (present via SKEW,
    # absent from partnership-map.json — sources also miss cases the other
    # has, so "additive" here does not mean "complete union" either).
    decentralization_added = 0
    hromadas_in_both = 0
    de_duplicates_tagged = 0
    de_dupe_lookup: dict[tuple[str, str], str] = {}
    if DE_DUPLICATE_PAIRS.exists():
        for pair in json.loads(DE_DUPLICATE_PAIRS.read_text(encoding="utf-8"))["pairs"]:
            de_dupe_lookup[(pair["katottg"], pair["dm_name"])] = pair["skew_name"]
    if PARTNERSHIP_MAP.exists():
        dm_payload = json.loads(PARTNERSHIP_MAP.read_text(encoding="utf-8"))
        for h in dm_payload.get("hromadas") or []:
            code = (h.get("katottg") or "").strip()
            if not code:
                continue
            row = by_katottg.get(code)
            if not row:
                continue
            hcode = (row.get("Katottg") or row["Name"]).strip()
            if hcode in by_hromada:
                hromadas_in_both += 1
            entry = by_hromada.setdefault(
                hcode,
                {
                    "name": row["Name"],
                    "short": short_name(row["Name"]),
                    "katottg": row.get("Katottg"),
                    "oblast": row.get("Oblast"),
                    "partners": [],
                },
            )
            for p in h.get("partners") or []:
                dupe_of = de_dupe_lookup.get((code, p.get("partner_name")))
                partner = {
                    "partner_name": p.get("partner_name"),
                    "partner_country": p.get("partner_country"),
                    "partner_region": None,
                    "type": "Municipal partnership",
                    "since": None,
                    "source": "decentralization_ua",
                    "source_url": (
                        "https://decentralization.ua/newgromada/"
                        f"{h.get('decentralization_id') or ''}"
                    ),
                    "confidence": "registry",
                }
                if dupe_of:
                    partner["duplicate_of_skew"] = dupe_of
                    de_duplicates_tagged += 1
                entry["partners"].append(partner)
                decentralization_added += 1

    hromadas = sorted(
        by_hromada.values(),
        key=lambda h: (-len(h["partners"]), h["short"]),
    )
    for h in hromadas:
        h["partner_count"] = len(h["partners"])
        h["distinct_partner_count"] = sum(
            1 for p in h["partners"] if not p.get("duplicate_of_skew")
        )

    generated = datetime.now(timezone.utc).isoformat()
    linked_edges = sum(1 for h in hromadas for p in h["partners"] if p["source"] == "skew")
    c4c_partner_rows = sum(
        1 for h in hromadas for p in h["partners"] if p["source"] == "cities4cities"
    )
    payload = {
        "generatedAt": generated,
        "warning": (
            "UA–EU twinning layer — separate from domestic МСС. "
            "SKEW links are registry-sourced (DE–UA); Cities4Cities pairs come from "
            "news titles (hypotheses); strategy mentions are hypotheses; "
            "decentralization_ua entries are Ministry-verified. Non-DE decentralization_ua "
            "rows are additive (SKEW is DE-only, so no overlap is possible). DE-country "
            "decentralization_ua rows ARE checked against SKEW via a manually-curated "
            "pair list (data/sources/twinning-de-duplicate-pairs.json, 38 pairs) — a "
            "matched row carries partner.duplicate_of_skew (the SKEW name it duplicates); "
            "use hromada.distinct_partner_count, not partner_count, when you need a "
            "non-inflated total. Un-tagged DE rows are genuinely additional partners not "
            "yet checked/confirmed either way for a handful of low-confidence cases — see "
            "docs/ua-eu-twinning.md. None of the sources here is complete on its own — "
            "each has confirmed cases the others miss. "
            "c4c_url marks listing in the C4C municipality database (seeking partners), "
            "not a confirmed twinning. Not folded into matching score."
        ),
        "sources": [
            {
                "id": "skew",
                "name": "SKEW German–Ukrainian municipal partnerships",
                "url": SKEW_MAP_URL,
                "list_url": SKEW_LIST_URL,
            },
            {
                "id": "cities4cities",
                "name": "Cities4Cities news pairs + municipality markers",
                "url": C4C_SITE,
                "markers_url": C4C_MARKERS_URL,
            },
            {
                "id": "strategy",
                "name": "Named foreign partners in strategy extractions",
                "path": "data/releases/hromadas.json",
            },
            {
                "id": "decentralization_ua",
                "name": "Ministry of Communities and Territories Development — partnership map",
                "url": "https://decentralization.ua/twincities",
                "path": "data/releases/partnership-map.json",
            },
        ],
        "coverage": {
            "skew_edges_raw": len(edges),
            "skew_edges_linked": linked_edges,
            "hromadas_with_partners": len(hromadas),
            "strategy_partners_added": strategy_added,
            "cities4cities_partners_added": c4c_added,
            "cities4cities_partner_rows": c4c_partner_rows,
            "cities4cities_listed": c4c_listed,
            "cities4cities_news_pairs_raw": len(c4c_pairs),
            "cities4cities_news_unmatched": len(c4c_unmatched),
            "unmatched_skew": len(unmatched),
            "resolve_stats": dict(stats),
            "decentralization_ua_partners_added": decentralization_added,
            "hromadas_in_both_skew_and_decentralization": hromadas_in_both,
            "decentralization_ua_de_duplicates_tagged": de_duplicates_tagged,
        },
        "hromadas": hromadas,
        "unmatched": unmatched[:200],
        "unmatched_cities4cities": c4c_unmatched[:50],
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    MANIFEST.write_text(
        json.dumps(
            {
                "generatedAt": generated,
                "hromadasWithPartners": len(hromadas),
                "skewEdgesLinked": linked_edges,
                "skewEdgesRaw": len(edges),
                "strategyPartnersAdded": strategy_added,
                "cities4citiesPartnersAdded": c4c_added,
                "cities4citiesListed": c4c_listed,
                "unmatchedSkew": len(unmatched),
                "method": "SKEW + Cities4Cities news/markers + strategy mentions; aliases in twinning-name-aliases.json",
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
                "caveat": "UA–EU twinning — SKEW + Cities4Cities news + strategy. Not domestic МСС.",
                "hromadaCount": len(hromadas),
                "skewLinked": linked_edges,
                "cities4citiesPartners": c4c_added,
                "cities4citiesListed": c4c_listed,
                "top": [
                    {
                        "short": h["short"],
                        "oblast": h.get("oblast"),
                        "partner_count": h["partner_count"],
                        "partners": [
                            f"{p['partner_name']}"
                            + (f" ({p['partner_country']})" if p.get("partner_country") else "")
                            for p in h["partners"][:5]
                        ],
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
        f"Wrote {OUT.relative_to(ROOT)} — {len(hromadas)} hromadas, "
        f"{linked_edges}/{len(edges)} SKEW edges linked, "
        f"+{strategy_added} strategy, +{c4c_added} C4C news, "
        f"+{decentralization_added} decentralization.ua "
        f"({de_duplicates_tagged} tagged duplicate_of_skew; "
        f"{hromadas_in_both} hromadas overlap with SKEW/strategy/C4C); "
        f"C4C listed={c4c_listed}; unmatched_skew={len(unmatched)}"
    )


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--offline", action="store_true", help="Do not fetch; use HTML cache")
    ap.add_argument("--fetch-only", action="store_true", help="Only refresh SKEW cache")
    ap.add_argument("--force-fetch", action="store_true", help="Re-download even if cache exists")
    args = ap.parse_args()

    if args.offline:
        if not CACHE_MAP.exists() or not CACHE_LIST.exists():
            raise SystemExit(
                "No SKEW HTML under data/cache/twinning/ — run without --offline first"
            )
    else:
        fetch_skew(force=args.force_fetch)
        fetch_cities4cities(force=args.force_fetch)

    edges = extract_skew_edges()
    print(f"Parsed {len(edges)} SKEW edges → {CACHE_EDGES.relative_to(ROOT)}")
    if CACHE_C4C_MARKERS.exists() or CACHE_C4C_NEWS.exists():
        print(
            f"C4C cache: markers="
            f"{'yes' if CACHE_C4C_MARKERS.exists() else 'no'}, "
            f"news={'yes' if CACHE_C4C_NEWS.exists() else 'no'}"
        )

    if args.fetch_only:
        return
    build_release(edges)


if __name__ == "__main__":
    main()
