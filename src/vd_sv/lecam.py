"""Restricted two-point (Le Cam) lower bound (paper sec. "Restricted lower-bound
sanity check"; Thm two_point_lower_bound, Prop. explicit_ip_bernoulli_v5).

For a fixed admissible protocol at budget ``R`` the two-point risk obeys
``sup_theta E[(mu_hat - mu_theta)^2] >= 1 / (8 R I_p)``.  For the one-qubit Bernoulli
transcript ``rho_{p,t} = (I + (1-p) t X)/2`` the per-resource information constant is

    I_p^Bern      = 4 (1-p)^2     (conservative, finite-interval),
    I_p,loc^Bern  = 2 (1-p)^2     (sharper local / Fisher),

giving the concrete bounds ``1/(32 R (1-p)^2)`` and ``1/(16 R (1-p)^2)``.

E11/P12 use these as an *arithmetic consistency check* of the bound on the toy where
it is derived, not as an independent empirical test (EXP. PLAN sec. 8 E11).
"""

from __future__ import annotations


def ip_bernoulli(p: float, local: bool = False) -> float:
    """Per-resource information constant of the one-qubit Bernoulli transcript."""
    base = 2.0 if local else 4.0
    return base * (1.0 - p) ** 2


def two_point_lower_bound(R: float, ip: float) -> float:
    """General two-point sampling lower bound ``1 / (8 R I_p)`` (eq. one_over_r_lower_bound)."""
    return 1.0 / (8.0 * R * ip)


def bernoulli_lower_bound(R: float, p: float, local: bool = False) -> float:
    """Concrete bound: ``1/(32 R (1-p)^2)`` (conservative) or ``1/(16 R (1-p)^2)`` (local)."""
    return two_point_lower_bound(R, ip_bernoulli(p, local=local))
