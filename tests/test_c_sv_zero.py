"""The discriminating structural test: c_SV = 0 exactly while c_VD != 0 and matches
the Hadamard formula (eq. hadamard_c_v4)."""


def test_c_sv_exactly_zero(model):
    assert model.sv(0.15)["c_SV"] == 0.0


def test_c_vd_matches_formula_and_nonzero(model):
    vd = model.vd(0.15, 2)
    expect = vd["mu_VD"] * (1 - vd["D_M"] ** 2) / vd["D_M"] ** 2
    assert abs(vd["c_VD"] - expect) < 1e-12
    assert abs(vd["c_VD"]) > 1e-3
