"""Screen mapping for the side view. This module stays free of the display library.

Screen y grows downward. One ``pixels_per_metre`` serves both axes, so a
loop stays a circle. Only the camera origin may ease in a later phase;
this phase keeps the pre-launch frame fixed.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from paper_airplane.config import Config


@dataclass(frozen=True)
class Camera:
    """Screen position of the world origin ``(r, h) = (0, 0)``."""

    cam_x: float
    cam_y: float

    def to_screen(self, r_m: float, h_m: float, pixels_per_metre: float) -> tuple[float, float]:
        """Map range and height to pixels: ``x = cam_x + r ppm``, ``y = cam_y - h ppm``."""
        return (
            self.cam_x + r_m * pixels_per_metre,
            self.cam_y - h_m * pixels_per_metre,
        )


def prelaunch_camera(config: Config) -> Camera:
    """Place ``h = 0`` on the ground row and ``r = 0`` at 8 percent of the width."""
    return Camera(
        cam_x=config.prelaunch_launcher_x_frac * config.window_width_px,
        cam_y=float(config.ground_screen_y0),
    )


def ground_scroll_px(cam_x: float, strip_width: int) -> int:
    """Horizontal shift that keeps world ``r = 0`` on the launcher pixel.

    The returned value is the source column shown at screen x = 0. Blitting
    the strip at ``x = -offset`` (and again one width to the right) tiles it.
    """
    if strip_width <= 0:
        return 0
    origin = int(round(cam_x))
    return (-origin) % strip_width


def visible_metre_marks(camera: Camera, width_px: int, pixels_per_metre: float) -> range:
    """Integer world-range marks that cross the screen, one metre apart."""
    if pixels_per_metre == 0:
        return range(0)
    r_left = (0.0 - camera.cam_x) / pixels_per_metre
    r_right = (width_px - camera.cam_x) / pixels_per_metre
    start = math.floor(min(r_left, r_right))
    stop = math.ceil(max(r_left, r_right))
    return range(start, stop + 1)


def unsplit_launcher_dest(
    config: Config,
    source_size: tuple[int, int] = (330, 279),
) -> tuple[float, float, float, float]:
    """Top-left and drawn size of the whole catapult, before the ramp is split.

    The painted pivot row sits on the launch height ``h0``. The base of the
    image sits on ``h = 0``. ``source_size`` is the catapult art, 330 by 279.
    """
    source_w, source_h = source_size
    base_to_pivot = source_h - config.launcher_pivot_px[1]
    if base_to_pivot <= 0:
        raise ValueError("launcher pivot must sit above the bottom of the image")
    scale = (config.pixels_per_metre * config.h0_m) / base_to_pivot
    drawn_w = source_w * scale
    drawn_h = source_h * scale
    left = config.prelaunch_launcher_x_frac * config.window_width_px
    top = config.ground_screen_y0 - drawn_h
    return (left, top, drawn_w, drawn_h)
