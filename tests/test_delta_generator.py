"""Closed-form delta_VD, delta_SV equal the finite-difference slope of the bias,
and Delta = L(rho_star) matches its Richardson finite-difference estimate."""

from vd_sv import noise


def _richardson_slope(fn, h=5e-4):
    return 2 * fn(h) / h - fn(2 * h) / (2 * h)


def test_delta_consistency(model):
    disc = noise.assert_delta_consistency(model.channel, model.rho_star, atol=1e-6)
    assert disc < 1e-6


def test_delta_vd_matches_finite_difference(model):
    closed = model.delta_vd()
    fd = _richardson_slope(lambda p: model.vd_floor(p)["b_VD_inf"])
    assert abs(closed - fd) < 1e-4
    assert abs(closed) > 1e-4  # generic (nonzero) first-order case


def test_delta_sv_matches_finite_difference(model):
    closed = model.delta_sv()
    fd = _richardson_slope(lambda p: model.sv(p)["b_SV"])
    assert abs(closed - fd) < 1e-4
    assert abs(closed) > 1e-5
