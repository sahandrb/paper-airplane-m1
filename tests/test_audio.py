"""Airflow mix. These tests do not open the mixer."""

import pytest

from paper_airplane.app.audio import audio_levels


def test_still_air_keeps_only_the_low_loop_at_the_floor() -> None:
    low, high = audio_levels(0.0, 3.55)
    assert low == pytest.approx(0.12)
    assert high == pytest.approx(0.0)


def test_three_v_star_is_the_high_loop_alone() -> None:
    v_star = 3.55
    low, high = audio_levels(3.0 * v_star, v_star)
    assert low == pytest.approx(0.0)
    assert high == pytest.approx(0.9)


def test_faster_than_the_reference_stays_clamped() -> None:
    v_star = 3.55
    assert audio_levels(100.0, v_star) == pytest.approx(audio_levels(3.0 * v_star, v_star))
