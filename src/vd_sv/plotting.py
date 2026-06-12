"""Minimal plotting helpers for the anchored Level 1 figures.

matplotlib is an optional dependency (extra ``figures``); imported lazily so the
Level 1 reproduction/verification path never requires it.
"""

from __future__ import annotations

import csv
from pathlib import Path


def _require_mpl():
    try:
        import matplotlib

        matplotlib.use("Agg")
        matplotlib.rcParams.update({
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "font.size": 9,
            "axes.prop_cycle": matplotlib.cycler(
                color=[
                    "#0072B2",  # blue
                    "#D55E00",  # vermillion
                    "#009E73",  # bluish green
                    "#CC79A7",  # reddish purple
                    "#E69F00",  # orange
                    "#56B4E9",  # sky blue
                ]
            ),
        })
        import matplotlib.pyplot as plt

        return plt
    except ImportError as exc:  # pragma: no cover
        raise SystemExit(
            "matplotlib is required for figures: pip install -e .[figures]"
        ) from exc


def load_csv(path: str | Path) -> list[dict]:
    with Path(path).open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _col(rows, name, where=None, cast=float):
    return [cast(r[name]) for r in rows if where is None or where(r)]
