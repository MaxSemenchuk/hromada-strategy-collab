#!/usr/bin/env python3
"""Spike: HydroBASINS lev06 ∩ hromada centroids × PIN / water МСС.

Does NOT fold into match.py score. Writes provenance JSON under
data/research-log/basin-overlay-spike.json.

Usage:
  python3 scripts/analysis/basin_overlay_spike.py
  python3 scripts/analysis/basin_overlay_spike.py --fetch   # re-download zip if missing
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import urllib.request
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / "data" / "cache" / "water"
HYBAS_ZIP = CACHE / "hybas_eu_lev06_v1c.zip"
HYBAS_SHP = CACHE / "hybas_eu_lev06_v1c.shp"
HYBAS_UA = CACHE / "hybas_ua_lev06.gpkg"
OUTLINE = ROOT / "docs" / "geo" / "ukraine-outline.geojson"
GEO = ROOT / "data" / "cache" / "kse" / "geography.csv"
PIN = ROOT / "data" / "cache" / "kse" / "partnerships-hromadas-network.csv"
HROMADAS = ROOT / "data" / "releases" / "hromadas.json"
MATCHING = ROOT / "data" / "releases" / "matching-edges.json"
COMPLEMENTARY = ROOT / "data" / "releases" / "matching-edges.complementary.json"
CANDIDATES = ROOT / "data" / "releases" / "mss-candidates.json"
OUT = ROOT / "data" / "research-log" / "basin-overlay-spike.json"

HYBAS_URL = (
    "https://data.hydrosheds.org/file/hydrobasins/standard/hybas_eu_lev06_v1c.zip"
)

# Control cases from project history / REFERENCES
CONTROL_PAIRS = [
    {
        "id": "halytska_dubovetska",
        "label": "Галицька ↔ Дубовецька (planned shared water)",
        "names": (
            "Галицька міська територіальна громада",
            "Дубовецька сільська територіальна громада",
        ),
    },
    {
        "id": "halytska_burshtynska",
        "label": "Галицька ↔ Бурштинська (water corridor)",
        "names": (
            "Галицька міська територіальна громада",
            "Бурштинська міська територіальна громада",
        ),
    },
    {
        "id": "nizhyn_kozelets",
        "label": "Ніжинська ↔ Козелецька (Остер / Chernihiv cluster)",
        "names": (
            "Ніжинська міська територіальна громада",
            "Козелецька селищна територіальна громада",
        ),
    },
    {
        "id": "kozelets_baturyn",
        "label": "Козелецька ↔ Батуринська (Chernihiv cluster)",
        "names": (
            "Козелецька селищна територіальна громада",
            "Батуринська міська територіальна громада",
        ),
    },
]

DNISTER_REG = "721"


def _fetch_hybas() -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
    if not HYBAS_ZIP.exists():
        print(f"Downloading {HYBAS_URL} …")
        req = urllib.request.Request(
            HYBAS_URL, headers={"User-Agent": "hromada-strategy-collab/0.1"}
        )
        with urllib.request.urlopen(req, timeout=180) as resp:
            HYBAS_ZIP.write_bytes(resp.read())
        print(f"  wrote {HYBAS_ZIP} ({HYBAS_ZIP.stat().st_size / 1e6:.1f} MB)")
    if not HYBAS_SHP.exists():
        print(f"Unzipping {HYBAS_ZIP.name} …")
        with zipfile.ZipFile(HYBAS_ZIP) as zf:
            zf.extractall(CACHE)


def _clip_to_ua():
    import geopandas as gpd

    if HYBAS_UA.exists() and HYBAS_UA.stat().st_mtime >= HYBAS_SHP.stat().st_mtime:
        return gpd.read_file(HYBAS_UA)

    print("Clipping HydroBASINS to Ukraine outline …")
    basins = gpd.read_file(HYBAS_SHP)
    outline = gpd.read_file(OUTLINE).to_crs(basins.crs)
    minx, miny, maxx, maxy = outline.total_bounds
    sub = basins.cx[minx:maxx, miny:maxy].copy()
    mask = (
        outline.geometry.union_all()
        if hasattr(outline.geometry, "union_all")
        else outline.unary_union
    )
    clipped = gpd.clip(sub, mask)
    keep = [c for c in ("HYBAS_ID", "PFAF_ID", "SUB_AREA", "MAIN_BAS", "geometry") if c in clipped.columns]
    clipped = clipped[keep]
    if HYBAS_UA.exists():
        HYBAS_UA.unlink()
    clipped.to_file(HYBAS_UA, driver="GPKG")
    print(f"  {len(clipped)} basins → {HYBAS_UA}")
    return clipped


def _load_geo() -> dict[str, dict]:
    out: dict[str, dict] = {}
    with GEO.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            code = row["hromada_code"]
            try:
                lat = float(row["lat_center"])
                lon = float(row["lon_center"])
            except (TypeError, ValueError):
                continue
            out[code] = {
                "name": row.get("hromada") or "",
                "oblast": row.get("oblast_name") or "",
                "raion": row.get("raion_name") or "",
                "lat": lat,
                "lon": lon,
            }
    return out


def _name_to_code(geo: dict[str, dict], hromadas_path: Path) -> dict[str, str]:
    """Map full/short hromada names → KATOTTG."""
    by_name: dict[str, str] = {}
    for code, g in geo.items():
        if g["name"]:
            by_name[g["name"]] = code
    if hromadas_path.exists():
        rows = json.loads(hromadas_path.read_text(encoding="utf-8"))
        if isinstance(rows, dict):
            rows = rows.get("hromadas") or rows.get("rows") or []
        for r in rows:
            name = r.get("Name") or ""
            code = r.get("Katottg") or ""
            if name and code:
                by_name[name] = code
                # short form without «… територіальна громада»
                short = name
                for suffix in (
                    " міська територіальна громада",
                    " селищна територіальна громада",
                    " сільська територіальна громада",
                    " територіальна громада",
                ):
                    if short.endswith(suffix):
                        short = short[: -len(suffix)]
                        break
                by_name.setdefault(short, code)
    return by_name


def _assign_basins(geo: dict[str, dict], basins) -> dict[str, dict]:
    import geopandas as gpd
    from shapely.geometry import Point

    codes = list(geo.keys())
    pts = gpd.GeoDataFrame(
        {"hromada_code": codes},
        geometry=[Point(geo[c]["lon"], geo[c]["lat"]) for c in codes],
        crs="EPSG:4326",
    )
    joined = gpd.sjoin(pts, basins.to_crs(pts.crs), how="left", predicate="within")
    # if a point lands on a boundary / gap, try nearest
    missing = joined["HYBAS_ID"].isna()
    if missing.any():
        bas_union_idx = basins.reset_index(drop=True)
        for idx in joined.index[missing]:
            pt = joined.loc[idx, "geometry"]
            # nearest polygon by distance
            dists = bas_union_idx.geometry.distance(pt)
            j = int(dists.idxmin())
            joined.at[idx, "HYBAS_ID"] = bas_union_idx.at[j, "HYBAS_ID"]
            if "PFAF_ID" in bas_union_idx.columns:
                joined.at[idx, "PFAF_ID"] = bas_union_idx.at[j, "PFAF_ID"]
            if "SUB_AREA" in bas_union_idx.columns:
                joined.at[idx, "SUB_AREA"] = bas_union_idx.at[j, "SUB_AREA"]

    # one row per hromada (sjoin can duplicate on overlaps — take first)
    assign: dict[str, dict] = {}
    for _, row in joined.iterrows():
        code = row["hromada_code"]
        if code in assign:
            continue
        hid = row.get("HYBAS_ID")
        if hid is None or (isinstance(hid, float) and hid != hid):
            continue
        assign[code] = {
            "basin_id": int(hid),
            "pfaf_id": int(row["PFAF_ID"]) if row.get("PFAF_ID") == row.get("PFAF_ID") else None,
            "sub_area_km2": float(row["SUB_AREA"]) if row.get("SUB_AREA") == row.get("SUB_AREA") else None,
            "oblast": geo[code]["oblast"],
            "name": geo[code]["name"],
            "lat": geo[code]["lat"],
            "lon": geo[code]["lon"],
        }
    return assign


def _pair_stats(
    pairs: list[tuple[str, str]],
    assign: dict[str, dict],
    geo: dict[str, dict],
) -> dict:
    same_basin = same_oblast = both_geo = 0
    cross_oblast_same_basin = 0
    missing = 0
    for a, b in pairs:
        ga, gb = assign.get(a), assign.get(b)
        if not ga or not gb:
            missing += 1
            continue
        both_geo += 1
        oa = ga.get("oblast") or geo.get(a, {}).get("oblast")
        ob = gb.get("oblast") or geo.get(b, {}).get("oblast")
        so = bool(oa and ob and oa == ob)
        sb = ga["basin_id"] == gb["basin_id"]
        if so:
            same_oblast += 1
        if sb:
            same_basin += 1
        if sb and not so:
            cross_oblast_same_basin += 1
    n = both_geo
    return {
        "pairs": len(pairs),
        "pairs_with_geo": n,
        "missing_assignment": missing,
        "same_oblast": same_oblast,
        "same_basin": same_basin,
        "same_oblast_share": round(same_oblast / n, 4) if n else None,
        "same_basin_share": round(same_basin / n, 4) if n else None,
        "cross_oblast_same_basin": cross_oblast_same_basin,
        "lift_basin_minus_oblast_pp": (
            round(100 * (same_basin / n - same_oblast / n), 2) if n else None
        ),
    }


def _unique_undirected(pairs: list[tuple[str, str]]) -> list[tuple[str, str]]:
    seen: set[frozenset[str]] = set()
    out: list[tuple[str, str]] = []
    for a, b in pairs:
        if not a or not b or a == b:
            continue
        key = frozenset((a, b))
        if key in seen:
            continue
        seen.add(key)
        out.append((a, b))
    return out


def _load_pin_pairs() -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    with PIN.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            pairs.append((row["hromada_code.x"], row["hromada_code.y"]))
    return _unique_undirected(pairs)


def _dnister_codes() -> list[str]:
    codes: set[str] = set()
    with PIN.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["register_number"] == DNISTER_REG:
                codes.add(row["hromada_code.x"])
                codes.add(row["hromada_code.y"])
    return sorted(codes)


def _theme_id(obj: dict) -> str | None:
    pkg = obj.get("package") or {}
    return pkg.get("theme_id") or obj.get("suggested_theme_id")


def _resolve_pair_names(
    a_name: str, b_name: str, by_name: dict[str, str]
) -> tuple[str | None, str | None]:
    return by_name.get(a_name), by_name.get(b_name)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--fetch", action="store_true", help="Download HydroBASINS zip if missing")
    args = ap.parse_args()

    try:
        import geopandas  # noqa: F401
    except ImportError:
        print("ERROR: geopandas required (pip install geopandas)", file=sys.stderr)
        return 1

    if args.fetch or not HYBAS_SHP.exists():
        _fetch_hybas()
    if not HYBAS_SHP.exists():
        print(f"ERROR: missing {HYBAS_SHP}; re-run with --fetch", file=sys.stderr)
        return 1

    basins = _clip_to_ua()
    geo = _load_geo()
    by_name = _name_to_code(geo, HROMADAS)
    print(f"Assigning {len(geo)} centroids → basins …")
    assign = _assign_basins(geo, basins)
    print(f"  assigned {len(assign)} / {len(geo)}")

    basin_counts = Counter(v["basin_id"] for v in assign.values())
    oblast_basin: dict[str, set[int]] = defaultdict(set)
    for v in assign.values():
        if v["oblast"]:
            oblast_basin[v["oblast"]].add(v["basin_id"])

    pin_pairs = _load_pin_pairs()
    pin_stats = _pair_stats(pin_pairs, assign, geo)

    # Matching edges: all + water theme
    matching = json.loads(MATCHING.read_text(encoding="utf-8"))
    m_edges = matching if isinstance(matching, list) else matching.get("edges", [])
    all_m: list[tuple[str, str]] = []
    water_m: list[tuple[str, str]] = []
    for e in m_edges:
        a, b = _resolve_pair_names(e.get("a", ""), e.get("b", ""), by_name)
        if not a or not b:
            continue
        all_m.append((a, b))
        if _theme_id(e) == "water":
            water_m.append((a, b))
    all_m = _unique_undirected(all_m)
    water_m = _unique_undirected(water_m)

    # Complementary water
    comp = json.loads(COMPLEMENTARY.read_text(encoding="utf-8"))
    c_edges = comp if isinstance(comp, list) else comp.get("edges", [])
    water_c: list[tuple[str, str]] = []
    for e in c_edges:
        if _theme_id(e) != "water":
            continue
        a = e.get("a_katottg") or by_name.get(e.get("a", ""))
        b = e.get("b_katottg") or by_name.get(e.get("b", ""))
        if a and b:
            water_c.append((a, b))
    water_c = _unique_undirected(water_c)

    # mss-candidates water hypotheses
    cands = json.loads(CANDIDATES.read_text(encoding="utf-8"))
    water_hyp: list[tuple[str, str]] = []
    for h in cands.get("hypotheses") or []:
        if _theme_id(h) != "water":
            continue
        a, b = _resolve_pair_names(h.get("a", ""), h.get("b", ""), by_name)
        if a and b:
            water_hyp.append((a, b))
    water_hyp = _unique_undirected(water_hyp)

    # Random baseline: sample of same-size random pairs from assigned codes
    import random

    rng = random.Random(42)
    codes = list(assign.keys())
    random_pairs: list[tuple[str, str]] = []
    while len(random_pairs) < min(2000, len(pin_pairs)):
        a, b = rng.sample(codes, 2)
        random_pairs.append((a, b))
    random_pairs = _unique_undirected(random_pairs)

    control = []
    for case in CONTROL_PAIRS:
        a_name, b_name = case["names"]
        a, b = by_name.get(a_name), by_name.get(b_name)
        entry = {
            "id": case["id"],
            "label": case["label"],
            "a": a_name,
            "b": b_name,
            "a_katottg": a,
            "b_katottg": b,
        }
        if a and b and a in assign and b in assign:
            entry["a_basin"] = assign[a]["basin_id"]
            entry["b_basin"] = assign[b]["basin_id"]
            entry["same_basin"] = assign[a]["basin_id"] == assign[b]["basin_id"]
            entry["a_oblast"] = assign[a]["oblast"]
            entry["b_oblast"] = assign[b]["oblast"]
            entry["same_oblast"] = assign[a]["oblast"] == assign[b]["oblast"]
        else:
            entry["same_basin"] = None
            entry["note"] = "unresolved name or missing assignment"
        control.append(entry)

    dnister = _dnister_codes()
    dnister_basins = sorted({assign[c]["basin_id"] for c in dnister if c in assign})
    dnister_oblasts = sorted({assign[c]["oblast"] for c in dnister if c in assign and assign[c]["oblast"]})

    # Decision heuristic from plan: lift if same_basin clearly exceeds same_oblast
    # OR (more realistic) if same_basin << same_oblast on PIN but water pairs stay
    # high same_basin while random is low — i.e. basin is finer than oblast.
    # "Trivial" ≈ same_basin_share ≈ same_oblast_share on PIN (basin as coarse as oblast).
    pin_sb = pin_stats["same_basin_share"] or 0
    pin_so = pin_stats["same_oblast_share"] or 0
    # Finer than oblast: same_basin share materially below same_oblast on dense PIN
    finer_than_oblast = pin_so - pin_sb >= 0.10
    water_stats = _pair_stats(water_m, assign, geo)
    water_c_stats = _pair_stats(water_c, assign, geo)
    rand_stats = _pair_stats(random_pairs, assign, geo)
    # Useful signal: water pairs more same-basin than random, and not identical to oblast
    water_sb = water_stats["same_basin_share"] or 0
    rand_sb = rand_stats["same_basin_share"] or 0
    useful = finer_than_oblast and (water_sb - rand_sb >= 0.15)
    # Also useful if control water cases share basin while Chernihiv cluster spans basins
    control_water_ok = all(
        c.get("same_basin") is True
        for c in control
        if c["id"] in ("halytska_dubovetska", "halytska_burshtynska")
    )

    decision = {
        "finer_than_oblast": finer_than_oblast,
        "water_above_random": (water_sb - rand_sb) if water_stats["pairs_with_geo"] else None,
        "useful_for_overlay": bool(useful or (finer_than_oblast and control_water_ok)),
        "rationale": (
            "Basin underlay warranted: lev06 is finer than oblast and water/"
            "control pairs cluster in-basin above random."
            if (useful or (finer_than_oblast and control_water_ok))
            else "No clear lift beyond oblast for product overlay at lev06; "
            "document only (try lev07/08 later if needed)."
        ),
        "add_map_underlay": bool(useful or (finer_than_oblast and control_water_ok)),
    }

    report = {
        "generated_at": __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc
        ).isoformat(),
        "source": {
            "hydrobasins": "HydroBASINS EU lev06 v1c (HydroSHEDS)",
            "url": HYBAS_URL,
            "license_note": "HydroSHEDS license — free for non-commercial/research; see HydroBASINS tech doc",
            "caveat": "Hydrological catchments, NOT legal Ukrainian river basin districts (DAVR RBD). DAVR WFS unreachable at spike time.",
            "ua_basins": int(len(basins)),
            "hromadas_assigned": len(assign),
            "hromadas_geo": len(geo),
        },
        "basin_size": {
            "unique_basins_with_hromadas": len(basin_counts),
            "hromadas_per_basin_median": sorted(basin_counts.values())[len(basin_counts) // 2]
            if basin_counts
            else None,
            "oblasts_spanning_multiple_basins": sum(
                1 for s in oblast_basin.values() if len(s) > 1
            ),
            "mean_basins_per_oblast": round(
                sum(len(s) for s in oblast_basin.values()) / len(oblast_basin), 2
            )
            if oblast_basin
            else None,
        },
        "stats": {
            "pin_undirected": pin_stats,
            "matching_all": _pair_stats(all_m, assign, geo),
            "matching_water_theme": water_stats,
            "complementary_water": water_c_stats,
            "candidates_water_hypotheses": _pair_stats(water_hyp, assign, geo),
            "random_pairs": rand_stats,
        },
        "control_cases": control,
        "dnister_canyon_reg721": {
            "parties": len(dnister),
            "assigned": sum(1 for c in dnister if c in assign),
            "unique_basins": dnister_basins,
            "unique_oblasts": dnister_oblasts,
            "single_basin": len(dnister_basins) == 1,
        },
        "decision": decision,
        # Compact assignment sample for provenance (full map is large)
        "assignment_top_basins": [
            {"basin_id": bid, "n_hromadas": n}
            for bid, n in basin_counts.most_common(15)
        ],
    }

    # Full assignment sidecar (for follow-up map build)
    assign_path = ROOT / "data" / "research-log" / "hromada-basin-assignment.json"
    assign_out = {
        "source": report["source"],
        "assignments": {
            code: {
                "basin_id": v["basin_id"],
                "pfaf_id": v["pfaf_id"],
                "oblast": v["oblast"],
                "name": v["name"],
            }
            for code, v in assign.items()
        },
    }
    assign_path.write_text(
        json.dumps(assign_out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # stdout summary
    print("\n=== basin overlay spike ===")
    for label, st in report["stats"].items():
        print(
            f"{label:28s}  n={st['pairs_with_geo']:4d}  "
            f"same_oblast={st['same_oblast_share']}  "
            f"same_basin={st['same_basin_share']}  "
            f"Δpp={st['lift_basin_minus_oblast_pp']}"
        )
    print("\ncontrol:")
    for c in control:
        print(
            f"  {c['id']}: same_basin={c.get('same_basin')}  "
            f"same_oblast={c.get('same_oblast')}  "
            f"basins={c.get('a_basin')}/{c.get('b_basin')}"
        )
    print(
        f"\nДністровський каньйон (reg#721): {len(dnister)} parties, "
        f"basins={dnister_basins}, oblasts={dnister_oblasts}"
    )
    print(f"\ndecision.add_map_underlay = {decision['add_map_underlay']}")
    print(f"  {decision['rationale']}")
    print(f"\nwrote {OUT}")
    print(f"wrote {assign_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
