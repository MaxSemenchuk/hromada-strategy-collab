#!/usr/bin/env python3
"""
Synthetic (simulated) dry-run of the AIM-CC field-experiment design —
internal/aim-cc-field-experiment-prereg.md.

**This does not contact any hromada.** No email/Telegram is sent. It is a
pre-launch check of the *design*, not a substitute for it:

  1. Rebuilds the three sampling pools §3 defines (Arm A thematic / Arm B
     operational / Arm C control) from the *current* matching-edges.json.
     The prereg's own sampling-frame table (§4: "455 thematic / 150
     operational / 4,345 mixed", 2026-08-03 snapshot) is already stale
     against this corpus — printed pool sizes below are the current ones,
     not a re-statement of the prereg table.
  2. Draws ONE concrete blocked pilot sample at the "preferred" N=12/arm
     size (§4), respecting blocking (oblast macro-region x population
     tertile, §2) and a no-hromada-reuse constraint across the whole
     sample (a design choice made here, not in the prereg, to avoid
     spillover between arms in a real launch — flagged in the report).
  3. Monte-Carlo simulates the primary outcome ("replied within 21 days")
     and the outcome ladder (§6) under an ASSUMED, ILLUSTRATIVE set of
     reply-rate priors, then runs the pre-registered analysis (Fisher
     exact, §8) on every replicate to report **statistical power** at the
     three candidate pilot sizes (§4: 8 / 12 / 20 per arm) — not effect
     estimates. There is no real AIM-CC funnel data yet; the priors here
     are elicited placeholders in the same spirit as coop_game_sim.py's
     TRACK_Q_PRIOR (thematic > operational > mixed/control), not fitted
     from data. Replace them once real reply/call/sign rates exist.

Use this to pressure-test "is N=12/arm even worth running" and to dry-run
the analysis pipeline end-to-end before real outreach — not to predict
real reply rates.

Usage:
  python scripts/analysis/aim_cc_synthetic_experiment.py
  python scripts/analysis/aim_cc_synthetic_experiment.py --seed 7 --reps 5000
  python scripts/analysis/aim_cc_synthetic_experiment.py --n-per-arm 12 --json
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np
from scipy.stats import binomtest, fisher_exact

sys.path.insert(0, str(Path(__file__).resolve().parent))
import recommend_for as rf  # noqa: E402  (same-dir import, needs sys.path above)

ROOT = Path(__file__).resolve().parents[2]
EDGES_PATH = ROOT / "data" / "releases" / "matching-edges.json"
HROMADAS_PATH = ROOT / "data" / "releases" / "hromadas.json"
INTENTS_PATH = ROOT / "data" / "releases" / "mss-intents.json"
COMPLEMENTARY_PATH = ROOT / "data" / "releases" / "matching-edges.complementary.json"
PIN_CORPUS_PATH = ROOT / "data" / "releases" / "matching-edges.pin-corpus.json"
OUT_JSON = ROOT / "internal" / "aim-cc-synthetic-experiment-results.json"

PREREG_PATH = "internal/aim-cc-field-experiment-prereg.md"

# --- §4 candidate pilot sizes (pairs per arm) ------------------------------
PILOT_SIZES = {"minimum": 8, "preferred": 12, "stretch": 20}

# --- §6 primary + ladder outcome priors (ASSUMPTION, illustrative only) ---
# Ordering thematic > operational > control follows coop_game_sim.py's
# TRACK_Q_PRIOR (0.35 / 0.30 / 0.15) for "negotiation succeeds"; "replied
# within 21 days" is a much lower bar than a signed agreement so absolute
# levels are set higher, keeping the same directional gaps H1/H2 test.
REPLY_PRIOR = {"A": 0.40, "B": 0.30, "C": 0.15}

# Conditional funnel below "replied" — held EQUAL across arms, matching the
# prereg's own H3 ("thematic converts interest to meeting at least as well
# as geo"), i.e. we simulate under H3's null and let H1/H2 do the work of
# separating arms at the top of the funnel only.
LADDER_PRIOR = {
    "both_replied_given_replied": 0.60,
    "call_scheduled_given_replied": 0.55,
    "call_held_given_scheduled": 0.80,
    "agreed_next_step_given_call_held": 0.45,
    "concept_drafted_3mo_given_agreed": 0.35,
    "registry_signed_12mo_given_concept": 0.20,
}

ALPHA = 0.05

# --- event-log simulation priors (ASSUMPTION, illustrative only) ----------
# Fraction of sent pairs that bounce / have a dead contact channel — from
# §8's "undeliverable contacts coded separately; primary analysis ITT among
# successfully delivered sends", not from real send data.
ATTRITION_RATE = 0.06
# Share of eventual repliers who reply before vs. after the day-10 reminder
# (§5.2). Illustrative: most real repliers answer early; the reminder
# recovers a minority of the rest.
SHARE_REPLY_BEFORE_REMINDER = 0.55
CHANNEL_MIX = {"email": 0.65, "telegram": 0.35}
# Terminal qualitative code for pairs that replied but stalled before the
# outcome ladder's higher rungs — §8's "short post-call code". Weights are
# illustrative, not observed.
STALL_CODE_WEIGHTS = {
    "recognized_shared_priority_stalled": 0.35,
    "rejected_as_irrelevant": 0.30,
    "capacity_blocked": 0.35,
}

# --- ALTERNATIVE intervention: "your hromada" report, not a partner ask ---
# Instead of asking hromada A to reply about a SPECIFIC partner B, send every
# sampled hromada its own personalized report and watch (a) whether they
# engage with it and (b) whether they proactively come back to us later
# asking for an intro. Unit of randomization = ONE hromada, not a pair — so
# this design is NOT subject to the pair/no-reuse corpus ceiling from the
# 3arm/2arm/hist_control designs (see main()'s corpus-ceiling note there).
# Arm "R" = report includes a real recommend_for() top pick (partner +
# package + why). Arm "B0" = report has no specific partner, just the
# hromada's own Goals summary / civic-tech benchmark (edem-barometer.json)
# — value-first, but no match hook, so it isolates whether the RECOMMENDATION
# itself (vs. just "someone made me a personalized report") drives the
# outcome that actually matters commercially: unprompted follow-up.
# ALL rates below are ASSUMPTIONS, not observed — directional logic: opening
# a low-effort report is much easier than replying to a partner ask, so open
# rates sit well above REPLY_PRIOR; replying to a report is a smaller ask
# than committing to an intro call, so it's set lower than REPLY_PRIOR;
# unprompted inbound follow-up is the rarest, highest-intent event of all.
REPORT_ENGAGEMENT_PRIOR = {
    "R": {
        "opened_given_delivered": 0.50,
        "clicked_recommendation_given_opened": 0.55,
        "replied_any_given_opened": 0.12,
        "inbound_request_30d_given_opened": 0.06,
        "inbound_request_90d_given_opened": 0.10,  # cumulative, includes the 30d ones
    },
    "B0": {
        "opened_given_delivered": 0.38,
        "clicked_recommendation_given_opened": 0.0,  # no recommendation section to click
        "replied_any_given_opened": 0.06,
        "inbound_request_30d_given_opened": 0.015,
        "inbound_request_90d_given_opened": 0.025,
    },
}
INBOUND_CODE_WEIGHTS = {
    "asked_intro_to_recommended_partner": 0.55,
    "asked_general_consult": 0.30,
    "asked_about_own_strategy_only": 0.15,
}

# Ukraine oblasts grouped into 5 macro-regions for blocking. The prereg
# names "oblast band" without defining bands; this grouping is a modeling
# choice for this dry run, not a prereg commitment.
MACRO_REGION = {
    "Волинська": "west", "Закарпатська": "west", "Івано-Франківська": "west",
    "Львівська": "west", "Рівненська": "west", "Тернопільська": "west",
    "Чернівецька": "west", "Хмельницька": "west",
    "Вінницька": "center", "Житомирська": "center", "Київська": "center",
    "Кіровоградська": "center", "Полтавська": "center", "Черкаська": "center",
    "Харківська": "east", "Донецька": "east", "Луганська": "east",
    "Дніпропетровська": "east", "Запорізька": "east",
    "Одеська": "south", "Миколаївська": "south", "Херсонська": "south",
    "Чернігівська": "north", "Сумська": "north",
}


def _norm_oblast(name: str | None) -> str:
    return (name or "").replace(" область", "").strip()


def load_hromadas() -> dict[str, dict[str, Any]]:
    rows = json.loads(HROMADAS_PATH.read_text(encoding="utf-8"))
    return {r["Katottg"]: r for r in rows if r.get("Katottg")}


def load_edges() -> list[dict[str, Any]]:
    return json.loads(EDGES_PATH.read_text(encoding="utf-8"))


def load_explicit_ask_katottgs() -> set[str]:
    data = json.loads(INTENTS_PATH.read_text(encoding="utf-8"))
    return {h["katottg"] for h in data.get("hromadas", []) if h.get("katottg")}


def load_historical_rates(total_pairs: int) -> dict[str, Any]:
    """Two candidate 'did nothing, what happens anyway' base rates, mined
    from the corpus itself instead of a live random-pair outreach arm:
      - network_tie: any real KSE-observed partnership signal (mss_network>0,
        PIN∩corpus) between the pair, ever — data/releases/matching-edges.pin-corpus.json
      - signed_known: a curated, confirmed МСС agreement between the pair, ever

    CAVEAT (load-bearing): both measure "did these two ever show any tie,
    over unknown history" — a totally different construct from "replied to
    an active email within 21 days". They are NOT interchangeable with a
    live random-pair control arm; they only answer "how often does this
    happen with zero active outreach at all", which is a much lower bar.
    """
    pin = json.loads(PIN_CORPUS_PATH.read_text(encoding="utf-8"))
    network_rate = pin["pairCount"] / total_pairs
    known_rate = pin["curatedKnownCount"] / total_pairs
    return {
        "denominator_total_pairs_in_corpus": total_pairs,
        "network_tie_ever": {"count": pin["pairCount"], "rate": network_rate},
        "signed_known_ever": {"count": pin["curatedKnownCount"], "rate": known_rate},
        "caveat": (
            "Historical 'ever had a tie' rate, not a 21-day active-outreach "
            "reply rate — treat as a sanity floor, not a substitute control arm."
        ),
    }


def population_tertiles(hromadas: dict[str, dict[str, Any]], katottgs: set[str]) -> tuple[float, float]:
    pops = sorted(
        h["Population"]
        for kat, h in hromadas.items()
        if kat in katottgs and isinstance(h.get("Population"), (int, float)) and h["Population"] > 0
    )
    if len(pops) < 3:
        return (0.0, 0.0)
    lo = pops[len(pops) // 3]
    hi = pops[(2 * len(pops)) // 3]
    return (lo, hi)


def pop_band(pop: float | None, cuts: tuple[float, float]) -> str:
    if not pop:
        return "unknown"
    lo, hi = cuts
    if pop <= lo:
        return "small"
    if pop <= hi:
        return "mid"
    return "large"


def block_key(edge: dict[str, Any], hromadas: dict[str, dict[str, Any]], cuts: tuple[float, float]) -> str:
    """Oblast macro-region (of side 'a') x population tertile (of side 'a')."""
    a = hromadas.get(edge.get("a_katottg"), {})
    region = MACRO_REGION.get(_norm_oblast(a.get("Oblast")), "other")
    band = pop_band(a.get("Population"), cuts)
    return f"{region}/{band}"


def hromada_block_key(h: dict[str, Any], cuts: tuple[float, float]) -> str:
    region = MACRO_REGION.get(_norm_oblast(h.get("Oblast")), "other")
    return f"{region}/{pop_band(h.get('Population'), cuts)}"


def build_report_sample(
    hromadas: dict[str, dict[str, Any]],
    edges: list[dict[str, Any]],
    matchable_pool: set[str],
    goals_ready: set[str],
    n_per_arm: int,
    rng: np.random.Generator,
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, int]]:
    """Draws n_per_arm DISTINCT hromadas for arm R (gets a real recommend_for
    top pick in its report) and n_per_arm more, non-overlapping, for arm B0
    (benchmark-only report) — unit is one hromada, no pairing, so up to
    len(matchable_pool) hromadas total are available (not //2).

    v0.7: matchable_pool (every hromada with a KATOTTG, ~1,424) replaces the
    old goals_ready-only pool (293) as the sampling frame — recommend_for.py
    now matches goals-less hromadas too (geo/network/complementary, see
    recommend_for.weights_without_goals). goals_ready still decides, per
    seed, which recommend_for path runs."""
    complementary = json.loads(COMPLEMENTARY_PATH.read_text(encoding="utf-8"))
    candidates = list(matchable_pool)
    rng.shuffle(candidates)

    diag = Counter()
    sample: dict[str, list[dict[str, Any]]] = {"R": [], "B0": []}
    used: set[str] = set()
    idx = 0

    while len(sample["R"]) < n_per_arm and idx < len(candidates):
        kat = candidates[idx]
        idx += 1
        if kat in used:
            continue
        seed_name = hromadas[kat]["Name"]
        try:
            if kat in goals_ready:
                cards = rf.recommend_for(
                    seed_name, motivation="general", k=3, edges=edges, complementary=complementary
                )
            else:
                cards = rf.recommend_for_no_goals(
                    hromadas[kat], motivation="general", k=3, hromadas=list(hromadas.values())
                )
        except Exception:
            diag["recommend_for_error"] += 1
            continue
        card = next((c for c in cards if not c.get("known")), None)
        if card is None:
            diag["no_eligible_card"] += 1
            continue
        used.add(kat)
        diag["accepted_R_no_goals" if kat not in goals_ready else "accepted_R_goals"] += 1
        sample["R"].append(
            {
                "katottg": kat,
                "name": seed_name,
                "goals_available": kat in goals_ready,
                "partner": card.get("partner"),
                "package_label_uk": (card.get("package") or {}).get("label_uk"),
                "why_helps_you_uk": card.get("why_helps_you_uk"),
                "goals_cosine": card.get("goals_cosine"),
            }
        )
        diag["accepted_R"] += 1

    while len(sample["B0"]) < n_per_arm and idx < len(candidates):
        kat = candidates[idx]
        idx += 1
        if kat in used:
            continue
        used.add(kat)
        sample["B0"].append({"katottg": kat, "name": hromadas[kat]["Name"]})
        diag["accepted_B0"] += 1

    return sample, dict(diag)


def simulate_report_log(
    sample: dict[str, list[dict[str, Any]]],
    hromadas: dict[str, dict[str, Any]],
    cuts: tuple[float, float],
    rng: np.random.Generator,
    guaranteed_view: bool = False,
) -> list[dict[str, Any]]:
    """Per-hromada, day-level simulation of the report-engagement funnel —
    entirely SYNTHETIC (see REPORT_ENGAGEMENT_PRIOR).

    guaranteed_view=True switches the delivery mechanism from "cold email,
    might not be opened" to "hromada visits a page/portal and the report
    (or placebo) just renders" — there's no separate open step to fail, so
    deliverable=opened=True for every sampled hromada and the funnel starts
    straight from clicked/replied/inbound. Only ATTRITION_RATE and
    opened_given_delivered are bypassed; the rest of REPORT_ENGAGEMENT_PRIOR
    (still illustrative) applies unchanged."""
    rows: list[dict[str, Any]] = []
    for arm, entries in sample.items():
        p = REPORT_ENGAGEMENT_PRIOR[arm]
        for i, entry in enumerate(entries):
            h = hromadas.get(entry["katottg"], {})
            row: dict[str, Any] = {
                "report_id": f"{arm}{i+1:03d}",
                "arm": arm,
                "hromada": entry["name"],
                "katottg": entry["katottg"],
                "block": hromada_block_key(h, cuts),
                "recommended_partner": entry.get("partner"),
                "package_label_uk": entry.get("package_label_uk"),
                "send_day": 0,
            }
            deliverable = True if guaranteed_view else rng.random() > ATTRITION_RATE
            row["deliverable"] = deliverable
            if not deliverable:
                row.update(
                    opened=False, opened_day=None, clicked_recommendation=False,
                    replied_any=False, reply_day=None,
                    inbound_request_30d=False, inbound_request_90d=False, inbound_day=None,
                    engagement_code="undeliverable",
                )
                rows.append(row)
                continue

            opened = True if guaranteed_view else rng.random() < p["opened_given_delivered"]
            row["opened"] = opened
            if not opened:
                row.update(
                    opened_day=None, clicked_recommendation=False,
                    replied_any=False, reply_day=None,
                    inbound_request_30d=False, inbound_request_90d=False, inbound_day=None,
                    engagement_code="not_opened",
                )
                rows.append(row)
                continue

            row["opened_day"] = int(rng.integers(0, 8))
            row["clicked_recommendation"] = (
                arm == "R" and rng.random() < p["clicked_recommendation_given_opened"]
            )
            replied = rng.random() < p["replied_any_given_opened"]
            row["replied_any"] = replied
            row["reply_day"] = row["opened_day"] + int(rng.integers(0, 6)) if replied else None

            inbound_90 = rng.random() < p["inbound_request_90d_given_opened"]
            inbound_30 = inbound_90 and rng.random() < (
                p["inbound_request_30d_given_opened"] / max(p["inbound_request_90d_given_opened"], 1e-9)
            )
            row["inbound_request_90d"] = inbound_90
            row["inbound_request_30d"] = inbound_30
            if inbound_90:
                row["inbound_day"] = int(rng.integers(1, 31)) if inbound_30 else int(rng.integers(31, 91))
                row["engagement_code"] = str(
                    rng.choice(list(INBOUND_CODE_WEIGHTS), p=list(INBOUND_CODE_WEIGHTS.values()))
                )
            else:
                row["inbound_day"] = None
                row["engagement_code"] = "opened_no_followup"
            rows.append(row)
    return rows


def analyze_report_log(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_arm: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        by_arm[r["arm"]].append(r)

    arm_stats: dict[str, Any] = {}
    for arm, arm_rows in by_arm.items():
        n_sent = len(arm_rows)
        delivered = [r for r in arm_rows if r["deliverable"]]
        n_delivered = len(delivered)
        opened = [r for r in delivered if r["opened"]]

        def rate_ci(flag: str) -> dict[str, Any]:
            n_yes = sum(r[flag] for r in delivered)
            lo, hi = wilson_ci(n_yes, n_delivered)
            return {"n": n_yes, "rate": round(n_yes / n_delivered, 3) if n_delivered else 0.0, "wilson_ci": [round(lo, 3), round(hi, 3)]}

        arm_stats[arm] = {
            "n_sent": n_sent,
            "n_delivered": n_delivered,
            "opened": rate_ci("opened"),
            "replied_any": rate_ci("replied_any"),
            "inbound_request_30d": rate_ci("inbound_request_30d"),
            "inbound_request_90d": rate_ci("inbound_request_90d"),
            "clicked_recommendation_of_opened": (
                round(sum(r["clicked_recommendation"] for r in opened) / len(opened), 3) if opened else None
            ),
            "engagement_codes": dict(Counter(r["engagement_code"] for r in delivered)),
        }

    tests: dict[str, Any] = {}
    if "R" in arm_stats and "B0" in arm_stats:
        r, b = arm_stats["R"], arm_stats["B0"]
        for outcome in ("opened", "replied_any", "inbound_request_30d", "inbound_request_90d"):
            table = [
                [r[outcome]["n"], r["n_delivered"] - r[outcome]["n"]],
                [b[outcome]["n"], b["n_delivered"] - b[outcome]["n"]],
            ]
            _, p_val = fisher_exact(table)
            tests[f"R_vs_B0_{outcome}"] = {
                "risk_difference": round(r[outcome]["rate"] - b[outcome]["rate"], 3),
                "fisher_p_value": round(p_val, 4),
                "significant_at_0.05": bool(p_val < ALPHA),
            }
    return {"by_arm": arm_stats, "analysis": tests}


def simulate_power_report(
    n_per_arm: int, reps: int, rng: np.random.Generator, guaranteed_view: bool = False
) -> dict[str, Any]:
    """Monte-Carlo power to detect R>B0 on the primary business metric
    (inbound_request_30d) and the engagement metric (opened), at alpha=0.05.
    Delivery attrition folded in via ATTRITION_RATE so n_per_arm is 'sent',
    matching how the other simulate_power_* functions report n — unless
    guaranteed_view=True (portal-view mechanism, see simulate_report_log),
    in which case opened=100% for every sampled hromada and n_per_arm is
    directly the number who see the report/placebo."""
    p_r_open = 1.0 if guaranteed_view else REPORT_ENGAGEMENT_PRIOR["R"]["opened_given_delivered"] * (1 - ATTRITION_RATE)
    p_b_open = 1.0 if guaranteed_view else REPORT_ENGAGEMENT_PRIOR["B0"]["opened_given_delivered"] * (1 - ATTRITION_RATE)
    p_r_inbound = p_r_open * REPORT_ENGAGEMENT_PRIOR["R"]["inbound_request_30d_given_opened"]
    p_b_inbound = p_b_open * REPORT_ENGAGEMENT_PRIOR["B0"]["inbound_request_30d_given_opened"]

    def run(p_r: float, p_b: float) -> float:
        r = rng.binomial(1, p_r, size=(reps, n_per_arm)).sum(axis=1)
        b = rng.binomial(1, p_b, size=(reps, n_per_arm)).sum(axis=1)
        sig = sum(
            fisher_exact([[r[i], n_per_arm - r[i]], [b[i], n_per_arm - b[i]]])[1] < ALPHA for i in range(reps)
        )
        return sig / reps

    return {
        "design": "report",
        "n_per_arm": n_per_arm,
        "total_hromadas": 2 * n_per_arm,
        "power_opened_R_vs_B0": round(run(p_r_open, p_b_open), 3),
        "power_inbound_30d_R_vs_B0": round(run(p_r_inbound, p_b_inbound), 3),
    }


def run_report_design(
    args: argparse.Namespace,
    hromadas: dict[str, dict[str, Any]],
    edges: list[dict[str, Any]],
    matchable_pool: set[str],
    goals_ready: set[str],
    cuts: tuple[float, float],
    rng: np.random.Generator,
) -> None:
    """"Send every hromada its own report, measure engagement + unprompted
    follow-up" design — unit is ONE hromada, so it sidesteps the pair-based
    corpus ceiling entirely (see the 3arm/2arm/hist_control note in main()).

    v0.7: the sampling frame is matchable_pool (every hromada with a
    KATOTTG, ~1,424) — recommend_for.py's goals-less fallback means Arm R
    no longer needs goals_ready (293) as its ceiling. goals_ready is still
    threaded through to build_report_sample so each seed uses the right
    recommend_for path.
    """
    max_per_arm = len(matchable_pool) // 2  # R and B0 split the pool, no pair reuse either

    base_sizes = list(PILOT_SIZES.values())
    if args.totals:
        base_sizes += [max(1, t // 2) for t in parse_int_list(args.totals)]
    if args.total_hromadas:
        base_sizes.append(max(1, args.total_hromadas // 2))
    sizes_to_run = [args.n_per_arm] if args.n_per_arm else base_sizes
    power_table = [
        simulate_power_report(min(n, max_per_arm), args.reps, rng, guaranteed_view=args.guaranteed_view)
        for n in sorted(set(sizes_to_run))
    ]

    draw_n = args.n_per_arm or (
        max(1, args.total_hromadas // 2) if args.total_hromadas else PILOT_SIZES["preferred"]
    )
    corpus_capped = draw_n * 2 > len(matchable_pool)

    sample, mechanics_diag = build_report_sample(hromadas, edges, matchable_pool, goals_ready, draw_n, rng)
    event_log = simulate_report_log(sample, hromadas, cuts, rng, guaranteed_view=args.guaranteed_view)
    event_analysis = analyze_report_log(event_log)

    result = {
        "generated_from": PREREG_PATH,
        "note": "SYNTHETIC — no hromada contacted. Priors are illustrative, not fitted.",
        "design": "report",
        "guaranteed_view": args.guaranteed_view,
        "matchable_pool_hromadas": len(matchable_pool),
        "goals_ready_hromadas": len(goals_ready),
        "max_per_arm_no_reuse": max_per_arm,
        "requested_exceeds_corpus_ceiling": corpus_capped,
        "seed": args.seed,
        "mc_reps": args.reps,
        "report_engagement_priors_assumed": REPORT_ENGAGEMENT_PRIOR,
        "power_table": power_table,
        "mechanics_check": mechanics_diag,
        "illustrative_draw_n_per_arm": draw_n,
        "event_log_analysis": event_analysis,
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    import csv

    csv_path = OUT_JSON.parent / "aim-cc-synthetic-report-engagement-log.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(event_log[0].keys()))
        writer.writeheader()
        writer.writerows(event_log)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    print(f"SYNTHETIC dry-run of the 'send every hromada its own report' design — no hromada contacted.")
    print(f"Unit = 1 hromada (no pairing) -> corpus ceiling is {len(matchable_pool)} total (R+B0 combined), "
          f"not //2 like the pair-based designs. ({len(goals_ready)} of those have parsed Goals text; the "
          f"rest are matched via recommend_for_no_goals — geo/network/complementary only, v0.7.)")
    if args.guaranteed_view:
        print(
            "MECHANISM: portal-view, not email — every sampled hromada is assumed to actually see its "
            "report/placebo (deliverable=opened=100%); ATTRITION_RATE and opened_given_delivered are ignored. "
            "The funnel starts at clicked/replied/inbound."
        )
    print()
    if corpus_capped:
        print(
            f"  Requested {draw_n*2} hromadas exceeds that -> arms short-filled from what's left. "
            f"Real max per arm today: {max_per_arm}.\n"
        )
    print("Assumed engagement funnel (ILLUSTRATIVE, not real data):")
    for arm, p in REPORT_ENGAGEMENT_PRIOR.items():
        print(f"  Arm {arm}: {p}")

    print(f"\nPower table (alpha=0.05, {args.reps} MC reps/point) — primary metric = inbound_request_30d:")
    for row in power_table:
        print(
            f"  n/arm={row['n_per_arm']:>4} ({row['total_hromadas']:>4} hromadas total): "
            f"power(opened)={row['power_opened_R_vs_B0']:.0%}  power(inbound@30d)={row['power_inbound_30d_R_vs_B0']:.0%}"
        )

    print(f"\nMechanics check (recommend_for.py per Arm-R hromada): {mechanics_diag}")
    for entry in sample["R"][:3]:
        print(f"  example: {entry['name']} -> report recommends {entry['partner']}  [{entry.get('package_label_uk')}]")

    print(f"\nSimulated engagement log — one draw at n={draw_n}/arm ({draw_n*2} hromadas total), SYNTHETIC:")
    for arm, s in event_analysis["by_arm"].items():
        print(
            f"  Arm {arm}: sent {s['n_sent']}, delivered {s['n_delivered']} -> "
            f"opened {s['opened']['n']} ({s['opened']['rate']:.0%}, CI {s['opened']['wilson_ci']}), "
            f"replied {s['replied_any']['n']} ({s['replied_any']['rate']:.0%}), "
            f"inbound@30d {s['inbound_request_30d']['n']} ({s['inbound_request_30d']['rate']:.0%}), "
            f"inbound@90d {s['inbound_request_90d']['n']} ({s['inbound_request_90d']['rate']:.0%})"
        )
        print(f"           engagement codes={s['engagement_codes']}")
    print("\n  R vs B0 (this one simulated draw):")
    for outcome, t in event_analysis["analysis"].items():
        verdict = "SIGNIFICANT" if t["significant_at_0.05"] else "not significant"
        print(f"    {outcome}: diff={t['risk_difference']:+.1%}, p={t['fisher_p_value']:.4f} -> {verdict}")
    print(f"\nPer-hromada log ({len(event_log)} rows) written to {csv_path.relative_to(ROOT)}")
    print(f"Full JSON written to {OUT_JSON.relative_to(ROOT)}")


def build_pools(edges: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    pools = {"A": [], "B": [], "C": []}
    for e in edges:
        if e.get("known"):
            continue
        track = e.get("track")
        if track == "thematic":
            pools["A"].append(e)
        elif track == "operational":
            pools["B"].append(e)
        elif track == "mixed":
            pools["C"].append(e)
    return pools


def build_rich_signal_arm_a(
    hromadas: dict[str, dict[str, Any]],
    edges: list[dict[str, Any]],
    goals_ready: set[str],
    used_hromadas: set[str],
    n_needed: int,
    rng: np.random.Generator,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Arm A built by actually RUNNING the real multi-signal recommender
    (recommend_for.py, motivation="general": goals 0.45 + geo 0.25 +
    network 0.15 + complementary 0.15 — the full signal stack, not a bare
    track=="thematic" label) for a sample of candidate seed hromadas, and
    taking each seed's top non-known, not-yet-used pick. This both (a)
    uses every signal the real card-generation pipeline uses, and (b) is
    itself a mechanics check: does recommend_for() run cleanly and return
    a sane card for each seed?

    Returns (edge-like rows compatible with block_key/summarize_sample,
    a diagnostics counter of why candidate seeds were skipped).
    """
    complementary = json.loads(COMPLEMENTARY_PATH.read_text(encoding="utf-8"))
    name_to_kat = {h["Name"]: kat for kat, h in hromadas.items()}

    candidate_kats = [k for k in goals_ready if k not in used_hromadas]
    rng.shuffle(candidate_kats)

    diag = Counter()
    rows: list[dict[str, Any]] = []
    for kat in candidate_kats:
        if len(rows) >= n_needed:
            break
        if kat in used_hromadas:
            continue
        seed_name = hromadas[kat]["Name"]
        try:
            cards = rf.recommend_for(
                seed_name, motivation="general", k=5, edges=edges, complementary=complementary
            )
        except Exception:
            diag["recommend_for_error"] += 1
            continue
        picked = None
        for card in cards:
            if card.get("known"):
                diag["skipped_known"] += 1
                continue
            partner_kat = name_to_kat.get(card.get("partner") or "")
            if not partner_kat or partner_kat == kat:
                diag["unresolvable_partner"] += 1
                continue
            if partner_kat in used_hromadas or kat in used_hromadas:
                diag["skipped_reused_hromada"] += 1
                continue
            picked = (card, partner_kat)
            break
        if picked is None:
            diag["no_eligible_card"] += 1
            continue
        card, partner_kat = picked
        used_hromadas.add(kat)
        used_hromadas.add(partner_kat)
        rows.append(
            {
                "a": seed_name,
                "b": card.get("partner"),
                "a_katottg": kat,
                "b_katottg": partner_kat,
                "goals_cosine": card.get("goals_cosine"),
                "geo_score": card.get("geo_score"),
                "mss_network": card.get("mss_network"),
                "complementary_score": card.get("complementary_score"),
                "track": card.get("track"),
                "known": card.get("known"),
                "agent_rank": card.get("agent_rank"),
                "package_label_uk": (card.get("package") or {}).get("label_uk"),
                "why_helps_you_uk": card.get("why_helps_you_uk"),
            }
        )
        diag["accepted"] += 1
    return rows, dict(diag)


def draw_blocked_sample(
    pools: dict[str, list[dict[str, Any]]],
    hromadas: dict[str, dict[str, Any]],
    cuts: tuple[float, float],
    n_per_arm: dict[str, int],
    used_hromadas: set[str],
    rng: np.random.Generator,
) -> dict[str, list[dict[str, Any]]]:
    """One concrete stratified draw per arm in `pools`, proportional to the
    largest pool's block distribution, with no hromada reused across the
    whole sample (avoids arm-to-arm spillover) — `used_hromadas` is shared
    with (and may already be seeded by) other arm-construction methods."""
    blocked: dict[str, dict[str, list[dict[str, Any]]]] = {}
    for arm, pool in pools.items():
        by_block: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for e in pool:
            by_block[block_key(e, hromadas, cuts)].append(e)
        blocked[arm] = by_block

    ref_arm = max(pools, key=lambda k: len(pools[k]))
    ref_counts = Counter({k: len(v) for k, v in blocked[ref_arm].items()})
    ref_total = sum(ref_counts.values()) or 1

    drawn: dict[str, list[dict[str, Any]]] = {arm: [] for arm in pools}

    def eligible(e: dict[str, Any]) -> bool:
        return e.get("a_katottg") not in used_hromadas and e.get("b_katottg") not in used_hromadas

    for arm in pools:
        need = n_per_arm.get(arm, 0)
        target_per_block = {
            k: max(0, round(need * n / ref_total)) for k, n in ref_counts.items()
        }
        block_order = sorted(target_per_block, key=lambda k: -target_per_block[k])
        for blk in block_order:
            if need <= 0:
                break
            take = min(target_per_block[blk], need)
            candidates = [e for e in blocked[arm].get(blk, []) if eligible(e)]
            rng.shuffle(candidates)
            for e in candidates[:take]:
                drawn[arm].append(e)
                used_hromadas.add(e["a_katottg"])
                used_hromadas.add(e["b_katottg"])
                need -= 1
                if need <= 0:
                    break
        if need > 0:
            # blocks under-filled (small pool, e.g. Arm B) -> top up from
            # any remaining eligible edge in the pool, ignoring block target
            leftovers = [e for e in pools[arm] if eligible(e) and e not in drawn[arm]]
            rng.shuffle(leftovers)
            for e in leftovers[:need]:
                drawn[arm].append(e)
                used_hromadas.add(e["a_katottg"])
                used_hromadas.add(e["b_katottg"])

    return drawn


def wilson_ci(successes: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 0.0)
    phat = successes / n
    denom = 1 + z**2 / n
    center = (phat + z**2 / (2 * n)) / denom
    margin = z * ((phat * (1 - phat) / n + z**2 / (4 * n**2)) ** 0.5) / denom
    return (max(0.0, center - margin), min(1.0, center + margin))


def simulate_power(n_per_arm: int, reps: int, rng: np.random.Generator) -> dict[str, Any]:
    """Monte-Carlo power (H1: A>C, H2: B>C) under REPLY_PRIOR, plus a
    null-of-interest run (A=B=C=C's rate) as a pipeline sanity check on
    the Type-I error rate."""

    def run(p_a: float, p_b: float, p_c: float) -> tuple[float, float]:
        a = rng.binomial(1, p_a, size=(reps, n_per_arm)).sum(axis=1)
        b = rng.binomial(1, p_b, size=(reps, n_per_arm)).sum(axis=1)
        c = rng.binomial(1, p_c, size=(reps, n_per_arm)).sum(axis=1)
        sig_a = sig_b = 0
        for i in range(reps):
            _, p1 = fisher_exact([[a[i], n_per_arm - a[i]], [c[i], n_per_arm - c[i]]])
            _, p2 = fisher_exact([[b[i], n_per_arm - b[i]], [c[i], n_per_arm - c[i]]])
            sig_a += p1 < ALPHA
            sig_b += p2 < ALPHA
        return sig_a / reps, sig_b / reps

    power_a, power_b = run(REPLY_PRIOR["A"], REPLY_PRIOR["B"], REPLY_PRIOR["C"])
    false_pos_a, false_pos_b = run(REPLY_PRIOR["C"], REPLY_PRIOR["C"], REPLY_PRIOR["C"])
    return {
        "design": "3arm",
        "n_per_arm": n_per_arm,
        "total_pairs": 3 * n_per_arm,
        "power_H1_A_vs_C": round(power_a, 3),
        "power_H2_B_vs_C": round(power_b, 3),
        "type1_error_A_vs_C": round(false_pos_a, 3),
        "type1_error_B_vs_C": round(false_pos_b, 3),
    }


def simulate_power_2arm(n_per_arm: int, reps: int, rng: np.random.Generator) -> dict[str, Any]:
    """No live control group: test Arm A vs Arm B directly (does thematic
    beat operational?). Frees the hromadas a 3rd arm would have used, but
    can no longer answer "does either beat doing nothing" — see hist_control
    design for that question instead."""
    p_a, p_b = REPLY_PRIOR["A"], REPLY_PRIOR["B"]
    a = rng.binomial(1, p_a, size=(reps, n_per_arm)).sum(axis=1)
    b = rng.binomial(1, p_b, size=(reps, n_per_arm)).sum(axis=1)
    sig = sum(
        fisher_exact([[a[i], n_per_arm - a[i]], [b[i], n_per_arm - b[i]]])[1] < ALPHA
        for i in range(reps)
    )
    a0 = rng.binomial(1, p_a, size=(reps, n_per_arm)).sum(axis=1)
    b0 = rng.binomial(1, p_a, size=(reps, n_per_arm)).sum(axis=1)  # same rate -> null
    false_pos = sum(
        fisher_exact([[a0[i], n_per_arm - a0[i]], [b0[i], n_per_arm - b0[i]]])[1] < ALPHA
        for i in range(reps)
    )
    return {
        "design": "2arm_no_control",
        "n_per_arm": n_per_arm,
        "total_pairs": 2 * n_per_arm,
        "power_A_vs_B": round(sig / reps, 3),
        "type1_error_A_vs_B": round(false_pos / reps, 3),
    }


def simulate_power_hist_control(
    n_per_arm: int, reps: int, hist_rate: float, rng: np.random.Generator
) -> dict[str, Any]:
    """No live control group at all: test each arm's assumed reply rate
    against a FIXED historical base rate (one-sample test) instead of a
    sampled control group. Removes control-group sampling noise entirely,
    at the cost of answering a different, weaker question — see
    load_historical_rates()'s caveat."""

    def run(p: float) -> tuple[float, float]:
        draws = rng.binomial(1, p, size=(reps, n_per_arm)).sum(axis=1)
        sig = sum(binomtest(int(k), n_per_arm, hist_rate, alternative="greater").pvalue < ALPHA for k in draws)
        null_draws = rng.binomial(1, hist_rate, size=(reps, n_per_arm)).sum(axis=1)
        false_pos = sum(
            binomtest(int(k), n_per_arm, hist_rate, alternative="greater").pvalue < ALPHA for k in null_draws
        )
        return sig / reps, false_pos / reps

    power_a, fp_a = run(REPLY_PRIOR["A"])
    power_b, fp_b = run(REPLY_PRIOR["B"])
    return {
        "design": "hist_control",
        "n_per_arm": n_per_arm,
        "total_pairs": 2 * n_per_arm,
        "historical_rate_used": hist_rate,
        "power_A_vs_history": round(power_a, 3),
        "power_B_vs_history": round(power_b, 3),
        "type1_error_A_vs_history": round(fp_a, 3),
        "type1_error_B_vs_history": round(fp_b, 3),
    }


def simulate_ladder(sample: dict[str, list[dict[str, Any]]], rng: np.random.Generator) -> dict[str, Any]:
    ladder: dict[str, dict[str, int]] = {}
    for arm, pairs in sample.items():
        n = len(pairs)
        p_reply = REPLY_PRIOR[arm]
        replied = int(rng.binomial(1, p_reply, n).sum())
        both = int(rng.binomial(1, LADDER_PRIOR["both_replied_given_replied"], replied).sum())
        scheduled = int(rng.binomial(1, LADDER_PRIOR["call_scheduled_given_replied"], replied).sum())
        held = int(rng.binomial(1, LADDER_PRIOR["call_held_given_scheduled"], scheduled).sum())
        agreed = int(rng.binomial(1, LADDER_PRIOR["agreed_next_step_given_call_held"], held).sum())
        concept = int(rng.binomial(1, LADDER_PRIOR["concept_drafted_3mo_given_agreed"], agreed).sum())
        signed = int(rng.binomial(1, LADDER_PRIOR["registry_signed_12mo_given_concept"], concept).sum())
        lo, hi = wilson_ci(replied, n)
        ladder[arm] = {
            "n_pairs": n,
            "replied_21d": replied,
            "reply_rate": round(replied / n, 3) if n else 0.0,
            "reply_rate_wilson_ci": [round(lo, 3), round(hi, 3)],
            "both_replied": both,
            "call_scheduled": scheduled,
            "call_held": held,
            "agreed_next_step_30d": agreed,
            "concept_drafted_3mo": concept,
            "registry_signed_12mo": signed,
        }
    return ladder


def simulate_event_log(
    sample: dict[str, list[dict[str, Any]]],
    hromadas: dict[str, dict[str, Any]],
    cuts: tuple[float, float],
    rng: np.random.Generator,
) -> list[dict[str, Any]]:
    """Per-pair, day-level simulation of one full run of the pilot — as if
    it had actually launched, entirely SYNTHETIC. Every pair gets: send day
    0 (§5.2, both sides same day), delivery success/attrition, a reply
    day/side/channel if it replies within the 21-day window (with a day-10
    reminder bump per §5.2), and the rest of the outcome ladder (§6) with
    plausible day offsets — plus the §8 qualitative stall code for pairs
    that reply but don't advance further. All timing/attrition/channel
    numbers are ASSUMPTIONS (see ATTRITION_RATE / SHARE_REPLY_BEFORE_REMINDER
    / CHANNEL_MIX / STALL_CODE_WEIGHTS above), not observed data."""
    rows: list[dict[str, Any]] = []
    for arm, pairs in sample.items():
        p_reply = REPLY_PRIOR[arm]
        for i, e in enumerate(pairs):
            row: dict[str, Any] = {
                "pair_id": f"{arm}{i+1:03d}",
                "arm": arm,
                "a": e.get("a"),
                "b": e.get("b"),
                "a_katottg": e.get("a_katottg"),
                "b_katottg": e.get("b_katottg"),
                "block": block_key(e, hromadas, cuts),
                "package_label_uk": e.get("package_label_uk"),
                "send_day": 0,
            }
            deliverable = rng.random() > ATTRITION_RATE
            row["deliverable"] = deliverable
            if not deliverable:
                row.update(
                    {
                        "reminder_sent_day": None,
                        "replied_21d": False,
                        "reply_side": None,
                        "reply_day": None,
                        "reply_channel": None,
                        "both_replied": False,
                        "call_scheduled": False,
                        "call_scheduled_day": None,
                        "call_held": False,
                        "call_held_day": None,
                        "agreed_next_step_30d": False,
                        "agreed_day": None,
                        "concept_drafted_3mo": False,
                        "concept_day": None,
                        "registry_signed_12mo": False,
                        "signed_day": None,
                        "qualitative_code": "undeliverable",
                    }
                )
                rows.append(row)
                continue

            replied = rng.random() < p_reply
            row["replied_21d"] = replied
            if not replied:
                row["reminder_sent_day"] = 10
                row.update(
                    {
                        "reply_side": None,
                        "reply_day": None,
                        "reply_channel": None,
                        "both_replied": False,
                        "call_scheduled": False,
                        "call_scheduled_day": None,
                        "call_held": False,
                        "call_held_day": None,
                        "agreed_next_step_30d": False,
                        "agreed_day": None,
                        "concept_drafted_3mo": False,
                        "concept_day": None,
                        "registry_signed_12mo": False,
                        "signed_day": None,
                        "qualitative_code": "no_response",
                    }
                )
                rows.append(row)
                continue

            before_reminder = rng.random() < SHARE_REPLY_BEFORE_REMINDER
            reply_day = int(rng.integers(1, 10)) if before_reminder else int(rng.integers(10, 22))
            row["reminder_sent_day"] = None if before_reminder else 10
            row["reply_day"] = reply_day
            row["reply_channel"] = str(rng.choice(list(CHANNEL_MIX), p=list(CHANNEL_MIX.values())))
            both = rng.random() < LADDER_PRIOR["both_replied_given_replied"]
            row["both_replied"] = both
            row["reply_side"] = "both" if both else str(rng.choice(["a", "b"]))

            scheduled = rng.random() < LADDER_PRIOR["call_scheduled_given_replied"]
            row["call_scheduled"] = scheduled
            row["call_scheduled_day"] = reply_day + int(rng.integers(2, 10)) if scheduled else None

            held = scheduled and rng.random() < LADDER_PRIOR["call_held_given_scheduled"]
            row["call_held"] = held
            row["call_held_day"] = row["call_scheduled_day"] + int(rng.integers(0, 5)) if held else None

            agreed = held and rng.random() < LADDER_PRIOR["agreed_next_step_given_call_held"]
            agreed_day = row["call_held_day"] + int(rng.integers(1, 10)) if agreed else None
            if agreed_day is not None and agreed_day > 30:
                agreed = False
                agreed_day = None
            row["agreed_next_step_30d"] = agreed
            row["agreed_day"] = agreed_day

            concept = agreed and rng.random() < LADDER_PRIOR["concept_drafted_3mo_given_agreed"]
            row["concept_drafted_3mo"] = concept
            row["concept_day"] = agreed_day + int(rng.integers(20, 80)) if concept else None

            signed = concept and rng.random() < LADDER_PRIOR["registry_signed_12mo_given_concept"]
            row["registry_signed_12mo"] = signed
            row["signed_day"] = row["concept_day"] + int(rng.integers(60, 250)) if signed else None

            if signed or concept:
                row["qualitative_code"] = "recognized_shared_priority_advanced"
            else:
                row["qualitative_code"] = str(
                    rng.choice(list(STALL_CODE_WEIGHTS), p=list(STALL_CODE_WEIGHTS.values()))
                )
            rows.append(row)
    return rows


def analyze_event_log(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Runs the §8 pre-registered analysis on a simulated event log: ITT
    among successfully delivered sends, Fisher exact H1 (A vs C) / H2 (B vs
    C), risk difference + Wilson CI per arm, plus the ladder and process
    stats (attrition, channel mix, days-to-reply) a real trial report would
    carry. Purely descriptive of the one simulated log passed in — not a
    Monte-Carlo estimate (see simulate_power_* for that)."""
    by_arm: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        by_arm[r["arm"]].append(r)

    arm_stats: dict[str, Any] = {}
    for arm, arm_rows in by_arm.items():
        n_sent = len(arm_rows)
        delivered = [r for r in arm_rows if r["deliverable"]]
        n_delivered = len(delivered)
        replied = [r for r in delivered if r["replied_21d"]]
        n_replied = len(replied)
        reply_days = [r["reply_day"] for r in replied if r["reply_day"] is not None]
        lo, hi = wilson_ci(n_replied, n_delivered)
        arm_stats[arm] = {
            "n_sent": n_sent,
            "n_delivered": n_delivered,
            "attrition_rate": round(1 - n_delivered / n_sent, 3) if n_sent else 0.0,
            "n_replied_21d": n_replied,
            "reply_rate_itt_delivered": round(n_replied / n_delivered, 3) if n_delivered else 0.0,
            "reply_rate_wilson_ci": [round(lo, 3), round(hi, 3)],
            "median_days_to_reply": float(np.median(reply_days)) if reply_days else None,
            "channel_mix": dict(Counter(r["reply_channel"] for r in replied)),
            "both_replied": sum(r["both_replied"] for r in delivered),
            "call_scheduled": sum(r["call_scheduled"] for r in delivered),
            "call_held": sum(r["call_held"] for r in delivered),
            "agreed_next_step_30d": sum(r["agreed_next_step_30d"] for r in delivered),
            "concept_drafted_3mo": sum(r["concept_drafted_3mo"] for r in delivered),
            "registry_signed_12mo": sum(r["registry_signed_12mo"] for r in delivered),
            "qualitative_codes": dict(Counter(r["qualitative_code"] for r in delivered)),
        }

    tests: dict[str, Any] = {}
    if "A" in arm_stats and "C" in arm_stats:
        a, c = arm_stats["A"], arm_stats["C"]
        table = [
            [a["n_replied_21d"], a["n_delivered"] - a["n_replied_21d"]],
            [c["n_replied_21d"], c["n_delivered"] - c["n_replied_21d"]],
        ]
        _, p = fisher_exact(table)
        tests["H1_A_vs_C"] = {
            "risk_difference": round(a["reply_rate_itt_delivered"] - c["reply_rate_itt_delivered"], 3),
            "fisher_p_value": round(p, 4),
            "significant_at_0.05": bool(p < ALPHA),
        }
    if "B" in arm_stats and "C" in arm_stats:
        b, c = arm_stats["B"], arm_stats["C"]
        table = [
            [b["n_replied_21d"], b["n_delivered"] - b["n_replied_21d"]],
            [c["n_replied_21d"], c["n_delivered"] - c["n_replied_21d"]],
        ]
        _, p = fisher_exact(table)
        tests["H2_B_vs_C"] = {
            "risk_difference": round(b["reply_rate_itt_delivered"] - c["reply_rate_itt_delivered"], 3),
            "fisher_p_value": round(p, 4),
            "significant_at_0.05": bool(p < ALPHA),
        }
    return {"by_arm": arm_stats, "prereg_analysis": tests}


def summarize_sample(
    sample: dict[str, list[dict[str, Any]]],
    hromadas: dict[str, dict[str, Any]],
    cuts: tuple[float, float],
    explicit_ask: set[str],
) -> dict[str, Any]:
    out = {}
    for arm, pairs in sample.items():
        rows = []
        for e in pairs:
            a = hromadas.get(e.get("a_katottg"), {})
            b = hromadas.get(e.get("b_katottg"), {})
            rows.append(
                {
                    "a": e.get("a"),
                    "b": e.get("b"),
                    "block": block_key(e, hromadas, cuts),
                    "goals_cosine": e.get("goals_cosine"),
                    "geo_score": e.get("geo_score"),
                    "explicit_ask_seed": bool(
                        e.get("a_katottg") in explicit_ask or e.get("b_katottg") in explicit_ask
                    ),
                }
            )
        blocks = Counter(r["block"] for r in rows)
        out[arm] = {"n": len(rows), "block_distribution": dict(blocks), "pairs": rows}
    return out


def parse_int_list(s: str) -> list[int]:
    return [int(x.strip()) for x in s.split(",") if x.strip()]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--reps", type=int, default=3000, help="Monte Carlo replicates per power-curve point")
    ap.add_argument(
        "--design",
        choices=["3arm", "2arm", "hist_control", "report"],
        default="3arm",
        help="3arm=A/B/C prereg RCT; 2arm=A vs B only, no live control; "
        "hist_control=A and B each tested vs a fixed historical base rate, no live control; "
        "report=send every hromada its OWN report (unit=hromada, not pair) and measure engagement "
        "+ unprompted follow-up instead of a partner-intro reply",
    )
    ap.add_argument(
        "--totals",
        type=str,
        default=None,
        help="comma-separated TOTAL HROMADAS (not pairs) budgets to add to the power table, e.g. '100,200' "
        "(each pair uses 2 hromadas, no reuse, so total_pairs = total_hromadas // 2)",
    )
    ap.add_argument("--n-per-arm", type=int, default=None, help="draw+ladder-simulate only this pilot size")
    ap.add_argument(
        "--total-hromadas",
        type=int,
        default=None,
        help="size the ONE illustrative draw (event log / ladder) from a total hromada budget instead of "
        "--n-per-arm, e.g. --total-hromadas 400. Also folded into the power table.",
    )
    ap.add_argument(
        "--event-log",
        dest="event_log",
        action="store_true",
        default=True,
        help="simulate a per-pair, day-level communication log (who/when/how replied, full §8 ITT analysis "
        "on it) for the illustrative draw, and write it to internal/aim-cc-synthetic-event-log.csv [default]",
    )
    ap.add_argument("--no-event-log", dest="event_log", action="store_false")
    ap.add_argument(
        "--rich-signals",
        dest="rich_signals",
        action="store_true",
        default=True,
        help="build Arm A via the real recommend_for.py recommender (all signals: goals+geo+network+"
        "complementary) instead of a bare track=='thematic' filter [default]",
    )
    ap.add_argument("--no-rich-signals", dest="rich_signals", action="store_false")
    ap.add_argument(
        "--guaranteed-view",
        dest="guaranteed_view",
        action="store_true",
        default=False,
        help="--design report only: the report/placebo renders as soon as the hromada visits a portal "
        "(no email-open step to fail) — deliverable=opened=100%% for every sampled hromada instead of "
        "ATTRITION_RATE / opened_given_delivered",
    )
    ap.add_argument("--json", action="store_true", help="print full JSON to stdout instead of a summary")
    args = ap.parse_args()

    rng = np.random.default_rng(args.seed)

    hromadas = load_hromadas()
    edges = load_edges()
    explicit_ask = load_explicit_ask_katottgs()
    pools = build_pools(edges)
    goals_ready = {kat for kat, h in hromadas.items() if (h.get("Goals") or "").strip()}
    cuts = population_tertiles(hromadas, goals_ready)
    total_pairs_in_corpus = len(edges)

    if args.design == "report":
        # v0.7: sampling frame is every hromada with a KATOTTG (hromadas is
        # already keyed by Katottg, see load_hromadas), not just goals_ready —
        # recommend_for.py now matches goals-less seeds too. Population
        # tertile cuts for blocking are recomputed over that wider frame.
        matchable_pool = set(hromadas.keys())
        cuts_matchable = population_tertiles(hromadas, matchable_pool)
        run_report_design(args, hromadas, edges, matchable_pool, goals_ready, cuts_matchable, rng)
        return

    pool_sizes = {arm: len(p) for arm, p in pools.items()}

    arms_in_design = {"3arm": 3, "2arm": 2, "hist_control": 2}[args.design]

    # --- power table: §4 pilot sizes (8/12/20 per arm) + any user --totals
    base_sizes = list(PILOT_SIZES.values())
    if args.totals:
        base_sizes += [max(1, t // 2 // arms_in_design) for t in parse_int_list(args.totals)]
    if args.total_hromadas:
        base_sizes.append(max(1, args.total_hromadas // 2 // arms_in_design))
    sizes_to_run = [args.n_per_arm] if args.n_per_arm else base_sizes

    if args.design == "3arm":
        power_table = [simulate_power(n, args.reps, rng) for n in sorted(set(sizes_to_run))]
    elif args.design == "2arm":
        power_table = [simulate_power_2arm(n, args.reps, rng) for n in sorted(set(sizes_to_run))]
    else:
        hist = load_historical_rates(total_pairs_in_corpus)
        hist_rate = hist["network_tie_ever"]["rate"]
        power_table = [
            simulate_power_hist_control(n, args.reps, hist_rate, rng) for n in sorted(set(sizes_to_run))
        ]

    # --- one concrete illustrative draw, at the chosen (or preferred) size
    draw_n = args.n_per_arm or (
        max(1, args.total_hromadas // 2 // arms_in_design) if args.total_hromadas else PILOT_SIZES["preferred"]
    )
    needs_partner_org = bool(args.total_hromadas and args.total_hromadas > 120)

    # Hard corpus ceiling: the no-hromada-reuse rule means the WHOLE sample
    # (every arm combined) can never use more than 2x the goals-ready pool.
    max_pairs_no_reuse = len(goals_ready) // 2
    requested_total_pairs = draw_n * arms_in_design
    corpus_capped = requested_total_pairs > max_pairs_no_reuse
    used_hromadas: set[str] = set()
    mechanics_diag: dict[str, int] = {}
    if args.design == "3arm":
        arms_needed = {"A": draw_n, "B": draw_n, "C": draw_n}
    else:
        arms_needed = {"A": draw_n, "B": draw_n}

    sample: dict[str, list[dict[str, Any]]] = {}
    if args.rich_signals:
        armA_rows, mechanics_diag = build_rich_signal_arm_a(
            hromadas, edges, goals_ready, used_hromadas, arms_needed["A"], rng
        )
        sample["A"] = armA_rows
    rest_pools = {k: v for k, v in pools.items() if k in arms_needed}
    if args.rich_signals:
        rest_pools.pop("A", None)
    rest_n = {k: arms_needed[k] for k in rest_pools}
    if rest_pools:
        drawn_rest = draw_blocked_sample(rest_pools, hromadas, cuts, rest_n, used_hromadas, rng)
        sample.update(drawn_rest)

    sample_summary = summarize_sample(sample, hromadas, cuts, explicit_ask)
    ladder = simulate_ladder(sample, rng)

    event_log = None
    event_analysis = None
    if args.event_log:
        event_log = simulate_event_log(sample, hromadas, cuts, rng)
        event_analysis = analyze_event_log(event_log)

    result = {
        "generated_from": PREREG_PATH,
        "note": "SYNTHETIC — no hromada contacted. Priors are illustrative, not fitted.",
        "design": args.design,
        "needs_partner_org": needs_partner_org,
        "goals_ready_hromadas": len(goals_ready),
        "max_pairs_no_reuse_whole_sample": max_pairs_no_reuse,
        "requested_total_pairs_exceeds_corpus_ceiling": corpus_capped,
        "rich_signals_arm_a": args.rich_signals,
        "seed": args.seed,
        "mc_reps": args.reps,
        "pool_sizes_current_corpus": pool_sizes,
        "population_tertile_cuts": {"low_mid": cuts[0], "mid_high": cuts[1]},
        "reply_priors_assumed": REPLY_PRIOR,
        "ladder_priors_assumed": LADDER_PRIOR,
        "event_log_priors_assumed": {
            "attrition_rate": ATTRITION_RATE,
            "share_reply_before_reminder": SHARE_REPLY_BEFORE_REMINDER,
            "channel_mix": CHANNEL_MIX,
            "stall_code_weights": STALL_CODE_WEIGHTS,
        },
        "power_table": power_table,
        "mechanics_check_arm_a": mechanics_diag,
        "illustrative_draw": {"n_per_arm": draw_n, "sample": sample_summary},
        "illustrative_outcome_ladder": ladder,
        "event_log_analysis": event_analysis,
    }
    if args.design == "hist_control":
        result["historical_rates"] = load_historical_rates(total_pairs_in_corpus)

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    if event_log:
        import csv

        csv_path = OUT_JSON.parent / "aim-cc-synthetic-event-log.csv"
        with csv_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(event_log[0].keys()))
            writer.writeheader()
            writer.writerows(event_log)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    print(f"SYNTHETIC dry-run of {PREREG_PATH} — no hromada contacted.")
    print(f"Design: {args.design} | Arm A signals: {'rich (recommend_for.py)' if args.rich_signals else 'track label only'}\n")
    print("Pool sizes (current corpus, known=false only):")
    for arm, label in (("A", "thematic"), ("B", "operational"), ("C", "control/mixed")):
        print(f"  Arm {arm} ({label}): {pool_sizes[arm]}")
    print("\nAssumed reply priors (ILLUSTRATIVE, not real data):")
    for arm, p in REPLY_PRIOR.items():
        print(f"  Arm {arm}: {p:.0%}")

    print(f"\nPower table (alpha=0.05, {args.reps} MC reps/point):")
    for row in power_table:
        n = row["n_per_arm"]
        if args.design == "3arm":
            print(
                f"  n/arm={n:>4} (total={row['total_pairs']:>3} pairs / {row['total_pairs']*2:>3} hromadas): "
                f"power H1(A>C)={row['power_H1_A_vs_C']:.0%}  power H2(B>C)={row['power_H2_B_vs_C']:.0%}  "
                f"type-I=[{row['type1_error_A_vs_C']:.0%},{row['type1_error_B_vs_C']:.0%}]"
            )
        elif args.design == "2arm":
            print(
                f"  n/arm={n:>4} (total={row['total_pairs']:>3} pairs / {row['total_pairs']*2:>3} hromadas): "
                f"power A-vs-B={row['power_A_vs_B']:.0%}  type-I={row['type1_error_A_vs_B']:.0%}"
            )
        else:
            print(
                f"  n/arm={n:>4} (total={row['total_pairs']:>3} pairs / {row['total_pairs']*2:>3} hromadas): "
                f"power A-vs-hist={row['power_A_vs_history']:.0%}  power B-vs-hist={row['power_B_vs_history']:.0%}  "
                f"(hist rate={row['historical_rate_used']:.3%})"
            )
    if args.design == "hist_control":
        hist = result["historical_rates"]
        print(f"\n  {hist['caveat']}")
        print(
            f"  network-tie-ever rate: {hist['network_tie_ever']['rate']:.3%} "
            f"({hist['network_tie_ever']['count']}/{hist['denominator_total_pairs_in_corpus']})"
        )
        print(
            f"  signed-known-ever rate: {hist['signed_known_ever']['rate']:.3%} "
            f"({hist['signed_known_ever']['count']}/{hist['denominator_total_pairs_in_corpus']})"
        )

    if args.rich_signals:
        print(f"\nMechanics check — recommend_for.py run for each Arm-A seed: {mechanics_diag}")
        for row in sample.get("A", [])[:3]:
            print(f"  example: {row['a']} -> {row['b']}  [{row.get('package_label_uk')}]")
            print(f"    why: {row.get('why_helps_you_uk')}")

    if needs_partner_org:
        print(
            f"\nNOTE: {draw_n * arms_in_design} pairs (~{draw_n * arms_in_design * 2} hromadas) exceeds the "
            "prereg's own §4 'stretch' ceiling (20/arm=60 pairs) — this size explicitly needs a partner org "
            "(U-LEAD / PIN / an association) to reach and process, per §4."
        )
    print(
        f"\nCORPUS CEILING: only {len(goals_ready)} hromadas have parsed Goals text at all — with the "
        f"no-hromada-reuse rule (no hromada appears in >1 pair, to avoid arm-to-arm spillover), the WHOLE "
        f"sample across every arm combined can never exceed {max_pairs_no_reuse} pairs "
        f"({max_pairs_no_reuse * 2} hromadas), no matter how the design is sliced."
    )
    if corpus_capped:
        print(
            f"  Requested {requested_total_pairs} pairs total ({requested_total_pairs * 2} hromadas) EXCEEDS "
            f"that ceiling -> some arm(s) below will be short-filled from whatever's left, not the requested "
            f"n/arm. To really reach this size: relax no-reuse (contamination risk), or grow the Goals corpus "
            f"(see docs/agent-centric-recommendations.md's sampling-frame note; only 293/1463 hromadas "
            "currently have parsed Goals)."
        )

    print(f"\nIllustrative draw at n={draw_n}/arm ({draw_n * arms_in_design} pairs total), block distribution:")
    for arm in sample:
        print(f"  Arm {arm}: n={sample_summary[arm]['n']}  blocks={sample_summary[arm]['block_distribution']}")

    if event_analysis:
        print(
            "\nSimulated communication log — as if this pilot actually ran, one random draw "
            "(SYNTHETIC, see event_log_priors_assumed in the JSON for the assumptions):"
        )
        for arm, s in event_analysis["by_arm"].items():
            ci = s["reply_rate_wilson_ci"]
            days = f"{s['median_days_to_reply']:.0f}d" if s["median_days_to_reply"] is not None else "n/a"
            print(
                f"  Arm {arm}: sent {s['n_sent']}, delivered {s['n_delivered']} "
                f"(attrition {s['attrition_rate']:.0%}) -> replied {s['n_replied_21d']} "
                f"({s['reply_rate_itt_delivered']:.0%}, Wilson 95% CI [{ci[0]:.0%},{ci[1]:.0%}]), "
                f"median time-to-reply {days}, channels={s['channel_mix']}"
            )
            print(
                f"           call held {s['call_held']}, agreed next step {s['agreed_next_step_30d']}, "
                f"concept@3mo {s['concept_drafted_3mo']}, signed@12mo {s['registry_signed_12mo']}, "
                f"stall codes={s['qualitative_codes']}"
            )
        print("\n  §8 pre-registered analysis on this simulated log (ITT among delivered):")
        for hyp, t in event_analysis["prereg_analysis"].items():
            verdict = "SIGNIFICANT" if t["significant_at_0.05"] else "not significant"
            print(
                f"    {hyp}: risk difference={t['risk_difference']:+.0%}, "
                f"Fisher p={t['fisher_p_value']:.4f} -> {verdict} at alpha=0.05"
            )
        print(f"\n  Per-pair event log ({len(event_log)} rows) written to "
              f"{(OUT_JSON.parent / 'aim-cc-synthetic-event-log.csv').relative_to(ROOT)}")
    else:
        print("\nSimulated outcome ladder for that one draw (illustrative, not a forecast):")
        for arm in sample:
            row = ladder[arm]
            ci = row["reply_rate_wilson_ci"]
            print(
                f"  Arm {arm}: {row['replied_21d']}/{row['n_pairs']} replied "
                f"({row['reply_rate']:.0%}, Wilson 95% CI [{ci[0]:.0%},{ci[1]:.0%}]) -> "
                f"call held {row['call_held']}, agreed next step {row['agreed_next_step_30d']}, "
                f"concept @3mo {row['concept_drafted_3mo']}, registry @12mo {row['registry_signed_12mo']}"
            )
    print(f"\nFull JSON written to {OUT_JSON.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
