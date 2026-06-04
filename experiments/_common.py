"""Shared frozen model and helpers for the Level 1 experiments E1-E4, E7.

This module defines the (provisional) frozen instance, angles, and noise channel
used by every Level 1 experiment, plus CSV writing.  At PAP freeze time these
values are replaced by the artifacts in results/frozen/ (instance list, QAOA
angles, channel constants).  Per the firewall (EXP. PLAN sec. 13), experiments
build the white-box model here and only contrast against ground truth at the
final adjudication step.
"""

from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import replace
from pathlib import Path

import numpy as np

from vd_sv import coefficients as cf
from vd_sv import noise, qaoa

# --- frozen model spec (provisional; [PRE-CONGELADO]) ----------------------
N_QUBITS = 6
SECTOR_WEIGHT = 2  # NOT half-filling (n/2=3): breaks particle-hole so delta != 0
RING_WEIGHTS = np.array([1.0, 1.3, 0.7, 1.1, 0.9, 1.2])
ANGLE_SEED = 0
ANGLE_RESTARTS = 8
CHANNEL_SEED = 1
KAPPA_VD = 2.0   # VD uses numerator + denominator streams (eq. resource_normalization_v13)
KAPPA_SV = 1.0
KAPPA_UNMIT = 1.0
REPO_ROOT = Path(__file__).resolve().parents[1]
FROZEN_INSTANCES = REPO_ROOT / "results" / "frozen" / "frozen_instances.csv"
FROZEN_ANGLES = REPO_ROOT / "results" / "frozen" / "frozen_qaoa_angles.csv"


def default_model(observable_normalization: str = "inf") -> cf.WhiteBoxModel:
    inst = qaoa.ring_instance(N_QUBITS, weights=RING_WEIGHTS, weight=SECTOR_WEIGHT, name="ring6_k2")
    gammas, betas, _ = qaoa.optimize_angles(inst, depth=1, seed=ANGLE_SEED, restarts=ANGLE_RESTARTS)
    channel = noise.heterogeneous_ad_pd(N_QUBITS, seed=CHANNEL_SEED)
    model = cf.build_model(inst, gammas, betas, channel)
    if observable_normalization == "inf":
        return model
    obs = normalized_observable(inst, observable_normalization)
    mu_star = float(np.real(model.psi.conj() @ (obs @ model.psi)))
    return replace(model, observable=obs, mu_star=mu_star)


def frozen_models(observable_normalization: str = "inf") -> list[cf.WhiteBoxModel]:
    """Build the included pre-freeze ensemble from pinned CSV artifacts."""
    if not FROZEN_INSTANCES.exists() or not FROZEN_ANGLES.exists():
        return [default_model(observable_normalization=observable_normalization)]
    instance_rows = _read_csv(FROZEN_INSTANCES)
    angle_rows = _read_csv(FROZEN_ANGLES)
    models = [
        _model_from_frozen_row(row, angle_rows, observable_normalization)
        for row in sorted(
            instance_rows,
            key=lambda r: (int(r["size_n"]), int(r["candidate_index"]), r["instance_id"]),
        )
        if row["selection_status"] == "included"
    ]
    return models or [default_model(observable_normalization=observable_normalization)]


def stable_seed(base_seed: int, *parts: object) -> int:
    payload = "|".join([str(int(base_seed)), *(str(part) for part in parts)]).encode("utf-8")
    digest = hashlib.sha256(payload).digest()
    return int.from_bytes(digest[:8], "big") % (2**63)


def normalized_observable(inst: qaoa.QAOAInstance, normalization: str) -> np.ndarray:
    if normalization == "inf":
        return qaoa.observable(inst)
    if normalization == "sector_trace_zero_spectral":
        diag = qaoa.cost_diagonal(inst)
        sector = np.real(np.diag(qaoa.symmetry_projector(inst))) > 0.5
        centered = diag - float(np.mean(diag[sector]))
        scale = float(np.max(np.abs(centered)))
        if scale == 0.0:
            raise ValueError("sector-trace-zero observable has zero spectral scale")
        return np.diag((centered / scale).astype(np.complex128))
    raise ValueError(f"unknown observable normalization: {normalization}")


def log_grid(lo: float, hi: float, n: int) -> np.ndarray:
    return np.unique(np.round(np.logspace(np.log10(lo), np.log10(hi), n)).astype(int)).astype(float)


def p_grid(lo: float, hi: float, n: int) -> np.ndarray:
    return np.round(np.logspace(np.log10(lo), np.log10(hi), n), 6)


def write_csv(path: str | Path, fieldnames: list[str], rows: list[dict]) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    return path


def _model_from_frozen_row(
    row: dict,
    angle_rows: list[dict],
    observable_normalization: str,
) -> cf.WhiteBoxModel:
    matching = sorted(
        (a for a in angle_rows if a["instance_id"] == row["instance_id"]),
        key=lambda a: int(a["layer"]),
    )
    if not matching:
        raise ValueError(f"missing frozen angles for {row['instance_id']}")
    inst = qaoa.QAOAInstance(
        n=int(row["size_n"]),
        weight=int(row["sector_weight"]),
        edges=tuple((int(i), int(j)) for i, j in json.loads(row["edges_json"])),
        weights=tuple(float(x) for x in json.loads(row["weights_json"])),
        mixer_edges=tuple((int(i), int(j)) for i, j in json.loads(row["mixer_edges_json"])),
        name=row["instance_id"],
    )
    gammas = np.asarray([float(a["gamma"]) for a in matching], dtype=np.float64)
    betas = np.asarray([float(a["beta"]) for a in matching], dtype=np.float64)
    channel = noise.heterogeneous_ad_pd(inst.n, seed=int(row["noise_channel_seed"]))
    model = cf.build_model(inst, gammas, betas, channel)
    if observable_normalization == "inf":
        return model
    obs = normalized_observable(inst, observable_normalization)
    mu_star = float(np.real(model.psi.conj() @ (obs @ model.psi)))
    return replace(model, observable=obs, mu_star=mu_star)


def _read_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def wls_fit(x_cols: np.ndarray, y: np.ndarray, w: np.ndarray):
    """Weighted least squares. ``x_cols`` shape (npoints, nparams).

    Returns ``(coeffs, cov)`` with ``cov`` the parameter covariance matrix.
    """
    sw = np.sqrt(w)
    a = x_cols * sw[:, None]
    bvec = y * sw
    coeffs, *_ = np.linalg.lstsq(a, bvec, rcond=None)
    # parameter covariance (Gauss-Markov, weights = 1/var)
    xtwx = (x_cols * w[:, None]).T @ x_cols
    cov = np.linalg.inv(xtwx)
    return coeffs, cov


def aic_gaussian(y: np.ndarray, yhat: np.ndarray, k: int) -> float:
    """Gaussian AIC = n ln(RSS/n) + 2k."""
    n = y.size
    rss = float(np.sum((y - yhat) ** 2))
    rss = max(rss, 1e-300)
    return n * np.log(rss / n) + 2 * k
