"""Resource and observable normalization sensitivity diagnostics."""

import csv

from experiments import e7_resource_observable_sensitivity as sens


def test_resource_and_observable_sensitivity_grid(tmp_path):
    path = sens.run(tmp_path, mode="fast")
    rows = list(csv.DictReader(path.open(encoding="utf-8")))

    resource_defs = {r["resource_definition"] for r in rows}
    obs_defs = {r["observable_normalization"] for r in rows}
    pairs = {r["method_pair"] for r in rows}
    assert len(resource_defs) >= 3
    assert len(obs_defs) >= 2
    assert {"vd_vs_unmitigated", "vd_vs_sv", "sv_vs_unmitigated"} <= pairs

    crossing_rows = [r for r in rows if r["method_pair"] == "vd_vs_unmitigated"]
    assert all(r["leading_regime"] == "leading_crossing" for r in crossing_rows)
    assert all(r["winner_large_R"] == "vd" for r in crossing_rows)
    assert all(float(r["leading_R0"]) > 0.0 for r in crossing_rows)

    by_obs = {}
    for row in crossing_rows:
        by_obs.setdefault(row["observable_normalization"], {})[row["resource_definition"]] = float(
            row["leading_R0"]
        )
    assert by_obs["inf"]["hadamard_call"] != by_obs["sector_trace_zero_spectral"]["hadamard_call"]
    assert by_obs["inf"]["two_qubit_gate_proxy"] > by_obs["inf"]["hadamard_call"]
