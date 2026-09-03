#!/usr/bin/env python3
"""Agent-centric МСС recommendations for one seed hromada.

Re-ranks existing release edges for seed A by motivation / job-to-be-done.
Does NOT rematch the corpus, change v7.1 weights, or set known:true.

Usage:
  yarn recommend-for --seed "Галицька" --motivation water_basin
  yarn recommend-for --katottg UA26020030000088465 --motivation cut_costs_service -k 8
  python3 scripts/analysis/recommend_for.py --list-motivations
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
RELEASES = ROOT / "data" / "releases"
HROMADAS = RELEASES / "hromadas.json"
EDGES = RELEASES / "matching-edges.json"
COMPLEMENTARY = RELEASES / "matching-edges.complementary.json"

# Motivation → policy. Weights re-rank candidates for seed A; they do not
# replace or rewrite the global v7.1 lab score.
MOTIVATIONS: dict[str, dict[str, Any]] = {
    "cut_costs_service": {
        "label_uk": "Скоротити витрати / спільна послуга",
        "label_en": "Cut costs / shared service",
        "weights": {
            "geo": 0.55,
            "network": 0.15,
            "goals": 0.15,
            "complementary": 0.15,
        },
        "theme_boost": {
            "cnap": 0.12,
            "utilities": 0.10,
            "fire": 0.10,
            "waste": 0.08,
            "education": 0.06,
            "health": 0.06,
            "social": 0.05,
        },
        "form_boost": {
            "delegation": 0.08,
            "joint_finance": 0.06,
            "joint_enterprise": 0.04,
        },
        "package_hint_uk": "типовий пакет: ЦНАП / послуга — делегування або спільне утримання",
        "package_hint_en": "typical package: admin service — delegation or joint upkeep",
    },
    "water_basin": {
        "label_uk": "Вода / спільний басейн",
        "label_en": "Water / shared basin",
        "weights": {
            "geo": 0.40,
            "goals": 0.20,
            "complementary": 0.25,
            "network": 0.15,
        },
        "theme_boost": {
            "water": 0.20,
            "utilities": 0.05,
        },
        "form_boost": {
            "joint_project": 0.05,
            "joint_enterprise": 0.04,
        },
        "package_hint_uk": "типовий пакет: вода — спільний проєкт (басейн = контекст, не score)",
        "package_hint_en": "typical package: water — joint project (basin is context, not score)",
    },
    "tourism_cluster": {
        "label_uk": "Туризм / кластерна візія",
        "label_en": "Tourism / cluster vision",
        "weights": {
            "goals": 0.55,
            "geo": 0.15,
            "complementary": 0.20,
            "network": 0.10,
        },
        "theme_boost": {
            "tourism": 0.20,
            "culture": 0.10,
        },
        "form_boost": {
            "joint_project": 0.06,
        },
        "package_hint_uk": "типовий пакет: туризм — спільний проєкт",
        "package_hint_en": "typical package: tourism — joint project",
    },
    "general": {
        "label_uk": "Загальний пошук",
        "label_en": "General discovery",
        "weights": {
            "goals": 0.45,
            "geo": 0.25,
            "network": 0.15,
            "complementary": 0.15,
        },
        "theme_boost": {},
        "form_boost": {},
        "package_hint_uk": "баланс сигналів (не global v7.1 score як UX)",
        "package_hint_en": "balanced signals (not global v7.1 score as UX)",
    },
}

DEFAULT_MOTIVATION = "general"
DEFAULT_K = 8


def short_name(full: str | None) -> str:
    if not full:
        return ""
    parts = full.replace("територіальна громада", "").strip().split()
    return parts[0] if parts else full


def pair_key(a: str, b: str) -> tuple[str, str]:
    return tuple(sorted((a.strip(), b.strip())))  # type: ignore[return-value]


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def index_hromadas(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Indexes for seed resolution: by katottg, exact name, goals list."""
    by_kat: dict[str, dict[str, Any]] = {}
    by_name: dict[str, dict[str, Any]] = {}
    goals_seeds: list[dict[str, Any]] = []
    for r in rows:
        name = (r.get("Name") or "").strip()
        kat = (r.get("Katottg") or "").strip()
        if kat:
            by_kat[kat] = r
        if name:
            by_name[name] = r
        if (r.get("Goals") or "").strip():
            goals_seeds.append(
                {
                    "name": name,
                    "katottg": kat or None,
                    "short": short_name(name),
                    "oblast": r.get("Oblast"),
                }
            )
    goals_seeds.sort(key=lambda s: s["short"] or s["name"])
    return {"by_kat": by_kat, "by_name": by_name, "goals_seeds": goals_seeds}


def resolve_seed(
    *,
    seed: str | None,
    katottg: str | None,
    index: dict[str, Any],
) -> dict[str, Any]:
    by_kat: dict[str, dict[str, Any]] = index["by_kat"]
    by_name: dict[str, dict[str, Any]] = index["by_name"]

    if katottg:
        kat = katottg.strip()
        row = by_kat.get(kat)
        if not row:
            raise SystemExit(f"Unknown KATOTTG: {kat}")
        return {
            "name": row["Name"],
            "katottg": kat,
            "short": short_name(row["Name"]),
            "oblast": row.get("Oblast"),
        }

    if not seed or not seed.strip():
        raise SystemExit("Provide --seed or --katottg")

    q = seed.strip()
    if q in by_name:
        row = by_name[q]
        return {
            "name": row["Name"],
            "katottg": (row.get("Katottg") or "").strip() or None,
            "short": short_name(row["Name"]),
            "oblast": row.get("Oblast"),
        }

    # Substring / short-name match among Goals seeds first, then all names
    goals = index["goals_seeds"]
    hits = [
        s
        for s in goals
        if q.lower() in (s["name"] or "").lower()
        or q.lower() in (s["short"] or "").lower()
    ]
    if not hits:
        hits = [
            {
                "name": n,
                "katottg": (r.get("Katottg") or "").strip() or None,
                "short": short_name(n),
                "oblast": r.get("Oblast"),
            }
            for n, r in by_name.items()
            if q.lower() in n.lower() or q.lower() in short_name(n).lower()
        ]
    if not hits:
        raise SystemExit(f"No hromada matching seed={q!r}")
    if len(hits) > 1:
        # Prefer exact short-name match
        exact = [h for h in hits if (h["short"] or "").lower() == q.lower()]
        if len(exact) == 1:
            return exact[0]
        sample = ", ".join((h["short"] or h["name"]) for h in hits[:8])
        raise SystemExit(
            f"Ambiguous seed={q!r} ({len(hits)} hits). Use --katottg. Examples: {sample}"
        )
    return hits[0]


def _f(edge: dict[str, Any], key: str) -> float:
    v = edge.get(key)
    if v is None:
        return 0.0
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def merge_complementary(
    edges: list[dict[str, Any]],
    complementary: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Attach complementary_score/reasons; add complementary-only pairs."""
    by_pair: dict[tuple[str, str], dict[str, Any]] = {}
    for e in edges:
        a, b = (e.get("a") or "").strip(), (e.get("b") or "").strip()
        if not a or not b:
            continue
        by_pair[pair_key(a, b)] = dict(e)

    for c in complementary:
        a, b = (c.get("a") or "").strip(), (c.get("b") or "").strip()
        if not a or not b:
            continue
        pk = pair_key(a, b)
        if pk in by_pair:
            cur = by_pair[pk]
            if c.get("complementary_score") is not None:
                cur["complementary_score"] = c["complementary_score"]
            if c.get("reasons"):
                cur["complementary_reasons"] = c["reasons"]
            # Prefer richer package from complementary when matching edge lacks theme
            pkg = cur.get("package") or {}
            if not pkg.get("theme_id") or pkg.get("theme_id") == "other":
                for key in (
                    "package",
                    "suggested_theme",
                    "suggested_theme_id",
                    "suggested_form",
                    "suggested_form_id",
                    "suggest_confidence",
                    "suggest_rationale",
                    "signals",
                    "signal_chips",
                    "discovery_primary",
                ):
                    if c.get(key) is not None:
                        cur[key] = c[key]
        else:
            row = dict(c)
            row.setdefault("goals_cosine", 0.0)
            row.setdefault("geo_score", 0.0)
            row.setdefault("mss_network", 0.0)
            row.setdefault("score", None)
            row.setdefault("known", False)
            by_pair[pk] = row

    return list(by_pair.values())


def edges_for_seed(edges: list[dict[str, Any]], seed_name: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for e in edges:
        a, b = (e.get("a") or "").strip(), (e.get("b") or "").strip()
        if a == seed_name or b == seed_name:
            out.append(e)
    return out


def partner_of(edge: dict[str, Any], seed_name: str) -> str:
    a, b = (edge.get("a") or "").strip(), (edge.get("b") or "").strip()
    if a == seed_name:
        return b
    return a


def agent_rank(edge: dict[str, Any], motivation: str) -> float:
    """Policy score for ordering — not the product claim and not v7.1 score.

    goals_cosine is discounted by template_collision (near-verbatim subgoal
    lines shared between the pair's two source documents — same consultant/
    boilerplate, not necessarily shared real priorities). This only affects
    ranking here, not the released match.py score/track — measured impact:
    8.2% of top-5 slots (74/293 seed hromadas) carried a collision>0.1
    "match" before this discount.
    """
    pol = MOTIVATIONS[motivation]
    w = pol["weights"]
    goals_adj = _f(edge, "goals_cosine") * (1.0 - _f(edge, "template_collision"))
    rank = (
        w.get("goals", 0) * goals_adj
        + w.get("geo", 0) * _f(edge, "geo_score")
        + w.get("network", 0) * _f(edge, "mss_network")
        + w.get("complementary", 0) * _f(edge, "complementary_score")
    )
    theme_id = (edge.get("package") or {}).get("theme_id") or edge.get(
        "suggested_theme_id"
    )
    form_id = (edge.get("package") or {}).get("form_id") or edge.get("suggested_form_id")
    rank += float(pol.get("theme_boost", {}).get(theme_id, 0) or 0)
    rank += float(pol.get("form_boost", {}).get(form_id, 0) or 0)
    return rank


def _why_helps(
    *,
    motivation: str,
    edge: dict[str, Any],
    partner_short: str,
    lang: str = "uk",
) -> str:
    """One short mutual-benefit line — never a score pitch."""
    pkg = edge.get("package") or {}
    label = pkg.get("label_uk") or (
        f"{edge.get('suggested_theme') or 'тема'} — "
        f"{edge.get('suggested_form') or 'спільний проєкт'}"
    )
    theme_id = pkg.get("theme_id") or edge.get("suggested_theme_id")
    geo = _f(edge, "geo_score")
    goals = _f(edge, "goals_cosine")
    comp = _f(edge, "complementary_score")
    waterish = theme_id in ("water", "utilities")

    if lang == "en":
        if motivation == "cut_costs_service":
            near = "Neighbour for shared service / cost cut" if geo >= 0.5 else "Service-share candidate"
            return f"{near}: {label}."
        if motivation == "water_basin":
            focus = "Water/utilities package" if waterish else "Nearby water/utilities candidate"
            extra = " Complementary signal." if comp > 0 else ""
            return f"{focus}: {label}.{extra} Basin = map context only."
        if motivation == "tourism_cluster":
            if theme_id in ("tourism", "culture"):
                return f"Cluster vision fit: {label}."
            if goals > 0.05:
                return f"Overlapping goals; package {label}."
            return f"Possible cluster package: {label}."
        bits = [f"Package {label}"]
        if goals > 0.05:
            bits.append("overlapping goals")
        if geo >= 0.5:
            bits.append("handy neighbour")
        return "; ".join(bits) + "."

    if motivation == "cut_costs_service":
        near = "Зручний сусід для спільної послуги / економії" if geo >= 0.5 else "Кандидат спільної послуги"
        return f"{near}: «{label}»."
    if motivation == "water_basin":
        focus = "Пакет води / ЖКГ" if waterish else "Кандидат для води / ЖКГ"
        extra = " Є доповнення ресурсів." if comp > 0 else ""
        return f"{focus}: «{label}».{extra} Басейн — лише контекст карти."
    if motivation == "tourism_cluster":
        if theme_id in ("tourism", "culture"):
            return f"Збіг візії / кластера: «{label}»."
        if goals > 0.05:
            return f"Перетин цілей; пакет «{label}»."
        return f"Можливий кластерний пакет «{label}»."
    bits_uk = [f"Пакет «{label}»"]
    if goals > 0.05:
        bits_uk.append("перетин цілей")
    if geo >= 0.5:
        bits_uk.append("зручний сусід")
    return "; ".join(bits_uk) + "."



def card_from_edge(
    edge: dict[str, Any],
    *,
    seed_name: str,
    motivation: str,
    rank_value: float,
) -> dict[str, Any]:
    partner = partner_of(edge, seed_name)
    pkg = edge.get("package") or {
        "theme": edge.get("suggested_theme"),
        "theme_id": edge.get("suggested_theme_id"),
        "form": edge.get("suggested_form"),
        "form_id": edge.get("suggested_form_id"),
        "label_uk": (
            f"{edge.get('suggested_theme') or 'тема не визначена'} — "
            f"{edge.get('suggested_form') or 'спільний проєкт'}"
        ),
        "confidence": edge.get("suggest_confidence"),
        "rationale": edge.get("suggest_rationale"),
    }
    chips = edge.get("signal_chips") or (edge.get("signals") or [])[:3]
    status = edge.get("status") or (
        "registry_known" if edge.get("known") else "hypothesis"
    )
    return {
        "kind": "mss_agent_recommendation",
        "seed": seed_name,
        "seed_short": short_name(seed_name),
        "partner": partner,
        "partner_short": short_name(partner),
        "motivation": motivation,
        "package": pkg,
        "signal_chips": chips,
        "why_helps_you_uk": _why_helps(
            motivation=motivation,
            edge=edge,
            partner_short=short_name(partner),
            lang="uk",
        ),
        "why_helps_you_en": _why_helps(
            motivation=motivation,
            edge=edge,
            partner_short=short_name(partner),
            lang="en",
        ),
        "status": status,
        "known": bool(edge.get("known")),
        "discovery_primary": edge.get("discovery_primary"),
        "track": edge.get("track"),
        # Internal only — do not surface as “strategy match” in UI copy
        "agent_rank": round(rank_value, 4),
        "lab_score": edge.get("score"),
        "goals_cosine": edge.get("goals_cosine"),
        "template_collision": edge.get("template_collision"),
        "geo_score": edge.get("geo_score"),
        "mss_network": edge.get("mss_network"),
        "complementary_score": edge.get("complementary_score"),
    }


def recommend_for(
    seed_name: str,
    *,
    motivation: str = DEFAULT_MOTIVATION,
    k: int = DEFAULT_K,
    edges: list[dict[str, Any]] | None = None,
    complementary: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    if motivation not in MOTIVATIONS:
        raise ValueError(
            f"Unknown motivation={motivation!r}. "
            f"Choose from: {', '.join(MOTIVATIONS)}"
        )
    if edges is None:
        from edge_io import load_matching_edges

        edges = load_matching_edges(prefer_rich_cache=True)
    if complementary is None and COMPLEMENTARY.exists():
        complementary = load_json(COMPLEMENTARY)
    merged = merge_complementary(edges, complementary or [])
    incident = edges_for_seed(merged, seed_name)
    from edge_io import ensure_packages

    ensure_packages(incident)
    scored = [(agent_rank(e, motivation), e) for e in incident]
    scored.sort(key=lambda t: (-t[0], -(t[1].get("score") or 0)))
    cards = [
        card_from_edge(e, seed_name=seed_name, motivation=motivation, rank_value=r)
        for r, e in scored[: max(0, k)]
    ]
    return cards


def recommend_payload(
    *,
    seed: str | None = None,
    katottg: str | None = None,
    motivation: str = DEFAULT_MOTIVATION,
    k: int = DEFAULT_K,
    hromadas: list[dict[str, Any]] | None = None,
    edges: list[dict[str, Any]] | None = None,
    complementary: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    rows = hromadas if hromadas is not None else load_json(HROMADAS)
    index = index_hromadas(rows)
    resolved = resolve_seed(seed=seed, katottg=katottg, index=index)
    cards = recommend_for(
        resolved["name"],
        motivation=motivation,
        k=k,
        edges=edges,
        complementary=complementary,
    )
    pol = MOTIVATIONS[motivation]
    return {
        "kind": "mss_agent_recommendations",
        "caveat_uk": (
            "Рекомендації для громади-агента: партнер · пакет (тема · форма) · "
            "сигнали · «чому це вам допомагає». Не «у вас високий score». "
            "Гіпотези, доки known: true. Global v7.1 score лишається lab-валідацією."
        ),
        "caveat_en": (
            "Hromada-as-agent recommendations: partner · package (theme · form) · "
            "signals · “why it helps you”. Never “you have a high score”. "
            "Hypotheses until known: true. Global v7.1 score remains lab validation."
        ),
        "seed": resolved,
        "motivation": {
            "id": motivation,
            "label_uk": pol["label_uk"],
            "label_en": pol["label_en"],
            "package_hint_uk": pol.get("package_hint_uk"),
            "package_hint_en": pol.get("package_hint_en"),
            "weights": pol["weights"],
        },
        "k": k,
        "recommendations": cards,
    }


def format_text(payload: dict[str, Any]) -> str:
    seed = payload["seed"]
    mot = payload["motivation"]
    lines = [
        f"Seed: {seed.get('short') or seed['name']}"
        + (f" ({seed['katottg']})" if seed.get("katottg") else ""),
        f"Motivation: {mot['id']} — {mot['label_uk']}",
        f"Hint: {mot.get('package_hint_uk') or '—'}",
        "",
    ]
    if not payload["recommendations"]:
        lines.append("No incident edges for this seed in the release.")
        return "\n".join(lines)
    for i, c in enumerate(payload["recommendations"], 1):
        pkg = (c.get("package") or {}).get("label_uk") or "—"
        chips = ", ".join(
            (ch.get("label_uk") or ch.get("id") or "")
            for ch in (c.get("signal_chips") or [])[:3]
        )
        tag = "known" if c.get("known") else "hypothesis"
        lines.append(f"{i}. {c['partner_short']} · {pkg} [{tag}]")
        if chips:
            lines.append(f"   signals: {chips}")
        lines.append(f"   why: {c.get('why_helps_you_uk')}")
        lines.append("")
    lines.append(payload["caveat_uk"])
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(
        description="Recommend IMC packages for one seed hromada (agent-centric)."
    )
    p.add_argument("--seed", help="Hromada name or short-name substring")
    p.add_argument("--katottg", help="KATOTTG code")
    p.add_argument(
        "--motivation",
        default=DEFAULT_MOTIVATION,
        choices=sorted(MOTIVATIONS.keys()),
        help=f"Job-to-be-done policy (default: {DEFAULT_MOTIVATION})",
    )
    p.add_argument("-k", type=int, default=DEFAULT_K, help="Top-K partners")
    p.add_argument("--json", action="store_true", help="Print JSON payload")
    p.add_argument(
        "--list-motivations",
        action="store_true",
        help="Print motivation policy table and exit",
    )
    args = p.parse_args(argv)

    if args.list_motivations:
        out = {
            mid: {
                "label_uk": m["label_uk"],
                "label_en": m["label_en"],
                "weights": m["weights"],
                "theme_boost": m["theme_boost"],
                "form_boost": m["form_boost"],
                "package_hint_uk": m.get("package_hint_uk"),
            }
            for mid, m in MOTIVATIONS.items()
        }
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return

    payload = recommend_payload(
        seed=args.seed,
        katottg=args.katottg,
        motivation=args.motivation,
        k=args.k,
    )
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(format_text(payload))


if __name__ == "__main__":
    main()
