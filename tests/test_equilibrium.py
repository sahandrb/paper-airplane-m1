"""Section 12.1 equilibrium glide."""

import pytest

from paper_airplane.equilibrium import (
    alpha_star_deg,
    alpha_star_rad,
    gamma_star_deg,
    gamma_star_rad,
    v_star,
    v_star_from_lift_balance,
    v_star_from_vertical_balance,
)


def test_equilibrium_state() -> None:
    assert v_star() == pytest.approx(3.54937084251753, abs=1e-12)
    assert gamma_star_rad() == pytest.approx(-0.179433441298775, abs=1e-12)
    assert gamma_star_deg() == pytest.approx(-10.2807788899282, abs=1e-12)
    assert alpha_star_rad() == pytest.approx(0.170472011882708, abs=1e-12)
    assert alpha_star_deg() == pytest.approx(9.76732680598316, abs=1e-12)


def test_the_two_speed_formulas_agree() -> None:
    vertical = v_star_from_vertical_balance()
    lift = v_star_from_lift_balance()
    assert vertical == pytest.approx(lift, abs=1e-15)
    assert v_star() == vertical
