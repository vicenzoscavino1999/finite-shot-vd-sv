"""The cost observable stays inside [-1, 1] after normalization (||O||_inf = 1)."""

import numpy as np

from vd_sv import qaoa


def test_observable_norm(instance):
    o = qaoa.observable(instance)
    eig = np.linalg.eigvalsh(o)
    assert np.max(np.abs(eig)) <= 1.0 + 1e-12
    assert np.isclose(np.max(np.abs(eig)), 1.0, atol=1e-12)  # normalization saturates
