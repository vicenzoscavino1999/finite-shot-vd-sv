"""SV hypothesis: the observable is symmetry-compatible (P O = O P) and the ideal
state lives in the sector (P rho_star P = rho_star).  Guards against silently
reverting to a MaxCut / X^n setup where the hypothesis fails."""

import numpy as np

from vd_sv import qaoa
from vd_sv.density_matrix import PAULI_Z, embed


def test_po_equals_op(instance):
    o = qaoa.observable(instance)
    p = qaoa.symmetry_projector(instance)
    assert np.allclose(p @ o, o @ p, atol=1e-12)


def test_ideal_state_in_sector(model):
    p = model.projector
    assert np.allclose(p @ model.rho_star @ p, model.rho_star, atol=1e-10)


def test_mixer_preserves_hamming_weight(instance):
    hm = qaoa.mixer_hamiltonian(instance)
    s = sum(embed(PAULI_Z, i, instance.n) for i in range(instance.n))
    assert np.allclose(hm @ s, s @ hm, atol=1e-10)
