import csv
import math
from pathlib import Path

import numpy as np

from experiments import e12_efron_stein_operational as e12


REPO_ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = REPO_ROOT / "results" / "secondary" / "e12_efron_stein_operational.csv"
REPORT_PATH = REPO_ROOT / "results" / "secondary" / "e12_efron_stein_operational_report.md"


def _rows():
    with CSV_PATH.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _one_row_per_instance(rows):
    by_instance = {}
    for row in rows:
        by_instance[row["instance_id"]] = row
    return [by_instance[key] for key in sorted(by_instance)]


def test_e12_outputs_are_present_and_on_declared_grid():
    assert CSV_PATH.exists()
    assert REPORT_PATH.exists()
    rows = _rows()
    assert len(rows) == 10 * len(e12.B_DEN_MULTIPLIERS)
    assert {float(row["noise_strength"]) for row in rows} == {e12.P_FIXED}

    by_instance = {}
    for row in rows:
        by_instance.setdefault(row["instance_id"], []).append(row)
    assert len(by_instance) == 10
    for inst_rows in by_instance.values():
        b_values = [int(row["B"]) for row in inst_rows]
        assert len(b_values) == len(e12.B_DEN_MULTIPLIERS)
        assert b_values == sorted(b_values)


def test_e12_variance_certificate_holds_in_all_cells():
    for row in _rows():
        var_empirical = float(row["var_empirical"])
        es_over_b = float(row["es_bound_over_B"])
        assert row["certificate_holds"] == "true"
        assert var_empirical <= es_over_b


def test_e12_sampler_is_deterministic_for_fixed_seed():
    model = e12.frozen_models()[0]
    vd = model.vd(e12.P_FIXED, e12.M_COPIES)
    seed = e12.stable_seed(e12.E12_SEED, model.inst.name, 32)
    sample_a = e12.sample_vd_clip(vd["N_M"], vd["D_M"], 32, 128, e12.make_rng(seed))
    sample_b = e12.sample_vd_clip(vd["N_M"], vd["D_M"], 32, 128, e12.make_rng(seed))
    assert np.array_equal(sample_a, sample_b)


def test_e12_es_constant_is_operational_relative_to_formal_scale():
    for row in _one_row_per_instance(_rows()):
        es_constant = float(row["es_constant"])
        ratio = float(row["es_vs_formal_ratio"])
        assert e12.ES_OPERATIONAL_MIN <= es_constant <= e12.ES_OPERATIONAL_MAX
        assert math.isclose(
            ratio,
            es_constant / e12.FORMAL_CONSTANT_SCALE,
            rel_tol=1e-12,
            abs_tol=1e-12,
        )
        assert ratio < 1e-4


def test_e12_unmitigated_crossing_is_finite_and_sv_dominance_is_recorded():
    rows = _one_row_per_instance(_rows())
    sv_flags = {row["sv_dominates_flag"] for row in rows}
    assert sv_flags == {"true", "false"}
    for row in rows:
        r_unmit = float(row["R_ES_vs_unmit"])
        assert math.isfinite(r_unmit)
        assert r_unmit > 0.0
        assert row["sv_dominates_flag"] in {"true", "false"}
