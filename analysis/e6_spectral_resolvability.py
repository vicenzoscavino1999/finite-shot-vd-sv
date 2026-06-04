"""Post-E6 spectral resolvability diagnostic for P8.

This is an additive diagnostic layer. It does not change E6, adjudication,
frozen manifests, or confirmatory outputs. Its purpose is to distinguish the
frozen lambda1-vs-lambda2 gap criterion from the lambda2-vs-lambda3 isolation
needed for a clean single-exponential copy-leakage regime.
"""

from __future__ import annotations

import csv
import math
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from experiments._common import frozen_models  # noqa: E402
from vd_sv.density_matrix import ordered_eigenvalues  # noqa: E402

LAMBDA2_TABLE = REPO_ROOT / "results" / "frozen" / "lambda2_gap_table.csv"
E6_REPORT = REPO_ROOT / "results" / "secondary" / "e6_copy_log_scale_report.md"
REPORT_PATH = REPO_ROOT / "analysis" / "e6_spectral_resolvability_report.md"

LAMBDA2_ISOLATION_THRESHOLD = 0.1
D_M_FLOOR = 1e-3
B_PATH = np.asarray([1e2, 1e4, 1e6, 1e8, 1e10, 1e12], dtype=np.float64)
REPRESENTATIVE_P_TARGETS = [0.01, 0.1, 0.25]


@dataclass(frozen=True)
class SpectralRow:
    instance_id: str
    p: float
    lambda1: float
    lambda2: float
    lambda3: float
    lambda4: float
    frozen_relative_gap: float
    lambda2_isolation_gap: float
    lambda3_over_lambda2: float
    lambda4_over_lambda2: float
    e6_candidate: bool


@dataclass(frozen=True)
class MStarPath:
    p: float
    m_max: int
    slope_predicted: float
    mstar_path: list[int]
    unique_mstar_count: int


def main() -> int:
    frozen_rows = _read_csv(LAMBDA2_TABLE)
    models = {model.inst.name: model for model in frozen_models()}
    spectral_rows = _spectral_rows(frozen_rows, models)
    candidate_id = _candidate_instance(frozen_rows)
    selected = _selected_e6_row(spectral_rows, candidate_id)
    representative_rows = _representative_candidate_rows(spectral_rows, candidate_id)
    mstar_paths = [
        _mstar_path(models[candidate_id], row.p, row.lambda2)
        for row in representative_rows
    ]
    REPORT_PATH.write_text(
        _render_report(
            spectral_rows=spectral_rows,
            candidate_id=candidate_id,
            selected=selected,
            representative_rows=representative_rows,
            mstar_paths=mstar_paths,
        ),
        encoding="utf-8",
    )
    print(REPORT_PATH)
    return 0


def _spectral_rows(frozen_rows: list[dict], models: dict) -> list[SpectralRow]:
    rows: list[SpectralRow] = []
    max_l1_diff = 0.0
    max_l2_diff = 0.0
    for row in frozen_rows:
        model = models[row["instance_id"]]
        p = float(row["noise_strength"])
        eig = ordered_eigenvalues(model.rho_p(p))
        lam1 = float(eig[0])
        lam2 = float(eig[1])
        lam3 = float(eig[2]) if eig.size > 2 else 0.0
        lam4 = float(eig[3]) if eig.size > 3 else 0.0
        max_l1_diff = max(max_l1_diff, abs(lam1 - float(row["lambda1"])))
        max_l2_diff = max(max_l2_diff, abs(lam2 - float(row["lambda2"])))
        lambda2_gap = (lam2 - lam3) / lam2 if lam2 > 0 else float("nan")
        rows.append(
            SpectralRow(
                instance_id=row["instance_id"],
                p=p,
                lambda1=lam1,
                lambda2=lam2,
                lambda3=lam3,
                lambda4=lam4,
                frozen_relative_gap=float(row["relative_gap"]),
                lambda2_isolation_gap=lambda2_gap,
                lambda3_over_lambda2=lam3 / lam2 if lam2 > 0 else float("nan"),
                lambda4_over_lambda2=lam4 / lam2 if lam2 > 0 else float("nan"),
                e6_candidate=row["e6_candidate"].strip().lower() == "yes",
            )
        )
    if max_l1_diff > 5e-13 or max_l2_diff > 5e-13:
        raise SystemExit(
            "spectral replay mismatch against lambda2_gap_table.csv: "
            f"max lambda1 diff={max_l1_diff:.3e}, max lambda2 diff={max_l2_diff:.3e}"
        )
    return rows


def _candidate_instance(frozen_rows: list[dict]) -> str:
    candidates = sorted({row["instance_id"] for row in frozen_rows if row["e6_candidate"] == "yes"})
    if len(candidates) != 1:
        raise SystemExit(f"expected exactly one E6 candidate instance, found {candidates}")
    return candidates[0]


def _selected_e6_row(rows: list[SpectralRow], candidate_id: str) -> SpectralRow:
    candidate_rows = [row for row in rows if row.instance_id == candidate_id]
    return max(candidate_rows, key=lambda row: row.frozen_relative_gap)


def _representative_candidate_rows(rows: list[SpectralRow], candidate_id: str) -> list[SpectralRow]:
    candidate_rows = [row for row in rows if row.instance_id == candidate_id]
    selected: list[SpectralRow] = []
    for target in REPRESENTATIVE_P_TARGETS:
        row = min(candidate_rows, key=lambda item: abs(item.p - target))
        if row not in selected:
            selected.append(row)
    return selected


def _mstar_path(model, p: float, lambda2: float) -> MStarPath:
    copy_values = []
    for m in range(2, 1000):
        coeff = model.vd(p, m)
        d_m = float(coeff["D_M"])
        if d_m < D_M_FLOOR:
            break
        copy_values.append((m, float(coeff["b_VD"]), float(coeff["v_tilde_VD"])))
    if not copy_values:
        raise SystemExit(f"no valid copies for {model.inst.name} p={p}")
    m_values = np.asarray([item[0] for item in copy_values], dtype=np.int64)
    b_values = np.asarray([item[1] for item in copy_values], dtype=np.float64)
    v_values = np.asarray([item[2] for item in copy_values], dtype=np.float64)
    mse = b_values[:, None] ** 2 + v_values[:, None] / B_PATH[None, :]
    winner = np.argmin(mse, axis=0)
    mstar = [int(value) for value in m_values[winner]]
    return MStarPath(
        p=p,
        m_max=int(m_values.max()),
        slope_predicted=1.0 / (2.0 * abs(math.log(lambda2))),
        mstar_path=mstar,
        unique_mstar_count=len(set(mstar)),
    )


def _render_report(
    spectral_rows: list[SpectralRow],
    candidate_id: str,
    selected: SpectralRow,
    representative_rows: list[SpectralRow],
    mstar_paths: list[MStarPath],
) -> str:
    all_gaps = np.asarray([row.lambda2_isolation_gap for row in spectral_rows], dtype=np.float64)
    candidate_rows = [row for row in spectral_rows if row.instance_id == candidate_id]
    candidate_gaps = np.asarray([row.lambda2_isolation_gap for row in candidate_rows], dtype=np.float64)
    isolated_all = int(np.sum(all_gaps >= LAMBDA2_ISOLATION_THRESHOLD))
    isolated_candidate = int(np.sum(candidate_gaps >= LAMBDA2_ISOLATION_THRESHOLD))
    best_candidate = max(candidate_rows, key=lambda row: row.lambda2_isolation_gap)

    lines = [
        "# E6 Spectral Resolvability Diagnostic",
        "",
        "Status: post_E6_diagnostic_only. Not a gate, not an adjudication, not a freeze.",
        "",
        "This diagnostic leaves E6 and all frozen artifacts unchanged. It checks whether the pre-frozen lambda2 gap criterion used for E6 selection also provides the lambda2-vs-lambda3 isolation needed for a clean single-exponential copy-leakage regime.",
        "",
        "## Existing E6 Selection",
        "",
        "| instance | selected p | frozen relative gap (lambda1-lambda2)/lambda1 | lambda2 | lambda3 | (lambda2-lambda3)/lambda2 | lambda3/lambda2 | isolation status |",
        "|---|---:|---:|---:|---:|---:|---:|---|",
        _spectral_table_row(selected),
        "",
        "Interpretation: the frozen criterion confirms lambda1 dominance over lambda2. P8 additionally needs the subdominant leakage to be effectively single-mode, which is probed by lambda2 isolation from lambda3.",
        "",
        "## Candidate Instance Representative p Values",
        "",
        f"B path for M*(B): {', '.join(f'{b:.0e}' for b in B_PATH)}.",
        "",
        "| p | lambda1 | lambda2 | lambda3 | lambda4 | lambda3/lambda2 | lambda4/lambda2 | lambda2 isolation gap | M_max | predicted slope | M*(B) path | unique M* |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|",
    ]
    path_by_p = {path.p: path for path in mstar_paths}
    for row in representative_rows:
        path = path_by_p[row.p]
        lines.append(
            f"| {row.p:.6g} | {row.lambda1:.6g} | {row.lambda2:.6g} | "
            f"{row.lambda3:.6g} | {row.lambda4:.6g} | {row.lambda3_over_lambda2:.3f} | "
            f"{row.lambda4_over_lambda2:.3f} | {row.lambda2_isolation_gap:.3f} | "
            f"{path.m_max} | {path.slope_predicted:.6g} | "
            f"{', '.join(str(m) for m in path.mstar_path)} | {path.unique_mstar_count} |"
        )
    lines.extend([
        "",
        "## Ensemble-Wide Isolation Summary",
        "",
        f"Diagnostic isolation threshold: `(lambda2-lambda3)/lambda2 >= {LAMBDA2_ISOLATION_THRESHOLD:g}`. This threshold is not a frozen gate; it is a scale-matched diagnostic for the missing theorem precondition.",
        "",
        "| scope | rows | isolated rows | min gap | median gap | max gap | best row |",
        "|---|---:|---:|---:|---:|---:|---|",
        (
            f"| full frozen lambda2 table | {len(spectral_rows)} | {isolated_all} | "
            f"{float(np.min(all_gaps)):.3f} | {float(np.median(all_gaps)):.3f} | "
            f"{float(np.max(all_gaps)):.3f} | {_best_row_label(max(spectral_rows, key=lambda row: row.lambda2_isolation_gap))} |"
        ),
        (
            f"| E6 candidate `{candidate_id}` | {len(candidate_rows)} | {isolated_candidate} | "
            f"{float(np.min(candidate_gaps)):.3f} | {float(np.median(candidate_gaps)):.3f} | "
            f"{float(np.max(candidate_gaps)):.3f} | {_best_row_label(best_candidate)} |"
        ),
        "",
        "## Conclusion",
        "",
        (
            "The E6 not_resolvable result is best explained as an operational-regime issue, "
            "not as a primary theory/code failure. The frozen selection rule optimized "
            "`(lambda1-lambda2)/lambda1`, but the clean P8 slope requires lambda2 to be "
            "isolated from lambda3. For the selected E6 p, lambda3 is close to lambda2, "
            "and M*(B) does not traverse enough copy numbers to estimate the predicted "
            "logarithmic slope. Higher p values improve lambda2 isolation somewhat, but "
            "the compact B path still shows at most a small number of integer steps."
        ),
        "",
        "Recommended framing: report P8 as a secondary descriptive endpoint that is not resolvable for the frozen E6 selection because the chosen row satisfies the frozen lambda1-dominance criterion but not the stronger lambda2-isolation condition. The ensemble-wide table is diagnostic only; using it to reselect an instance or p after observing E6 would be exploratory. A clean demonstration of the P8 law would require a separate toy/supplemental example with deliberately isolated lambda2, marked as illustrative rather than confirmatory.",
    ])
    if E6_REPORT.exists():
        lines.extend([
            "",
            f"Linked E6 output: `{E6_REPORT.as_posix()}`.",
        ])
    return "\n".join(lines) + "\n"


def _spectral_table_row(row: SpectralRow) -> str:
    status = (
        "isolated"
        if row.lambda2_isolation_gap >= LAMBDA2_ISOLATION_THRESHOLD
        else "near-degenerate"
    )
    return (
        f"| {row.instance_id} | {row.p:.6g} | {row.frozen_relative_gap:.3f} | "
        f"{row.lambda2:.6g} | {row.lambda3:.6g} | {row.lambda2_isolation_gap:.3f} | "
        f"{row.lambda3_over_lambda2:.3f} | {status} |"
    )


def _best_row_label(row: SpectralRow) -> str:
    return f"{row.instance_id}@p={row.p:.6g} gap={row.lambda2_isolation_gap:.3f}"


def _read_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


if __name__ == "__main__":
    raise SystemExit(main())
