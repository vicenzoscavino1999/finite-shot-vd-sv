"""Resource-kappa and observable-normalization sensitivity for E7.

EXPERIMENTAL_PLAN sec. 10 requires reporting whether crossing conclusions depend
on the resource normalization ``kappa`` or on the observable convention.  This
Level-1 diagnostic recomputes the leading laws

    MSE_m(R) = b_m^2 + s_m/R

for several pre-declared kappa proxies and two diagonal, symmetry-compatible
observable normalizations.

The output is exploratory until these conventions are frozen in Fase 0.
"""

from __future__ import annotations

from pathlib import Path

from vd_sv.crossing import MethodLaw, certified_crossing

from ._common import frozen_models, write_csv

P_FIXED = 0.15
M_COPIES = 2

OBSERVABLE_NORMALIZATIONS = ("inf", "sector_trace_zero_spectral")


def resource_definitions(n_qubits: int):
    return {
        # Statistical convention: one completed VD quotient replica is charged as one sample.
        "paired_sample": {"vd": 1.0, "sv": 1.0, "unmitigated": 1.0},
        # Current Level-1 physical-call convention: numerator + denominator streams.
        "hadamard_call": {"vd": 2.0, "sv": 1.0, "unmitigated": 1.0},
        # Conservative proxy for two-qubit derangement overhead per numerator/denominator call.
        "two_qubit_gate_proxy": {
            "vd": 2.0 * (1.0 + n_qubits * (M_COPIES - 1)),
            "sv": 1.0,
            "unmitigated": 1.0,
        },
        # Wall-clock proxy: derangement depth plus a modest SV postselection bookkeeping cost.
        "wall_clock_proxy": {
            "vd": 2.0 * (1.0 + 0.5 * n_qubits * (M_COPIES - 1)),
            "sv": 1.25,
            "unmitigated": 1.0,
        },
    }
PAIRS = (
    ("vd", "unmitigated"),
    ("vd", "sv"),
    ("sv", "unmitigated"),
)
FIELDS = [
    "instance_id",
    "noise_strength",
    "copies_M",
    "observable_normalization",
    "resource_definition",
    "method_pair",
    "method_a",
    "method_b",
    "kappa_vd",
    "kappa_sv",
    "kappa_unmitigated",
    "b2_a",
    "s_a",
    "b2_b",
    "s_b",
    "lower_bias_method",
    "g_bias_gap",
    "delta_s_lower_minus_other",
    "has_leading_crossing",
    "leading_R0",
    "leading_regime",
    "winner_large_R",
]


def run(outdir: str | Path, mode: str = "fast", seed: int = 808) -> Path:
    del mode, seed  # deterministic white-box diagnostic
    rows = []
    for obs_norm in OBSERVABLE_NORMALIZATIONS:
        for model in frozen_models(observable_normalization=obs_norm):
            coeffs = _method_coefficients(model)
            for resource_name, kappas in resource_definitions(model.inst.n).items():
                laws = {
                    name: MethodLaw(
                        name=name,
                        b2=vals["b2"],
                        s=kappas[name] * vals["v_tilde"],
                        C=0.0,
                    )
                    for name, vals in coeffs.items()
                }
                for method_a, method_b in PAIRS:
                    cert = certified_crossing(laws[method_a], laws[method_b])
                    lower_bias_method = (
                        method_a if laws[method_a].b2 <= laws[method_b].b2 else method_b
                    )
                    rows.append({
                        "instance_id": model.inst.name,
                        "noise_strength": P_FIXED,
                        "copies_M": M_COPIES,
                        "observable_normalization": obs_norm,
                        "resource_definition": resource_name,
                        "method_pair": f"{method_a}_vs_{method_b}",
                        "method_a": method_a,
                        "method_b": method_b,
                        "kappa_vd": kappas["vd"],
                        "kappa_sv": kappas["sv"],
                        "kappa_unmitigated": kappas["unmitigated"],
                        "b2_a": laws[method_a].b2,
                        "s_a": laws[method_a].s,
                        "b2_b": laws[method_b].b2,
                        "s_b": laws[method_b].s,
                        "lower_bias_method": lower_bias_method,
                        "g_bias_gap": cert.g,
                        "delta_s_lower_minus_other": cert.delta_s,
                        "has_leading_crossing": int(cert.R0 is not None),
                        "leading_R0": float(cert.R0) if cert.R0 is not None else 0.0,
                        "leading_regime": _leading_regime(cert.regime),
                        "winner_large_R": cert.winner_large_R or "none",
                    })
    return write_csv(Path(outdir) / "e7_resource_observable_sensitivity.csv", FIELDS, rows)


def _method_coefficients(model):
    vd = model.vd(P_FIXED, M_COPIES)
    sv = model.sv(P_FIXED)
    unmitigated = model.unmitigated(P_FIXED)
    return {
        "vd": {"b2": vd["b_VD"] ** 2, "v_tilde": vd["v_tilde_VD"]},
        "sv": {"b2": sv["b_SV"] ** 2, "v_tilde": sv["v_tilde_SV"]},
        "unmitigated": {
            "b2": unmitigated["b_0"] ** 2,
            "v_tilde": unmitigated["v_tilde_0"],
        },
    }


def _leading_regime(regime: str) -> str:
    if regime == "certified_crossing":
        return "leading_crossing"
    return regime


if __name__ == "__main__":
    print(run("results", mode="fast"))
