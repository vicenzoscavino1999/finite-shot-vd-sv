# Level 2 Foundation

Status: Level 2 foundation (Phase B robustness layer). Trotterized gate-level circuit; ideal reference is its own noiseless state, not Level 1. Additive layer, does not modify any frozen/hashed artifact.

## Circuit And Ordering

- Initial state: Qiskit `StatePreparation` of the Dicke vector `|D^n_k>`.
- Cost convention: `RZZGate(theta)=exp(-i theta ZZ/2)`, so each cost edge uses `theta=2*gamma*w`.
- Mixer convention: `XXPlusYYGate(theta,0)=exp(-i theta(XX+YY)/4)`, so each Trotter substep uses `theta=4*beta/s`.
- Mixer Trotter substeps per QAOA layer: `1` (realistic gate-level default).
- Optional high-fidelity diagnostic substeps: `128` (not a realistic noisy-circuit depth).
- Ordering: Level 1 is big-endian; Qiskit statevectors are little-endian. Logical qubit labels are kept the same and statevectors are bit-reversed for comparison.

## Noiseless Cross-Check

- Max sector leakage: `2.694e-27` with tolerance `1.0e-10`.
- Max `|mu_L2-mu_L1|` at realistic depth: `0.214093`. This is informative only, not a PASS/FAIL gate.
- Optional high-fidelity max `|mu_L2-mu_L1|`: `0.00766977` at `128` substeps.

| instance | n | k | engine | substeps | mu_L1 | mu_L2 | abs gap | sector leakage | in-sector | gap status |
|---|---:|---:|---|---:|---:|---:|---:|---:|---|---|
| g6_k2_c000 | 6 | 2 | aer | 1 | -0.241379902392 | -0.243431939047 | 0.00205204 | 1.780e-29 | PASS | informative_only |
| g6_k2_c001 | 6 | 2 | aer | 1 | -0.268202493567 | -0.187546088705 | 0.0806564 | 1.698e-29 | PASS | informative_only |
| g6_k2_c002 | 6 | 2 | aer | 1 | -0.289773777963 | -0.0756811869483 | 0.214093 | 1.613e-29 | PASS | informative_only |
| g6_k2_c003 | 6 | 2 | aer | 1 | -0.26333447264 | -0.0702553946486 | 0.193079 | 1.746e-29 | PASS | informative_only |
| g6_k2_c004 | 6 | 2 | aer | 1 | -0.239207703119 | -0.0459785241752 | 0.193229 | 1.685e-29 | PASS | informative_only |
| g8_k3_c000 | 8 | 3 | aer | 1 | -0.15369090421 | -0.0668269693964 | 0.0868639 | 2.692e-27 | PASS | informative_only |
| g8_k3_c001 | 8 | 3 | aer | 1 | -0.172105059618 | -0.0714285714286 | 0.100676 | 2.651e-27 | PASS | informative_only |
| g8_k3_c002 | 8 | 3 | aer | 1 | -0.130001830242 | -0.122131009802 | 0.00787082 | 2.694e-27 | PASS | informative_only |
| g8_k3_c003 | 8 | 3 | aer | 1 | -0.128983285317 | -0.0952735377535 | 0.0337097 | 2.684e-27 | PASS | informative_only |
| g8_k3_c004 | 8 | 3 | aer | 1 | -0.188909904802 | -0.119064875119 | 0.069845 | 2.690e-27 | PASS | informative_only |

## Noise Model Snapshot

- Backend label: `AerSyntheticThermalReadoutV1`.
- Source: Manual qiskit_aer.noise snapshot because the installed [level2] extra exposes no FakeBackendV2 provider.
- Seed simulator: `20260604`.
- Basis gates: `['cx', 'id', 'rz', 'sx', 'u']`.
- Noise instructions: `['cx', 'measure', 'u']`.
- Includes readout error: `True`.

This step only establishes the circuit, noiseless Level 2 reference, ordering cross-check, and loadable Aer noise model. It does not implement noisy sampling, folding, readout mitigation, or Level 2 E5/E7/E12 experiments.
