"""XY-mixer QAOA on a fixed Hamming-weight sector (instance family, EXP. PLAN sec. 4.1).

Why this family.  The verifiable symmetry is ``S = sum_i Z_i`` (total magnetization
== Hamming weight).  The XY mixer ``H_M = sum_{(i,j)} (X_i X_j + Y_i Y_j)`` *preserves*
the Hamming-weight sector, the cost ``H_C = sum_{(i,j)} w_ij Z_i Z_j`` is Z-diagonal
and commutes with ``S``, and the observable ``O = H_C / ||H_C||_inf`` is therefore
symmetry-compatible (``P O = O P``).  This is exactly the SV hypothesis in the paper
(``P rho_star P = rho_star`` with a symmetry-compatible observable), and it avoids the
MaxCut / ``X^{(x)n}`` setup where the hypothesis fails.

All operators are built as dense matrices for ``n <= 8``.  ``H_C`` is diagonal, so its
matrix exponential is exact; ``H_M`` is diagonalized once and reused across angles.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from itertools import combinations
from math import comb

import numpy as np

from .density_matrix import (
    PAULI_X,
    PAULI_Y,
    embed_two,
    pure_state_rho,
    sector_projector,
)


@dataclass(frozen=True)
class QAOAInstance:
    """A frozen QAOA instance on a fixed Hamming-weight sector."""

    n: int
    weight: int
    edges: tuple[tuple[int, int], ...]
    weights: tuple[float, ...]
    mixer_edges: tuple[tuple[int, int], ...] = field(default=())
    name: str = "instance"

    def __post_init__(self) -> None:
        if not 1 <= self.weight < self.n:
            raise ValueError("weight must satisfy 1 <= weight < n")
        if len(self.edges) != len(self.weights):
            raise ValueError("edges and weights length mismatch")
        if not self.mixer_edges:
            object.__setattr__(self, "mixer_edges", tuple(self.edges))


def ring_instance(n: int, weights: np.ndarray | None = None,
                  weight: int | None = None, name: str = "ring") -> QAOAInstance:
    """Weighted ring on ``n`` nodes.

    ``weights=None`` gives the unit-weight ring; a weight vector breaks the ring
    symmetry.  ``weight`` is the fixed Hamming-weight sector; it defaults to
    ``n//2 - 1`` (NOT half-filling).  At half-filling ``k = n/2`` the QAOA state
    is invariant under the bit-complement (particle-hole) symmetry ``s_i -> -s_i``,
    which forces all odd correlators -- and hence ``delta_VD`` and ``delta_SV`` --
    to vanish identically.  A non-half-filled sector exhibits the generic
    first-order-bias case (paper Prop. generic_toy_v10) that E3/E4 validate.
    """
    edges = tuple((i, (i + 1) % n) for i in range(n))
    if weights is None:
        w = tuple(1.0 for _ in edges)
    else:
        w = tuple(float(x) for x in np.asarray(weights).reshape(-1)[: len(edges)])
    k = weight if weight is not None else max(1, n // 2 - 1)
    return QAOAInstance(n=n, weight=k, edges=edges, weights=w, name=name)


# --- Hamiltonians and observable -------------------------------------------


def _bits(n: int) -> np.ndarray:
    """Bit matrix of shape (2**n, n); column i is the value of qubit i."""
    z = np.arange(2**n, dtype=np.int64)
    return np.array([[(zz >> (n - 1 - i)) & 1 for i in range(n)] for zz in z], dtype=np.int64)


def cost_diagonal(inst: QAOAInstance) -> np.ndarray:
    """Diagonal of ``H_C = sum w_ij Z_i Z_j`` (real vector of length 2**n)."""
    bits = _bits(inst.n)
    s = 1 - 2 * bits  # Z eigenvalue: +1 for |0>, -1 for |1>
    diag = np.zeros(2**inst.n, dtype=np.float64)
    for (i, j), w in zip(inst.edges, inst.weights):
        diag += w * s[:, i] * s[:, j]
    return diag


def cost_hamiltonian(inst: QAOAInstance) -> np.ndarray:
    return np.diag(cost_diagonal(inst).astype(np.complex128))


def observable(inst: QAOAInstance) -> np.ndarray:
    """``O = H_C / ||H_C||_inf`` -- diagonal, ``||O||_inf = 1`` (EXP. PLAN sec. 4.1)."""
    diag = cost_diagonal(inst)
    scale = float(np.max(np.abs(diag)))
    if scale == 0.0:
        raise ValueError("degenerate cost Hamiltonian (all-zero diagonal)")
    return np.diag((diag / scale).astype(np.complex128))


def symmetry_projector(inst: QAOAInstance) -> np.ndarray:
    return sector_projector(inst.n, inst.weight)


def mixer_hamiltonian(inst: QAOAInstance) -> np.ndarray:
    """XY mixer ``H_M = sum_{(i,j)} (X_i X_j + Y_i Y_j)`` (preserves Hamming weight)."""
    n = inst.n
    h = np.zeros((2**n, 2**n), dtype=np.complex128)
    for i, j in inst.mixer_edges:
        h += embed_two(PAULI_X, i, PAULI_X, j, n) + embed_two(PAULI_Y, i, PAULI_Y, j, n)
    return h


# --- states -----------------------------------------------------------------


def dicke_state(n: int, k: int) -> np.ndarray:
    """Dicke state ``|D^n_k>``: equal superposition of all weight-``k`` strings."""
    psi = np.zeros(2**n, dtype=np.complex128)
    amp = 1.0 / np.sqrt(comb(n, k))
    for ones in combinations(range(n), k):
        z = 0
        for i in ones:
            z |= 1 << (n - 1 - i)
        psi[z] = amp
    return psi


def _layer_operators(inst: QAOAInstance):
    """Precompute the data needed to apply QAOA layers fast."""
    cost_diag = cost_diagonal(inst)  # H_C diagonal
    h_m = mixer_hamiltonian(inst)
    evals_m, evecs_m = np.linalg.eigh(h_m)
    return cost_diag, evals_m, evecs_m


def qaoa_state(inst: QAOAInstance, gammas, betas, _cache=None) -> np.ndarray:
    """``|psi(gamma,beta)> = prod_l e^{-i beta_l H_M} e^{-i gamma_l H_C} |D^n_k>``."""
    gammas = np.atleast_1d(np.asarray(gammas, dtype=np.float64))
    betas = np.atleast_1d(np.asarray(betas, dtype=np.float64))
    if gammas.shape != betas.shape:
        raise ValueError("gammas and betas must have the same length L")
    if _cache is None:
        _cache = _layer_operators(inst)
    cost_diag, evals_m, evecs_m = _cache

    psi = dicke_state(inst.n, inst.weight)
    for g, b in zip(gammas, betas):
        psi = np.exp(-1j * g * cost_diag) * psi  # e^{-i g H_C}, H_C diagonal
        # e^{-i b H_M} via the precomputed mixer eigendecomposition
        psi = evecs_m @ (np.exp(-1j * b * evals_m) * (evecs_m.conj().T @ psi))
    return psi


def ideal_state(inst: QAOAInstance, gammas, betas) -> np.ndarray:
    """Ideal density matrix ``rho_star = |psi><psi|`` for frozen angles."""
    return pure_state_rho(qaoa_state(inst, gammas, betas))


# --- angle optimization (frozen pre-data; EXP. PLAN sec. 5.5.1) -------------


def optimize_angles(inst: QAOAInstance, depth: int = 1, seed: int = 0, restarts: int = 8):
    """Minimize the noiseless cost ``<psi|H_C|psi>`` over ``(gamma, beta)``.

    Deterministic given ``(seed, restarts)``: this is the frozen angle rule of
    EXPERIMENTAL_PLAN sec. 5.5.1 (fixed optimizer + fixed seed, on the noiseless cost).
    Returns ``(gammas, betas, cost)``.
    """
    from scipy.optimize import minimize

    cache = _layer_operators(inst)
    cost_diag = cache[0]
    rng = np.random.Generator(np.random.PCG64(seed))

    def objective(x: np.ndarray) -> float:
        g, b = x[:depth], x[depth:]
        psi = qaoa_state(inst, g, b, _cache=cache)
        return float(np.real(np.sum(cost_diag * (np.abs(psi) ** 2))))

    best_x, best_f = None, np.inf
    for _ in range(restarts):
        x0 = rng.uniform(0.0, np.pi, size=2 * depth)
        res = minimize(objective, x0, method="L-BFGS-B",
                       bounds=[(0.0, 2 * np.pi)] * (2 * depth))
        if res.fun < best_f:
            best_f, best_x = float(res.fun), res.x
    return best_x[:depth].copy(), best_x[depth:].copy(), best_f


# --- diagnostics ------------------------------------------------------------


def entanglement_entropy(psi: np.ndarray, n: int, cut: int | None = None) -> float:
    """Von Neumann entropy (base 2) of the reduced state on the first ``cut`` qubits."""
    if cut is None:
        cut = n // 2
    mat = np.asarray(psi, dtype=np.complex128).reshape(2**cut, 2 ** (n - cut))
    s = np.linalg.svd(mat, compute_uv=False)
    p = (s**2)
    p = p[p > 1e-15]
    return float(-np.sum(p * np.log2(p)))
