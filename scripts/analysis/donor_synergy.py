#!/usr/bin/env python3
"""Build donor/fund portfolio synergy slices from DonorsPrograms + matching edges.

For each tagged donor program, surface:
  - within_portfolio: both ends tagged with the program (shared next grant / МСС)
  - bridge: one end in portfolio, one outside (structural-hole / network leverage)
  - coverage: how many tagged hromadas have Goals in the matching corpus

Hypotheses only — same caveat as matching-edges. Absence of a tag ≠ no program.

Usage:
  python scripts/analysis/donor_synergy.py
"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HROMADAS = ROOT / "data" / "releases" / "hromadas.json"
EDGES = ROOT / "data" / "releases" / "matching-edges.json"
OUT = ROOT / "data" / "releases" / "donor-synergy.json"
MANIFEST = ROOT / "data" / "releases" / "donor-synergy.manifest.json"
PREVIEW = ROOT / "docs" / "assets" / "donor-synergy-preview.json"

WITHIN_LIMIT = 15
BRIDGE_LIMIT = 15
PREVIEW_WITHIN = 10
PREVIEW_BRIDGE = 10
PREVIEW_HUBS = 6
PREVIEW_MEMBERS = 20


def parse_programs(raw) -> list[str]:
    if raw is None or raw == "":
        return []
    if isinstance(raw, list):
        return [str(x).strip() for x in raw if str(x).strip()]
    return [p.strip() for p in str(raw).replace(";", ",").split(",") if p.strip()]


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


def main() -> None:
    hromadas = json.loads(HROMADAS.read_text(encoding="utf-8"))
    edges = json.loads(EDGES.read_text(encoding="utf-8"))

    by_name: dict[str, dict] = {}
    program_members: dict[str, set[str]] = defaultdict(set)
    tagged_total = 0

    for row in hromadas:
        name = row.get("Name") or ""
        if not name:
            continue
        programs = parse_programs(row.get("DonorsPrograms"))
        by_name[name] = {
            "name": name,
            "short": short_name(name),
            "katottg": row.get("Katottg") or row.get("KATOTTG"),
            "oblast": row.get("Oblast"),
            "source_quality": row.get("SourceQuality"),
            "has_goals": bool((row.get("Goals") or "").strip()),
            "programs": programs,
        }
        if programs:
            tagged_total += 1
            for p in programs:
                program_members[p].add(name)

    # Degree in matching graph (all edges) — simple leverage proxy
    degree: dict[str, int] = defaultdict(int)
    for e in edges:
        degree[e["a"]] += 1
        degree[e["b"]] += 1

    programs_out = []
    for prog in sorted(program_members.keys(), key=lambda p: (-len(program_members[p]), p)):
        members = program_members[prog]
        member_rows = [by_name[n] for n in sorted(members)]
        with_goals = [m for m in member_rows if m["has_goals"]]
        in_graph = [m for m in with_goals if degree.get(m["name"], 0) > 0]

        within = []
        bridges = []
        for e in edges:
            a_in = e["a"] in members
            b_in = e["b"] in members
            if not a_in and not b_in:
                continue
            item = {
                "a": e["a"],
                "b": e["b"],
                "a_short": short_name(e["a"]),
                "b_short": short_name(e["b"]),
                "score": e.get("score"),
                "goals_cosine": e.get("goals_cosine"),
                "geo_score": e.get("geo_score"),
                "mss_network": e.get("mss_network"),
                "track": e.get("track"),
                "known": bool(e.get("known")),
            }
            if a_in and b_in:
                within.append(item)
            else:
                item["in_portfolio"] = e["a"] if a_in else e["b"]
                item["outside"] = e["b"] if a_in else e["a"]
                item["in_portfolio_short"] = short_name(item["in_portfolio"])
                item["outside_short"] = short_name(item["outside"])
                bridges.append(item)

        # Prefer known, then thematic goals_cosine, then combined score
        def rank_key(x):
            return (
                0 if x.get("known") else 1,
                -(x.get("goals_cosine") or 0),
                -(x.get("score") or 0),
            )

        within_sorted = sorted(within, key=rank_key)[:WITHIN_LIMIT]
        bridges_sorted = sorted(bridges, key=rank_key)[:BRIDGE_LIMIT]

        # Hub-ish portfolio members: high matching degree among tagged+graph
        hubs = sorted(
            (
                {
                    "name": m["name"],
                    "short": m["short"],
                    "oblast": m["oblast"],
                    "degree": degree.get(m["name"], 0),
                    "source_quality": m["source_quality"],
                }
                for m in in_graph
            ),
            key=lambda x: -x["degree"],
        )[:8]

        programs_out.append(
            {
                "program": prog,
                "tagged": len(members),
                "with_goals": len(with_goals),
                "in_matching_graph": len(in_graph),
                "within_edge_count": len(within),
                "bridge_edge_count": len(bridges),
                "members_with_goals": [
                    {
                        "name": m["name"],
                        "short": m["short"],
                        "oblast": m["oblast"],
                        "source_quality": m["source_quality"],
                        "degree": degree.get(m["name"], 0),
                    }
                    for m in sorted(with_goals, key=lambda x: x["short"])
                ],
                "hubs": hubs,
                "within_portfolio": within_sorted,
                "bridges": bridges_sorted,
            }
        )

    payload = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "method": "v6 matching edges × DonorsPrograms tags",
        "caveat": (
            "Matching scores are hypotheses unless known=true. "
            "DonorsPrograms absence means not found in tagging pass, not 'no program'. "
            "Pilot corpus: only text-mined Goals enter matching."
        ),
        "totals": {
            "hromadas": len(hromadas),
            "tagged": tagged_total,
            "programs": len(programs_out),
            "matching_edges": len(edges),
        },
        "programs": programs_out,
    }

    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    MANIFEST.write_text(
        json.dumps(
            {
                "generatedAt": payload["generatedAt"],
                "source": "hromadas.json DonorsPrograms + matching-edges.json",
                "programCount": len(programs_out),
                "taggedHromadas": tagged_total,
                "license": "CC BY 4.0 — see DATA-LICENSE.md",
                "warning": payload["caveat"],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    # Slim Pages preview (docs/ cannot fetch ../data/releases/ when served alone)
    preview = {
        "generatedAt": payload["generatedAt"],
        "method": payload["method"],
        "caveat": payload["caveat"],
        "totals": payload["totals"],
        "programs": [],
    }
    for p in programs_out:
        preview["programs"].append(
            {
                "program": p["program"],
                "tagged": p["tagged"],
                "with_goals": p["with_goals"],
                "in_matching_graph": p["in_matching_graph"],
                "within_edge_count": p["within_edge_count"],
                "bridge_edge_count": p["bridge_edge_count"],
                "hubs": p["hubs"][:PREVIEW_HUBS],
                "within_portfolio": [
                    {
                        "a_short": e["a_short"],
                        "b_short": e["b_short"],
                        "score": e["score"],
                        "goals_cosine": e["goals_cosine"],
                        "geo_score": e["geo_score"],
                        "mss_network": e["mss_network"],
                        "track": e["track"],
                        "known": e["known"],
                    }
                    for e in p["within_portfolio"][:PREVIEW_WITHIN]
                ],
                "bridges": [
                    {
                        "in_portfolio_short": e["in_portfolio_short"],
                        "outside_short": e["outside_short"],
                        "score": e["score"],
                        "goals_cosine": e["goals_cosine"],
                        "geo_score": e["geo_score"],
                        "mss_network": e["mss_network"],
                        "track": e["track"],
                        "known": e["known"],
                    }
                    for e in p["bridges"][:PREVIEW_BRIDGE]
                ],
                "members_with_goals": [
                    {
                        "short": m["short"],
                        "oblast": m["oblast"],
                        "degree": m["degree"],
                    }
                    for m in p["members_with_goals"][:PREVIEW_MEMBERS]
                ],
            }
        )
    PREVIEW.parent.mkdir(parents=True, exist_ok=True)
    PREVIEW.write_text(json.dumps(preview, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Wrote {OUT.relative_to(ROOT)} ({len(programs_out)} programs, {tagged_total} tagged).")
    print(f"Wrote {PREVIEW.relative_to(ROOT)} (Pages preview).")
    for p in programs_out:
        print(
            f"  {p['program']}: tagged={p['tagged']} goals={p['with_goals']} "
            f"within={p['within_edge_count']} bridges={p['bridge_edge_count']}"
        )


if __name__ == "__main__":
    main()
