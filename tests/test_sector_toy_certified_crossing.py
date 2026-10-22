"""Sector-toy certified VD--SV crossing (paper App. C): numbers stated in the paper."""

from __future__ import annotations

from scripts import sector_toy_certified_crossing as toy


def test_certified_interval_matches_paper():
    cert = toy.certify()
    assert abs(cert["R0"] - 724.2) < 0.05
    assert abs(cert["eta"] - 0.0486) < 5e-4
    assert abs(cert["R_L"] - 715.3) < 0.05
    assert abs(cert["R_U"] - 732.9) < 0.05
    assert cert["vd_lo"] > 0 and cert["vd_hi"] <= toy.C_VD
    assert cert["sv"] <= toy.C_SV


def test_exact_sums_respect_the_certificate():
    cert = toy.certify()
    info = toy.check_exact(cert, r_max=1200)
    assert info["switch"] == (728, 730)
    lo, hi = info["vd_exact"]
    assert cert["vd_lo"] <= lo <= hi <= cert["vd_hi"]
    assert info["sv_exact"] <= cert["sv"]
