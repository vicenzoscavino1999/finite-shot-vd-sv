"""Finite-shot operating windows for virtual distillation (VD) and symmetry
verification (SV) -- Level 1 white-box reproduction package.

The Level 1 core is exact density-matrix simulation in plain NumPy/SciPy. It has
no Qiskit dependency: the closed-form coefficients (delta_VD, delta_SV, c_SV = 0)
and the operating-window crossing diagnostics can be reproduced without any
quantum-cloud account.

Module map (mirrors the theory anchors in paper/main.tex):

- density_matrix : exact density-matrix engine, operators, spectra, rho^M
- qaoa           : XY-mixer QAOA on a fixed Hamming-weight sector; H_C, projector P
- noise          : one-parameter noise channels; rho_p and Delta = L(rho_star)
- coefficients   : closed-form b, c, v, delta_VD, delta_SV (white-box ground truth)
- estimators     : finite-shot sampling + clipped quotient estimator
- vd             : controlled-derangement / Hadamard-test sampling for VD
- sv             : Hamming-weight postselection sampling for SV
- crossing       : crossing classification and eta = 4C/(g R0^2) diagnostics
- lecam          : two-point (Le Cam) lower bound, Bernoulli Fisher information
"""

__version__ = "0.1.0"
