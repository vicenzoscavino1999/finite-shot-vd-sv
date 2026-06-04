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
    assert any(r["leading_regime"] == "leading_crossing" for r in crossing_rows)
    assert all(float(r["leading_R0"]) >= 0.0 for r in crossing_rows)

    by_obs = {}
    for row in crossing_rows:
        key = (row["instance_id"], row["observable_normalization"])
        by_obs.setdefault(key, {})[row["resource_definition"]] = float(row["leading_R0"])
    for resources in by_obs.values():
        assert resources["two_qubit_gate_proxy"] >= resources["hadamard_call"]
