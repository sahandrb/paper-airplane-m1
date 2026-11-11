"""Pre-launch framing. These tests do not open a window."""

from pathlib import Path

import pytest

from paper_airplane.app.camera import (
    Camera,
    ground_scroll_px,
    prelaunch_camera,
    unsplit_launcher_dest,
    visible_metre_marks,
)
from paper_airplane.config import DEFAULT_CONFIG


def test_prelaunch_puts_the_ground_at_y_548_and_the_launcher_at_x_102() -> None:
    camera = prelaunch_camera(DEFAULT_CONFIG)
    assert camera.cam_y == 548
    assert camera.cam_x == pytest.approx(0.08 * 1280)
    assert round(camera.cam_x) == 102


def test_screen_scale_is_isotropic() -> None:
    camera = prelaunch_camera(DEFAULT_CONFIG)
    ppm = DEFAULT_CONFIG.pixels_per_metre
    x0, y0 = camera.to_screen(0.0, 0.0, ppm)
    x1, y1 = camera.to_screen(1.0, 0.0, ppm)
    x2, y2 = camera.to_screen(0.0, 1.0, ppm)
    assert x0 == pytest.approx(camera.cam_x)
    assert y0 == pytest.approx(548)
    assert x1 - x0 == pytest.approx(ppm)
    assert y0 - y2 == pytest.approx(ppm)
    assert y1 == pytest.approx(y0)
    assert x2 == pytest.approx(x0)
    assert ppm == 83.5


def test_world_to_screen_uses_one_scale_on_both_axes() -> None:
    camera = Camera(cam_x=10.0, cam_y=20.0)
    x, y = camera.to_screen(2.0, 3.0, 83.5)
    assert x == pytest.approx(10.0 + 2.0 * 83.5)
    assert y == pytest.approx(20.0 - 3.0 * 83.5)


def test_unsplit_launcher_seat_is_two_metres_above_the_ground() -> None:
    seating_row = 17.0
    left, top, _drawn_w, drawn_h = unsplit_launcher_dest(DEFAULT_CONFIG, seating_row=seating_row)
    scale = drawn_h / 279
    seat_y = top + seating_row * scale
    pivot_y = top + DEFAULT_CONFIG.launcher_pivot_px[1] * scale
    assert left == pytest.approx(0.08 * 1280)
    assert seat_y == pytest.approx(548 - 2.0 * 83.5)
    assert seat_y == pytest.approx(381)
    assert pivot_y > seat_y


def test_ground_scroll_keeps_range_zero_on_the_launcher_pixel() -> None:
    assert ground_scroll_px(0.0, 1280) == 0
    assert (-ground_scroll_px(102.4, 1280)) % 1280 == 102
    assert (-ground_scroll_px(40.0, 1280)) % 1280 == 40


def test_metre_marks_are_one_metre_apart_and_include_the_origin() -> None:
    camera = prelaunch_camera(DEFAULT_CONFIG)
    marks = list(visible_metre_marks(camera, 1280, 83.5))
    assert marks[0] <= 0 <= marks[-1]
    assert [b - a for a, b in zip(marks, marks[1:])] == [1] * (len(marks) - 1)


def test_framing_modules_do_not_import_pygame() -> None:
    root = Path(__file__).resolve().parents[1] / "src" / "paper_airplane" / "app"
    for name in ("camera.py", "about.py"):
        text = (root / name).read_text(encoding="utf-8")
        assert "pygame" not in text
        assert "smooth_display_angle" not in text
    for path in root.rglob("*.py"):
        assert "smooth_display_angle" not in path.read_text(encoding="utf-8")
