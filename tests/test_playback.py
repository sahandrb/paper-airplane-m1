"""Headless checks for playback, the follow camera, and trail labels."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from paper_airplane.app.camera import follow_camera, prelaunch_camera
from paper_airplane.config import DEFAULT_CONFIG
from paper_airplane.playback import advance_time, cycle_speed, sample_at
from paper_airplane.simulation import Trajectory
from paper_airplane.trails import (
    REFERENCE_NOTE,
    TRAIL_COLOURS,
    Session,
    Trail,
    TrailBook,
    begin_trail,
    cleared,
    legend_line,
    returned,
)


def _path(height: np.ndarray) -> Trajectory:
    zeros = np.zeros(2)
    return Trajectory(
        t=np.array([0.0, 2.0]),
        v=np.array([2.0, 4.0]),
        gamma=np.array([0.0, -0.2]),
        h=height,
        r=np.array([0.0, 10.0]),
        theta=np.array([0.1, -0.1]),
        q_dyn=zeros,
        ke=zeros,
        pe=zeros,
        energy=zeros,
        status="ok",
        terminated_by="tf",
    )


def test_sample_at_interpolates_and_clamps_ground_height() -> None:
    mid = sample_at(_path(np.array([2.0, 0.0])), 1.0)
    assert mid.v == pytest.approx(3.0)
    assert mid.r == pytest.approx(5.0)
    assert mid.h == pytest.approx(1.0)
    assert sample_at(_path(np.array([1e-16, 1e-16])), 1.0).h == 0.0
    assert sample_at(_path(np.array([-1.8, -1.8])), 0.0).h == pytest.approx(-1.8)


def test_advance_time_clamps_and_speed_cycles() -> None:
    assert advance_time(5.9, 0.2, 1.0, 6.0) == pytest.approx(6.0)
    assert advance_time(0.0, 0.1, 4.0, 6.0) == pytest.approx(0.4)
    assert cycle_speed(1.0, 1) == 4.0
    assert cycle_speed(1.0, -1) == 0.25
    assert cycle_speed(0.25, -1) == 4.0


def test_follow_camera_holds_the_cg_fraction_and_the_vertical_margin() -> None:
    config = replace(DEFAULT_CONFIG, camera_tau_s=0.0)
    camera = prelaunch_camera(config)
    followed = follow_camera(camera, 5.0, 2.0, 0.1, config)
    screen_x = followed.cam_x + 5.0 * config.pixels_per_metre
    assert screen_x == pytest.approx(config.follow_x_frac * config.window_width_px)
    assert followed.cam_y == pytest.approx(config.ground_screen_y0)

    high = follow_camera(camera, 0.0, 10.0, 0.1, config)
    screen_y = high.cam_y - 10.0 * config.pixels_per_metre
    assert screen_y == pytest.approx(config.margin_px)


def test_trail_colours_reset_and_restart() -> None:
    book = begin_trail(TrailBook(), 3.0, 0.0, "reference", DEFAULT_CONFIG)
    book = begin_trail(book, 4.0, 1.0, "physical", DEFAULT_CONFIG)
    assert book.trails[0].colour == "#0072BD"
    assert book.trails[1].colour == "#D95319"
    assert tuple(trail.colour for trail in book.trails) == TRAIL_COLOURS[:2]

    session = Session(book=book, speed=4.0, phase="frozen")
    empty = cleared(session)
    assert empty.book.trails == ()
    assert empty.phase == "prelaunch"
    assert empty.speed == 4.0
    kept = returned(session)
    assert kept.book.trails == book.trails
    assert kept.phase == "prelaunch"


def test_overflow_drops_the_oldest_trail() -> None:
    book = TrailBook()
    for index in range(DEFAULT_CONFIG.max_trails + 1):
        book = begin_trail(book, float(index), 0.0, "reference", DEFAULT_CONFIG)
    assert len(book.trails) == DEFAULT_CONFIG.max_trails
    assert book.overflow
    assert book.trails[0].colour == TRAIL_COLOURS[1]


def test_reference_caption_and_range_label() -> None:
    assert REFERENCE_NOTE == (
        "Reference mode: integration continues below h = 0 (professor / Stengel, tf = 6 s)."
    )
    finished = Trail(
        colour="#0072BD",
        v0_m_s=3.55,
        gamma0_deg=-10.3,
        mode="reference",
        tag="A",
        range_m=20.95,
        complete=True,
    )
    assert legend_line(finished) == "A  V0=3.55 m/s  γ0=−10.3°  r(6 s)=20.95 m"
    partial = replace(finished, complete=False, range_m=5.0)
    assert legend_line(partial) == "A  V0=3.55 m/s  γ0=−10.3°  r=5.00 m"
    physical = replace(finished, mode="physical", tag="", range_m=11.03)
    assert legend_line(physical) == "V0=3.55 m/s  γ0=−10.3°  r=11.03 m"


def test_playback_modules_do_not_filter_the_angle() -> None:
    root = Path(__file__).resolve().parents[1] / "src" / "paper_airplane"
    for relative in ("playback.py", "trails.py", "app/camera.py"):
        text = (root / relative).read_text(encoding="utf-8")
        assert "pygame" not in text
        assert "smooth_display_angle" not in text
