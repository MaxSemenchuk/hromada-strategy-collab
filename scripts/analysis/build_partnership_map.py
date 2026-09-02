#!/usr/bin/env python3
"""Ministry «Партнерство задля відновлення та розвитку» partnership map.

Source: decentralization.ua/newgromada/<id> per-hromada pages. Ministry of
Communities and Territories Development, built with Council of Europe /
Swiss DECIDE project / U-LEAD with Europe support; data verified per the
site "станом на кінець 2025 року" (2119 agreements, 490/1470 hromadas,
1740 foreign partners, 64 countries — see decentralization.ua/twincities).

Unlike SKEW (Germany-only, resolved via German-side transliteration) this
source lists partner country + partner city **per Ukrainian hromada**,
joined directly on KATOTTG (no transliteration/alias table needed) and
covers ALL partner countries, not just Germany. Trade-off: no per-partner
"since" date or partnership type — just a verified country+city pair.

Does NOT fold into v7 combined `score`. Does NOT set known=true (that flag
is for curated domestic registry МСС only). Separate release layer, joined
with — but not merged into — twinning-partners.json (different source,
different fields; cross-checking the two is future work).

Usage:
  yarn partnership-map                 # fetch (listing + all hromada pages) + build release
  yarn partnership-map --offline       # rebuild from cache only, no network
  yarn partnership-map --limit N       # fetch only first N hromadas (testing)
  yarn fetch-partnership-map           # refresh data/cache/decentralization/ only
"""

from __future__ import annotations

import argparse
import json
import re
import ssl
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / "data" / "cache" / "decentralization"
CACHE_LISTING = CACHE / "listing"
CACHE_PAGES = CACHE / "pages"
CACHE_INDEX = CACHE / "hromada-index.json"
HROMADAS = ROOT / "data" / "releases" / "hromadas.json"
OUT = ROOT / "data" / "releases" / "partnership-map.json"
MANIFEST = ROOT / "data" / "releases" / "partnership-map.manifest.json"
PREVIEW = ROOT / "docs" / "assets" / "partnership-map-preview.json"

BASE = "https://decentralization.ua"
LISTING_URL = f"{BASE}/newgromada"
DETAIL_URL = f"{BASE}/newgromada/{{id}}"

UA_HDR = (
    "hromada-strategy-collab/0.1 "
    "(+https://github.com/MaxSemenchuk/hromada-strategy-collab; research cache)"
)

REQUEST_DELAY_S = 0.2

# Best-effort UA country name -> ISO2, for the countries that actually show
# up as hromada partners. Unmapped names are kept as-is (partner_country
# stays None, partner_country_ua carries the raw name) rather than guessed.
COUNTRY_UA_TO_ISO = {
    "польща": "PL",
    "німеччина": "DE",
    "литва": "LT",
    "латвія": "LV",
    "естонія": "EE",
    "чехія": "CZ",
    "словаччина": "SK",
    "угорщина": "HU",
    "румунія": "RO",
    "франція": "FR",
    "італія": "IT",
    "іспанія": "ES",
    "нідерланди": "NL",
    "швеція": "SE",
    "данія": "DK",
    "фінляндія": "FI",
    "норвегія": "NO",
    "бельгія": "BE",
    "австрія": "AT",
    "болгарія": "BG",
    "хорватія": "HR",
    "словенія": "SI",
    "португалія": "PT",
    "швейцарія": "CH",
    "велика британія": "GB",
    "великобританія": "GB",
    "сполучене королівство": "GB",
    "ірландія": "IE",
    "греція": "GR",
    "кіпр": "CY",
    "мальта": "MT",
    "люксембург": "LU",
    "ісландія": "IS",
    "молдова": "MD",
    "республіка молдова": "MD",
    "грузія": "GE",
    "туреччина": "TR",
    "сша": "US",
    "сполучені штати америки": "US",
    "канада": "CA",
    "японія": "JP",
    "південна корея": "KR",
    "республіка корея": "KR",
    "австралія": "AU",
    "ліхтенштейн": "LI",
    "чорногорія": "ME",
    "північна македонія": "MK",
    "боснія і герцеговина": "BA",
    "сербія": "RS",
    "албанія": "AL",
    "чеська республіка": "CZ",
    "китай": "CN",
    "китайська народна республіка": "CN",
    "ізраїль": "IL",
    "азербайджан": "AZ",
    "вірменія": "AM",
    "казахстан": "KZ",
    "узбекистан": "UZ",
    "індія": "IN",
    "бразилія": "BR",
    "аргентина": "AR",
    "мексика": "MX",
    "єгипет": "EG",
    "марокко": "MA",
    "південно-африканська республіка": "ZA",
    "об'єднані арабські емірати": "AE",
    "об’єднані арабські емірати": "AE",
    "саудівська аравія": "SA",
    "нова зеландія": "NZ",
    "андорра": "AD",
    "монако": "MC",
    "сан-марино": "SM",
    "ватикан": "VA",
    "білорусь": "BY",
    "росія": "RU",
    "англія": "GB",
    "південна африка": "ZA",
    "ґватемала": "GT",
    "гватемала": "GT",
    "перу": "PE",
    "узбекистан": "UZ",
    "узбекістан": "UZ",
}


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


def http_get(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA_HDR})
    try:
        with urllib.request.urlopen(req, context=_ssl_context(), timeout=90) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception as exc:
        import subprocess

        try:
            out = subprocess.check_output(["curl", "-sL", "-A", UA_HDR, url], timeout=90)
            return out.decode("utf-8", errors="replace")
        except Exception as curl_exc:
            raise RuntimeError(f"fetch failed ({exc}); curl fallback: {curl_exc}") from exc


def norm_apos(s: str) -> str:
    return s.replace("'", "’").replace("ʼ", "’").replace("`", "’")


LAST_PAGE_RE = re.compile(r'href="/newgromada\?page=(\d+)">Остання</a>')
ID_NAME_RE = re.compile(
    r'href="/newgromada/(\d+)">([^<]+?)територіальна громад[а]?\s*\n?</a>'
)


def fetch_listing(force: bool = False) -> dict[str, str]:
    """Return {id: name} for every hromada in the /newgromada directory."""
    CACHE_LISTING.mkdir(parents=True, exist_ok=True)
    page1_file = CACHE_LISTING / "page-1.html"
    if force or not page1_file.exists():
        html = http_get(LISTING_URL)
        page1_file.write_text(html, encoding="utf-8")
    else:
        html = page1_file.read_text(encoding="utf-8")

    m = LAST_PAGE_RE.search(html)
    last_page = int(m.group(1)) if m else 1
    print(f"Listing: {last_page} pages")

    ids: dict[str, str] = {}

    def collect(page_html: str) -> None:
        for pid, name in ID_NAME_RE.findall(page_html):
            ids[pid] = norm_apos(name.strip())

    collect(html)
    for page in range(2, last_page + 1):
        page_file = CACHE_LISTING / f"page-{page}.html"
        if force or not page_file.exists():
            page_html = http_get(f"{LISTING_URL}?page={page}")
            page_file.write_text(page_html, encoding="utf-8")
            time.sleep(REQUEST_DELAY_S)
        else:
            page_html = page_file.read_text(encoding="utf-8")
        collect(page_html)
        if page % 10 == 0:
            print(f"  listing page {page}/{last_page} — {len(ids)} ids so far")

    CACHE_INDEX.write_text(
        json.dumps(ids, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"Listing done: {len(ids)} hromada ids")
    return ids


def fetch_detail(hid: str, force: bool = False) -> str:
    CACHE_PAGES.mkdir(parents=True, exist_ok=True)
    cache_file = CACHE_PAGES / f"{hid}.html"
    if not force and cache_file.exists():
        return cache_file.read_text(encoding="utf-8")
    html = http_get(DETAIL_URL.format(id=hid))
    cache_file.write_text(html, encoding="utf-8")
    time.sleep(REQUEST_DELAY_S)
    return html


TITLE_RE = re.compile(r"single-page-title'>\s*([^<]+?)\s*</div>", re.S)
OBLAST_RE = re.compile(r'href="/areas/[^"]*">\s*([^<]+?)\s*\n?</a>')
KATOTTG_RE = re.compile(r"КАТОТТГ:\s*<span class='value'>\s*([A-Z0-9]+)\s*</span>")
TYPE_RE = re.compile(r"Тип громади:\s*</div>\s*<span class='value'>\s*([^\s<]+)\s*</span>")
POPULATION_RE = re.compile(
    r"Чисельність населення громади:\s*<span class='value'>\s*([\d\s]+)\s*</span>"
)
COUNTRY_NAME_RE = re.compile(r'href="/countries/(\d+)">\s*([^<\n]+?)\s*\n?</a>')


def parse_detail(hid: str, html: str) -> dict | None:
    title_m = TITLE_RE.search(html)
    if not title_m:
        return None
    katottg_m = KATOTTG_RE.search(html)
    oblast_m = OBLAST_RE.search(html)
    type_m = TYPE_RE.search(html)
    pop_m = POPULATION_RE.search(html)

    i = html.find("Країни партнери")
    countries: list[dict] = []
    if i != -1:
        j = html.find("Склад громади", i)
        section = html[i : j if j != -1 else len(html)]
        for block in re.split(r"<div class='community-table", section)[1:]:
            cm = COUNTRY_NAME_RE.search(block)
            if not cm:
                continue
            country_id, country_ua = cm.group(1), norm_apos(cm.group(2).strip())
            cities = [norm_apos(c.strip()) for c in re.findall(r"<p>([^<]+)</p>", block)]
            cities = [c for c in cities if c]
            if not cities:
                continue
            countries.append(
                {
                    "country_id": country_id,
                    "country_ua": country_ua,
                    "country_iso2": COUNTRY_UA_TO_ISO.get(country_ua.lower()),
                    "cities": cities,
                }
            )

    return {
        "decentralization_id": hid,
        "name": norm_apos(title_m.group(1).strip()),
        "katottg": katottg_m.group(1) if katottg_m else None,
        "oblast": oblast_m.group(1).strip() if oblast_m else None,
        "community_type": type_m.group(1).strip() if type_m else None,
        "population": int(pop_m.group(1).replace(" ", "")) if pop_m else None,
        "countries": countries,
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


def build_release(details: list[dict]) -> None:
    hromada_rows = json.loads(HROMADAS.read_text(encoding="utf-8"))
    by_katottg = {
        (r.get("Katottg") or "").strip(): r for r in hromada_rows if (r.get("Katottg") or "").strip()
    }

    hromadas: list[dict] = []
    unmatched: list[dict] = []
    country_counts: dict[str, int] = {}
    total_partner_cities = 0

    for d in details:
        if not d or not d.get("countries"):
            continue
        katottg = d.get("katottg")
        row = by_katottg.get(katottg or "")
        partners = []
        for c in d["countries"]:
            code = c["country_iso2"] or c["country_ua"]
            country_counts[code] = country_counts.get(code, 0) + len(c["cities"])
            for city in c["cities"]:
                partners.append(
                    {
                        "partner_name": city,
                        "partner_country": c["country_iso2"],
                        "partner_country_ua": c["country_ua"],
                        "source": "decentralization_ua",
                        "confidence": "registry",
                    }
                )
        total_partner_cities += len(partners)
        entry = {
            "name": (row.get("Name") if row else None) or d["name"],
            "short": short_name((row.get("Name") if row else None) or d["name"]),
            "katottg": katottg,
            "oblast": (row.get("Oblast") if row else None) or d.get("oblast"),
            "decentralization_id": d["decentralization_id"],
            "partners": partners,
            "partner_count": len(partners),
            "partner_country_count": len(d["countries"]),
        }
        hromadas.append(entry)
        if not row:
            unmatched.append({"decentralization_id": d["decentralization_id"], "name": d["name"], "katottg": katottg})

    hromadas.sort(key=lambda h: (-h["partner_count"], h["short"]))

    generated = datetime.now(timezone.utc).isoformat()
    payload = {
        "generatedAt": generated,
        "warning": (
            "Ministry «Партнерство задля відновлення та розвитку» partnership map "
            "(decentralization.ua/newgromada, data verified as of end 2025). Separate "
            "layer from twinning-partners.json (SKEW/Cities4Cities/strategy-mentions) — "
            "different source, no per-partner date/type, not cross-validated against it "
            "yet. Not folded into matching score."
        ),
        "source": {
            "id": "decentralization_ua",
            "name": "Ministry of Communities and Territories Development — partnership map",
            "url": "https://decentralization.ua/twincities",
            "listing_url": LISTING_URL,
            "operator": "Мінрозвитку + Council of Europe DECIDE project + U-LEAD with Europe",
        },
        "coverage": {
            "hromadas_fetched": len(details),
            "hromadas_with_partners": len(hromadas),
            "unmatched_katottg": len(unmatched),
            "total_partner_city_rows": total_partner_cities,
            "country_breakdown": dict(
                sorted(country_counts.items(), key=lambda kv: -kv[1])
            ),
        },
        "hromadas": hromadas,
        "unmatched": unmatched[:200],
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    MANIFEST.write_text(
        json.dumps(
            {
                "generatedAt": generated,
                "hromadasFetched": len(details),
                "hromadasWithPartners": len(hromadas),
                "totalPartnerCityRows": total_partner_cities,
                "unmatchedKatottg": len(unmatched),
                "method": "decentralization.ua/newgromada/<id> per-hromada scrape, joined on KATOTTG",
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
                "caveat": "Ministry partnership map — decentralization.ua, verified end-2025 data.",
                "hromadaCount": len(hromadas),
                "totalPartnerCityRows": total_partner_cities,
                "top": [
                    {
                        "short": h["short"],
                        "oblast": h.get("oblast"),
                        "partner_count": h["partner_count"],
                        "countries": sorted(
                            {p["partner_country"] or p["partner_country_ua"] for p in h["partners"]}
                        ),
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
        f"Wrote {OUT.relative_to(ROOT)} — {len(hromadas)} hromadas with partners, "
        f"{total_partner_cities} partner-city rows, {len(unmatched)} unmatched KATOTTG"
    )


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--offline", action="store_true", help="Do not fetch; use HTML cache only")
    ap.add_argument("--fetch-only", action="store_true", help="Only refresh the HTML cache")
    ap.add_argument("--force-fetch", action="store_true", help="Re-download even if cache exists")
    ap.add_argument("--limit", type=int, default=None, help="Fetch only first N hromadas (testing)")
    args = ap.parse_args()

    if args.offline:
        if not CACHE_INDEX.exists():
            raise SystemExit("No cached listing — run without --offline first")
        ids = json.loads(CACHE_INDEX.read_text(encoding="utf-8"))
    else:
        ids = fetch_listing(force=args.force_fetch)

    id_list = list(ids.items())
    if args.limit:
        id_list = id_list[: args.limit]

    details: list[dict] = []
    for n, (hid, name) in enumerate(id_list, 1):
        html = fetch_detail(hid, force=(args.force_fetch and not args.offline))
        d = parse_detail(hid, html)
        if d:
            details.append(d)
        if n % 100 == 0:
            print(f"  fetched {n}/{len(id_list)} hromada pages")

    if args.fetch_only:
        print(f"Fetched {len(details)} hromada pages")
        return
    build_release(details)


if __name__ == "__main__":
    main()
