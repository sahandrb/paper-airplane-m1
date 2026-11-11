"""Nose rotation about the CG. No window."""

from pathlib import Path

import pytest

from paper_airplane.sprite_geometry import (
    alpha_centroid,
    anchor_screen_position,
    clamp_sprite_center_y,
    pivoted_center,
    rail_seat_offset,
    rotate_offset,
)


def test_level_rail_lifts_the_blit_and_the_horizon_holds_the_sprite() -> None:
    shift = rail_seat_offset(0.0, 18.0)
    assert shift[0] == pytest.approx(0.0)
    assert shift[1] == pytest.approx(-(9.0 + 10.0))
    assert shift[1] < 0.0
    held = clamp_sprite_center_y(540.0, 30.0, 548.0)
    assert held == pytest.approx(548.0 - 15.0)
    assert held + 15.0 <= 548.0
    clear = clamp_sprite_center_y(400.0, 30.0, 548.0)
    assert clear == pytest.approx(400.0)


def test_positive_theta_raises_a_right_pointing_nose() -> None:
    assert rotate_offset(1.0, 0.0, 0.0) == pytest.approx((1.0, 0.0))
    raised = rotate_offset(1.0, 0.0, 90.0)
    assert raised[1] < 0.0
    assert raised[0] == pytest.approx(0.0, abs=1e-9)
    lowered = rotate_offset(1.0, 0.0, -90.0)
    assert lowered[1] > 0.0
    assert lowered[0] == pytest.approx(0.0, abs=1e-9)


def test_nose_stays_right_of_the_cg_at_zero_and_above_it_at_ninety() -> None:
    nose_from_cg = (60.0, 0.0)
    level = rotate_offset(*nose_from_cg, 0.0)
    above = rotate_offset(*nose_from_cg, 90.0)
    below = rotate_offset(*nose_from_cg, -90.0)
    assert level[0] > 0.0
    assert above[1] < 0.0
    assert below[1] > 0.0


def test_cg_screen_position_does_not_change_with_theta() -> None:
    cg_screen = (400.0, 300.0)
    size = (110.0, 28.9)
    cg_px = (45.0, 14.2)
    for angle in (0.0, 20.0, 90.0, -90.0, 180.0):
        center = pivoted_center(cg_screen, size, cg_px, angle)
        found = anchor_screen_position(center, size, cg_px, angle)
        assert found == pytest.approx(cg_screen)


def test_alpha_centroid_is_the_mean_of_opaque_pixels() -> None:
    mask = __import__("numpy").zeros((6, 4))
    mask[1, 0] = 20
    mask[3, 0] = 20
    mask[1, 2] = 20
    assert alpha_centroid(mask) == pytest.approx((5.0 / 3.0, 2.0 / 3.0))


def test_geometry_module_does_not_smooth_or_import_pygame() -> None:
    text = Path(__file__).resolve().parents[1].joinpath(
        "src", "paper_airplane", "sprite_geometry.py"
    ).read_text(encoding="utf-8")
    assert "pygame" not in text
    assert "smooth_display_angle" not in text
