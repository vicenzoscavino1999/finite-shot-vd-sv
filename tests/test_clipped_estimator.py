"""The clipped quotient matches the ordinary quotient once B >= B_den (the clip
activates only on the exponentially rare bad-denominator event)."""

import numpy as np

from vd_sv import vd as vd_mod
from vd_sv.estimators import make_rng


def test_clip_inactive_above_bden(model):
    vc = model.vd(0.1, 2)
    big_b = int(vc["B_den"] * 5) + 1000
    clipped = vd_mod.sample_vd_quotient(vc["N_M"], vc["D_M"], big_b, 2000, make_rng(9))
    ordinary = vd_mod.sample_vd_quotient(vc["N_M"], vc["D_M"], big_b, 2000, make_rng(9), clip=False)
    # identical except on the (here essentially empty) clip-active event
    assert np.mean(np.abs(clipped - ordinary) > 1e-12) < 0.01
