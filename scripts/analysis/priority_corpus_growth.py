#!/usr/bin/env python3
"""Suggest next strategy extractions to grow PIN ∩ corpus overlap.

Ranks hromadas that:
  - lack Goals in the release corpus
  - share at least one KSE PIN edge with a corpus member

Primary sort: # of PIN links into the corpus (more overlaps for the PIN∩corpus
report). Secondary: PIN degree. Writes data/releases/corpus-growth-priority.json
and prints a short table.

Note: project-history also recommends low-МСС oblasts for *discovery* whitespace;
this list optimises for *validation coverage*, not cold-start matchmaking.
"""

from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))

HROMADAS = ROOT / "data" / "releases" / "hromadas.json"
PIN = ROOT / "data" / "cache" / "kse" / "partnerships-hromadas-network.csv"
OUT = ROOT / "data" / "releases" / "corpus-growth-priority.json"
LIMIT = 40


def ensure_pin_csv() -> Path:
    if PIN.exists():
        return PIN
    from enrich_from_kse import partnerships_network_pairs  # noqa: WPS433

    partnerships_network_pairs()  # populates cache via enrich_from_kse
    if not PIN.exists():
        raise SystemExit(f"Missing {PIN} — fetch KSE partnerships first")
    return PIN


def load_pin() -> tuple[set[tuple[str, str]], dict[str, int], dict[str, str]]:
    pairs: set[tuple[str, str]] = set()
    degree: dict[str, int] = defaultdict(int)
    labels: dict[str, str] = {}
    with ensure_pin_csv().open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            a, b = row["hromada_code.x"], row["hromada_code.y"]
            if not a or not b or a == b:
                continue
            key = tuple(sorted((a, b)))
            if key in pairs:
                continue
            pairs.add(key)
            degree[a] += 1
            degree[b] += 1
            labels[a] = row.get("hromada_name.x") or a
            labels[b] = row.get("hromada_name.y") or b
    return pairs, dict(degree), labels


def main() -> None:
    rows = json.loads(HROMADAS.read_text(encoding="utf-8"))
    by_code: dict[str, dict] = {}
    for r in rows:
        code = r.get("Katottg")
        if code:
            by_code[code] = r

    corpus_codes = {
        code
        for code, r in by_code.items()
        if (r.get("Goals") or "").strip()
    }
    pin_pairs, degree, pin_labels = load_pin()

    # code -> set of corpus neighbours
    corpus_links: dict[str, set[str]] = defaultdict(set)
    for a, b in pin_pairs:
        if a in corpus_codes and b not in corpus_codes:
            corpus_links[b].add(a)
        elif b in corpus_codes and a not in corpus_codes:
            corpus_links[a].add(b)

    # oblast corpus coverage (among mainland metadata rows with oblast)
    oblast_total: dict[str, int] = defaultdict(int)
    oblast_corpus: dict[str, int] = defaultdict(int)
    for r in rows:
        ob = r.get("Oblast")
        if not ob or not r.get("Katottg"):
            continue
        oblast_total[ob] += 1
        if (r.get("Goals") or "").strip():
            oblast_corpus[ob] += 1

    candidates = []
    for code, neighbours in corpus_links.items():
        meta = by_code.get(code, {})
        oblast = meta.get("Oblast")
        total = oblast_total.get(oblast or "", 0)
        cov = oblast_corpus.get(oblast or "", 0)
        candidates.append(
            {
                "katottg": code,
                "name": meta.get("Name") or pin_labels.get(code) or code,
                "oblast": oblast,
                "pinDegree": degree.get(code, 0),
                "corpusPinLinks": len(neighbours),
                "corpusNeighbourCodes": sorted(neighbours),
                "oblastCorpusCount": cov,
                "oblastTotal": total,
                "oblastCorpusShare": round(cov / total, 3) if total else None,
                "sourceQuality": meta.get("SourceQuality"),
                "hasMetadataRow": code in by_code,
            }
        )

    candidates.sort(
        key=lambda c: (
            -c["corpusPinLinks"],
            -c["pinDegree"],
            c["oblastCorpusShare"] if c["oblastCorpusShare"] is not None else 1.0,
            c["name"] or "",
        )
    )
    top = candidates[:LIMIT]

    payload = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "purpose": (
            "Grow strategy corpus where it adds PIN∩corpus validation pairs "
            "(neighbours of current Goals corpus in the KSE МСС network)."
        ),
        "corpusSize": len(corpus_codes),
        "pinEdges": len(pin_pairs),
        "candidatesTotal": len(candidates),
        "limit": LIMIT,
        "candidates": top,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        f"Corpus Goals={len(corpus_codes)} · PIN neighbours missing Goals={len(candidates)} "
        f"· showing top {len(top)}"
    )
    print(f"{'#':>3}  {'links':>5}  {'deg':>4}  {'oblast cov':>10}  name")
    for i, c in enumerate(top, 1):
        share = c["oblastCorpusShare"]
        share_s = f"{share:.0%}" if share is not None else "—"
        short = (c["name"] or "").replace("територіальна громада", "").strip()
        print(f"{i:>3}  {c['corpusPinLinks']:>5}  {c['pinDegree']:>4}  {share_s:>10}  {short} ({c['oblast'] or '—'})")
    print(f"\nWrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
