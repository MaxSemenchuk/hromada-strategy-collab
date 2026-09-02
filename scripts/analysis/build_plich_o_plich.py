#!/usr/bin/env python3
"""Пліч-о-Пліч — domestic hromada-partnership layer, mined from news text.

"Пліч-о-Пліч: згуртовані громади" (plich-o-plich.gov.ua) is the national
project pairing "rear" (тилові) hromadas with "forpost" (прифронтові/border)
hromadas for mutual support. It looks like it should have a clean pairs
table, but it doesn't: the "Учасники проєкту" oblast pages render their one
headline pair as pre-vectorized SVG (text converted to `<path>` outlines at
export time — confirmed by inspecting the live DOM: zero `<text>`/`<img>`
nodes anywhere in that widget, only `<path>` shapes) so it isn't scrapable as
text, and it shows only one example pair per oblast anyway, not the full set.

The actual comprehensive source is the news feed (`/novyny/`, ~52 pages,
Dec 2024–present, real server-rendered HTML): every hromada-to-hromada
activity gets its own article, and article bodies name both partners in
plain Ukrainian text. This script crawls that feed and regex-extracts
"Adjective + громада" mentions (any grammatical case — matched via the
ськ/зьк/цьк/ьк adjective-suffix marker, which sits before the case ending),
resolves each against the canonical `hromadas.json` registry by name stem
(disambiguating homonyms using oblast names mentioned in the same article),
and builds a co-occurrence edge per article (all resolved hromadas named in
one article ↔ one another).

This is NOT an authoritative pairs registry — it's a lower-bound, best-effort
extraction:
  - Articles that name a partner only as a bare town noun without the word
    "громада" attached nearby (e.g. a title like "Мена — Миронівка" whose
    body only ever says "на Миронівщину") are under-captured: whichever side
    IS attached to "громада" resolves normally, the other is missed.
  - Homonyms (multiple hromadas sharing a name across oblasts) that can't be
    disambiguated by an oblast hint in the same article are left unresolved
    rather than guessed — see docs/plich-o-plich.md and the KATOTTG homonym
    note in project memory.

Usage:
  yarn plich-o-plich                 # fetch (cached) + build release
  yarn plich-o-plich --offline       # build from cache only, no network
  yarn plich-o-plich --force-refresh # ignore cache, re-fetch everything
"""

from __future__ import annotations

import argparse
import json
import re
import ssl
import urllib.error
import urllib.request
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / "data" / "cache" / "plich-o-plich"
CACHE_LISTING = CACHE / "listing.json"
CACHE_ARTICLES = CACHE / "articles.json"
HROMADAS = ROOT / "data" / "releases" / "hromadas.json"
OUT = ROOT / "data" / "releases" / "plich-o-plich.json"
MANIFEST = ROOT / "data" / "releases" / "plich-o-plich.manifest.json"

BASE = "https://www.plich-o-plich.gov.ua"
NEWS_URL = f"{BASE}/novyny/"
NEWS_PAGE_URL = f"{BASE}/novyny/page/{{n}}/"
UA_HDR = "hromada-strategy-collab/0.1 (+https://github.com/MaxSemenchuk/hromada-strategy-collab; research cache)"
MAX_WORKERS = 8

# Common generic adjectives that precede "громада" without naming a specific
# hromada — filtered out before resolution attempts.
STOP_ADJ = {
    "місцева", "місцеві", "прифронтова", "прифронтові", "тилова", "тилові",
    "наша", "наші", "ця", "ці", "така", "такі", "кожна", "кожні",
    "обидві", "обидва", "деякі", "інша", "інші", "усі", "всі",
    "партнерська", "партнерські", "українська", "українські",
    "згуртована", "згуртовані", "нова", "нові", "одна", "приймаюча",
}

# Colloquial oblast-name stems (genitive/adjectival forms all share this
# prefix before the case ending) → canonical Oblast string in hromadas.json.
COLLOQUIAL_OBLAST = {
    "донеччин": "Донецька область",
    "тернопільщин": "Тернопільська область",
    "львівщин": "Львівська область",
    "харківщин": "Харківська область",
    "сумщин": "Сумська область",
    "полтавщин": "Полтавська область",
    "луганщин": "Луганська область",
    "чернігівщин": "Чернігівська область",
    "херсонщин": "Херсонська область",
    "запоріжж": "Запорізька область",
    "запорізьк": "Запорізька область",
    "одещин": "Одеська область",
    "миколаївщин": "Миколаївська область",
    "волинщин": "Волинська область",
    "рівненщин": "Рівненська область",
    "хмельниччин": "Хмельницька область",
    "вінниччин": "Вінницька область",
    "черкащин": "Черкаська область",
    "кіровоградщин": "Кіровоградська область",
    "житомирщин": "Житомирська область",
    "київщин": "Київська область",
    "закарпатт": "Закарпатська область",
    "буковин": "Чернівецька область",
    "чернівеччин": "Чернівецька область",
    "прикарпатт": "Івано-Франківська область",
    "франківщин": "Івано-Франківська область",
    "дніпропетровщин": "Дніпропетровська область",
    "дніпрощин": "Дніпропетровська область",
}

ADJ = r"[А-ЯЇЄҐІ][а-яіїєґ'’ʼ\-]{2,}"
ADJ_CHAIN_GROMADA_RE = re.compile(
    rf"((?:{ADJ}(?:\s*,\s*|\s+та\s+|\s+і\s+))*{ADJ})\s+громад(?:а|и|у|ою|і|ах|ами)\b"
)
CHAIN_SPLIT_RE = re.compile(r"\s*,\s*|\s+та\s+|\s+і\s+")
ADJ_SUFFIX_MARKER_RE = re.compile(r"(ськ|зьк|цьк|ьк)")


def _ssl_context() -> ssl.SSLContext:
    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        ctx = ssl.create_default_context()
        try:
            ctx.load_default_certs()
        except Exception:
            pass
        return ctx


def http_get(url: str, timeout: int = 30) -> str | None:
    req = urllib.request.Request(url, headers={"User-Agent": UA_HDR})
    try:
        with urllib.request.urlopen(req, context=_ssl_context(), timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
        print(f"  WARN fetch failed {url}: {e}")
        return None


def discover_page_count() -> int:
    html = http_get(NEWS_URL)
    if not html:
        return 1
    soup = BeautifulSoup(html, "html.parser")
    nums = [int(m.group(1)) for a in soup.find_all("a", href=True) if (m := re.search(r"/page/(\d+)/", a["href"]))]
    return max(nums) if nums else 1


def crawl_listing(force: bool = False) -> list[dict]:
    if CACHE_LISTING.exists() and not force:
        return json.loads(CACHE_LISTING.read_text(encoding="utf-8"))

    CACHE.mkdir(parents=True, exist_ok=True)
    n_pages = discover_page_count()
    print(f"Discovered {n_pages} news listing pages")

    urls = [NEWS_URL] + [NEWS_PAGE_URL.format(n=n) for n in range(2, n_pages + 1)]
    articles: dict[str, dict] = {}

    def fetch_page(url: str) -> list[dict]:
        html = http_get(url)
        if not html:
            return []
        soup = BeautifulSoup(html, "html.parser")
        main = soup.find("main")
        if not main:
            return []
        out = []
        for art in main.find_all("article"):
            h2 = art.find("h2", class_="entry-title")
            a = h2.find("a") if h2 else None
            time_el = art.find("time", class_="entry-date")
            if not a or not a.get("href"):
                continue
            out.append(
                {
                    "url": a["href"],
                    "title": a.get_text(strip=True),
                    "date": time_el["datetime"] if time_el and time_el.get("datetime") else None,
                }
            )
        return out

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futures = {ex.submit(fetch_page, u): u for u in urls}
        for i, fut in enumerate(as_completed(futures), 1):
            for row in fut.result():
                articles.setdefault(row["url"], row)
            if i % 10 == 0:
                print(f"  listing pages fetched: {i}/{len(urls)}")

    rows = sorted(articles.values(), key=lambda r: r["date"] or "", reverse=True)
    CACHE_LISTING.write_text(json.dumps(rows, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"Listing: {len(rows)} unique articles across {n_pages} pages")
    return rows


def crawl_articles(listing: list[dict], force: bool = False) -> dict[str, str]:
    cached: dict[str, str] = {}
    if CACHE_ARTICLES.exists() and not force:
        cached = json.loads(CACHE_ARTICLES.read_text(encoding="utf-8"))

    todo = [row["url"] for row in listing if row["url"] not in cached]
    if todo:
        print(f"Fetching {len(todo)} article bodies…")

        def fetch_body(url: str) -> tuple[str, str]:
            html = http_get(url)
            if not html:
                return url, ""
            soup = BeautifulSoup(html, "html.parser")
            content = soup.find("div", class_="entry-content")
            return url, content.get_text(" ", strip=True) if content else ""

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
            futures = {ex.submit(fetch_body, u): u for u in todo}
            for i, fut in enumerate(as_completed(futures), 1):
                url, text = fut.result()
                cached[url] = text
                if i % 25 == 0:
                    print(f"  article bodies fetched: {i}/{len(todo)}")

        CACHE.mkdir(parents=True, exist_ok=True)
        CACHE_ARTICLES.write_text(json.dumps(cached, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return cached


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


def adj_stem(word: str) -> str:
    """Stem an Ukrainian adjective past its ськ/зьк/цьк/ьк marker, dropping
    the (case-dependent) tail after it — works across nominative/genitive/
    dative/accusative/instrumental forms since the marker sits before the
    case ending in all of them."""
    w = norm_apos(word).lower().replace("’", "")
    matches = list(ADJ_SUFFIX_MARKER_RE.finditer(w))
    if matches:
        return w[: matches[-1].end()]
    # Fallback for non-ськ adjectives (e.g. "Ювілейна"): strip a trailing
    # single-vowel case ending.
    if len(w) > 4 and w[-1] in "аиіуюоеїй":
        return w[:-1]
    return w


def load_hromada_index() -> tuple[dict[str, list[dict]], dict[str, dict]]:
    rows = json.loads(HROMADAS.read_text(encoding="utf-8"))
    by_stem: dict[str, list[dict]] = defaultdict(list)
    by_katottg: dict[str, dict] = {}
    for r in rows:
        name = norm_apos((r.get("Name") or "").strip())
        if not name:
            continue
        code = (r.get("Katottg") or "").strip()
        rec = {"Name": name, "Katottg": code, "Oblast": r.get("Oblast") or ""}
        if code:
            by_katottg[code] = rec
        adj = short_name(name)
        by_stem[adj_stem(adj)].append(rec)
    return by_stem, by_katottg


def find_oblast_hints(text: str) -> set[str]:
    low = text.lower()
    return {oblast for stem, oblast in COLLOQUIAL_OBLAST.items() if stem in low}


def resolve_mention(raw: str, oblast_hints: set[str], by_stem: dict[str, list[dict]]) -> tuple[dict | None, str, list[str]]:
    stem = adj_stem(raw)
    hits = by_stem.get(stem, [])
    uniq: dict[str, dict] = {h["Katottg"] or h["Name"]: h for h in hits}
    hits = list(uniq.values())
    if not hits:
        return None, "unmatched", []
    if len(hits) == 1:
        return hits[0], "unique", []
    if oblast_hints:
        filtered = [h for h in hits if h["Oblast"] in oblast_hints]
        if len(filtered) == 1:
            return filtered[0], "oblast_hint", []
    city = [h for h in hits if "міська" in h["Name"]]
    if len(city) == 1 and not oblast_hints:
        return city[0], "prefer_city", [h["Name"] for h in hits]
    return None, "ambiguous", [h["Name"] for h in hits]


def extract_mentions(text: str) -> list[str]:
    out: list[str] = []
    for m in ADJ_CHAIN_GROMADA_RE.finditer(text):
        chain = m.group(1)
        for tok in CHAIN_SPLIT_RE.split(chain):
            tok = tok.strip()
            if tok and tok.lower() not in STOP_ADJ:
                out.append(tok)
    return out


def build_release(listing: list[dict], bodies: dict[str, str]) -> None:
    by_stem, by_katottg = load_hromada_index()

    articles_out = []
    edge_counts: dict[tuple[str, str], dict] = {}
    unmatched_counter: dict[str, int] = defaultdict(int)
    ambiguous_counter: dict[str, int] = defaultdict(int)

    for row in listing:
        body = bodies.get(row["url"], "")
        full_text = f"{row['title']} {body}"
        hints = find_oblast_hints(full_text)
        raw_mentions = extract_mentions(body) or extract_mentions(row["title"])

        resolved: list[dict] = []
        seen_codes: set[str] = set()
        for raw in raw_mentions:
            rec, match_type, candidates = resolve_mention(raw, hints, by_stem)
            if rec:
                code = rec["Katottg"] or rec["Name"]
                if code in seen_codes:
                    continue
                seen_codes.add(code)
                resolved.append(
                    {
                        "raw": raw,
                        "name": rec["Name"],
                        "katottg": rec["Katottg"] or None,
                        "oblast": rec["Oblast"],
                        "match_type": match_type,
                    }
                )
            elif match_type == "unmatched":
                unmatched_counter[raw] += 1
            elif match_type == "ambiguous":
                ambiguous_counter[raw] += 1
                resolved.append(
                    {"raw": raw, "name": None, "katottg": None, "oblast": None, "match_type": "ambiguous", "candidates": candidates}
                )

        if not resolved:
            continue

        articles_out.append(
            {
                "url": row["url"],
                "title": row["title"],
                "date": row["date"],
                "oblast_hints": sorted(hints),
                "hromadas": resolved,
            }
        )

        resolved_codes = sorted({r["katottg"] or r["name"] for r in resolved if r["katottg"]})
        article_size = len(resolved_codes)
        for i in range(len(resolved_codes)):
            for j in range(i + 1, len(resolved_codes)):
                key = (resolved_codes[i], resolved_codes[j])
                edge = edge_counts.setdefault(
                    key,
                    {
                        "a_katottg": key[0],
                        "a_name": by_katottg.get(key[0], {}).get("Name"),
                        "a_oblast": by_katottg.get(key[0], {}).get("Oblast"),
                        "b_katottg": key[1],
                        "b_name": by_katottg.get(key[1], {}).get("Name"),
                        "b_oblast": by_katottg.get(key[1], {}).get("Oblast"),
                        "article_count": 0,
                        "min_article_hromada_count": article_size,
                        "first_seen": row["date"],
                        "last_seen": row["date"],
                        "source_urls": [],
                    },
                )
                edge["article_count"] += 1
                edge["min_article_hromada_count"] = min(edge["min_article_hromada_count"], article_size)
                if row["date"]:
                    if not edge["first_seen"] or row["date"] < edge["first_seen"]:
                        edge["first_seen"] = row["date"]
                    if not edge["last_seen"] or row["date"] > edge["last_seen"]:
                        edge["last_seen"] = row["date"]
                if len(edge["source_urls"]) < 10:
                    edge["source_urls"].append(row["url"])

    for edge in edge_counts.values():
        # "Bilateral" = at least one contributing article named exactly this
        # pair and nobody else — a direct report, not a multi-hromada
        # roundup where co-mention doesn't imply a claimed partnership.
        edge["bilateral_confirmed"] = edge["min_article_hromada_count"] == 2

    edges = sorted(
        edge_counts.values(),
        key=lambda e: (not e["bilateral_confirmed"], -e["article_count"], e["a_name"] or ""),
    )

    top_unmatched = sorted(unmatched_counter.items(), key=lambda kv: -kv[1])[:40]
    top_ambiguous = sorted(ambiguous_counter.items(), key=lambda kv: -kv[1])[:40]

    payload = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": {
            "project": "Пліч-о-Пліч: згуртовані громади (Мінрозвитку/Кулеба office)",
            "site": BASE,
            "method": (
                "The oblast 'Учасники проєкту' pages render their pairs as pre-outlined SVG "
                "paths (text converted to vector shapes at design-export time, confirmed via "
                "live DOM inspection — zero <text>/<img>/<canvas> nodes carry the pair names) "
                "so they are NOT machine-readable, and show only one headline pair per oblast "
                "anyway. This dataset instead regex-extracts 'Adjective + громада' mentions "
                "(any grammatical case) from the /novyny/ news feed article bodies, resolves "
                "each against hromadas.json by name stem, and treats hromadas co-named in the "
                "same article as a partnership edge."
            ),
            "notes": [
                "NOT an authoritative pairs registry — a lower-bound, best-effort text-mining "
                "extraction. Articles that name a partner only as a bare town/raion noun "
                "without the word 'громада' nearby (e.g. '...візит на Миронівщину') under-"
                "capture that side; the attached side still resolves normally.",
                "Homonym hromada names (same adjective, different oblast) are left unresolved "
                "(match_type='ambiguous') rather than guessed when no oblast hint is present "
                "in the same article — see the KATOTTG homonym pattern in project notes.",
                "An edge is 'two hromadas named in the same article', not a verified bilateral "
                "memorandum — trilateral/multilateral articles (3+ hromadas) produce one edge "
                "per pair, all attributed to that single article. A few roundup articles name "
                "5-15 forpost hromadas at once (e.g. a summer-camp or memoranda-signing digest) "
                "— those produce a fully-connected clique of edges among everyone mentioned, "
                "which is NOT a claim that each of them partners with all the others. Use "
                "'bilateral_confirmed' (true only if some article named exactly that pair and "
                "no one else) to filter to the higher-confidence direct-report edges; the rest "
                "are co-mention-only.",
                f"{sum(unmatched_counter.values())} raw mentions across the corpus never "
                "matched any hromada stem (foreign partners, oblast/raion names misfired as "
                "adjectives, OCR-adjacent noise) — see top_unmatched_mentions below.",
                f"{sum(ambiguous_counter.values())} raw mentions matched >1 hromada with no "
                "oblast hint to disambiguate — see top_ambiguous_mentions below.",
            ],
        },
        "coverage": {
            "articles_crawled": len(listing),
            "articles_with_resolved_hromada": len(articles_out),
            "edges_total": len(edges),
            "edges_bilateral_confirmed": sum(1 for e in edges if e["bilateral_confirmed"]),
            "edges_comention_only": sum(1 for e in edges if not e["bilateral_confirmed"]),
            "unique_hromadas_in_edges": len({e["a_katottg"] for e in edges} | {e["b_katottg"] for e in edges}),
        },
        "top_unmatched_mentions": [{"raw": k, "count": v} for k, v in top_unmatched],
        "top_ambiguous_mentions": [{"raw": k, "count": v} for k, v in top_ambiguous],
        "edges": edges,
        "articles": articles_out,
    }

    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    MANIFEST.write_text(
        json.dumps(
            {
                "file": "plich-o-plich.json",
                "generated_at": payload["generated_at"],
                "coverage": payload["coverage"],
                "source": payload["source"],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(
        f"Wrote {OUT.relative_to(ROOT)} — {len(edges)} edges "
        f"({payload['coverage']['edges_bilateral_confirmed']} bilateral-confirmed, "
        f"{payload['coverage']['edges_comention_only']} co-mention-only) from "
        f"{len(articles_out)}/{len(listing)} articles, "
        f"{payload['coverage']['unique_hromadas_in_edges']} unique hromadas; "
        f"{sum(unmatched_counter.values())} unmatched, {sum(ambiguous_counter.values())} ambiguous mentions"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--offline", action="store_true", help="build from cache only, no network")
    parser.add_argument("--force-refresh", action="store_true", help="ignore cache, re-fetch everything")
    args = parser.parse_args()

    if args.offline:
        if not CACHE_LISTING.exists() or not CACHE_ARTICLES.exists():
            raise SystemExit("No cache found — run without --offline first.")
        listing = json.loads(CACHE_LISTING.read_text(encoding="utf-8"))
        bodies = json.loads(CACHE_ARTICLES.read_text(encoding="utf-8"))
    else:
        listing = crawl_listing(force=args.force_refresh)
        bodies = crawl_articles(listing, force=args.force_refresh)

    build_release(listing, bodies)


if __name__ == "__main__":
    main()
