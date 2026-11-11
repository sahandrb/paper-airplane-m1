"""Section 12.3 Reference cases, Section 12.4 landings, and the range grid."""

import math

import numpy as np
import pytest

from paper_airplane.aero import ld_max
from paper_airplane.config import DEFAULT_CONFIG
from paper_airplane.equilibrium import gamma_star_rad, v_star
from paper_airplane.simulation import (
    cases_abcd,
    integrate_physical,
    monte_carlo,
    preview,
    range_heatmap,
)

_FINALS = {
    "a": (3.54937084, -0.17943344, -1.80078285, 20.95431343),
    "b": (3.55406177, -0.180656, -1.75113483, 20.82484652),
    "c": (3.54499023, -0.18894738, -1.13747005, 20.56742542),
    "d": (3.59308599, 6.07663869, -0.33072098, 17.36450918),
}


def test_case_a_stays_on_the_equilibrium_glide() -> None:
    flight = cases_abcd()["a"]
    assert np.max(np.abs(flight.v - v_star())) < 1e-10
    assert np.max(np.abs(flight.gamma - gamma_star_rad())) < 1e-12


def test_reference_final_states() -> None:
    flights = cases_abcd()
    for name, expected in _FINALS.items():
        flight = flights[name]
        actual = (flight.v[-1], flight.gamma[-1], flight.h[-1], flight.r[-1])
        assert actual == pytest.approx(expected, abs=5e-6)


def test_case_d_loops_and_every_case_keeps_speed() -> None:
    flights = cases_abcd()
    assert float(np.max(flights["d"].gamma)) > 2.0 * math.pi
    assert float(np.max(flights["d"].h)) == pytest.approx(4.42279, abs=1e-3)
    for flight in flights.values():
        assert float(np.min(flight.v)) > 2.0


def _landing(speed: float, gamma: float):
    return integrate_physical(
        speed,
        gamma,
        rtol=DEFAULT_CONFIG.physical_rtol,
        atol=DEFAULT_CONFIG.physical_atol,
    )


def test_physical_landings() -> None:
    speed = v_star()
    glide = gamma_star_rad()
    case_a = _landing(speed, glide)
    assert case_a.h[-1] == 0.0
    assert case_a.t[-1] == pytest.approx(3.15724430361, abs=5e-4)
    assert case_a.r[-1] == pytest.approx(11.02631445225, abs=5e-4)
    assert case_a.r[-1] == pytest.approx(DEFAULT_CONFIG.h0_m * ld_max(), abs=1e-8)
    assert case_a.t[-1] == pytest.approx(
        -DEFAULT_CONFIG.h0_m / (speed * math.sin(glide)),
        abs=1e-8,
    )

    case_b = _landing(speed, 0.0)
    assert case_b.t[-1] == pytest.approx(3.224730, abs=5e-4)
    assert case_b.r[-1] == pytest.approx(11.142685, abs=5e-4)
    assert case_b.h[-1] == 0.0

    case_c = _landing(1.5 * speed, 0.0)
    assert case_c.t[-1] == pytest.approx(4.241136, abs=5e-4)
    assert case_c.r[-1] == pytest.approx(14.419941, abs=5e-4)
    assert float(np.max(case_c.h)) == pytest.approx(2.647747, abs=5e-4)

    case_d = _landing(3.0 * speed, 0.0)
    assert case_d.t[-1] == pytest.approx(5.549812, abs=5e-4)
    assert case_d.r[-1] == pytest.approx(15.813362, abs=5e-4)
    assert float(np.max(case_d.h)) == pytest.approx(4.422791, abs=5e-4)
    assert case_d.h[-1] == 0.0


def test_preview_uses_the_mode_termination() -> None:
    speed = v_star()
    glide = gamma_star_rad()
    reference = preview(speed, glide, mode="reference")
    physical = preview(speed, glide, mode="physical")
    assert reference.t[-1] == pytest.approx(DEFAULT_CONFIG.tf_s)
    assert reference.h[-1] < 0.0
    assert physical.h[-1] == 0.0
    assert physical.terminated_by == "ground"


def test_monte_carlo_is_one_summary() -> None:
    result = monte_carlo(v_star(), gamma_star_rad(), n=2, rng=np.random.default_rng(1))
    assert len(result.trajectories) == 2
    assert result.speed_collapse_count >= 0
    assert result.assumption.startswith("Assumption:")


def test_heatmap_peak_is_near_the_survey() -> None:
    grid = range_heatmap()
    assert grid.range_m.shape == (DEFAULT_CONFIG.heatmap_n_g, DEFAULT_CONFIG.heatmap_n_v)
    index = int(np.nanargmax(grid.range_m))
    row, column = np.unravel_index(index, grid.range_m.shape)
    peak = float(grid.range_m[row, column])
    speed = float(grid.v0_m_s[column])
    gamma_deg = float(np.rad2deg(grid.gamma0_rad[row]))
    assert peak == pytest.approx(16.0, rel=0.04)
    assert speed == pytest.approx(9.4, abs=1.0)
    assert gamma_deg == pytest.approx(-8.0, abs=4.0)
