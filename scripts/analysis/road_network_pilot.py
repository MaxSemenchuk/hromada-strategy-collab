#!/usr/bin/env python3
"""
Road-network pilot: does drive time between hromada centres explain real
domestic ММС ties better than straight-line distance?

Needs a local OSRM server (see docs/road-network-pilot.md):
    docker run -p 5050:5000 -v data/cache/osrm:/data osrm/osrm-backend \
        osrm-routed --algorithm mld --max-table-size 2000 /data/ukraine-latest.osrm

Usage: python scripts/analysis/road_network_pilot.py [--osrm http://localhost:5050]
Writes data/research-log/road-network-pilot.json and a drive-time matrix cache.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[2]
GEO = ROOT / "data" / "cache" / "kse" / "geography.csv"
HROMADAS = ROOT / "data" / "releases" / "hromadas.json"
CACHE = ROOT / "data" / "cache" / "osrm" / "drive-minutes.npy"
OUT = ROOT / "data" / "research-log" / "road-network-pilot.json"
BATCH = 500  # sources/destinations per /table call


def haversine_matrix(lat: np.ndarray, lon: np.ndarray) -> np.ndarray:
    p = np.radians(lat)[:, None]
    q = np.radians(lat)[None, :]
    dl = np.radians(lon)[None, :] - np.radians(lon)[:, None]
    a = np.sin((q - p) / 2) ** 2 + np.cos(p) * np.cos(q) * np.sin(dl / 2) ** 2
    return 2 * 6371.0 * np.arcsin(np.sqrt(a))


def osrm_matrix(base: str, lat: np.ndarray, lon: np.ndarray) -> np.ndarray:
    n = len(lat)
    coords = ";".join(f"{x:.6f},{y:.6f}" for x, y in zip(lon, lat))
    out = np.full((n, n), np.nan, dtype=np.float32)
    for i0 in range(0, n, BATCH):
        for j0 in range(0, n, BATCH):
            src = range(i0, min(i0 + BATCH, n))
            dst = range(j0, min(j0 + BATCH, n))
            idx = sorted(set(src) | set(dst))
            pos = {k: p for p, k in enumerate(idx)}
            c = ";".join(
                f"{lon[k]:.6f},{lat[k]:.6f}" for k in idx
            )
            r = requests.get(
                f"{base}/table/v1/driving/{c}",
                params={
                    "sources": ";".join(str(pos[k]) for k in src),
                    "destinations": ";".join(str(pos[k]) for k in dst),
                },
                timeout=600,
            )
            r.raise_for_status()
            d = np.array(r.json()["durations"], dtype=float)
            d[d == None] = np.nan  # noqa: E711
            out[i0 : i0 + len(src), j0 : j0 + len(dst)] = d / 60.0
        print(f"  rows {i0}-{min(i0 + BATCH, n)} done", flush=True)
    return out


def known_pairs() -> set[frozenset[str]]:
    import sys

    sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
    from enrich_from_kse import partnerships_network_pairs, plich_o_plich_pairs

    pairs = set(partnerships_network_pairs())
    pairs |= {k for k, v in plich_o_plich_pairs().items() if v >= 1.0}
    return pairs


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--osrm", default="http://localhost:5050")
    args = ap.parse_args()

    geo = pd.read_csv(GEO, usecols=["hromada_code", "hromada", "oblast_name", "lat_center", "lon_center"])
    geo = geo.dropna(subset=["lat_center", "lon_center"]).drop_duplicates("hromada_code").reset_index(drop=True)
    lat, lon = geo.lat_center.to_numpy(float), geo.lon_center.to_numpy(float)
    codes = geo.hromada_code.tolist()
    n = len(codes)
    print(f"{n} hromada centres")

    if CACHE.exists() and np.load(CACHE).shape == (n, n):
        mins = np.load(CACHE)
    else:
        mins = osrm_matrix(args.osrm, lat, lon)
        np.save(CACHE, mins)
    km = haversine_matrix(lat, lon)

    # Detour factor: drive time vs what straight line at 60 km/h would give.
    with np.errstate(invalid="ignore", divide="ignore"):
        detour = mins / (km / 60 * 60)  # minutes / (km at 1 km/min)
    iu = np.triu_indices(n, 1)
    near = km[iu] <= 60
    print(f"median drive/straight ratio (≤60 km pairs): {np.nanmedian(detour[iu][near]):.2f}")
    unreachable = int(np.isnan(mins[iu]).sum())
    print(f"unreachable pairs: {unreachable}")

    # --- Validation: known ММС ties vs random pairs, within same oblast pool ---
    known = known_pairs()
    code_idx = {c: i for i, c in enumerate(codes)}
    kp = [(code_idx[a], code_idx[b]) for k in known for a, b in [tuple(k)] if a in code_idx and b in code_idx]
    print(f"known ММС pairs with coordinates: {len(kp)} of {len(known)}")
    ki = np.array([i for i, _ in kp]); kj = np.array([j for _, j in kp])
    k_min, k_km = mins[ki, kj], km[ki, kj]

    # Null: for each known pair, a random hromada at similar straight-line distance (±15%)
    rng = np.random.default_rng(7)
    wins = ties = losses = 0
    null_min = []
    for i, j in kp:
        d = km[i, j]
        cand = np.where((km[i] > d * 0.85) & (km[i] < d * 1.15) & (np.arange(n) != j) & ~np.isnan(mins[i]))[0]
        if len(cand) == 0:
            continue
        c = rng.choice(cand, size=min(50, len(cand)), replace=False)
        null_min.extend(mins[i, c])
        # Is the known partner faster to reach than the same-distance decoys?
        frac_slower = float(np.mean(mins[i, c] > mins[i, j]))
        wins += frac_slower > 0.5
        losses += frac_slower < 0.5
        ties += frac_slower == 0.5
    summary = {
        "n_hromadas": n,
        "n_known_pairs": len(kp),
        "known_drive_min_median": float(np.nanmedian(k_min)),
        "known_drive_min_p75": float(np.nanpercentile(k_min, 75)),
        "known_km_median": float(np.nanmedian(k_km)),
        "known_detour_median": float(np.nanmedian(k_min / (k_km))),
        "decoy_same_km_drive_min_median": float(np.nanmedian(null_min)) if null_min else None,
        "known_faster_than_same_km_decoys": {"yes": int(wins), "no": int(losses), "tie": int(ties)},
    }
    # Predictive power: AUC of (-drive time) vs (-km) separating known pairs from all pairs ≤150 km
    pool = (km[iu] <= 150) & ~np.isnan(mins[iu])
    pi, pj = iu[0][pool], iu[1][pool]
    key = {(min(a, b), max(a, b)) for a, b in kp}
    y = np.array([(a, b) in key for a, b in zip(pi, pj)])

    def auc(score: np.ndarray) -> float:
        order = score.argsort(); ranks = np.empty(len(score)); ranks[order] = np.arange(len(score))
        pos = y.sum(); neg = len(y) - pos
        return float((ranks[y].sum() - pos * (pos - 1) / 2) / (pos * neg)) if pos and neg else float("nan")

    summary["auc_minus_drive_min"] = auc(-mins[pi, pj])
    summary["auc_minus_km"] = auc(-km[pi, pj])

    # --- Road clusters: connected components at ≤ T minutes (single linkage) ---
    clusters = {}
    for T in (20, 30):
        adj = mins <= T
        np.fill_diagonal(adj, False)
        seen = np.full(n, -1); cid = 0
        for s in range(n):
            if seen[s] >= 0:
                continue
            stack = [s]; seen[s] = cid
            while stack:
                u = stack.pop()
                for v in np.where(adj[u])[0]:
                    if seen[v] < 0:
                        seen[v] = cid; stack.append(v)
            cid += 1
        sizes = np.bincount(seen)
        clusters[f"T{T}"] = {"n_clusters": int(cid), "largest": int(sizes.max()), "singletons": int((sizes == 1).sum())}

    # Bucha–Hostomel–Irpin sanity check
    names = geo.hromada.tolist()
    probe = {}
    for nm in ("Бучанська", "Гостомельська", "Ірпінська", "Ворзельська"):
        ix = [i for i, x in enumerate(names) if x == nm]
        probe[nm] = ix
    sample = {}
    if probe["Бучанська"] and probe["Гостомельська"]:
        a, b = probe["Бучанська"][0], probe["Гостомельська"][0]
        sample["Буча-Гостомель"] = {"km": float(km[a, b]), "drive_min": float(mins[a, b])}

    # Biggest km-vs-drive divergences (river/mountain barriers) among close pairs
    close = (km[iu] <= 30) & ~np.isnan(mins[iu])
    ci, cj = iu[0][close], iu[1][close]
    ratio = mins[ci, cj] / np.maximum(km[ci, cj], 1)
    top = np.argsort(-ratio)[:15]
    barriers = [
        {"a": names[ci[t]], "b": names[cj[t]], "oblast": geo.oblast_name[ci[t]], "km": round(float(km[ci[t], cj[t]]), 1), "drive_min": round(float(mins[ci[t], cj[t]]), 1)}
        for t in top
    ]

    res = {"summary": summary, "clusters": clusters, "samples": sample, "largest_detours_within_30km": barriers}
    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(res, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
