"""Shared fixtures: a small, fast, deterministic white-box model (no angle optimization)."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

# make the repo-root `experiments` package importable from tests
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from vd_sv import coefficients as cf
from vd_sv import noise, qaoa


@pytest.fixture(scope="session")
def model() -> cf.WhiteBoxModel:
    # n=6, sector k=2 (NOT half-filling), fixed angles, heterogeneous AD+PD channel.
    inst = qaoa.ring_instance(6, weights=np.array([1.0, 1.3, 0.7, 1.1, 0.9, 1.2]),
                              weight=2, name="ring6_k2")
    gammas, betas = np.array([0.6]), np.array([1.1])  # fixed -> fast & deterministic
    channel = noise.heterogeneous_ad_pd(6, seed=1)
    return cf.build_model(inst, gammas, betas, channel)


@pytest.fixture(scope="session")
def instance():
    return qaoa.ring_instance(6, weights=np.array([1.0, 1.3, 0.7, 1.1, 0.9, 1.2]), weight=2)
