"""Same seed -> identical Level 1 experiment output (RNG-heavy E7 and white-box E3)."""

from pathlib import Path

from experiments import e3_delta_vd_generator as e3
from experiments import e5_denominator_concentration as e5
from experiments import e7_certified_crossing as e7


def test_e7_deterministic(tmp_path):
    a = e7.run(tmp_path / "a", mode="fast")
    b = e7.run(tmp_path / "b", mode="fast")
    assert Path(a).read_text(encoding="utf-8") == Path(b).read_text(encoding="utf-8")


def test_e3_deterministic(tmp_path):
    a = e3.run(tmp_path / "a", mode="fast")
    b = e3.run(tmp_path / "b", mode="fast")
    assert Path(a).read_text(encoding="utf-8") == Path(b).read_text(encoding="utf-8")


def test_e5_deterministic(tmp_path):
    a = e5.run(tmp_path / "a", mode="fast")
    b = e5.run(tmp_path / "b", mode="fast")
    assert Path(a).read_text(encoding="utf-8") == Path(b).read_text(encoding="utf-8")
