"""E5 denominator concentration: bad denominator tails collapse around B_den."""

import csv

from experiments import e5_denominator_concentration as e5


def test_e5_denominator_tail_regime(tmp_path):
    path = e5.run(tmp_path, mode="fast")
    rows = sorted(csv.DictReader(path.open(encoding="utf-8")), key=lambda r: int(r["B"]))

    exact = [float(r["bad_denominator_prob_exact"]) for r in rows]
    assert all(a > b for a, b in zip(exact, exact[1:]))

    near_bden = min(rows, key=lambda r: abs(float(r["B_over_Bden"]) - 1.0))
    assert float(near_bden["bernstein_bound"]) <= 1.1e-3
    assert float(near_bden["bad_denominator_prob_exact"]) < 1e-3

    below = rows[0]
    above = rows[-1]
    assert float(below["bad_denominator_prob_exact"]) > 1e-2
    assert float(above["bad_denominator_prob_exact"]) < 1e-20
    assert float(below["excess_kurtosis_ordinary_finite"]) > float(below["excess_kurtosis_clipped"])
    assert abs(float(above["relative_deviation_clipped"])) < abs(float(below["relative_deviation_clipped"]))
