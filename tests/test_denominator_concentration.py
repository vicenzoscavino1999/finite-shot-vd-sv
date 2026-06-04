"""E5 denominator concentration: bad denominator tails collapse around B_den."""

import csv

from experiments import e5_denominator_concentration as e5


def test_e5_denominator_tail_regime(tmp_path):
    path = e5.run(tmp_path, mode="fast")
    rows = list(csv.DictReader(path.open(encoding="utf-8")))

    by_instance = {}
    for row in rows:
        by_instance.setdefault(row["instance_id"], []).append(row)

    for instance_rows in by_instance.values():
        instance_rows = sorted(instance_rows, key=lambda r: int(r["B"]))
        exact = [float(r["bad_denominator_prob_exact"]) for r in instance_rows]
        assert all(a > b for a, b in zip(exact, exact[1:]))

        near_bden = min(instance_rows, key=lambda r: abs(float(r["B_over_Bden"]) - 1.0))
        assert float(near_bden["bernstein_bound"]) <= 1.1e-3
        assert float(near_bden["bad_denominator_prob_exact"]) < 1e-3

        below = instance_rows[0]
        above = instance_rows[-1]
        assert float(below["bad_denominator_prob_exact"]) > 1e-2
        assert float(above["bad_denominator_prob_exact"]) < 1e-20
        assert float(below["excess_kurtosis_ordinary_finite"]) > float(below["excess_kurtosis_clipped"])
        assert abs(float(above["relative_deviation_clipped"])) < abs(float(below["relative_deviation_clipped"]))
