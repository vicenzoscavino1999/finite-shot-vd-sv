"""Certified operating-window crossings (paper sec. "Certified operating-window
crossings"; Thm certified_crossing, Thm selection_trichotomy_v10).

A method has a resource law ``MSE_m(R) = b_m^2 + s_m/R + rho_m(R)``, ``|rho_m| <= C_m/R^2``.
For two methods the leading indifference budget is ``R0 = Delta_s / g`` with
``g = b_j^2 - b_i^2`` and ``Delta_s = s_i - s_j``.  A crossing is *certified* only when
``eta = 4C/(g R0^2) < 1/2`` (and ``R0(1-eta) >= R_min``); then a true crossing lies in
``[R0(1-eta), R0(1+eta)]``.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class MethodLaw:
    """Leading resource law of one method."""

    name: str
    b2: float  # squared population bias b_m^2
    s: float   # resource-normalized sampling coefficient s_m = kappa_m * v_tilde_m
    C: float   # remainder constant (|rho_m(R)| <= C/R^2)


@dataclass(frozen=True)
class CrossingCertificate:
    regime: str  # 'degenerate_tie' | 'uniform_dominance' | 'certified_crossing'
    winner_large_R: str | None
    g: float
    delta_s: float
    R0: float | None
    eta: float | None
    interval: tuple[float, float] | None
    valid: bool


def certified_crossing(method_a: MethodLaw, method_b: MethodLaw,
                       r_min: float = 0.0) -> CrossingCertificate:
    """Classify the (a, b) comparison and, for a genuine tradeoff, certify the band.

    Returns a :class:`CrossingCertificate`.  Labels the lower-bias method as ``i``;
    it wins at large ``R`` (the bias floor dominates there).
    """
    # order so that i = lower bias (smaller b^2)
    if method_a.b2 <= method_b.b2:
        i, j = method_a, method_b
    else:
        i, j = method_b, method_a
    g = j.b2 - i.b2          # >= 0
    delta_s = i.s - j.s      # lower-bias method's sampling minus the other's
    C = i.C + j.C

    if g <= 0 and delta_s == 0:
        return CrossingCertificate("degenerate_tie", None, g, delta_s, None, None, None, False)

    # genuine tradeoff requires the lower-bias method to also cost more (delta_s > 0)
    if not (g > 0 and delta_s > 0):
        # uniform dominance: the method that is both lower-bias and not-costlier wins
        winner = i.name if delta_s <= 0 else j.name
        return CrossingCertificate("uniform_dominance", winner, g, delta_s, None, None, None, True)

    r0 = delta_s / g
    eta = 4.0 * C / (g * r0**2)
    interval = (r0 * (1.0 - eta), r0 * (1.0 + eta))
    valid = bool(eta < 0.5 and interval[0] >= r_min)
    return CrossingCertificate("certified_crossing", i.name, g, delta_s, r0, eta, interval, valid)


def empirical_crossing(resource: np.ndarray, mse_a: np.ndarray, mse_b: np.ndarray) -> float | None:
    """First resource ``R*`` where ``mse_a - mse_b`` changes sign (linear interpolation).

    Returns ``None`` if no sign change is present on the grid.
    """
    r = np.asarray(resource, dtype=np.float64)
    d = np.asarray(mse_a, dtype=np.float64) - np.asarray(mse_b, dtype=np.float64)
    order = np.argsort(r)
    r, d = r[order], d[order]
    sign = np.sign(d)
    for k in range(len(r) - 1):
        if sign[k] == 0:
            return float(r[k])
        if sign[k] * sign[k + 1] < 0:
            # linear interpolation of the root of d(R)
            r0, r1, d0, d1 = r[k], r[k + 1], d[k], d[k + 1]
            return float(r0 - d0 * (r1 - r0) / (d1 - d0))
    if sign[-1] == 0:
        return float(r[-1])
    return None


def fit_remainder_constant(resource: np.ndarray, mse: np.ndarray, b2: float, s: float) -> float:
    """Operational remainder constant from ``MSE(R) - (b^2 + s/R) ~ C/R^2``.

    Least-squares fit of the residual against ``1/R^2``; returns ``|C|`` as an
    operational (Efron-Stein-scale) estimate, not the conservative proof certificate.
    """
    r = np.asarray(resource, dtype=np.float64)
    resid = np.asarray(mse, dtype=np.float64) - (b2 + s / r)
    x = 1.0 / r**2
    c = float(np.dot(x, resid) / np.dot(x, x))
    return abs(c)
