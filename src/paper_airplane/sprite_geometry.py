"""Screen-space rotation about a chosen pixel.

The display y axis points down. Positive pitch raises a right-pointing nose
toward smaller y. This module stays free of the display library, and it does
not ease or filter the angle.
"""

from __future__ import annotations

import math

import numpy as np


def rotate_offset(dx: float, dy: float, theta_deg: float) -> tuple[float, float]:
    """Rotate an offset counter-clockwise in y-down screen axes.

    A vector (1, 0) at positive theta moves upward, toward smaller y.
    """
    angle = math.radians(theta_deg)
    cosine = math.cos(angle)
    sine = math.sin(angle)
    return (dx * cosine + dy * sine, -dx * sine + dy * cosine)


def pivoted_center(
    anchor_screen: tuple[float, float],
    image_size: tuple[float, float],
    anchor_px: tuple[float, float],
    theta_deg: float,
) -> tuple[float, float]:
    """Center of a rotated image so that ``anchor_px`` lands on ``anchor_screen``.

    Rotation is about the image center. The returned point is that center.
    """
    width, height = image_size
    offset = (anchor_px[0] - width / 2.0, anchor_px[1] - height / 2.0)
    rotated = rotate_offset(offset[0], offset[1], theta_deg)
    return (anchor_screen[0] - rotated[0], anchor_screen[1] - rotated[1])


def anchor_screen_position(
    image_center: tuple[float, float],
    image_size: tuple[float, float],
    anchor_px: tuple[float, float],
    theta_deg: float,
) -> tuple[float, float]:
    """Inverse of ``pivoted_center``. The anchor pixel must not wander."""
    width, height = image_size
    offset = (anchor_px[0] - width / 2.0, anchor_px[1] - height / 2.0)
    rotated = rotate_offset(offset[0], offset[1], theta_deg)
    return (image_center[0] + rotated[0], image_center[1] + rotated[1])


def rail_seat_offset(gamma_deg: float, thickness_px: float, extra_px: float = 10.0) -> tuple[float, float]:
    """Shift from the center of mass onto the rail, along the upward normal.

    At ``gamma = 0`` the shift is straight up the screen (negative y).
    ``thickness_px`` is the unrotated sprite height.
    """
    distance = thickness_px / 2.0 + extra_px
    return rotate_offset(0.0, -distance, gamma_deg)


def clamp_sprite_center_y(center_y: float, drawn_height: float, horizon_y: float) -> float:
    """Keep the bottom of the drawn sprite on or above the horizon line."""
    half = drawn_height / 2.0
    if center_y + half > horizon_y:
        return horizon_y - half
    return center_y


def rail_seating_row(
    alpha_xy: np.ndarray,
    pivot_px: tuple[float, float],
    rest_gamma_deg: float,
    threshold: float = 40.0,
) -> float:
    """Source row of the toothed rail beside the pivot, at the painted angle.

    ``alpha_xy`` has shape ``(width, height)``. Columns to the right of the
    pivot follow the painted rail. The linkage is on the other side, and the
    pivot row itself is the hinge, not the seat.
    """
    alpha = np.asarray(alpha_xy)
    _width, _height = alpha.shape
    pivot_x, pivot_y = pivot_px
    along = rotate_offset(1.0, 0.0, rest_gamma_deg)
    rows: list[float] = []
    for step in range(10, 110, 2):
        x = int(round(pivot_x + along[0] * step))
        if x < 0 or x >= alpha.shape[0]:
            continue
        column = alpha[x]
        opaque = np.nonzero(column > threshold)[0]
        above = opaque[opaque < pivot_y - 2.0]
        if above.size:
            rows.append(float(above[0]))
    if not rows:
        raise ValueError("rail bed has no opaque pixels beside the pivot")
    rows.sort()
    return rows[len(rows) // 2]


def alpha_centroid(alpha_xy: np.ndarray, threshold: float = 16.0) -> tuple[float, float]:
    """Mean of pixels with alpha above ``threshold``.

    ``alpha_xy`` has shape ``(width, height)``, column x then row y.
    """
    xs, ys = np.nonzero(np.asarray(alpha_xy) > threshold)
    if xs.size == 0:
        raise ValueError("alpha mask has no pixels above the threshold")
    return (float(xs.mean()), float(ys.mean()))
