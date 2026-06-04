"""Closed-form white-box ground truth (EXPERIMENTAL_PLAN sec. 7; paper sec. 3-6, 8).

Every quantity here is computed exactly from ``(rho_star, O, P, Delta, rho_p)`` and is
the ground truth against which the finite-shot estimators are contrasted.  Per the
firewall in EXPERIMENTAL_PLAN sec. 13, the estimation pipeline must not read these
values except at the final adjudication/contrast step.

Theory anchors (paper/main.tex):
- delta_VD       eq. delta_vd_explicit          : 2 Re <psi| O Q_star Delta |psi>
- delta_SV       eq. delta_sv_precise           : Tr(O P Delta P) - mu_star Tr(P Delta P)
- c_VD           eq. vd_c_v4 / hadamard_c_v4
- v_VD           eq. vd_v_v4 / hadamard_v_v4
- c_SV = 0       eq. sv_quotient_bias_zero_v14   (exact)
- Hadamard vars  eq. hadamard_variances_v4       : sigma_N^2=1-N^2, sigma_D^2=1-D^2, sigma_ND=0
- Efron-Stein    eq. efron_stein_vd_bound_v11    : 8 K_N^2 (D+2K_D)^2 / D^4 / B
- B_den          eq. hadamard_Bmin_v4
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from . import noise as noise_mod
from .density_matrix import dominant_eigenpair, mpow, trace_of_product, vd_population
from .qaoa import QAOAInstance, ideal_state, observable, symmetry_projector

# Bounded one-shot Hadamard-test signs: X_M, Y_M in {+-1}  =>  K_N = 1, K_D = 2
K_N = 1.0
K_D = 2.0


@dataclass
class WhiteBoxModel:
    """Frozen white-box model: ideal state, observable, symmetry, noise generator."""

    inst: QAOAInstance
    gammas: np.ndarray
    betas: np.ndarray
    channel: noise_mod.NoiseChannel
    rho_star: np.ndarray
    psi: np.ndarray
    observable: np.ndarray
    projector: np.ndarray
    mu_star: float
    delta: np.ndarray  # Delta = L(rho_star), closed form

    # -- noisy state ---------------------------------------------------------
    def rho_p(self, p: float) -> np.ndarray:
        return self.channel.apply(self.rho_star, p)

    # -- first-order endpoint coefficients (p-independent generators) --------
    def delta_vd(self) -> float:
        """delta_VD = 2 Re <psi| O Q_star Delta |psi>  (eq. delta_vd_explicit)."""
        dpsi = self.delta @ self.psi
        q_dpsi = dpsi - (self.psi.conj() @ dpsi) * self.psi  # Q_star |w>
        val = self.psi.conj() @ (self.observable @ q_dpsi)
        return float(2.0 * np.real(val))

    def delta_sv(self) -> float:
        """delta_SV = Tr(O P Delta P) - mu_star Tr(P Delta P)  (eq. delta_sv_precise)."""
        p_dp_p = self.projector @ self.delta @ self.projector
        term1 = trace_of_product(self.observable, p_dp_p).real
        term2 = self.mu_star * np.trace(p_dp_p).real
        return float(term1 - term2)

    # -- VD population + Hadamard-implementation coefficients -----------------
    def vd(self, p: float, m: int = 2) -> dict:
        rho_p = self.rho_p(p)
        n_m, d_m, mu = vd_population(rho_p, self.observable, m)
        b = mu - self.mu_star
        sigma_n2 = 1.0 - n_m**2          # eq. hadamard_variances_v4
        sigma_d2 = 1.0 - d_m**2
        sigma_nd = 0.0
        c = (mu * sigma_d2 - sigma_nd) / d_m**2            # eq. vd_c_v4 (= hadamard_c_v4)
        v = (sigma_n2 + mu**2 * sigma_d2 - 2 * mu * sigma_nd) / d_m**2  # eq. vd_v_v4
        v_tilde = v + 2.0 * b * c                          # leading 1/B coefficient
        return {
            "N_M": n_m, "D_M": d_m, "mu_VD": mu, "b_VD": b,
            "sigma_N2": sigma_n2, "sigma_D2": sigma_d2, "sigma_ND": sigma_nd,
            "c_VD": c, "v_VD": v, "v_tilde_VD": v_tilde,
            "B_den": self.b_den(d_m), "efron_stein_bound": efron_stein_bound(d_m),
        }

    def vd_floor(self, p: float) -> dict:
        """Infinite-copy floor b_VD,inf(p) = O_11(p) - mu_star (eq. b_VD,inf)."""
        rho_p = self.rho_p(p)
        _lam1, phi1 = dominant_eigenpair(rho_p)
        o11 = float(np.real(phi1.conj() @ (self.observable @ phi1)))
        return {"O_11": o11, "b_VD_inf": o11 - self.mu_star}

    @staticmethod
    def b_den(d_m: float, eps: float = 1e-3) -> float:
        """Denominator sample threshold (eq. hadamard_Bmin_v4)."""
        return (8.0 * (1.0 - d_m**2) / d_m**2 + 8.0 / (3.0 * d_m)) * np.log(1.0 / eps)

    # -- SV postselection coefficients ---------------------------------------
    def sv(self, p: float) -> dict:
        rho_p = self.rho_p(p)
        pz = np.real(np.diag(rho_p))                 # Z-measurement distribution
        ozz = np.real(np.diag(self.observable))
        acc = np.real(np.diag(self.projector)) > 0.5  # accepted = correct Hamming weight
        a = float(pz[acc].sum())                      # a(p) = Tr(P rho_p)
        mu_sv = float((pz[acc] * ozz[acc]).sum() / a)
        e_w2 = float((pz[acc] * ozz[acc] ** 2).sum() / a)
        sigma_acc2 = e_w2 - mu_sv**2                  # Var(W | accepted)
        v_sv = sigma_acc2 / a                         # eq. v_SV = sigma_acc^2 / a
        return {
            "a": a, "mu_SV": mu_sv, "b_SV": mu_sv - self.mu_star,
            "c_SV": 0.0, "sigma_acc2": sigma_acc2, "v_SV": v_sv, "v_tilde_SV": v_sv,
        }

    # -- unmitigated baseline ------------------------------------------------
    def unmitigated(self, p: float) -> dict:
        rho_p = self.rho_p(p)
        pz = np.real(np.diag(rho_p))
        ozz = np.real(np.diag(self.observable))
        mu0 = float((pz * ozz).sum())
        sigma0_2 = float((pz * ozz**2).sum() - mu0**2)
        return {"mu_0": mu0, "b_0": mu0 - self.mu_star, "sigma_0_2": sigma0_2,
                "c_0": 0.0, "v_0": sigma0_2, "v_tilde_0": sigma0_2}


def build_model(inst: QAOAInstance, gammas, betas,
                channel: noise_mod.NoiseChannel) -> WhiteBoxModel:
    gammas = np.atleast_1d(np.asarray(gammas, dtype=np.float64))
    betas = np.atleast_1d(np.asarray(betas, dtype=np.float64))
    rho_star = ideal_state(inst, gammas, betas)
    psi = rho_star_to_psi(rho_star)
    obs = observable(inst)
    proj = symmetry_projector(inst)
    mu_star = float(np.real(psi.conj() @ (obs @ psi)))
    delta = channel.delta(rho_star)
    return WhiteBoxModel(inst, gammas, betas, channel, rho_star, psi, obs, proj, mu_star, delta)


def rho_star_to_psi(rho_star: np.ndarray) -> np.ndarray:
    """Recover the (phase-fixed) state vector of a pure density matrix."""
    _lam, phi = dominant_eigenpair(rho_star)
    # fix global phase so the first sizeable entry is real-positive (deterministic)
    j = int(np.argmax(np.abs(phi)))
    phi = phi * np.exp(-1j * np.angle(phi[j]))
    return phi


def efron_stein_bound(d_m: float) -> float:
    """Efron-Stein total-variance constant 8 K_N^2 (D + 2 K_D)^2 / D^4 (per 1/B)."""
    return 8.0 * K_N**2 * (d_m + 2.0 * K_D) ** 2 / d_m**4


# --- resource-normalized sampling coefficient ------------------------------


def resource_sampling_coeff(v_tilde: float, kappa: float) -> float:
    """s_m = kappa_m * v_tilde_m  (paper eq. for MSE_m(p,R) = b^2 + s/R)."""
    return kappa * v_tilde
