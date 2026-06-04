"""The empirical VD MSE recovers the leading law b^2 + (v + 2bc)/B on a white-box
cell (eq. vd_mse_certified_v4)."""

from vd_sv import vd as vd_mod
from vd_sv.estimators import make_rng, mse


def test_mse_leading_law(model):
    p = 0.12
    vc = model.vd(p, 2)
    rng = make_rng(5)
    B, T = 20000, 40000
    est = vd_mod.sample_vd_quotient(vc["N_M"], vc["D_M"], B, T, rng)
    observed = mse(est, model.mu_star)
    predicted = vc["b_VD"] ** 2 + vc["v_tilde_VD"] / B
    assert abs(observed - predicted) / predicted < 0.05
