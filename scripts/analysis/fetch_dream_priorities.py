#!/usr/bin/env python3
"""Fetch DREAM public ideas into data/cache/dream/ (gitignored) and aggregate
revealed priorities by hromada KATOTTG → data/releases/dream-priorities.json.

Listing uses cursor pagination via `?from=<updated>` (~16k ideas). Details are
cached per-id so re-runs are incremental. Settlement CATOTTG codes are mapped
to hromada codes via KSE ua-admin-map.

Usage:
  yarn fetch-dream                 # list + details (resume cache) + aggregate
  yarn fetch-dream --list-only
  yarn fetch-dream --aggregate-only
  yarn fetch-dream --limit 200     # details cap (smoke test)
  yarn fetch-dream --workers 12
"""

from __future__ import annotations

import argparse
import json
import re
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / "data" / "cache" / "dream"
INDEX_PATH = CACHE / "ideas-index.json"
DETAILS_DIR = CACHE / "ideas"
OUT = ROOT / "data" / "releases" / "dream-priorities.json"
MANIFEST = ROOT / "data" / "releases" / "dream-priorities.manifest.json"

BASE = "https://public-api.dream.gov.ua/marketplace/public/dream"
UA = (
    "hromada-strategy-collab/0.1 "
    "(+https://github.com/MaxSemenchuk/hromada-strategy-collab; research cache)"
)

# World Bank economic sector codes seen in DREAM additionalClassifications (WB-ECO).
# Note: bare B/BH (Public Administration) is NOT mapped to Е-врядування — too noisy
# (rada buildings, shelters, culture halls). Those only tag via title keywords below.
WB_ECO_TO_SECTOR = {
    "E": "Освіта",
    "ES": "Освіта",
    "EC": "Освіта",
    "ET": "Освіта",
    "EZ": "Освіта",
    "H": "Охорона здоров'я",
    "HQ": "Охорона здоров'я",
    "HG": "Охорона здоров'я",
    "W": "Вода / каналізація (ЖКГ)",
    "WA": "Вода / каналізація (ЖКГ)",
    "WB": "Вода / каналізація (ЖКГ)",
    "WC": "Вода / каналізація (ЖКГ)",
    "WZ": "Довкілля / екологія",
    "T": "Транспорт / логістика",
    "TI": "Транспорт / логістика",
    "TF": "Транспорт / логістика",
    "L": "Енергетика (ВДЕ)",
    "LU": "Енергетика (ВДЕ)",
    "LN": "Енергетика (ВДЕ)",
    "LT": "Енергетика (ВДЕ)",
    "Y": "Підприємництво / МСБ",
    "YH": "Підприємництво / МСБ",
    "YS": "Підприємництво / МСБ",
    "S": "Соціальні послуги",
    "SA": "Соціальні послуги",
    "C": "IT / цифровізація",
    "A": "Сільське господарство / АПК",
    "O": "Відновлення / реконструкція",
}

# Title keywords — order matters little; both e-gov and digital can apply.
KEYWORD_SECTORS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"школ|ліце|садоч|освіт|універс|дитяч", re.I), "Освіта"),
    (re.compile(r"лікарн|амбулатор|поліклін|мед |медич|ФАП|здоров", re.I), "Охорона здоров'я"),
    (re.compile(r"водо|каналіз|очиск|колодяз|гідрант", re.I), "Вода / каналізація (ЖКГ)"),
    (re.compile(r"смітт|ТПВ|відход|полігон|еколог", re.I), "Довкілля / екологія"),
    (re.compile(r"дорог|міст |мосту|тролейбус|транспорт|аеропорт", re.I), "Транспорт / логістика"),
    (re.compile(r"котельн|тепло|енерг|соняч|ВДЕ|когенер", re.I), "Енергетика (ВДЕ)"),
    (re.compile(r"укритт|безпек|ЦЗ|бомбосховищ|пожежн", re.I), "Безпека / ЦЗ"),
    (re.compile(r"культур|музей|театр|бібліот|спадщин", re.I), "Культура / спадщина"),
    (re.compile(r"спорт|стадіон|спортзал", re.I), "Культура / спадщина"),
    (re.compile(r"житл|будинк|відбудов|реконструк", re.I), "Відновлення / реконструкція"),
    # Admin-service delivery (not every «адмінбудівля»)
    (
        re.compile(
            r"ЦНАП|адмінпослуг|Центр\s*Дія|Дія\.?\s*Центр|е-послуг|електронн\w*\s+послуг|"
            r"е-урядуван|електронн\w*\s+урядуван",
            re.I,
        ),
        "Е-врядування",
    ),
    (re.compile(r"турист", re.I), "Туризм"),
]

# Digital component — separate from e-gov; can co-occur (e.g. digital CNAP).
DIGITAL_KEYWORD = re.compile(
    r"цифров|інформатизац|смарт[-\s]?city|smart[-\s]?city|\bIT\b|ІТ-|"
    r"інтернет|оптоволок|Wi-?Fi|вай-?фай|дата[-\s]?центр|data\s*cent|"
    r"геоінформ|\bГІС\b|геоінформаційн|портал\s+послуг|онлайн[-\s]?послуг|"
    r"електронн\w*\s+послуг|е-послуг|хаб\s+цифров",
    re.I,
)
# Med imaging / lab «цифрове» обладнання ≠ civic digitalisation;
# Latin GIS alone often means gas-insulated switchgear in energy titles.
DIGITAL_EXCLUDE = re.compile(
    r"рентген|томограф|УЗД|мамограф|мікроскоп|"
    r"діагностичн\w+\s+систем|медичн\w+\s+обладнання|"
    r"медичн\w+\s+цифров|цифров\w+\s+комплекс\s+рентген|"
    r"лаборатор|gas\s*insulat|\bGIS\s*110|\bGIS\s*kV|switchgear|"
    r"багатофункціональн\w+\s+пристр|принтер|\bCanon\b|\bMF\d|"
    r"цифров\w+\s+підстанц",
    re.I,
)

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


def _get_json(url: str, retries: int = 4) -> dict:
    ctx = _ssl_context()
    last_exc: Exception | None = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
            with urllib.request.urlopen(req, context=ctx, timeout=90) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            last_exc = exc
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"GET failed {url}: {last_exc}")


def uk_title(cdu: dict) -> str:
    title = cdu.get("title")
    if isinstance(title, list):
        for item in title:
            if isinstance(item, dict) and item.get("lang") == "uk":
                return (item.get("translation") or "").strip()
        if title and isinstance(title[0], dict):
            return (title[0].get("translation") or "").strip()
    if isinstance(title, str):
        return title.strip()
    return ""


def extract_locations(cdu: dict) -> list[str]:
    codes: list[str] = []
    for approach in cdu.get("approaches") or []:
        for item in approach.get("items") or []:
            for loc in item.get("locations") or []:
                gaz = loc.get("gazetteer") or {}
                if gaz.get("scheme") == "UA-CATOTTG":
                    for ident in gaz.get("identifiers") or []:
                        if ident:
                            codes.append(str(ident).strip())
    return codes


def classify_sectors(cdu: dict) -> list[str]:
    """Map a DREAM idea to controlled sector tags.

    Е-врядування = admin-service delivery (ЦНАП / Дія / е-послуги), not WB Public Admin.
    IT / цифровізація = digital component (incl. WB-ECO C + title cues), excl. med imaging.
    A project may carry both (e.g. digital CNAP).
    """
    sectors: list[str] = []
    for ac in cdu.get("additionalClassifications") or []:
        if ac.get("scheme") == "WB-ECO":
            mapped = WB_ECO_TO_SECTOR.get(str(ac.get("id") or "").upper())
            if mapped:
                sectors.append(mapped)
    title = uk_title(cdu)
    for pattern, sector in KEYWORD_SECTORS:
        if pattern.search(title):
            sectors.append(sector)
    if DIGITAL_KEYWORD.search(title) and not DIGITAL_EXCLUDE.search(title):
        sectors.append("IT / цифровізація")

    # de-dupe preserve order
    seen: set[str] = set()
    out: list[str] = []
    for s in sectors:
        if s not in seen:
            seen.add(s)
            out.append(s)
    if not out:
        purpose = str(cdu.get("purpose") or "")
        if purpose in ("restoration", "development"):
            out.append("Відновлення / реконструкція")
    return out


def list_ideas(force: bool = False) -> list[dict]:
    CACHE.mkdir(parents=True, exist_ok=True)
    if INDEX_PATH.exists() and not force:
        data = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
        items = data.get("items") or []
        print(f"Using cached index ({len(items)} ideas) — pass --force to refresh")
        return items

    print("Listing DREAM ideas (paginated via from=)…")
    items: list[dict] = []
    seen: set[str] = set()
    from_ts: str | None = None
    t0 = time.time()
    while True:
        url = f"{BASE}/ideas"
        if from_ts:
            url += f"?from={urllib.parse.quote(from_ts)}"
        batch = _get_json(url).get("data") or []
        if not batch:
            break
        new = 0
        for row in batch:
            iid = row.get("internal", {}).get("id")
            if not iid or iid in seen:
                continue
            seen.add(iid)
            items.append(
                {
                    "id": iid,
                    "code": row.get("internal", {}).get("code"),
                    "updated": row.get("external", {}).get("updated"),
                }
            )
            new += 1
            from_ts = row.get("external", {}).get("updated") or from_ts
        print(f"  listed={len(items)} new={new} elapsed={time.time() - t0:.1f}s", flush=True)
        if new == 0 or len(batch) < 1000:
            break

    INDEX_PATH.write_text(
        json.dumps(
            {
                "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "count": len(items),
                "items": items,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {INDEX_PATH} ({len(items)} ideas)")
    return items


def _detail_path(idea_id: str) -> Path:
    return DETAILS_DIR / f"{idea_id}.json"


def fetch_details(items: list[dict], limit: int | None, workers: int, force: bool) -> int:
    DETAILS_DIR.mkdir(parents=True, exist_ok=True)
    todo: list[str] = []
    for row in items:
        iid = row["id"]
        if limit is not None and len(todo) >= limit:
            break
        path = _detail_path(iid)
        if path.exists() and not force:
            continue
        todo.append(iid)

    cached = len(items) - len(todo) if limit is None else max(0, min(len(items), limit or 0) - len(todo))
    # recount properly
    existing = sum(1 for row in items[: limit or len(items)] if _detail_path(row["id"]).exists())
    print(f"Details: need {len(todo)}, already cached in scope {existing}, workers={workers}")

    if not todo:
        return 0

    ok = 0
    fail = 0

    def one(iid: str) -> tuple[str, bool, str | None]:
        try:
            data = _get_json(f"{BASE}/ideas/{iid}")
            _detail_path(iid).write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            return iid, True, None
        except Exception as exc:
            return iid, False, str(exc)

    t0 = time.time()
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(one, iid): iid for iid in todo}
        done = 0
        for fut in as_completed(futures):
            done += 1
            _, success, err = fut.result()
            if success:
                ok += 1
            else:
                fail += 1
                if fail <= 5:
                    print(f"  FAIL {err}")
            if done % 200 == 0 or done == len(todo):
                print(
                    f"  details {done}/{len(todo)} ok={ok} fail={fail} "
                    f"elapsed={time.time() - t0:.1f}s",
                    flush=True,
                )
    return ok


def aggregate(items: list[dict], limit: int | None) -> None:
    from enrich_from_kse import settlement_to_hromada  # noqa: WPS433

    mapping = settlement_to_hromada()
    if not mapping:
        raise RuntimeError("settlement→hromada map empty — check KSE admin_map fetch")

    # optional names from release
    names: dict[str, str] = {}
    hromadas_path = ROOT / "data" / "releases" / "hromadas.json"
    if hromadas_path.exists():
        for row in json.loads(hromadas_path.read_text(encoding="utf-8")):
            code = (row.get("Katottg") or "").strip()
            if code:
                names[code] = row.get("Name") or ""

    per: dict[str, dict] = {}
    # Flat catalog for the stakeholder UI (title + code + hromada), capped later.
    sector_catalog: dict[str, list[dict]] = defaultdict(list)
    skipped_no_loc = 0
    skipped_unmap = 0
    processed = 0
    activeish = 0
    SAMPLE_PER_SECTOR = 5

    scope = items[:limit] if limit is not None else items
    for row in scope:
        path = _detail_path(row["id"])
        if not path.exists():
            continue
        try:
            detail = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        processed += 1
        status = str((detail.get("internal") or {}).get("status") or "")
        cdu = detail.get("cdu_response") or {}
        if status and "cancel" in status:
            # still count cancelled? skip — they are noise for priorities
            continue
        activeish += 1
        locs = extract_locations(cdu)
        if not locs:
            skipped_no_loc += 1
            continue
        hromada_codes: set[str] = set()
        for loc in locs:
            h = mapping.get(loc)
            if h:
                hromada_codes.add(h)
            else:
                skipped_unmap += 1
        if not hromada_codes:
            continue

        sectors = classify_sectors(cdu)
        title = uk_title(cdu)
        purpose = cdu.get("purpose")
        ptype = cdu.get("type")
        code = (detail.get("internal") or {}).get("code") or row.get("code")
        title_short = (title or "")[:180]

        for hcode in hromada_codes:
            bucket = per.setdefault(
                hcode,
                {
                    "katottg": hcode,
                    "name": names.get(hcode),
                    "project_count": 0,
                    "sectors": Counter(),
                    "purposes": Counter(),
                    "types": Counter(),
                    "sample_titles": [],
                    "project_codes": [],
                    "sector_samples": defaultdict(list),
                },
            )
            bucket["project_count"] += 1
            for s in sectors:
                bucket["sectors"][s] += 1
                samples = bucket["sector_samples"][s]
                if title_short and len(samples) < SAMPLE_PER_SECTOR:
                    samples.append({"title": title_short, "code": code})
                # One catalog row per (project, hromada, sector) — UI dedupes by code.
                if title_short:
                    sector_catalog[s].append(
                        {
                            "katottg": hcode,
                            "name": names.get(hcode) or "",
                            "title": title_short,
                            "code": code,
                        }
                    )
            if purpose:
                bucket["purposes"][str(purpose)] += 1
            if ptype:
                bucket["types"][str(ptype)] += 1
            if title_short and len(bucket["sample_titles"]) < 5:
                bucket["sample_titles"].append(title_short)
            if code and len(bucket["project_codes"]) < 20:
                bucket["project_codes"].append(code)

    rows = []
    for hcode, bucket in sorted(per.items(), key=lambda kv: (-kv[1]["project_count"], kv[0])):
        sector_counts = dict(bucket["sectors"].most_common())
        top_sectors = [s for s, _ in bucket["sectors"].most_common(5)]
        sector_samples = {
            s: list(samples)
            for s, samples in bucket["sector_samples"].items()
            if samples
        }
        rows.append(
            {
                "katottg": hcode,
                "name": bucket["name"],
                "project_count": bucket["project_count"],
                "top_sectors": top_sectors,
                "sector_counts": sector_counts,
                "purpose_counts": dict(bucket["purposes"]),
                "type_counts": dict(bucket["types"]),
                "sample_titles": bucket["sample_titles"],
                "sample_project_codes": bucket["project_codes"],
                "sector_samples": sector_samples,
            }
        )

    # Keep all projects for sparse sectors; cap dense ones for release size.
    CATALOG_CAP = 80
    SPARSE_KEEP_ALL = 40
    sector_projects: dict[str, list[dict]] = {}
    for sector, entries in sector_catalog.items():
        # Prefer unique project codes (first hromada wins for multi-location ideas).
        seen_codes: set[str] = set()
        unique: list[dict] = []
        for e in entries:
            key = str(e.get("code") or e.get("title") or "")
            if not key or key in seen_codes:
                continue
            seen_codes.add(key)
            unique.append(e)
        if len(unique) <= SPARSE_KEEP_ALL:
            sector_projects[sector] = unique
        else:
            sector_projects[sector] = unique[:CATALOG_CAP]

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    payload = {
        "generated_at": generated_at,
        "source": {
            "api": BASE,
            "docs": "https://open-contracting.github.io/dream-api-docs/",
            "notes": [
                "Revealed priorities from DREAM project locations (UA-CATOTTG), not strategy PDF text.",
                "Sectors: WB-ECO (except bare Public Admin B/BH) + title keywords → controlled vocabulary.",
                "Е-врядування = ЦНАП/Дія/е-послуги only; IT / цифровізація = digital component (excl. med imaging).",
                "Cancelled ideas excluded. Settlement codes mapped to hromada via KSE ua-admin-map.",
                "Hypothesis layer — do not treat as approved municipal strategy.",
                "sector_projects / sector_samples are title samples for UI — not a full project dump for dense sectors.",
            ],
        },
        "coverage": {
            "ideas_indexed": len(items),
            "details_processed": processed,
            "ideas_kept_non_cancelled": activeish,
            "hromadas_with_projects": len(rows),
            "skipped_no_location": skipped_no_loc,
            "unmapped_location_hits": skipped_unmap,
            "details_cached": sum(1 for p in DETAILS_DIR.glob("*.json")),
        },
        "sector_projects": sector_projects,
        "hromadas": rows,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    MANIFEST.write_text(
        json.dumps(
            {
                "file": "dream-priorities.json",
                "generated_at": generated_at,
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
        f"Wrote {OUT.relative_to(ROOT)} — {len(rows)} hromadas, "
        f"{processed} details processed, {activeish} non-cancelled"
    )


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--list-only", action="store_true")
    p.add_argument("--aggregate-only", action="store_true")
    p.add_argument("--force", action="store_true", help="Refresh index / re-download details")
    p.add_argument("--limit", type=int, default=None, help="Cap details fetch/aggregate")
    p.add_argument("--workers", type=int, default=10)
    return p.parse_args()


def main() -> None:
    args = parse_args()
    if args.aggregate_only:
        if not INDEX_PATH.exists():
            raise SystemExit("No ideas-index.json — run without --aggregate-only first")
        items = json.loads(INDEX_PATH.read_text(encoding="utf-8")).get("items") or []
        aggregate(items, args.limit)
        return

    items = list_ideas(force=args.force)
    if args.list_only:
        return

    fetch_details(items, limit=args.limit, workers=args.workers, force=args.force)
    aggregate(items, args.limit)


if __name__ == "__main__":
    main()
