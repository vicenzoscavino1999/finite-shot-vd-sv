"""E5 - VD denominator concentration (validates P7 in development mode).

Theory anchor: Lemma denom_bernstein_v4, eqs. bernstein_denominator_v4 and
denom_sample_threshold_v4.  At a fixed cell with a small VD denominator, compare
the bad-denominator event ``D_hat < D_M/2`` and the quotient tails on a grid that
straddles ``B_den``.

This Phase-A Level-1 output is exploratory until the PAP freeze artifacts fix the
registered grid, tolerances, and adjudication rule.
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
from scipy.stats import binom

from vd_sv.estimators import make_rng, mse

from ._common import frozen_models, stable_seed, write_csv

P_FIXED = 0.20
M_COPIES = 3
FIELDS = [
    "instance_id",
    "noise_strength",
    "copies_M",
    "method",
    "B",
    "B_over_Bden",
    "D_M",
    "B_den",
    "bernstein_bound",
    "bad_denominator_prob_exact",
    "bad_denominator_prob_empirical",
    "clip_activation_rate",
    "mse_clipped",
    "mse_ordinary_finite",
    "ordinary_nonfinite_rate",
    "p1_leading_mse",
    "relative_deviation_clipped",
    "relative_deviation_ordinary_finite",
    "excess_kurtosis_clipped",
    "excess_kurtosis_ordinary_finite",
]


def run(outdir: str | Path, mode: str = "fast", seed: int = 505) -> Path:
    t = 20000 if mode == "fast" else 100000
    factors = (
        np.array([0.125, 0.25, 0.5, 1.0, 2.0, 4.0, 8.0])
        if mode == "fast"
        else np.array([0.125, 0.177, 0.25, 0.354, 0.5, 0.707, 1.0, 1.414, 2.0, 4.0, 8.0])
    )
    rows = []
    for model in frozen_models():
        rng = make_rng(stable_seed(seed, model.inst.name, "e5"))
        vdc = model.vd(P_FIXED, M_COPIES)
        d_m = float(vdc["D_M"])
        n_m = float(vdc["N_M"])
        b_den = float(vdc["B_den"])

        for factor in factors:
            B = max(2, int(round(b_den * float(factor))))
            n_hat, d_hat = _sample_vd_stream_means(n_m, d_m, B, t, rng)
            clipped = n_hat / np.maximum(d_hat, 0.5 * d_m)
            with np.errstate(divide="ignore", invalid="ignore"):
                ordinary = n_hat / d_hat
            finite = np.isfinite(ordinary)
            ordinary_finite = ordinary[finite]

            bad_emp = float(np.mean(d_hat < 0.5 * d_m))
            clip_rate = bad_emp
            leading = float(vdc["b_VD"] ** 2 + vdc["v_tilde_VD"] / B)
            mse_clip = mse(clipped, model.mu_star)
            mse_ord = float(np.mean((ordinary_finite - model.mu_star) ** 2))

            rows.append({
                "instance_id": model.inst.name,
                "noise_strength": P_FIXED,
                "copies_M": M_COPIES,
                "method": "vd",
                "B": B,
                "B_over_Bden": float(B / b_den),
                "D_M": d_m,
                "B_den": b_den,
                "bernstein_bound": _bernstein_bound(d_m, B),
                "bad_denominator_prob_exact": _bad_denominator_prob_exact(d_m, B),
                "bad_denominator_prob_empirical": bad_emp,
                "clip_activation_rate": clip_rate,
                "mse_clipped": mse_clip,
                "mse_ordinary_finite": mse_ord,
                "ordinary_nonfinite_rate": float(1.0 - np.mean(finite)),
                "p1_leading_mse": leading,
                "relative_deviation_clipped": float((mse_clip - leading) / leading),
                "relative_deviation_ordinary_finite": float((mse_ord - leading) / leading),
                "excess_kurtosis_clipped": _excess_kurtosis(clipped),
                "excess_kurtosis_ordinary_finite": _excess_kurtosis(ordinary_finite),
            })
    return write_csv(Path(outdir) / "e5_denominator_concentration.csv", FIELDS, rows)


def _sample_vd_stream_means(
    N_M: float,
    D_M: float,
    B: int,
    T: int,
    rng,
) -> tuple[np.ndarray, np.ndarray]:
    q_n = 0.5 * (1.0 + N_M)
    q_d = 0.5 * (1.0 + D_M)
    k_n = rng.binomial(B, q_n, size=T)
    k_d = rng.binomial(B, q_d, size=T)
    return 2.0 * k_n / B - 1.0, 2.0 * k_d / B - 1.0


def _bad_denominator_prob_exact(D_M: float, B: int) -> float:
    q_d = 0.5 * (1.0 + D_M)
    cutoff = B * (1.0 + 0.5 * D_M) / 2.0
    k_max = math.ceil(cutoff) - 1
    if k_max < 0:
        return 0.0
    return float(binom.cdf(k_max, B, q_d))


def _bernstein_bound(D_M: float, B: int) -> float:
    sigma_d2 = 1.0 - D_M**2
    denom = 8.0 * sigma_d2 + (8.0 / 3.0) * D_M  # K_D=2 for Hadamard signs.
    return float(math.exp(-B * D_M**2 / denom))


def _excess_kurtosis(x: np.ndarray) -> float:
    arr = np.asarray(x, dtype=np.float64)
    if arr.size == 0:
        return float("nan")
    centered = arr - float(np.mean(arr))
    var = float(np.mean(centered**2))
    if var <= 0.0:
        return 0.0
    return float(np.mean(centered**4) / (var * var) - 3.0)


if __name__ == "__main__":
    print(run("results", mode="fast"))
