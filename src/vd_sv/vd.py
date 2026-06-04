"""Virtual distillation: finite-shot controlled-derangement / Hadamard-test sampling.

Idealized independent Hadamard-test implementation (paper sec. "Concrete independent
derangement/Hadamard-test implementation").  The numerator and denominator are each
estimated by an independent Hadamard test returning a sign in ``{+-1}``:

    X_M in {+-1},  E[X_M] = N_M = Tr(O rho_p^M),
    Y_M in {+-1},  E[Y_M] = D_M = Tr(rho_p^M),   independent streams.

So ``sigma_N^2 = 1 - N_M^2``, ``sigma_D^2 = 1 - D_M^2``, ``sigma_ND = 0``
(eq. hadamard_variances_v4).  The clipped quotient estimator is
``N_hat / max(D_hat, D_M/2)`` (eq. clipped_quotient_v4).
"""

from __future__ import annotations

import numpy as np


def sample_vd_quotient(N_M: float, D_M: float, B: int, T: int, rng,
                       clip: bool = True) -> np.ndarray:
    """``T`` replicas of the VD Hadamard-test quotient estimator at budget ``B``.

    ``B`` numerator shots and ``B`` denominator shots per replica (two independent
    streams; physical resource is ``2 * kappa_M * B``, eq. resource_normalization_v13).
    """
    if not -1.0 <= N_M <= 1.0:
        raise ValueError(f"N_M={N_M} outside [-1,1]")
    if not 0.0 < D_M <= 1.0:
        raise ValueError(f"D_M={D_M} outside (0,1]")
    q_n = 0.5 * (1.0 + N_M)
    q_d = 0.5 * (1.0 + D_M)
    k_n = rng.binomial(B, q_n, size=T)
    k_d = rng.binomial(B, q_d, size=T)
    n_hat = 2.0 * k_n / B - 1.0
    d_hat = 2.0 * k_d / B - 1.0
    if clip:
        return n_hat / np.maximum(d_hat, 0.5 * D_M)
    with np.errstate(divide="ignore", invalid="ignore"):
        return n_hat / d_hat
