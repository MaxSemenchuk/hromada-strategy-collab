"""Pairwise social-capital / cooperation-readiness score (v7.3 0.15 slot).

This is NOT «they have a Law 1508-VII agreement» and never sets known=true.
Direct domestic ties (KSE PIN / Пліч-о-пліч) are the floor — the same signal
that used to occupy the whole 0.15 slot as `mss_network`. Extra evidence of
readiness (named neighbour in a strategy, both practiced UA–EU twinning,
shared donor cohort) adds at lower weight, capped at 1.0.

One-sided twinning or «both did IMC with someone else» is not a pair signal —
it flooded the Goals matrix (~half of edges) and hub-boosted cities like Odesa.

Kept out of this slot (different jobs):
  - complementary resource↔Challenges («навіщо» / benefit)
  - HydroBASINS / same_basin (map context)
  - goals cosine / geo (the other two formula slots)
  - STRATEGY LAB / Ре:Форм tags (corpus methodology, not IMC portfolio)

`mss_network` remains the KSE|Пліч pairwise field for PIN∩corpus reports
and operational-slice exclusion.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
RELEASES = ROOT / "data" / "releases"
HROMADAS = RELEASES / "hromadas.json"
EXPLICIT_ASK = RELEASES / "matching-edges.explicit-ask.json"
TWINNING = RELEASES / "twinning-partners.json"

# Direct domestic floor is whatever mss_network_score already returns (0 / 0.5 / 1).
W_NAMED = 0.70  # strategy named this exact neighbour
W_COINTENT = 0.40  # both use МСС language, same oblast, not named
W_TWINNING_BOTH = 0.30  # both have registry-confidence UA–EU twinning
W_SHARED_DONOR = 0.25  # shared DOBRE / U-LEAD / … cohort

# Node-level «one twin / both did IMC with someone else» is too dense in the
# Goals corpus (tens of thousands of pairs) and hub-biased (Odesa). Pairwise
# readiness only: a *shared* affiliation or a named/direct tie.

# Strategy-writing support, not an IMC/donor cohort (see docs/donor-programs.md).
METHODOLOGY_PROGRAMS = frozenset({"STRATEGY LAB", "Ре:Форм"})


def parse_programs(raw: Any) -> list[str]:
    if raw is None or raw == "":
        return []
    if isinstance(raw, list):
        items = [str(x).strip() for x in raw if str(x).strip()]
    else:
        items = [p.strip() for p in str(raw).replace(";", ",").split(",") if p.strip()]
    return [p for p in items if p not in METHODOLOGY_PROGRAMS]


def combine_social_capital(
    *,
    mss_network: float = 0.0,
    named: bool = False,
    cointent: bool = False,
    twinning_both: bool = False,
    shared_donor: bool = False,
) -> tuple[float, dict[str, Any]]:
    """Blend sub-signals. Direct ties take max(); affiliations add; cap 1.0."""
    mss = max(0.0, min(1.0, float(mss_network or 0.0)))
    flags: list[str] = []
    if mss >= 1.0:
        flags.append("kse_or_plich")
    elif mss > 0:
        flags.append("plich_comention")
    if named:
        flags.append("named")
    elif cointent:
        flags.append("cointent")
    direct = max(mss, W_NAMED if named else 0.0, W_COINTENT if cointent else 0.0)
    extras = 0.0
    if twinning_both:
        extras += W_TWINNING_BOTH
        flags.append("twinning_both")
    if shared_donor:
        extras += W_SHARED_DONOR
        flags.append("shared_donor")
    score = min(1.0, direct + extras)
    parts = {
        "direct": round(direct, 3),
        "extras": round(extras, 3),
        "flags": flags,
    }
    return score, parts


def _pair_in(
    name_set: set[frozenset[str]],
    kat_set: set[frozenset[str]],
    *,
    name_a: str | None,
    name_b: str | None,
    kat_a: str | None,
    kat_b: str | None,
) -> bool:
    if kat_a and kat_b and frozenset((kat_a, kat_b)) in kat_set:
        return True
    if name_a and name_b and frozenset((name_a, name_b)) in name_set:
        return True
    return False


@lru_cache(maxsize=1)
def load_index() -> dict[str, Any]:
    name_to_kat: dict[str, str] = {}
    programs_by_kat: dict[str, frozenset[str]] = {}
    programs_by_name: dict[str, frozenset[str]] = {}
    if HROMADAS.exists():
        for row in json.loads(HROMADAS.read_text(encoding="utf-8")):
            name = (row.get("Name") or "").strip()
            kat = (row.get("Katottg") or row.get("KATOTTG") or "").strip()
            if name and kat:
                name_to_kat.setdefault(name, kat)
            programs = frozenset(parse_programs(row.get("DonorsPrograms")))
            if programs:
                if kat:
                    programs_by_kat[kat] = programs
                if name:
                    programs_by_name[name] = programs

    named_names: set[frozenset[str]] = set()
    named_kats: set[frozenset[str]] = set()
    cointent_names: set[frozenset[str]] = set()
    cointent_kats: set[frozenset[str]] = set()
    if EXPLICIT_ASK.exists():
        payload = json.loads(EXPLICIT_ASK.read_text(encoding="utf-8"))
        rows = payload if isinstance(payload, list) else payload.get("edges") or []
        for e in rows:
            a, b = (e.get("a") or "").strip(), (e.get("b") or "").strip()
            if not a or not b:
                continue
            reasons = " ".join(e.get("reasons") or [])
            is_named = "named" in reasons.lower() or float(e.get("explicit_ask_score") or 0) >= 0.9
            key_n = frozenset((a, b))
            ka, kb = name_to_kat.get(a), name_to_kat.get(b)
            key_k = frozenset((ka, kb)) if ka and kb else None
            if is_named:
                named_names.add(key_n)
                if key_k:
                    named_kats.add(key_k)
            else:
                cointent_names.add(key_n)
                if key_k:
                    cointent_kats.add(key_k)

    twinning_registry: set[str] = set()
    if TWINNING.exists():
        for row in json.loads(TWINNING.read_text(encoding="utf-8")).get("hromadas") or []:
            kat = (row.get("katottg") or "").strip()
            if not kat:
                continue
            if any(p.get("confidence") == "registry" for p in row.get("partners") or []):
                twinning_registry.add(kat)

    return {
        "name_to_kat": name_to_kat,
        "named_names": named_names,
        "named_kats": named_kats,
        "cointent_names": cointent_names,
        "cointent_kats": cointent_kats,
        "twinning_registry": twinning_registry,
        "programs_by_kat": programs_by_kat,
        "programs_by_name": programs_by_name,
    }


def social_capital_score(
    kat_a: str | None,
    kat_b: str | None,
    *,
    name_a: str | None = None,
    name_b: str | None = None,
    mss_network: float | None = None,
    index: dict[str, Any] | None = None,
) -> tuple[float, dict[str, Any]]:
    idx = index if index is not None else load_index()
    ka = (kat_a or "").strip() or None
    kb = (kat_b or "").strip() or None
    na = (name_a or "").strip() or None
    nb = (name_b or "").strip() or None
    if mss_network is None:
        from enrich_from_kse import mss_network_score

        mss = mss_network_score(ka, kb)
    else:
        mss = float(mss_network)

    named = _pair_in(
        idx["named_names"], idx["named_kats"], name_a=na, name_b=nb, kat_a=ka, kat_b=kb
    )
    cointent = (not named) and _pair_in(
        idx["cointent_names"],
        idx["cointent_kats"],
        name_a=na,
        name_b=nb,
        kat_a=ka,
        kat_b=kb,
    )
    twin_a = bool(ka and ka in idx["twinning_registry"])
    twin_b = bool(kb and kb in idx["twinning_registry"])
    progs_a = idx["programs_by_kat"].get(ka or "") or idx["programs_by_name"].get(na or "") or frozenset()
    progs_b = idx["programs_by_kat"].get(kb or "") or idx["programs_by_name"].get(nb or "") or frozenset()
    return combine_social_capital(
        mss_network=mss,
        named=named,
        cointent=cointent,
        twinning_both=twin_a and twin_b,
        shared_donor=bool(progs_a & progs_b),
    )


def annotate_edges(edges: list[dict[str, Any]]) -> dict[str, int]:
    """Set social_capital / parts / explicit_ask_score on existing edges."""
    idx = load_index()
    n_gt_mss = 0
    n_pos = 0
    for e in edges:
        mss = float(e.get("mss_network") or 0.0)
        sc, parts = social_capital_score(
            e.get("a_katottg"),
            e.get("b_katottg"),
            name_a=e.get("a"),
            name_b=e.get("b"),
            mss_network=mss,
            index=idx,
        )
        e["social_capital"] = round(sc, 3)
        e["social_capital_parts"] = parts
        flags = parts.get("flags") or []
        if "named" in flags:
            e["explicit_ask_score"] = max(float(e.get("explicit_ask_score") or 0), 0.95)
        elif "cointent" in flags:
            e["explicit_ask_score"] = max(float(e.get("explicit_ask_score") or 0), 0.75)
        if sc > 0:
            n_pos += 1
        if sc > mss + 1e-9:
            n_gt_mss += 1
    return {
        "annotated": len(edges),
        "positive": n_pos,
        "above_mss_network": n_gt_mss,
    }


def rescore_edges(edges: list[dict[str, Any]]) -> None:
    """Recompute combined `score` from stored priority + geo + social_capital."""
    from dream_priority import combined_match_score, priority_from_edge

    for e in edges:
        sc = float(e.get("social_capital") or 0.0)
        geo = float(e.get("geo_score") or 0.0)
        e["score"] = round(combined_match_score(priority_from_edge(e), geo, sc), 3)
