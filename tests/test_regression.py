"""A small white-box grid matches a committed reference fixture."""

import csv
from pathlib import Path

import numpy as np

FIXTURE = Path(__file__).parent / "fixtures" / "regression_2x2.csv"


def test_b_vd_inf_regression(model):
    ref = list(csv.DictReader(FIXTURE.open(encoding="utf-8")))
    got = [model.vd_floor(float(r["noise_strength"]))["b_VD_inf"] for r in ref]
    exp = [float(r["b_vd_inf"]) for r in ref]
    assert np.allclose(got, exp, atol=1e-12, rtol=0.0)
