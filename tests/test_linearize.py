"""Section 12.5 linear phugoid."""

import math

import numpy as np
import pytest

from paper_airplane.dynamics import rhs
from paper_airplane.equilibrium import gamma_star_rad, v_star
from paper_airplane.linearize import (
    damping_ratio,
    eigenvalues_at_eq,
    hybrid_path,
    jacobian_at_eq,
    lanchester_period_s,
    linear_period_s,
    linear_state,
)
from paper_airplane.simulation import integrate_reference

_J = np.array(
    [
        [-0.985541970605702, -9.64266066331038],
        [1.53081998978802, -0.492770985302851],
    ]
)


def test_jacobian_and_eigenvalues() -> None:
    assert jacobian_at_eq() == pytest.approx(_J, abs=1e-9)
    values = eigenvalues_at_eq()
    assert np.real(values) == pytest.approx(-0.739156477954277, abs=1e-7)
    assert np.max(np.abs(np.imag(values))) == pytest.approx(3.83411944090805, abs=1e-7)
    assert linear_period_s() == pytest.approx(1.63875575709543, abs=1e-6)
    assert damping_ratio() == pytest.approx(0.18929829015866, abs=1e-6)
    assert lanchester_period_s() == pytest.approx(1.60912644463448, abs=1e-9)


def test_equilibrium_vector_field_is_zero() -> None:
    rates = rhs(0.0, np.array([v_star(), gamma_star_rad(), 2.0, 0.0]))
    assert rates[0] == pytest.approx(0.0, abs=1e-14)
    assert rates[1] == pytest.approx(0.0, abs=1e-14)


def test_case_b_hybrid_altitude_stays_close() -> None:
    nonlinear = integrate_reference(v_star(), 0.0)
    linear = hybrid_path(0.0, -gamma_star_rad())
    assert linear.t.shape == nonlinear.t.shape
    assert np.max(np.abs(linear.h - nonlinear.h)) < 0.02


def test_case_d_linear_model_does_not_loop() -> None:
    time = np.linspace(0.0, 6.0, 2401)
    _, gamma = linear_state(time, 2.0 * v_star(), -gamma_star_rad())
    assert float(np.max(gamma)) <= 2.0 * math.pi
