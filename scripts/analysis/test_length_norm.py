#!/usr/bin/env python3
"""Unit checks for v7.1 bipartite+centroid length/hub blend (no model download)."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
from match import WEIGHT_BIPARTITE, WEIGHT_CENTROID, _blend_bipartite_centroid  # noqa: E402


def _ortho_basis(dim: int = 8) -> np.ndarray:
    rng = np.random.default_rng(0)
    m = rng.normal(size=(dim, dim))
    q, _ = np.linalg.qr(m)
    return q


def test_focused_pair_scores_higher_than_comprehensive_hubs() -> None:
    """Two focused docs sharing one axis beat two long diverse 'hub' docs."""
    basis = _ortho_basis(8)
    # Focused: both near axis 0
    focused_a = np.stack([basis[0], 0.9 * basis[0] + 0.1 * basis[1]])
    focused_b = np.stack([basis[0], 0.85 * basis[0] + 0.15 * basis[2]])
    # Comprehensive hubs: cover many orthogonal axes (centroid → near 0 after re-center)
    hub_a = basis[:6]
    hub_b = np.stack([basis[(i + 1) % 8] for i in range(6)])

    stacked = np.vstack([focused_a, focused_b, hub_a, hub_b])
    centered = stacked - stacked.mean(axis=0)
    centered = centered / np.clip(np.linalg.norm(centered, axis=1, keepdims=True), 1e-8, None)
    weight = np.ones(len(centered))

    fa, fb = [0, 1], [2, 3]
    ha, hb = list(range(4, 10)), list(range(10, 16))
    focused, _ = _blend_bipartite_centroid(centered, weight, fa, fb)
    hubs, _ = _blend_bipartite_centroid(centered, weight, ha, hb)
    assert focused > hubs, f"expected focused {focused:.3f} > hubs {hubs:.3f}"
    assert focused > 0.2


def test_true_cosine_not_ix_slice() -> None:
    """Identical unit vectors must score ~1 (would fail under the old np.ix_ bug)."""
    v = np.zeros((2, 8))
    v[0, 0] = 1.0
    v[1, 0] = 1.0
    weight = np.ones(2)
    score, _ = _blend_bipartite_centroid(v, weight, [0], [1])
    assert score > 0.99, f"identical vectors scored {score}"


def test_blend_weights_sum_to_one() -> None:
    assert abs(WEIGHT_BIPARTITE + WEIGHT_CENTROID - 1.0) < 1e-9


def test_empty_returns_zero() -> None:
    centered = np.eye(3)
    weight = np.ones(3)
    score, evidence = _blend_bipartite_centroid(centered, weight, [], [0])
    assert score == 0.0
    assert evidence is None


def test_length_cap_prefers_shared_core() -> None:
    """Long doc vs short: only top-min(n,m) matches count on each side."""
    basis = _ortho_basis(8)
    short = np.stack([basis[0], basis[1]])
    # long: two shared axes + four orthogonal noise lines
    long = np.stack([basis[0], basis[1], basis[2], basis[3], basis[4], basis[5]])
    stacked = np.vstack([short, long])
    centered = stacked - stacked.mean(axis=0)
    centered = centered / np.clip(np.linalg.norm(centered, axis=1, keepdims=True), 1e-8, None)
    weight = np.ones(len(centered))
    score, _ = _blend_bipartite_centroid(centered, weight, [0, 1], list(range(2, 8)))
    # Should stay healthy thanks to shared axes (not dragged down by 4 noise lines)
    assert score > 0.25, score


def main() -> None:
    test_blend_weights_sum_to_one()
    test_empty_returns_zero()
    test_true_cosine_not_ix_slice()
    test_focused_pair_scores_higher_than_comprehensive_hubs()
    test_length_cap_prefers_shared_core()
    print("OK: length-norm blend unit checks passed")


if __name__ == "__main__":
    main()
