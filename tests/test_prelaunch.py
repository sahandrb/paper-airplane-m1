"""Pre-launch pose, presets, and captions. The draw check uses a dummy display."""

from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

from pathlib import Path

import numpy as np
import pygame
import pytest

from paper_airplane.app.actors import load_flight_art
from paper_airplane.app.background import project_root
from paper_airplane.app.camera import prelaunch_camera
from paper_airplane.app.main import _apply_launch_key
from paper_airplane.app.prelaunch import (
    BUCKLE_WARNING,
    LaunchInputs,
    alpha_arc_label,
    apply_preset,
    buckle_warning,
    cg_within_spec,
    dash_segments,
    default_inputs,
    launcher_scale,
    pivot_screen,
    presets,
    ramp_rotation_deg,
    readout_lines,
    scale_caption,
    step_launch,
)
from paper_airplane.config import DEFAULT_CONFIG
from paper_airplane.equilibrium import alpha_star_deg, gamma_star_deg, v_star
from paper_airplane.sprite_geometry import alpha_centroid


def test_rest_ramp_has_no_extra_rotation_and_the_seat_is_two_metres_up() -> None:
    camera = prelaunch_camera(DEFAULT_CONFIG)
    seat_x, seat_y = pivot_screen(camera, DEFAULT_CONFIG)
    assert seat_x == pytest.approx(0.08 * 1280)
    assert seat_y == pytest.approx(381)
    assert seat_y == pytest.approx(548 - 2.0 * 83.5)
    assert ramp_rotation_deg(16.1, DEFAULT_CONFIG, painted=True) == pytest.approx(0.0)
    assert launcher_scale(DEFAULT_CONFIG) * 155 == pytest.approx(167.0)


def test_presets_match_the_professor_cases() -> None:
    speed = v_star(DEFAULT_CONFIG)
    glide = gamma_star_deg(DEFAULT_CONFIG)
    assert presets(DEFAULT_CONFIG)["a"] == pytest.approx((speed, glide))
    assert presets(DEFAULT_CONFIG)["b"] == pytest.approx((speed, 0.0))
    assert presets(DEFAULT_CONFIG)["c"] == pytest.approx((1.5 * speed, 0.0))
    assert presets(DEFAULT_CONFIG)["d"] == pytest.approx((3.0 * speed, 0.0))
    inputs = apply_preset(default_inputs(DEFAULT_CONFIG), "d", DEFAULT_CONFIG)
    assert inputs.v0_m_s == pytest.approx(3.0 * speed)
    assert inputs.gamma0_deg == pytest.approx(0.0)


def test_keys_step_the_sliders_and_snap_presets() -> None:
    inputs = default_inputs(DEFAULT_CONFIG)
    stepped = _apply_launch_key(pygame.K_RIGHT, inputs, DEFAULT_CONFIG)
    assert stepped.gamma0_deg == pytest.approx(inputs.gamma0_deg + 0.5)
    stepped = _apply_launch_key(pygame.K_w, inputs, DEFAULT_CONFIG)
    assert stepped.v0_m_s == pytest.approx(inputs.v0_m_s + 0.05)
    snapped = _apply_launch_key(pygame.K_2, inputs, DEFAULT_CONFIG)
    assert snapped.gamma0_deg == pytest.approx(0.0)
    assert snapped.v0_m_s == pytest.approx(v_star(DEFAULT_CONFIG))
    capped = step_launch(inputs, DEFAULT_CONFIG, v_steps=10_000)
    assert capped.v0_m_s == DEFAULT_CONFIG.v0_max_m_s


def test_buckle_sentence_appears_only_above_5_metres_per_second() -> None:
    assert buckle_warning(5.0) is None
    assert buckle_warning(5.01) == BUCKLE_WARNING
    assert "buckle above ~5 m/s" in BUCKLE_WARNING
    assert "10.65 m/s" in BUCKLE_WARNING


def test_alpha_label_and_scale_caption() -> None:
    assert alpha_arc_label(DEFAULT_CONFIG) == f"alpha = {alpha_star_deg(DEFAULT_CONFIG):.2f} deg"
    assert alpha_arc_label(DEFAULT_CONFIG) == "alpha = 9.77 deg"
    caption = scale_caption(DEFAULT_CONFIG)
    assert caption.startswith("SPRITE NOT TO SCALE \u00d7")
    assert caption.endswith("9.4")


def test_physical_readout_includes_the_landing_and_reference_does_not() -> None:
    inputs = default_inputs(DEFAULT_CONFIG)
    reference = readout_lines(inputs, DEFAULT_CONFIG, landing_range_m=11.0, flight_time_s=3.0)
    assert all("landing" not in line for line in reference)
    physical = readout_lines(
        LaunchInputs(inputs.v0_m_s, inputs.gamma0_deg, "physical"),
        DEFAULT_CONFIG,
        landing_range_m=11.03,
        flight_time_s=3.16,
    )
    assert "landing range = 11.03 m" in physical
    assert "flight time = 3.16 s" in physical


def test_dashed_preview_leaves_gaps() -> None:
    pieces = dash_segments([(0.0, 0.0), (30.0, 0.0)], dash=10.0, gap=5.0)
    covered = [start[0] for start, _end in pieces]
    assert covered[0] == pytest.approx(0.0)
    assert 12.0 not in [round(x, 5) for x in covered]
    assert pieces[-1][1][0] == pytest.approx(30.0) or pieces[-1][0][0] < 30.0


def test_measured_dart_cg_keeps_the_config_pivot() -> None:
    pygame.display.init()
    pygame.display.set_mode((64, 64))
    image = pygame.image.load(str(project_root() / "assets" / "aircraft" / "paper_dart.png")).convert_alpha()
    measured = alpha_centroid(pygame.surfarray.array_alpha(image))
    assert measured == pytest.approx((387.78, 119.31), abs=0.5)
    assert cg_within_spec(measured)
    assert DEFAULT_CONFIG.cg_px == (388.0, 119.0)


def test_gamma_changes_the_drawn_pose() -> None:
    pygame.display.init()
    pygame.font.init()
    pygame.display.set_mode((1280, 720))
    from paper_airplane.app.actors import draw_pose

    art = load_flight_art(None, Path("."), DEFAULT_CONFIG)
    camera = prelaunch_camera(DEFAULT_CONFIG)
    first = pygame.Surface((1280, 720))
    second = pygame.Surface((1280, 720))
    draw_pose(first, camera, DEFAULT_CONFIG, art, LaunchInputs(3.5, 0.0))
    draw_pose(second, camera, DEFAULT_CONFIG, art, LaunchInputs(3.5, 40.0))
    assert not np.array_equal(pygame.surfarray.array3d(first), pygame.surfarray.array3d(second))


def test_app_does_not_smooth_the_sprite_angle() -> None:
    root = Path(__file__).resolve().parents[1] / "src" / "paper_airplane"
    for path in root.rglob("*.py"):
        assert "smooth_display_angle" not in path.read_text(encoding="utf-8")
