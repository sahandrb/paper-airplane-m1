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


def alpha_centroid(alpha_xy: np.ndarray, threshold: float = 16.0) -> tuple[float, float]:
    """Mean of pixels with alpha above ``threshold``.

    ``alpha_xy`` has shape ``(width, height)``, column x then row y.
    """
    xs, ys = np.nonzero(np.asarray(alpha_xy) > threshold)
    if xs.size == 0:
        raise ValueError("alpha mask has no pixels above the threshold")
    return (float(xs.mean()), float(ys.mean()))
