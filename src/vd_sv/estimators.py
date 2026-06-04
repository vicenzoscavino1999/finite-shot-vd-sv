"""Finite-shot sampling helpers shared by VD and SV.

To keep memory ``O(T)`` even for large shot budgets ``B``, sample mean estimators
are drawn from their sufficient statistics (binomial / multinomial counts) rather
than by materializing ``B`` individual shots.  For a one-shot variable in ``{+-1}``
with mean ``m``, the sample mean over ``B`` shots is exactly
``2 * Binomial(B, (1+m)/2) / B - 1``.
"""

from __future__ import annotations

import numpy as np


def make_rng(seed: int) -> np.random.Generator:
    """Project RNG convention (REPRODUCIBILITY_PLAN randomness policy)."""
    return np.random.Generator(np.random.PCG64(seed))


def clipped_quotient(n_hat: np.ndarray, d_hat: np.ndarray, d_floor: float) -> np.ndarray:
    """Clipped ratio ``n_hat / max(d_hat, d_floor)`` (eq. clipped_quotient_v4)."""
    return n_hat / np.maximum(d_hat, d_floor)


def mse(estimates: np.ndarray, mu_star: float) -> float:
    """Empirical MSE of estimator replicas against the exact target ``mu_star``."""
    e = np.asarray(estimates, dtype=np.float64)
    return float(np.mean((e - mu_star) ** 2))


def replicate_mse(estimates: np.ndarray, mu_star: float, n_boot: int, rng) -> tuple[float, float]:
    """MSE plus a bootstrap standard error over the ``T`` replicas (for WLS weights)."""
    e = np.asarray(estimates, dtype=np.float64)
    point = float(np.mean((e - mu_star) ** 2))
    if n_boot <= 0:
        return point, 0.0
    t = e.size
    idx = rng.integers(0, t, size=(n_boot, t))
    boots = np.mean((e[idx] - mu_star) ** 2, axis=1)
    return point, float(np.std(boots, ddof=1))


def sample_direct_mean(pz: np.ndarray, value: np.ndarray, B: int, T: int,
                       rng) -> np.ndarray:
    """Unmitigated estimator: sample mean of a Z-diagonal observable over ``B`` shots.

    Returns ``T`` replicas of ``mean_s O(z_s)`` with ``z_s ~ pz``.
    """
    counts = rng.multinomial(B, _normalize(pz), size=T)
    return counts @ np.asarray(value, dtype=np.float64) / B


def _normalize(pz: np.ndarray) -> np.ndarray:
    p = np.clip(np.asarray(pz, dtype=np.float64), 0.0, None)
    s = p.sum()
    if s <= 0:
        raise ValueError("non-positive probability vector")
    return p / s
