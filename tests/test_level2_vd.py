import csv
from pathlib import Path

from level2 import vd


REPO_ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = REPO_ROOT / "level2" / "level2_vd_results.csv"
REPORT_PATH = REPO_ROOT / "level2" / "level2_vd_report.md"


def _rows():
    with CSV_PATH.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _row(b):
    for row in _rows():
        if int(row["B"]) == int(b):
            return row
    raise KeyError(b)


def test_level2_vd_outputs_are_present_and_scoped():
    assert CSV_PATH.exists()
    assert REPORT_PATH.exists()
    rows = _rows()
    assert len(rows) == len(vd.B_VALUES)
    assert {row["method"] for row in rows} == {"vd_m2_hadamard_swap"}
    assert {int(row["copies_M"]) for row in rows} == {2}
    assert {int(row["mixer_trotter_steps"]) for row in rows} == {1}
    report = REPORT_PATH.read_text(encoding="utf-8")
    assert "validacion EN FORMA" in report
    assert "Not implemented here: M>2, folding, ensemble run" in report


def test_level2_vd_noiseless_crosscheck_recovers_pure_state_reference():
    for row in _rows():
        assert abs(float(row["noiseless_D_hat"]) - 1.0) <= vd.NOISELESS_D_TOL
        assert float(row["noiseless_mu_abs_error"]) <= vd.NOISELESS_MU_TOL


def test_level2_vd_smoke_does_not_claim_bias_reduction():
    row = _row(max(vd.B_VALUES))
    assert row["vd_bias_interpretation"] == "not_inferable_small_denominator_smoke"
    assert float(row["B_den_impl_estimate"]) > max(vd.B_VALUES)
    assert float(row["B_over_B_den_impl_estimate"]) < 0.25
    report = REPORT_PATH.read_text(encoding="utf-8")
    assert "does not support a VD bias-reduction claim" in report
    assert "deferred to the Step 5 high-power" in report


def test_level2_vd_clip_and_resource_columns_are_present():
    for row in _rows():
        assert float(row["denominator_clip_value"]) > 0.0
        assert float(row["mean_D_clipped"]) >= float(row["denominator_clip_value"])
        assert int(row["raw_hadamard_calls_per_rep"]) == 2 * int(row["B"])
        assert int(row["resource_paired_sample"]) == int(row["B"])
        assert int(row["resource_two_qubit_gate_proxy"]) == 14 * int(row["B"])
        assert int(row["vd_circuit_qubits"]) == 2 * int(row["n_qubits_system"]) + 1
        assert int(row["cswap_cx_count"]) > 0
        assert int(row["numerator_cx_count"]) >= int(row["cswap_cx_count"])
        assert int(row["denominator_cx_count"]) >= int(row["cswap_cx_count"])


def test_level2_vd_small_run_is_deterministic():
    cfg = vd.VDSamplingConfig(
        b_values=(32,),
        repetitions=1,
        noiseless_check_shots=512,
        noisy_denominator_reference_shots=128,
        base_seed=333,
    )
    rows_a, _report_a = vd.run_vd_sampling(cfg, started_at=0.0)
    rows_b, _report_b = vd.run_vd_sampling(cfg, started_at=0.0)
    scrubbed_a = [{**row, "runtime_seconds": 0.0} for row in rows_a]
    scrubbed_b = [{**row, "runtime_seconds": 0.0} for row in rows_b]
    assert scrubbed_a == scrubbed_b
