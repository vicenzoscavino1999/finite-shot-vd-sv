"""Exact density-matrix engine for the Level 1 white-box simulations.

Conventions
-----------
- ``n`` qubits, Hilbert space dimension ``d = 2**n``.
- Big-endian / Qiskit-incompatible qubit ordering: qubit 0 is the *leftmost*
  tensor factor.  For a computational-basis index ``z`` in ``range(2**n)`` the
  value of qubit ``i`` is ``(z >> (n - 1 - i)) & 1``.  The Hamming weight of
  ``z`` (its number of ``1`` bits) is the number of qubits in state ``|1>``.
  This convention is documented in METHODS.md; the Qiskit cross-check mapping
  for Level 2 is the bit-reversal of this ordering.

All matrices are dense complex128 ``numpy`` arrays.  For ``n <= 8`` (``d <= 256``)
this is cheap: a density matrix is at most ``256 x 256``.
"""

from __future__ import annotations

import numpy as np

# --- single-qubit operators -------------------------------------------------

I2 = np.eye(2, dtype=np.complex128)
PAULI_X = np.array([[0, 1], [1, 0]], dtype=np.complex128)
PAULI_Y = np.array([[0, -1j], [1j, 0]], dtype=np.complex128)
PAULI_Z = np.array([[1, 0], [0, -1]], dtype=np.complex128)
PROJ0 = np.array([[1, 0], [0, 0]], dtype=np.complex128)  # |0><0|
PROJ1 = np.array([[0, 0], [0, 1]], dtype=np.complex128)  # |1><1|
SIGMA_MINUS = np.array([[0, 1], [0, 0]], dtype=np.complex128)  # |0><1| (lowering)


def embed(op: np.ndarray, qubit: int, n: int) -> np.ndarray:
    """Embed a single-qubit operator on ``qubit`` into the ``n``-qubit space."""
    if not 0 <= qubit < n:
        raise ValueError(f"qubit {qubit} out of range for n={n}")
    left = np.eye(2**qubit, dtype=np.complex128)
    right = np.eye(2 ** (n - 1 - qubit), dtype=np.complex128)
    return np.kron(np.kron(left, op), right)


def embed_two(op_a: np.ndarray, qa: int, op_b: np.ndarray, qb: int, n: int) -> np.ndarray:
    """Embed the product of single-qubit operators on two distinct qubits."""
    if qa == qb:
        raise ValueError("qa and qb must differ")
    return embed(op_a, qa, n) @ embed(op_b, qb, n)


def hamming_weights(n: int) -> np.ndarray:
    """Hamming weight (number of |1> qubits) of each basis index 0..2**n-1."""
    idx = np.arange(2**n, dtype=np.int64)
    return np.array([int(bin(z).count("1")) for z in idx], dtype=np.int64)


def sector_projector(n: int, weight: int) -> np.ndarray:
    """Diagonal projector ``P`` onto the fixed-Hamming-weight sector."""
    diag = (hamming_weights(n) == weight).astype(np.complex128)
    return np.diag(diag)


# --- density-matrix utilities ----------------------------------------------


def pure_state_rho(psi: np.ndarray) -> np.ndarray:
    """Density matrix ``|psi><psi|`` of a (normalized) state vector."""
    psi = np.asarray(psi, dtype=np.complex128).reshape(-1)
    nrm = np.linalg.norm(psi)
    if nrm == 0:
        raise ValueError("zero state vector")
    psi = psi / nrm
    return np.outer(psi, psi.conj())


def mpow(rho: np.ndarray, m: int) -> np.ndarray:
    """Matrix power ``rho**m`` via the Hermitian eigendecomposition.

    Using the spectral form keeps it numerically stable for the small,
    near-singular ``rho_p^M`` that arise at large copy number ``M``.
    """
    if m < 1:
        raise ValueError("m must be >= 1")
    if m == 1:
        return rho.copy()
    w, v = np.linalg.eigh(_hermitize(rho))
    w = np.clip(w, 0.0, None)  # physical eigenvalues are >= 0
    return (v * (w**m)) @ v.conj().T


def trace_of_product(a: np.ndarray, b: np.ndarray) -> complex:
    """``Tr(a @ b)`` without forming the full product matrix."""
    return complex(np.einsum("ij,ji->", a, b))


def vd_population(rho_p: np.ndarray, observable: np.ndarray, m: int):
    """VD population law objects at copy number ``m`` (eq. vd_population_law).

    Returns ``(N_M, D_M, mu_VD_M)`` with ``N_M = Tr(O rho_p^M)``,
    ``D_M = Tr(rho_p^M)`` and ``mu_VD_M = N_M / D_M``.
    """
    rp = mpow(rho_p, m)
    n_m = trace_of_product(observable, rp).real
    d_m = np.trace(rp).real
    return float(n_m), float(d_m), float(n_m / d_m)


def dominant_eigenpair(rho: np.ndarray):
    """Largest-eigenvalue (eigenvalue, eigenvector) pair of a Hermitian matrix."""
    w, v = np.linalg.eigh(_hermitize(rho))
    j = int(np.argmax(w))
    return float(w[j]), v[:, j]


def ordered_eigenvalues(rho: np.ndarray) -> np.ndarray:
    """Eigenvalues of a Hermitian matrix sorted in descending order."""
    w = np.linalg.eigvalsh(_hermitize(rho))
    return np.sort(w.real)[::-1]


def spectral_gap(rho: np.ndarray):
    """``(lambda_1, lambda_2)`` -- the two largest eigenvalues of ``rho``."""
    w = ordered_eigenvalues(rho)
    lam1 = float(w[0])
    lam2 = float(w[1]) if w.size > 1 else 0.0
    return lam1, lam2


# --- validity checks --------------------------------------------------------


def _hermitize(a: np.ndarray) -> np.ndarray:
    return 0.5 * (a + a.conj().T)


def is_hermitian(a: np.ndarray, atol: float = 1e-12) -> bool:
    return bool(np.allclose(a, a.conj().T, atol=atol, rtol=0.0))


def is_trace_one(rho: np.ndarray, atol: float = 1e-12) -> bool:
    return bool(abs(np.trace(rho) - 1.0) <= atol)


def is_psd(rho: np.ndarray, atol: float = 1e-10) -> bool:
    w = np.linalg.eigvalsh(_hermitize(rho))
    return bool(w.min() >= -atol)


def assert_density_matrix(rho: np.ndarray, atol: float = 1e-10) -> None:
    """Raise ``AssertionError`` if ``rho`` is not a valid density matrix."""
    assert is_hermitian(rho, atol=max(atol, 1e-12)), "rho is not Hermitian"
    assert is_trace_one(rho, atol=max(atol, 1e-12)), "Tr(rho) != 1"
    assert is_psd(rho, atol=atol), "rho is not positive semidefinite"
