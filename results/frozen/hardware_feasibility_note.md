# Level 3 Hardware Feasibility Note

Status: pap_freeze_ready.

Level 3 hardware execution is outside the Phase A confirmatory scope. The
confirmatory claims for this freeze are carried by the Level 1 white-box path:
closed-form coefficient validation for `delta_VD`, `delta_SV`, `c_SV = 0`, and
the Level 1 crossing diagnostics defined in the PAP.

The Phase A compute budget records Level 3 as `omitido`, with zero hardware
instances, grids, shots, and wall-time. This is an explicit design decision, not
a data-dependent exclusion. No Phase A adjudication criterion depends on a
hardware job, hardware queue state, or post-freeze calibration outcome.

Level 3 is deferred to Phase B as analysis-from-counts. If hardware data are
added in Phase B, the reproducible artifact is the analysis applied to archived
raw counts and calibration snapshots; the quantum device is not re-executed as
part of the reproduction contract. Any Phase B hardware figure is a feasibility
or robustness demonstration and does not validate the Level 1 coefficient
claims.
