"""AFCCRE French jumelage directory — FR analogue of SKEW.

PDFs (no public CSV/API). Registry-confidence twinning, never known=true,
never folded into v7 score. Kyiv city/districts and Crimea Yalta are skipped;
occupied hromadas with a KATOTTG stay (same as SKEW/Ministry rows).
"""

from __future__ import annotations

import json
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / "data" / "cache" / "twinning"
CACHE_ANNUAIRE_PDF = CACHE / "afccre-annuaire.pdf"
CACHE_NOUVEAUX_PDF = CACHE / "afccre-nouveaux-2025.pdf"
CACHE_EDGES = CACHE / "afccre-edges.json"
FR_ALIASES = ROOT / "data" / "sources" / "twinning-fr-aliases.json"

AFCCRE_ANNUAIRE_URL = (
    "https://www.afccre.org/sites/default/files/Annuaire%20des%20communes%20jumel%C3%A9es_1.pdf"
)
AFCCRE_NOUVEAUX_URL = (
    "https://www.afccre.org/sites/default/files/Nouveaux%20jumelages%202025.pdf"
)
AFCCRE_HOME = "https://www.afccre.org/"

# Directory lines: "UKRAINE KREMENTCHOUK 2023POTLAVA"
UA_LINE = re.compile(
    r"^UKRAINE\s+(.+?)\s+(19\d{2}|20\d{2})([A-ZÀ-ÖÏÝ\- ]*)\s*$"
)
# Commune header: "ST ETIENNE42007"
FR_HEADER = re.compile(r"^([A-ZÀ-ÖØ-Þ'’ \-]{3,}?)(\d{5})$")

AFCCRE_OBLAST = {
    "POTLAVA": "Полтавська область",
    "POLTAVA": "Полтавська область",
    "SOUMY": "Сумська область",
    "JYTOMYR": "Житомирська область",
    "KIEV": "Київська область",
    "DNIPROPETROVSK": "Дніпропетровська область",
    "TCHERNIHIV": "Чернігівська область",
    "VINNYTSYA": "Вінницька область",
    "TCHERNIVTSI": "Чернівецька область",
    "KHMELNYSTYÏ": "Хмельницька область",
    "KHMELNYTSKYI": "Хмельницька область",
    "TCHERKASSY": "Черкаська область",
    "KHARKIV": "Харківська область",
    "TERNOPIL": "Тернопільська область",
    "MIKOLAÏV": "Миколаївська область",
    "MIKOLAIV": "Миколаївська область",
    "LVIV": "Львівська область",
    "IVANO FRANKIVSK": "Івано-Франківська область",
}

# 2025 «nouveaux jumelages» UA slot (longest first).
NOUVEAUX_UA = [
    "KRYVYÏ RIH",
    "KRYVYI RIH",
    "MYKOLAÏV",
    "MYKOLAIV",
    "LIOUBOTYN",
    "MARIOUPOL",
    "SEMENIVKA",
    "OVROUTCH",
    "ZLATOPIL",
    "KOLOMYA",
    "KHERSON",
    "SOUMY",
    "SMILA",
]

FR_DEPTS = {
    "SOMME",
    "ISERE",
    "HAUTE MARNE",
    "SEINE MARITIME",
    "HERAULT",
    "LOIRE ATLANTIQUE",
    "AUDE",
    "VAL DE MARNE",
    "LOIRET",
    "NORD",
    "COTES D'ARMOR",
    "COTES D ARMOR",
    "PYRENEES ATLANTIQUES",
}

SKIP_UA = {
    "kiev": "kyiv_city",
    "kievdniprovskyi": "kyiv_city",
    "kievpetchersk": "kyiv_city",
    "darnitsa": "kyiv_city",
    "yalta": "crimea",
    "lougansk": "no_katottg",
    "thorezgrad": "no_katottg",
}


def norm_key(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower().replace("’", "").replace("'", "").replace("`", "")
    return re.sub(r"[^a-z0-9]", "", s)


def pretty_fr(name: str) -> str:
    name = re.sub(r"\s+", " ", name or "").strip()
    name = re.sub(r"^ST\s+", "Saint ", name, flags=re.I)
    return name.title()


def pdf_text(path: Path) -> str:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    return "\n".join((page.extract_text() or "") for page in reader.pages)


def parse_ua_line(line: str) -> tuple[str, str | None, str | None] | None:
    m = UA_LINE.match(line.strip())
    if not m:
        return None
    city = re.sub(r"\s+", " ", m.group(1)).strip()
    year = m.group(2)
    oblast = re.sub(r"\s+", " ", m.group(3) or "").strip() or None
    return city, year, oblast


def skip_reason(ua_city: str) -> str | None:
    return SKIP_UA.get(norm_key(ua_city))


def parse_annuaire(text: str) -> list[dict]:
    current: dict[str, str] | None = None
    edges: list[dict] = []
    seen: set[tuple[str, str, str]] = set()
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        hm = FR_HEADER.match(line)
        if hm and not line.startswith("UKRAINE"):
            current = {"name": hm.group(1).strip(), "cp": hm.group(2)}
            continue
        parsed = parse_ua_line(line)
        if not parsed or not current:
            continue
        city, year, oblast = parsed
        key = (current["name"], city, year)
        if key in seen:
            continue
        seen.add(key)
        edges.append(
            {
                "fr_name": pretty_fr(current["name"]),
                "fr_raw": current["name"],
                "fr_cp": current["cp"],
                "ua_name_fr": city,
                "ua_oblast_lat": oblast,
                "since": year,
                "type": "Jumelage",
                "source": "afccre",
                "source_url": AFCCRE_ANNUAIRE_URL,
                "list": "annuaire",
            }
        )
    return edges


def _strip_dept(fr: str) -> str:
    fr = re.sub(r"\s+", " ", fr).strip(" -")
    upper = fr.upper()
    for dept in sorted(FR_DEPTS, key=len, reverse=True):
        if upper.endswith(" " + dept):
            fr = fr[: -(len(dept) + 1)].strip()
            break
    return fr


def parse_nouveaux(text: str, year: str = "2025") -> list[dict]:
    """One jumelage per line-group that ends with UKRAINE (handles wrapped PDFs)."""
    country_end = (
        "UKRAINE",
        "POLOGNE",
        "ITALIE",
        "ALLEMAGNE",
        "ESPAGNE",
        "PORTUGAL",
        "BELGIQUE",
        "ROUMANIE",
        "GRECE",
        "ROYAUME UNI",
        "BOSNIE HERZEGOVINE",
        "SERBIE",
    )
    records: list[str] = []
    buf = ""
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        buf = f"{buf} {line}".strip() if buf else line
        upper = buf.upper()
        if any(upper.endswith(c) for c in country_end):
            records.append(buf)
            buf = ""
    ua_alt = "|".join(re.escape(u) for u in sorted(NOUVEAUX_UA, key=len, reverse=True))
    tail = re.compile(rf"^(?P<fr>.+?)\s+(?P<ua>{ua_alt})\s*$", re.I)
    edges: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for rec in records:
        if not rec.upper().endswith("UKRAINE"):
            continue
        body = rec[: -len("UKRAINE")].strip()
        m = tail.match(body)
        if not m:
            continue
        fr_raw = re.sub(r"^\d+\s+", "", _strip_dept(m.group("fr")))
        # Drop leftover previous-record tokens if the FR slot still looks like a dump.
        fr_raw = re.sub(
            r"^(?:.*\b(?:Pologne|Italie|Allemagne|Espagne|Portugal|Belgique|Roumanie|Grece|Royaume Uni)\b)\s+",
            "",
            fr_raw,
            flags=re.I,
        ).strip()
        ua = re.sub(r"\s+", " ", m.group("ua")).strip()
        key = (norm_key(fr_raw), norm_key(ua))
        if not fr_raw or key in seen:
            continue
        seen.add(key)
        edges.append(
            {
                "fr_name": pretty_fr(fr_raw),
                "fr_raw": fr_raw,
                "fr_cp": None,
                "ua_name_fr": ua,
                "ua_oblast_lat": None,
                "since": year,
                "type": "Jumelage",
                "source": "afccre",
                "source_url": AFCCRE_NOUVEAUX_URL,
                "list": "nouveaux_2025",
            }
        )
    return edges


def merge_edges(annuaire: list[dict], nouveaux: list[dict]) -> list[dict]:
    """Nouveaux rows that already appear in the directory (same FR+UA) are dropped."""
    have = {(norm_key(e["fr_raw"]), norm_key(e["ua_name_fr"])) for e in annuaire}
    extra = []
    for e in nouveaux:
        key = (norm_key(e["fr_raw"]), norm_key(e["ua_name_fr"]))
        if key in have:
            continue
        extra.append(e)
        have.add(key)
    return annuaire + extra


def load_fr_aliases() -> dict[str, dict]:
    if not FR_ALIASES.exists():
        return {}
    raw = json.loads(FR_ALIASES.read_text(encoding="utf-8"))
    out: dict[str, dict] = {}
    for k, v in raw.items():
        if k.startswith("_"):
            continue
        out[norm_key(k)] = v if isinstance(v, dict) else {"name": v}
    return out


def fetch_afccre(get_bytes, force: bool = False) -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
    for path, url in (
        (CACHE_ANNUAIRE_PDF, AFCCRE_ANNUAIRE_URL),
        (CACHE_NOUVEAUX_PDF, AFCCRE_NOUVEAUX_URL),
    ):
        if force or not path.exists():
            print(f"Fetching {url}")
            path.write_bytes(get_bytes(url))
        else:
            print(f"Using cached {path.relative_to(ROOT)}")


def extract_afccre_edges() -> list[dict]:
    if not CACHE_ANNUAIRE_PDF.exists():
        raise FileNotFoundError(CACHE_ANNUAIRE_PDF)
    annuaire = parse_annuaire(pdf_text(CACHE_ANNUAIRE_PDF))
    nouveaux: list[dict] = []
    if CACHE_NOUVEAUX_PDF.exists():
        nouveaux = parse_nouveaux(pdf_text(CACHE_NOUVEAUX_PDF))
    edges = merge_edges(annuaire, nouveaux)
    CACHE_EDGES.write_text(
        json.dumps(
            {
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "annuaire_url": AFCCRE_ANNUAIRE_URL,
                "nouveaux_url": AFCCRE_NOUVEAUX_URL,
                "annuaire_count": len(annuaire),
                "nouveaux_count": len(nouveaux),
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
