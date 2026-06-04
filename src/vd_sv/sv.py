"""Symmetry verification: finite-shot Hamming-weight postselection sampling.

At Level 1 (ideal measurement) SV is exact: measure all qubits in the Z basis,
postselect on the correct Hamming weight, evaluate the Z-diagonal observable on
accepted bitstrings (paper sec. "Symmetry verification").  Each shot yields an
acceptance indicator ``A in {0,1}`` and, when accepted, the value ``W = O(z)``;
``Z = A W``.  The clipped estimator is ``Z_bar / max(A_bar, a/2)`` with
``a = Tr(P rho_p)`` (eq. sv_acceptance_bernstein_v5).

Readout error (Levels 2-3) would move bitstrings between Hamming sectors and
contaminate the accepted set; the mitigation-before-postselection protocol
(EXP. PLAN sec. 4.3) is a Level-2 concern and not part of this Level-1 sampler.
"""

from __future__ import annotations

import numpy as np

from .coefficients import WhiteBoxModel
from .estimators import _normalize


def sv_measurement_data(model: WhiteBoxModel, p: float):
    """Per-bitstring ``(pz, accept, value, a)`` for the SV sampler at noise ``p``.

    - ``pz``      : Z-measurement distribution diag(rho_p)
    - ``accept``  : 1.0 if the bitstring has the correct Hamming weight, else 0.0
    - ``value``   : O(z) = diagonal of the (Z-diagonal) observable
    - ``a``       : acceptance probability Tr(P rho_p)
    """
    rho_p = model.rho_p(p)
    pz = _normalize(np.real(np.diag(rho_p)))
    accept = (np.real(np.diag(model.projector)) > 0.5).astype(np.float64)
    value = np.real(np.diag(model.observable))
    a = float(pz @ accept)
    return pz, accept, value, a


def sample_sv_quotient(pz: np.ndarray, accept: np.ndarray, value: np.ndarray, a: float,
                       B: int, T: int, rng, clip: bool = True) -> np.ndarray:
    """``T`` replicas of the SV postselection quotient estimator at ``B`` total shots.

    All ``B`` shots are counted as resource (accepted *and* rejected), matching the
    SV resource normalization in EXPERIMENTAL_PLAN sec. 6.2.
    """
    counts = rng.multinomial(B, _normalize(pz), size=T)  # (T, d)
    zw = accept * value
    a_bar = counts @ accept / B
    z_bar = counts @ zw / B
    if clip:
        return z_bar / np.maximum(a_bar, 0.5 * a)
    with np.errstate(divide="ignore", invalid="ignore"):
        return z_bar / a_bar
