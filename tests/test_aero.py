"""Section 12.1 coefficients and Section 12.2 geometry."""

import inspect

import pytest

from paper_airplane import aero
from paper_airplane.config import DEFAULT_CONFIG


def test_homework_pi_is_not_numpy_pi() -> None:
    source = inspect.getsource(aero)
    assert "numpy.pi" not in source
    assert "math.pi" not in source
    assert DEFAULT_CONFIG.pi_homework == 3.141592


def test_coefficients_match_the_homework_table() -> None:
    assert aero.cla() == pytest.approx(1.29362167202453, abs=1e-12)
    assert aero.epsilon() == pytest.approx(0.411253168483586, abs=1e-12)
    assert aero.cl_star() == pytest.approx(0.220526289045093, abs=1e-12)
    assert aero.cd_star() == pytest.approx(0.04, abs=1e-15)
    assert aero.cd_star() == pytest.approx(2.0 * DEFAULT_CONFIG.cd0, abs=1e-15)
    assert aero.ld_max() == pytest.approx(5.51315722612733, abs=1e-12)


def test_geometry() -> None:
    assert aero.span_m() == pytest.approx(0.120913192001535, abs=1e-12)
    assert aero.mean_chord_m() == pytest.approx(0.140596734885506, abs=1e-12)
