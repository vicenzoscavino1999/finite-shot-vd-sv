"""One-parameter noise channels for Level 1 (EXPERIMENTAL_PLAN sec. 5).

Each channel is a product over qubits of one or more elementary single-qubit
processes, applied at noise scale ``p`` with a *per-qubit* rate.  Every process is
exact CPTP for any ``p``, so the resulting ``rho_p`` is an *exact* density matrix
(not a Taylor truncation), yet ``rho_p = rho_star + p*Delta + O(p^2)`` with
``Delta = L(rho_star)`` the sum of per-qubit Lindblad dissipators.  ``Delta`` is
available in closed form and cross-checked by Richardson finite differences.

Why per-qubit (heterogeneous) rates.  With a Z-diagonal observable ``O`` and a fixed
Hamming-weight sector, *homogeneous* amplitude damping makes the within-sector
generator proportional to the (sector-constant) number operator ``sum_i n_i = k``,
which cancels in ``delta_SV = Tr(O P Delta P) - mu_star Tr(P Delta P)`` and also kills
``delta_VD``.  Heterogeneous rates (realistic: qubit-dependent T1/T2, EXP. PLAN
sec. 5.5.3) break this cancellation and give the generic ``delta_VD, delta_SV != 0``
case (paper Prop. generic_toy_v10) that E3/E4 need.

Channels
--------
- (b) amplitude damping + dephasing  -- primary.
- (a) depolarizing                    -- sensitivity.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np

from .density_matrix import I2, PAULI_X, PAULI_Y, PAULI_Z, SIGMA_MINUS, embed


def _dissipator(jump: np.ndarray, rho: np.ndarray) -> np.ndarray:
    """Lindblad dissipator ``L rho L^dag - 1/2 {L^dag L, rho}``."""
    ld = jump.conj().T
    lld = ld @ jump
    return jump @ rho @ ld - 0.5 * (lld @ rho + rho @ lld)


@dataclass(frozen=True)
class Process:
    """A single-qubit elementary process: exact Kraus map + Lindblad generator."""

    name: str
    kraus_fn: Callable[[float], list[np.ndarray]]  # arg = c_i * p (rate-scaled noise)
    jumps: tuple[tuple[np.ndarray, float], ...]  # (jump op, factor); Lindblad rate = c_i * factor


@dataclass(frozen=True)
class NoiseChannel:
    """Product over qubits of processes, each with a per-qubit rate vector."""

    n: int
    processes: tuple[tuple[Process, tuple[float, ...]], ...]
    name: str

    def apply(self, rho: np.ndarray, p: float) -> np.ndarray:
        """Exact ``rho_p = E_p(rho)``."""
        out = np.asarray(rho, dtype=np.complex128)
        for proc, rates in self.processes:
            for i in range(self.n):
                kr = [embed(k, i, self.n) for k in proc.kraus_fn(rates[i] * float(p))]
                out = sum(k @ out @ k.conj().T for k in kr)
        return out

    def delta(self, rho_star: np.ndarray) -> np.ndarray:
        """Closed-form ``Delta = L(rho_star)`` (sum of per-qubit dissipators)."""
        out = np.zeros_like(rho_star, dtype=np.complex128)
        for proc, rates in self.processes:
            for jump_single, factor in proc.jumps:
                for i in range(self.n):
                    if rates[i] == 0.0:
                        continue
                    out = out + rates[i] * factor * _dissipator(embed(jump_single, i, self.n), rho_star)
        return out

    def delta_fd(self, rho_star: np.ndarray, h: float = 1e-4) -> np.ndarray:
        """Richardson finite-difference estimate of ``Delta`` (O(h^2) accurate)."""
        f1 = self.apply(rho_star, h)
        f2 = self.apply(rho_star, 2.0 * h)
        d1 = (f1 - rho_star) / h
        d2 = (f2 - rho_star) / (2.0 * h)
        return 2.0 * d1 - d2


# --- elementary processes ---------------------------------------------------

_AMPLITUDE_DAMPING = Process(
    name="AD",
    kraus_fn=lambda g: [
        np.array([[1.0, 0.0], [0.0, np.sqrt(max(0.0, 1.0 - _check01(g, "amplitude damping"))) ]],
                 dtype=np.complex128),
        np.array([[0.0, np.sqrt(g)], [0.0, 0.0]], dtype=np.complex128),
    ],
    jumps=((SIGMA_MINUS, 1.0),),
)

_DEPHASING = Process(
    name="PD",
    kraus_fn=lambda g: [
        np.sqrt(0.5 * (1.0 + np.exp(-2.0 * g))) * I2,
        np.sqrt(1.0 - 0.5 * (1.0 + np.exp(-2.0 * g))) * PAULI_Z,
    ],
    jumps=((PAULI_Z, 1.0),),
)

_DEPOLARIZING = Process(
    name="Depol",
    kraus_fn=lambda q: [
        np.sqrt(1.0 - 0.75 * _check_depol(q)) * I2,
        np.sqrt(q / 4.0) * PAULI_X,
        np.sqrt(q / 4.0) * PAULI_Y,
        np.sqrt(q / 4.0) * PAULI_Z,
    ],
    jumps=((PAULI_X, 0.25), (PAULI_Y, 0.25), (PAULI_Z, 0.25)),
)


def _check01(g: float, what: str) -> float:
    if g < 0 or g > 1:
        raise ValueError(f"{what} rate {g} outside [0,1]; reduce p_max")
    return g


def _check_depol(q: float) -> float:
    if q < 0 or q > 4.0 / 3.0:
        raise ValueError(f"depolarizing strength {q} outside [0,4/3]; reduce p_max")
    return q


def _rates(c, n: int) -> tuple[float, ...]:
    arr = np.broadcast_to(np.asarray(c, dtype=np.float64), (n,))
    return tuple(float(x) for x in arr)


# --- public channel constructors -------------------------------------------


def amplitude_damping_dephasing(n: int, c_ad, c_pd) -> NoiseChannel:
    """Primary channel (b): amplitude damping + dephasing per qubit.

    ``c_ad``, ``c_pd`` are scalars (homogeneous) or length-``n`` arrays
    (heterogeneous; needed for delta_VD, delta_SV != 0).
    """
    return NoiseChannel(
        n=n,
        processes=((_AMPLITUDE_DAMPING, _rates(c_ad, n)), (_DEPHASING, _rates(c_pd, n))),
        name=f"AD+PD(c_ad={np.round(_rates(c_ad,n),4)},c_pd={np.round(_rates(c_pd,n),4)})",
    )


def depolarizing(n: int, c_dep) -> NoiseChannel:
    """Sensitivity channel (a): depolarizing per qubit."""
    return NoiseChannel(n=n, processes=((_DEPOLARIZING, _rates(c_dep, n)),),
                        name=f"Depol(c={np.round(_rates(c_dep,n),4)})")


def heterogeneous_ad_pd(n: int, seed: int = 0, c_ad_range: tuple[float, float] = (0.4, 1.3),
                        c_pd_ratio: float = 0.4) -> NoiseChannel:
    """Deterministic heterogeneous AD+PD channel (provisional; frozen by the pilot).

    Per-qubit ``c_ad`` is drawn once from a seeded RNG; ``c_pd = c_pd_ratio * c_ad``
    fixes the relaxation/dephasing ratio (T1/T2-like, EXP. PLAN sec. 5.5.3).  The
    heterogeneity is what makes ``delta_VD, delta_SV != 0`` (see noise module
    docstring).  Magnitudes here are a placeholder to be anchored to a backend
    snapshot at PAP freeze time.
    """
    rng = np.random.Generator(np.random.PCG64(seed))
    c_ad = rng.uniform(c_ad_range[0], c_ad_range[1], size=n)
    c_pd = c_pd_ratio * c_ad
    return amplitude_damping_dephasing(n, c_ad, c_pd)


def assert_delta_consistency(channel: NoiseChannel, rho_star: np.ndarray,
                             h: float = 1e-4, atol: float = 1e-6) -> float:
    """Check closed-form ``Delta`` against finite differences and Lindblad sanity.

    Returns the max-abs discrepancy; raises ``AssertionError`` on failure.
    """
    d_closed = channel.delta(rho_star)
    d_fd = channel.delta_fd(rho_star, h=h)
    discrepancy = float(np.max(np.abs(d_closed - d_fd)))
    assert discrepancy <= atol, f"Delta closed-form vs finite-diff mismatch: {discrepancy:.2e}"
    assert abs(np.trace(d_closed)) <= 1e-10, "Tr(Delta) != 0"
    assert np.allclose(d_closed, d_closed.conj().T, atol=1e-12), "Delta not Hermitian"
    return discrepancy
