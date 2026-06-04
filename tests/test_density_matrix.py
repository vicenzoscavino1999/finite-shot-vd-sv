"""rho_p stays Hermitian, trace-preserving, and PSD; rho_star is pure."""

import numpy as np
import pytest

from vd_sv.density_matrix import assert_density_matrix


@pytest.mark.parametrize("p", [0.0, 0.05, 0.15, 0.25])
def test_rho_p_valid(model, p):
    assert_density_matrix(model.rho_p(p))


def test_rho_star_pure(model):
    rho = model.rho_star
    assert np.isclose(np.trace(rho @ rho).real, 1.0, atol=1e-9)
