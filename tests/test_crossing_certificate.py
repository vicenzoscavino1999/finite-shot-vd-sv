"""Certified-crossing machinery: the leading crossing lies in the certified band,
eta < 1/2, and the empirical root finder locates the sign change."""

import numpy as np

from vd_sv.crossing import MethodLaw, certified_crossing, empirical_crossing


def test_certified_band():
    i = MethodLaw("i", b2=1e-3, s=20.0, C=50.0)   # lower bias, higher cost
    j = MethodLaw("j", b2=2e-2, s=1.0, C=5.0)      # higher bias, lower cost
    cert = certified_crossing(i, j)
    assert cert.regime == "certified_crossing"
    assert cert.eta < 0.5
    assert cert.interval[0] <= cert.R0 <= cert.interval[1]
    assert cert.winner_large_R == "i"


def test_uniform_dominance_detected():
    i = MethodLaw("i", b2=1e-6, s=0.01, C=1.0)     # both lower bias AND lower cost
    j = MethodLaw("j", b2=1e-2, s=10.0, C=1.0)
    cert = certified_crossing(i, j)
    assert cert.regime == "uniform_dominance"
    assert cert.winner_large_R == "i"


def test_empirical_root():
    r = np.array([10.0, 100.0, 1000.0, 10000.0])
    mse_i = 1e-3 + 20.0 / r
    mse_j = 2e-2 + 1.0 / r
    rstar = empirical_crossing(r, mse_i, mse_j)
    assert rstar is not None and 100.0 < rstar < 10000.0
