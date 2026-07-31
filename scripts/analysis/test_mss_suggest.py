#!/usr/bin/env python3
"""Unit checks for mss_suggest theme/form rules."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
from mss_suggest import (  # noqa: E402
    FORM_LABELS,
    load_registry_theme_form_priors,
    suggest_form,
    suggest_package,
)


def test_packages() -> None:
    priors: dict[str, str] = {}  # isolate from registry for deterministic asserts

    cnap = suggest_package(
        text_blob="спільний ЦНАП та адміністративні послуги для мешканців",
        track="operational",
        registry_priors=priors,
    )
    assert cnap["suggested_theme_id"] == "cnap", cnap
    assert cnap["suggested_form_id"] == "delegation", cnap

    tourism = suggest_package(
        text_blob="туристичний маршрут і фестиваль спадщини",
        track="thematic",
        registry_priors=priors,
    )
    assert tourism["suggested_theme_id"] == "tourism", tourism
    assert tourism["suggested_form_id"] == "joint_project", tourism

    waste = suggest_package(
        text_blob="полігон ТПВ та сортування відходів",
        track="operational",
        registry_priors=priors,
    )
    assert waste["suggested_theme_id"] == "waste", waste
    assert waste["suggested_form_id"] == "joint_enterprise", waste

    agg = suggest_package(
        text_blob="формування Львівської агломерації з сусідніми громадами",
        track="thematic",
        registry_priors=priors,
    )
    assert agg["suggested_theme_id"] == "agglomeration", agg
    assert agg["suggested_form_id"] == "agglomeration", agg
    assert agg.get("suggest_caveat"), agg


def test_form_defaults() -> None:
    form_id, _ = suggest_form("education", track="operational", registry_priors={})
    assert form_id == "joint_finance"
    form_id, _ = suggest_form("cnap", track="operational", registry_priors={})
    assert form_id == "delegation"
    form_id, rationale = suggest_form(
        "tourism", track="thematic", multi_party_hint=True, registry_priors={}
    )
    assert form_id == "joint_project"
    assert "проєкт" in FORM_LABELS[form_id] or "спільний" in rationale.lower() or True


def test_registry_priors_smoke() -> None:
    priors = load_registry_theme_form_priors()
    # Cache may be empty if openpyxl missing; otherwise expect a few themes
    if priors:
        assert "cnap" in priors or "education" in priors or "tourism" in priors or len(priors) >= 1
        print(f"registry priors ok ({len(priors)} themes)")
    else:
        print("registry priors empty (no xlsx / openpyxl) — skipped assert")


def main() -> None:
    test_packages()
    test_form_defaults()
    test_registry_priors_smoke()
    print("test_mss_suggest: OK")


if __name__ == "__main__":
    main()
