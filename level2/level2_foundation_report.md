# Level 2 Foundation

Status: Level 2 foundation (Phase B robustness layer). Trotterized gate-level circuit; ideal reference is its own noiseless state, not Level 1. Additive layer, does not modify any frozen/hashed artifact.

## Circuit And Ordering

- Initial state: Qiskit `StatePreparation` of the Dicke vector `|D^n_k>`.
- Cost convention: `RZZGate(theta)=exp(-i theta ZZ/2)`, so each cost edge uses `theta=2*gamma*w`.
- Mixer convention: `XXPlusYYGate(theta,0)=exp(-i theta(XX+YY)/4)`, so each Trotter substep uses `theta=4*beta/s`.
- Mixer Trotter substeps per QAOA layer: `128`.
- Ordering: Level 1 is big-endian; Qiskit statevectors are little-endian. Logical qubit labels are kept the same and statevectors are bit-reversed for comparison.

## Noiseless Cross-Check

- Max sector leakage: `5.252e-27` with tolerance `1.0e-10`.
- Max `|mu_L2-mu_L1|`: `0.00766977` with tolerance `1.0e-02`.

| instance | n | k | engine | mu_L1 | mu_L2 | abs gap | sector leakage | in-sector | gap |
|---|---:|---:|---|---:|---:|---:|---:|---|---|
| g6_k2_c000 | 6 | 2 | aer | -0.241379902392 | -0.241506822514 | 0.00012692 | 1.146e-27 | PASS | PASS |
| g6_k2_c001 | 6 | 2 | aer | -0.268202493567 | -0.260532722115 | 0.00766977 | 1.223e-28 | PASS | PASS |
| g6_k2_c002 | 6 | 2 | aer | -0.289773777963 | -0.288167987906 | 0.00160579 | 5.724e-28 | PASS | PASS |
| g6_k2_c003 | 6 | 2 | aer | -0.26333447264 | -0.266455046328 | 0.00312057 | 1.261e-28 | PASS | PASS |
| g6_k2_c004 | 6 | 2 | aer | -0.239207703119 | -0.23744967787 | 0.00175803 | 7.539e-28 | PASS | PASS |
| g8_k3_c000 | 8 | 3 | aer | -0.15369090421 | -0.153929900487 | 0.000238996 | 5.252e-27 | PASS | PASS |
| g8_k3_c001 | 8 | 3 | aer | -0.172105059618 | -0.174715623767 | 0.00261056 | 2.401e-27 | PASS | PASS |
| g8_k3_c002 | 8 | 3 | aer | -0.130001830242 | -0.129980081484 | 2.17488e-05 | 5.025e-27 | PASS | PASS |
| g8_k3_c003 | 8 | 3 | aer | -0.128983285317 | -0.129096905024 | 0.00011362 | 4.382e-27 | PASS | PASS |
| g8_k3_c004 | 8 | 3 | aer | -0.188909904802 | -0.188190536719 | 0.000719368 | 3.691e-27 | PASS | PASS |

## Noise Model Snapshot

- Backend label: `AerSyntheticThermalReadoutV1`.
- Source: Manual qiskit_aer.noise snapshot because the installed [level2] extra exposes no FakeBackendV2 provider.
- Seed simulator: `20260604`.
- Basis gates: `['cx', 'id', 'rz', 'sx', 'u']`.
- Noise instructions: `['cx', 'measure', 'u']`.
- Includes readout error: `True`.

This step only establishes the circuit, noiseless Level 2 reference, ordering cross-check, and loadable Aer noise model. It does not implement noisy sampling, folding, readout mitigation, or Level 2 E5/E7/E12 experiments.
