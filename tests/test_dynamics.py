"""Right-hand side, speed guard, and the ban on display smoothing."""

import inspect

import numpy as np
import pytest

from paper_airplane import aero, dynamics, energy, equilibrium, linearize, simulation
from paper_airplane.config import DEFAULT_CONFIG
from paper_airplane.dynamics import SpeedTooSmallError, rhs
from paper_airplane.equilibrium import gamma_star_rad, v_star


def test_equilibrium_force_balance_is_stationary() -> None:
    state = np.array([v_star(), gamma_star_rad(), DEFAULT_CONFIG.h0_m, 0.0])
    rates = rhs(0.0, state)
    assert rates[0] == pytest.approx(0.0, abs=1e-14)
    assert rates[1] == pytest.approx(0.0, abs=1e-14)


def test_speed_below_v_eps_raises() -> None:
    state = np.array([0.0, gamma_star_rad(), 1.0, 0.0])
    with pytest.raises(SpeedTooSmallError):
        rhs(0.0, state)
    state[0] = DEFAULT_CONFIG.v_eps_m_s * 0.5
    with pytest.raises(SpeedTooSmallError):
        rhs(0.0, state)


def test_physics_modules_do_not_smooth_pitch_or_import_pygame() -> None:
    modules = (aero, dynamics, energy, equilibrium, linearize, simulation)
    for module in modules:
        assert not hasattr(module, "smooth_display_angle")
        assert "smooth_display_angle" not in inspect.getsource(module)
        assert "pygame" not in module.__dict__
