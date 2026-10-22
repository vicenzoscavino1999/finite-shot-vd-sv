"""Sector toy (u = l = 1, p = 0.01, M = 2): direct remainder bounds, the certified
VD--SV crossing interval, and the exact finite-budget MSE of both clipped estimators.

Paper: App. C, Lemma "Direct remainders in the sector toy" and Proposition
"Certified VD--SV crossing in the sector toy".

Resource convention: an even physical budget R gives VD B = R/2 numerator and B
denominator +-1 Hadamard signs (independent streams) and SV R shots.  The exact
MSEs are finite binomial sums; no Monte Carlo is used.

The certificate uses the sharp interval [R_L, R_U] of the comparison rule (paper
Prop. 8(b)).  ``vd_sv.crossing.certified_crossing`` implements the looser band
[R0(1-eta), R0(1+eta)] used by the pre-specified Level 1 analysis; for eta < 1/2
the band contains [R_L, R_U].

Every check raises ``CertificationError`` (not ``assert``), so it also runs under
``python -O``.

Run:  python scripts/sector_toy_certified_crossing.py
"""

from __future__ import annotations

import math

import numpy as np
from scipy.stats import binom

U = L = 1.0
P = 0.01
R_MIN = 200
R_MAX_CHECK = 4000
C_VD, C_SV = 2.6, 1e-3  # constants stated in the paper

ALPHA, BETA, LAM = 1 - (U + L) * P, U * P, L * P
N = ALPHA**2 - BETA**2
D = ALPHA**2 + BETA**2 + LAM**2
MU = N / D
A = ALPHA + BETA
Q = BETA / A
MU_SV = 1 - 2 * Q
SIG_N2 = 1 - N**2
M2 = 1 - D**2
M3 = -2 * D * (1 - D**2)
M4 = (1 - D**2) * (1 + 3 * D**2)
SIG_ACC2 = 1 - MU_SV**2

B_VD = MU - 1
C_COEF = MU * M2 / D**2
V_VD = (SIG_N2 + MU**2 * M2) / D**2
S_VD = 2 * (V_VD + 2 * B_VD * C_COEF)
B_SV = MU_SV - 1
S_SV = SIG_ACC2 / A
G = B_SV**2 - B_VD**2
R0 = (S_VD - S_SV) / G

NUMERIC_TOL = 1e-6  # tolerance on R^2 * rho when comparing exact sums with the bounds


class CertificationError(RuntimeError):
    """A rigorous bound, a validity condition, or the exact cross-check failed."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise CertificationError(message)


def vd_remainder_bounds(b_min: int = R_MIN // 2) -> tuple[float, float]:
    """Interval for B^2 * rho_VD (remainder in the B variable), valid for all B >= b_min."""
    k2 = 3 * SIG_N2 * M2 / D**4 + MU * M3 * (2 - 4 * MU) / D**3
    k3 = -4 * SIG_N2 * M3 / D**5
    _require(M4 - 3 * M2**2 >= 0, "E t^4 bound assumes m4 >= 3 m2^2")
    e4 = 3 * M2**2 + (M4 - 3 * M2**2) / b_min  # B^2 D^4 E[t^4] for B >= b_min
    up = (N**2 + SIG_N2 / b_min) * 12 * e4 / D**6
    lo = 2 * N * 2 * e4 / D**5
    tmax = (1 + D) / D  # |t| on the bad event
    bad1 = 2 / D + (1 + tmax + tmax**2 + tmax**3) / D
    bad2 = 4 / D**2 + (1 + 2 * tmax + 3 * tmax**2 + 4 * tmax**3) / D**2
    eps = D / 2
    rate = eps**2 / (2 * M2 + (2 / 3) * (1 + D) * eps)  # one-sided Bernstein, |zeta| <= 1 + D
    _require(b_min >= 2 / rate, "B^2 exp(-rate B) must be decreasing from b_min on")
    bad = ((N**2 + SIG_N2 / b_min) * bad2 + 2 * N * bad1) * b_min**2 * math.exp(-rate * b_min)
    return k2 - abs(k3) / b_min - lo - bad, k2 + abs(k3) / b_min + up + bad


def sv_remainder_bound(r_min: int = R_MIN) -> float:
    """Bound on R^2 |rho_SV| valid for all R >= r_min."""
    # bad event: more than R (1 - a/2) of the R shots rejected; Chernoff on the binomial
    k, q = 1 - A / 2, 1 - A
    _require(k > q, "Chernoff bound needs 1 - a/2 > 1 - a")
    kl = k * math.log(k / q) + (1 - k) * math.log((1 - k) / (1 - q))
    _require(r_min >= 2 / kl, "R^2 exp(-kl R) must be decreasing from r_min on")
    bad = (1.1 + 1 / A + 1 / A**2) * r_min**2 * math.exp(-kl * r_min)
    return 2 * SIG_ACC2 * (1 - A) / A**2 + bad


def mse_vd(r: int) -> float:
    """Exact MSE of the clipped VD estimator at even physical budget r."""
    b = r // 2
    j = np.arange(b + 1)
    pj = binom.pmf(j, b, (1 + D) / 2)
    d = np.maximum((2 * j - b) / b, D / 2)
    return float(np.sum(pj * ((N**2 + SIG_N2 / b) / d**2 - 2 * N / d + 1)))


def mse_sv(r: int) -> float:
    """Exact MSE of the clipped SV estimator at physical budget r."""
    m = np.arange(r + 1)
    pm = binom.pmf(m, r, A)
    x = m / r
    d = np.maximum(x, A / 2)
    return float(np.sum(pm * ((x**2 * MU_SV**2 + x * SIG_ACC2 / r) / d**2 - 2 * x * MU_SV / d + 1)))


def certify() -> dict[str, float]:
    """Rigorous bounds and the certified interval of the comparison rule."""
    lo, hi = vd_remainder_bounds()
    sv = sv_remainder_bound()
    _require(4 * max(abs(lo), abs(hi)) <= C_VD, f"VD bound 4*max(|{lo}|,|{hi}|) exceeds C_VD={C_VD}")
    _require(sv <= C_SV, f"SV bound {sv} exceeds C_SV={C_SV}")
    c = C_VD + C_SV
    eta = 4 * c / (G * R0**2)
    _require(eta < 1, f"eta={eta} >= 1: no certified crossing")
    r_l = (1 + math.sqrt(1 - eta)) / 2 * R0
    r_u = (1 + math.sqrt(1 + eta)) / 2 * R0
    r_lo = eta / (2 * (1 + math.sqrt(1 - eta))) * R0
    _require(r_lo < R_MIN, f"R_lo={r_lo} >= R_MIN: SV-better region not certified from R_MIN")
    _require(r_l >= R_MIN, f"R_L={r_l} < R_MIN")
    return {"vd_lo": 4 * lo, "vd_hi": 4 * hi, "sv": sv, "C": c, "eta": eta,
            "R0": R0, "R_L": r_l, "R_U": r_u, "R_lo": r_lo}


def check_exact(cert: dict[str, float], r_max: int = R_MAX_CHECK) -> dict[str, object]:
    """Exact sums on even R in [R_MIN, r_max]: remainders inside the bounds, ordering as certified."""
    lo_ex, hi_ex, sv_ex = math.inf, -math.inf, 0.0
    switches = []
    prev = None
    for r in range(R_MIN, r_max + 1, 2):
        mv, ms = mse_vd(r), mse_sv(r)
        rv = (mv - B_VD**2 - S_VD / r) * r**2
        rs = (ms - B_SV**2 - S_SV / r) * r**2
        _require(cert["vd_lo"] - NUMERIC_TOL <= rv <= cert["vd_hi"] + NUMERIC_TOL,
                 f"exact R^2 rho_VD={rv} outside the rigorous bounds at R={r}")
        _require(abs(rs) <= cert["sv"] + NUMERIC_TOL, f"exact R^2 |rho_SV|={abs(rs)} above the bound at R={r}")
        vd_better = mv < ms
        _require(not (r < cert["R_L"] and vd_better), f"VD better at R={r} < R_L")
        _require(not (r > cert["R_U"] and not vd_better), f"SV better at R={r} > R_U")
        if prev is not None and vd_better != prev:
            switches.append((r - 2, r))
        prev = vd_better
        lo_ex, hi_ex, sv_ex = min(lo_ex, rv), max(hi_ex, rv), max(sv_ex, abs(rs))
    _require(len(switches) == 1, f"expected one SV -> VD switch on the grid, found {switches}")
    return {"switch": switches[0], "vd_exact": (lo_ex, hi_ex), "sv_exact": sv_ex}


def main() -> int:
    try:
        cert = certify()
        info = check_exact(cert)
    except CertificationError as exc:
        print(f"SECTOR_TOY_CERTIFICATE_FAIL: {exc}")
        return 1
    print(f"N2={N:.4f} D2={D:.4f} a={A}  b_VD^2={B_VD**2:.3e} b_SV^2={B_SV**2:.4e}")
    print(f"s_VD={S_VD:.4f} s_SV={S_SV:.4f} R0={R0:.1f}")
    print(f"rigorous: R^2 rho_VD in [{cert['vd_lo']:.3f}, {cert['vd_hi']:.3f}], R^2 |rho_SV| <= {cert['sv']:.2e}")
    print(f"C={cert['C']} eta={cert['eta']:.4f} [R_L, R_U]=[{cert['R_L']:.1f}, {cert['R_U']:.1f}]")
    lo_ex, hi_ex = info["vd_exact"]
    print(f"exact (even R <= {R_MAX_CHECK}): R^2 rho_VD in [{lo_ex:.3f}, {hi_ex:.3f}], "
          f"max R^2|rho_SV|={info['sv_exact']:.2e}")
    s0, s1 = info["switch"]
    print(f"exact switch SV -> VD between R={s0} and R={s1}")
    print("SECTOR_TOY_CERTIFICATE_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
