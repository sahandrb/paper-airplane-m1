"""Pre-launch inputs, captions, and the dashed-preview geometry.

No display library here. Sliders, presets, and the pose angles are plain numbers.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace
from typing import Literal

from paper_airplane.aero import mean_chord_m
from paper_airplane.app.camera import Camera
from paper_airplane.config import Config
from paper_airplane.equilibrium import alpha_star_deg, gamma_star_deg, v_star
from paper_airplane.sprite_geometry import rotate_offset

PreviewMode = Literal["reference", "physical"]
DOCK_WIDTH = 300

BUCKLE_WARNING = (
    "Stengel notes that a real paper wing may buckle above ~5 m/s. "
    "Case d (3 V* ≈ 10.65 m/s) is a numerical demonstration."
)

SPEC_CG_PX = (387.78, 119.31)


@dataclass(frozen=True)
class LaunchInputs:
    """What the dock is set to before a launch. Angles are degrees."""

    v0_m_s: float
    gamma0_deg: float
    mode: PreviewMode = "reference"


def default_inputs(config: Config) -> LaunchInputs:
    """Equilibrium glide: V* and gamma*."""
    return LaunchInputs(v0_m_s=v_star(config), gamma0_deg=gamma_star_deg(config))


def presets(config: Config) -> dict[str, tuple[float, float]]:
    """Professor cases. Values are (V0 m/s, gamma0 degrees)."""
    speed = v_star(config)
    glide = gamma_star_deg(config)
    return {
        "a": (speed, glide),
        "b": (speed, 0.0),
        "c": (1.5 * speed, 0.0),
        "d": (3.0 * speed, 0.0),
    }


def apply_preset(inputs: LaunchInputs, name: str, config: Config) -> LaunchInputs:
    speed, glide = presets(config)[name]
    return replace(inputs, v0_m_s=speed, gamma0_deg=glide)


def step_launch(
    inputs: LaunchInputs,
    config: Config,
    *,
    v_steps: int = 0,
    gamma_steps: int = 0,
) -> LaunchInputs:
    """Move one slider by whole steps and keep it inside its range."""
    speed = inputs.v0_m_s + v_steps * config.v0_step_m_s
    glide = inputs.gamma0_deg + gamma_steps * config.gamma0_step_deg
    return replace(
        inputs,
        v0_m_s=_clamp(speed, config.v0_min_m_s, config.v0_max_m_s),
        gamma0_deg=_clamp(glide, config.gamma0_min_deg, config.gamma0_max_deg),
    )


def slider_value(fraction: float, low: float, high: float, step: float) -> float:
    """Quantize a 0..1 track position onto the slider step."""
    fraction = _clamp(fraction, 0.0, 1.0)
    raw = low + fraction * (high - low)
    if step <= 0.0:
        return raw
    count = int(round((raw - low) / step))
    return _clamp(low + count * step, low, high)


def toggle_mode(inputs: LaunchInputs) -> LaunchInputs:
    mode: PreviewMode = "physical" if inputs.mode == "reference" else "reference"
    return replace(inputs, mode=mode)


def theta0_deg(inputs: LaunchInputs, config: Config) -> float:
    """Body angle. The ramp is gamma0; the wedge between them is alpha_star."""
    return inputs.gamma0_deg + alpha_star_deg(config)


def ramp_rotation_deg(gamma0_deg: float, config: Config, *, painted: bool) -> float:
    """Degrees to rotate the ramp image.

    The painted ramp already sits at the art angle, so the extra rotation is
    ``gamma0 - 16.1 deg``. A drawn fallback has no painted tilt, so it rotates
    by ``gamma0`` itself.
    """
    if painted:
        return gamma0_deg - config.launcher_rest_gamma_deg
    return gamma0_deg


def launcher_scale(config: Config) -> float:
    """Pixels of catapult art per source pixel, so the pillar spans h = 0 to h = 2."""
    _x, _y, _w, height = config.launcher_pillar_crop
    return (config.pixels_per_metre * config.h0_m) / height


def pivot_screen(camera: Camera, config: Config) -> tuple[float, float]:
    """Screen position of the launch point (r, h) = (0, 2). The pillar axis is r = 0."""
    return camera.to_screen(0.0, config.h0_m, config.pixels_per_metre)


def buckle_warning(v0_m_s: float) -> str | None:
    """The wing-buckle note. It does not change the equations."""
    if v0_m_s > 5.0:
        return BUCKLE_WARNING
    return None


def alpha_arc_label(config: Config) -> str:
    """Live alpha_star, which is constant for this model."""
    return f"alpha = {alpha_star_deg(config):.2f} deg"


def scale_caption(config: Config) -> str:
    """How many mean chords fit in the drawn dart. One decimal."""
    metres = config.sprite_display_length_px / config.pixels_per_metre
    factor = metres / mean_chord_m(config)
    return f"SPRITE NOT TO SCALE \u00d7{factor:.1f}"


def readout_lines(
    inputs: LaunchInputs,
    config: Config,
    *,
    landing_range_m: float | None = None,
    flight_time_s: float | None = None,
) -> tuple[str, ...]:
    """Dock numbers. Landing figures appear only in Physical mode."""
    speed = v_star(config)
    lines = [
        f"V0 = {inputs.v0_m_s:.2f} m/s  ({inputs.v0_m_s / speed:.2f} V*)",
        f"gamma0 = {inputs.gamma0_deg:.2f} deg",
        f"theta0 = {theta0_deg(inputs, config):.2f} deg",
        f"alpha* = {alpha_star_deg(config):.2f} deg",
    ]
    if inputs.mode == "physical" and landing_range_m is not None and flight_time_s is not None:
        lines.append(f"landing range = {landing_range_m:.2f} m")
        lines.append(f"flight time = {flight_time_s:.2f} s")
    return tuple(lines)


def dash_segments(
    points: list[tuple[float, float]],
    dash: float = 10.0,
    gap: float = 7.0,
) -> list[tuple[tuple[float, float], tuple[float, float]]]:
    """On/off pieces of a polyline. The preview is drawn from these."""
    if len(points) < 2 or dash <= 0.0:
        return []
    pieces: list[tuple[tuple[float, float], tuple[float, float]]] = []
    pen_down = True
    budget = dash
    cx, cy = points[0]
    for x1, y1 in points[1:]:
        dx = x1 - cx
        dy = y1 - cy
        distance = math.hypot(dx, dy)
        if distance == 0.0:
            continue
        ux = dx / distance
        uy = dy / distance
        while distance > 1e-9:
            step = min(budget, distance)
            nx = cx + ux * step
            ny = cy + uy * step
            if pen_down:
                pieces.append(((cx, cy), (nx, ny)))
            cx, cy = nx, ny
            distance -= step
            budget -= step
            if budget <= 1e-9:
                pen_down = not pen_down
                budget = dash if pen_down else gap
    return pieces


def arc_points(
    center: tuple[float, float],
    radius: float,
    start_deg: float,
    sweep_deg: float,
    count: int = 14,
) -> list[tuple[float, float]]:
    """Wedge samples from ``start_deg`` through ``sweep_deg``, using the pose rotation."""
    points: list[tuple[float, float]] = []
    steps = max(count, 1)
    for index in range(steps + 1):
        angle = start_deg + sweep_deg * index / steps
        dx, dy = rotate_offset(radius, 0.0, angle)
        points.append((center[0] + dx, center[1] + dy))
    return points


def cg_within_spec(measured: tuple[float, float], tolerance_px: float = 0.5) -> bool:
    """True when a remeasure agrees with the spec centroid (387.78, 119.31)."""
    return (
        abs(measured[0] - SPEC_CG_PX[0]) <= tolerance_px
        and abs(measured[1] - SPEC_CG_PX[1]) <= tolerance_px
    )


def _clamp(value: float, low: float, high: float) -> float:
    return min(high, max(low, value))
