"""Lazy-fetch KSE-Loc-Data-Hub covariates and join on KATOTTG (hromada_code)."""

from __future__ import annotations

import json
import math
import ssl
import urllib.request
from functools import lru_cache
from io import StringIO
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
PIN_PATH = ROOT / "data" / "sources" / "kse-pin.json"
CACHE_DIR = ROOT / "data" / "cache" / "kse"


def load_pin() -> dict:
    return json.loads(PIN_PATH.read_text(encoding="utf-8"))


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


def _download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "hromada-strategy-collab/0.1"})
    with urllib.request.urlopen(req, context=_ssl_context(), timeout=120) as resp:
        dest.write_bytes(resp.read())


@lru_cache(maxsize=8)
def _fetch_csv(name: str) -> pd.DataFrame:
    pin = load_pin()
    filename = pin["files"][name]
    url = f"{pin['base_url']}/{filename}"
    dest = CACHE_DIR / filename
    if not dest.exists():
        try:
            _download(url, dest)
        except Exception as exc:
            # Fallback: try without custom SSL (some envs already trust GitHub)
            try:
                pd.read_csv(url, low_memory=False).to_csv(dest, index=False)
            except Exception as exc2:
                raise RuntimeError(f"Failed to fetch KSE {name} from {url}: {exc}; fallback: {exc2}") from exc2
    return pd.read_csv(dest, low_memory=False)


@lru_cache(maxsize=1)
def geography_df() -> pd.DataFrame | None:
    try:
        df = _fetch_csv("geography")
    except Exception as exc:
        print(f"WARNING: KSE geography unavailable ({exc}); using oblast/rayon fallback only")
        return None
    for col in ("lat_center", "lon_center"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df.set_index("hromada_code", drop=False)


@lru_cache(maxsize=1)
def edem_df() -> pd.DataFrame:
    return _fetch_csv("edem").set_index("hromada_code", drop=False)


@lru_cache(maxsize=1)
def partnerships_network_pairs() -> set[frozenset[str]]:
    try:
        df = _fetch_csv("partnerships_network")
    except Exception as exc:
        print(f"WARNING: KSE partnerships network unavailable ({exc})")
        return set()
    pairs: set[frozenset[str]] = set()
    for _, row in df.iterrows():
        a, b = str(row["hromada_code.x"]), str(row["hromada_code.y"])
        if a and b and a != "nan" and b != "nan":
            pairs.add(frozenset((a, b)))
    return pairs


@lru_cache(maxsize=1)
def plich_o_plich_pairs() -> dict[frozenset[str], float]:
    """Domestic МСС network signal from Пліч-о-пліч news-mention mining
    (data/releases/plich-o-plich.json) — separate from the KSE academic
    partnerships snapshot above, same kind of signal (a real, ongoing
    domestic hromada-to-hromada cooperation program). bilateral_confirmed
    edges (a memorandum, or an article naming exactly that pair) score the
    same as a KSE tie (1.0); comention-only edges (could be inflated by a
    multi-hromada roundup article's fully-connected clique — see the
    dataset's own notes) score lower, not full confidence."""
    path = ROOT / "data" / "releases" / "plich-o-plich.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"WARNING: plich-o-plich.json unavailable ({exc})")
        return {}
    pairs: dict[frozenset[str], float] = {}
    for e in data.get("edges") or []:
        a, b = e.get("a_katottg"), e.get("b_katottg")
        if not a or not b:
            continue
        score = 1.0 if e.get("bilateral_confirmed") else 0.5
        key = frozenset((a, b))
        pairs[key] = max(pairs.get(key, 0.0), score)
    return pairs


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _admin_fallback(
    oblast_a: str | None,
    oblast_b: str | None,
    rayon_a: str | None,
    rayon_b: str | None,
) -> float:
    if oblast_a and oblast_b and oblast_a == oblast_b:
        if rayon_a and rayon_b and rayon_a == rayon_b:
            return 0.7
        return 0.4
    return 0.0


def geo_score(
    katottg_a: str | None,
    katottg_b: str | None,
    oblast_a: str | None = None,
    oblast_b: str | None = None,
    rayon_a: str | None = None,
    rayon_b: str | None = None,
) -> float:
    """0–1 proximity: close centers / same rayon / same oblast."""
    geo = geography_df()
    if katottg_a and katottg_b and geo is not None:
        if katottg_a in geo.index and katottg_b in geo.index:
            row_a = geo.loc[katottg_a]
            row_b = geo.loc[katottg_b]
            lat_a, lon_a = row_a.get("lat_center"), row_a.get("lon_center")
            lat_b, lon_b = row_b.get("lat_center"), row_b.get("lon_center")
            if pd.notna(lat_a) and pd.notna(lon_a) and pd.notna(lat_b) and pd.notna(lon_b):
                dist = haversine_km(float(lat_a), float(lon_a), float(lat_b), float(lon_b))
                if dist <= 15:
                    return 1.0
                if dist <= 40:
                    return 0.85
                if dist <= 80:
                    return 0.6
                if dist <= 150:
                    return 0.35

            ra, rb = str(row_a.get("raion_name", "")), str(row_b.get("raion_name", ""))
            oa, ob = str(row_a.get("oblast_name", "")), str(row_b.get("oblast_name", ""))
            if ra and rb and ra == rb and ra != "nan":
                return 0.75
            if oa and ob and oa == ob and oa != "nan":
                return 0.45

    return _admin_fallback(oblast_a, oblast_b, rayon_a, rayon_b)


def mss_network_score(katottg_a: str | None, katottg_b: str | None) -> float:
    """Domestic МСС network-tie signal — KSE academic snapshot OR'd with
    Пліч-о-пліч (higher of the two when both have a row for this pair)."""
    if not katottg_a or not katottg_b:
        return 0.0
    key = frozenset((katottg_a, katottg_b))
    if key in partnerships_network_pairs():
        return 1.0
    return plich_o_plich_pairs().get(key, 0.0)


def edem_total(katottg: str | None) -> float | None:
    """Return edem_total for scraped hromadas; None if absent from edem-data.csv."""
    if not katottg:
        return None
    try:
        df = edem_df()
    except Exception:
        return None
    if katottg not in df.index:
        return None
    val = df.loc[katottg].get("edem_total")
    return float(val) if pd.notna(val) else None


@lru_cache(maxsize=1)
def budget_df() -> pd.DataFrame | None:
    try:
        return _fetch_csv("budget")
    except Exception as exc:
        print(f"WARNING: KSE budget unavailable ({exc})")
        return None


@lru_cache(maxsize=1)
def latest_budget_df() -> pd.DataFrame | None:
    """One row per hromada_code — latest year in the 2020–2022 panel."""
    df = budget_df()
    if df is None or df.empty:
        return None
    out = df.copy()
    out["year"] = pd.to_numeric(out["year"], errors="coerce")
    out = out.sort_values("year").groupby("hromada_code", as_index=False).tail(1)
    return out.set_index("hromada_code", drop=False)


@lru_cache(maxsize=1)
def dfrr_df() -> pd.DataFrame | None:
    try:
        return _fetch_csv("dfrr")
    except Exception as exc:
        print(f"WARNING: KSE DFRR unavailable ({exc})")
        return None


@lru_cache(maxsize=1)
def competence_df() -> pd.DataFrame | None:
    """Youth councils/centers + business support — ~376 hromadas only."""
    try:
        return _fetch_csv("competence").set_index("hromada_code", drop=False)
    except Exception as exc:
        print(f"WARNING: KSE competence unavailable ({exc})")
        return None


@lru_cache(maxsize=1)
def population_df() -> pd.DataFrame | None:
    try:
        return _fetch_csv("population").set_index("hromada_code", drop=False)
    except Exception as exc:
        print(f"WARNING: KSE population unavailable ({exc})")
        return None


@lru_cache(maxsize=1)
def war_status_df() -> pd.DataFrame | None:
    try:
        df = _fetch_csv("war_status")
    except Exception as exc:
        print(f"WARNING: KSE war status unavailable ({exc})")
        return None
    if "hromada_code" not in df.columns:
        return None
    return df.set_index("hromada_code", drop=False)


@lru_cache(maxsize=1)
def health_facilities_by_hromada() -> pd.DataFrame | None:
    """Join health_facilities (name-only) onto hromada_code via hromada.csv."""
    try:
        health = _fetch_csv("health")
        hromada = _fetch_csv("hromada")
    except Exception as exc:
        print(f"WARNING: KSE health facilities unavailable ({exc})")
        return None
    if "hromada_name" not in health.columns:
        return None
    # Prefer unique name matches; drop ambiguous names
    name_counts = hromada["hromada_name"].value_counts()
    unique_names = set(name_counts[name_counts == 1].index)
    h_unique = hromada[hromada["hromada_name"].isin(unique_names)][
        ["hromada_code", "hromada_name"]
    ]
    merged = health.merge(h_unique, on="hromada_name", how="inner")
    if merged.empty:
        return None
    return merged.set_index("hromada_code", drop=False)


@lru_cache(maxsize=1)
def settlement_to_hromada() -> dict[str, str]:
    """Map settlement CATOTTG → hromada CATOTTG (for DREAM location gazetteers)."""
    try:
        admin = _fetch_csv("admin_map")
    except Exception as exc:
        print(f"WARNING: KSE admin map unavailable ({exc})")
        return {}
    mapping: dict[str, str] = {}
    for _, row in admin.iterrows():
        s = str(row.get("settlement_code") or "").strip()
        h = str(row.get("hromada_code") or "").strip()
        if s and h and s != "nan" and h != "nan":
            mapping[s] = h
        # also allow identity lookup when a hromada code is used directly
        if h and h != "nan":
            mapping.setdefault(h, h)
    return mapping


@lru_cache(maxsize=1)
def koatuu_to_hromada() -> dict[str, str]:
    """Map legacy KOATUU (10-digit, zero-padded) → hromada CATOTTG.

    Sources both `settlement_code_old` (matches city/town self-administered
    portals, e.g. e-dem.ua city councils) and `rada_code` (matches village/
    settlement council-level portals) from KSE's admin map — a KOATUU value
    can land on either depending on how the external platform registered the
    community. First writer wins on the rare key collision (~0.1% of rows).
    """
    try:
        admin = _fetch_csv("admin_map")
    except Exception as exc:
        print(f"WARNING: KSE admin map unavailable ({exc})")
        return {}
    mapping: dict[str, str] = {}
    for _, row in admin.iterrows():
        h = str(row.get("hromada_code") or "").strip()
        if not h or h == "nan":
            continue
        for col in ("settlement_code_old", "rada_code"):
            k = str(row.get(col) or "").strip()
            if k and k != "nan":
                k = k.zfill(10)
                mapping.setdefault(k, h)
    return mapping
