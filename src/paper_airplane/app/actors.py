"""Split catapult, dart, dashed preview, and the scale caption."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import pygame

from paper_airplane.app.camera import Camera
from paper_airplane.app.prelaunch import (
    LaunchInputs,
    alpha_arc_label,
    arc_points,
    art_pivot_screen,
    cg_within_spec,
    dash_segments,
    launcher_scale,
    pivot_screen,
    ramp_rotation_deg,
    theta0_deg,
)
from paper_airplane.app.theme import ACCENT, PREVIEW, number_font
from paper_airplane.config import Config
from paper_airplane.simulation import Trajectory
from paper_airplane.sprite_geometry import (
    alpha_centroid,
    clamp_sprite_center_y,
    pivoted_center,
    rail_seating_row,
)

log = logging.getLogger(__name__)

_DART_SOURCE = (949, 249)
_GREY = (168, 174, 180)
_CYAN = (80, 196, 214)


@dataclass(frozen=True)
class Piece:
    """A scaled image and the pixel that must stay on the hinge or the CG."""

    image: pygame.Surface
    anchor_px: tuple[float, float]
    painted: bool
    seat_px: float = 0.0


@dataclass(frozen=True)
class FlightArt:
    pillar: Piece
    ramp: Piece
    dart: Piece
    warnings: tuple[str, ...]
    seating_row: float = 0.0
    source_height: float = 0.0


def load_flight_art(
    launcher: pygame.Surface | None,
    root: Path,
    config: Config,
) -> FlightArt:
    """Scale the dart and split the catapult. A missing file becomes a plain shape."""
    warnings: list[str] = []
    seating_row = 0.0
    source_height = 0.0
    if launcher is not None:
        seating_row = rail_seating_row(
            pygame.surfarray.array_alpha(launcher),
            config.launcher_pivot_px,
            config.launcher_rest_gamma_deg,
        )
        source_height = float(launcher.get_height())
    pillar, ramp = _load_launcher(launcher, config, warnings, seating_row, source_height)
    dart = _load_dart(root, config, warnings)
    return FlightArt(
        pillar=pillar,
        ramp=ramp,
        dart=dart,
        warnings=tuple(warnings),
        seating_row=seating_row,
        source_height=source_height,
    )


def draw_preview_path(
    screen: pygame.Surface,
    camera: Camera,
    config: Config,
    trajectory: Trajectory | None,
) -> None:
    """Dashed predicted path, under the dock and the airplane."""
    if trajectory is not None:
        _draw_preview(screen, camera, config, trajectory)


def draw_pose(
    screen: pygame.Surface,
    camera: Camera,
    config: Config,
    art: FlightArt,
    inputs: LaunchInputs,
    *,
    dart_world: tuple[float, float] | None = None,
    dart_theta_deg: float | None = None,
    seat_gamma_deg: float | None = None,
    show_arc: bool = True,
) -> None:
    """Pillar and ramp stay in the world. The dart CG is the launch point, or ``dart_world``."""
    del seat_gamma_deg
    launch = pivot_screen(camera, config)
    hinge = launch
    if art.ramp.painted and art.source_height > 0.0:
        hinge = art_pivot_screen(camera, config, art.seating_row, art.source_height)
    _blit_piece(screen, art.pillar, hinge, 0.0)
    _blit_piece(
        screen,
        art.ramp,
        hinge,
        ramp_rotation_deg(inputs.gamma0_deg, config, painted=art.ramp.painted),
    )
    if dart_world is None:
        place = launch
        angle = theta0_deg(inputs, config)
    else:
        place = camera.to_screen(dart_world[0], dart_world[1], config.pixels_per_metre)
        angle = theta0_deg(inputs, config) if dart_theta_deg is None else dart_theta_deg
    _blit_dart(screen, art.dart, place, angle, camera.cam_y)
    if show_arc and dart_world is None:
        _draw_alpha_arc(screen, launch, inputs, config)


def _load_launcher(
    launcher: pygame.Surface | None,
    config: Config,
    warnings: list[str],
    seating_row: float,
    source_height: float,
) -> tuple[Piece, Piece]:
    if launcher is None:
        return _fallback_pillar(config), _fallback_ramp()
    scale = launcher_scale(config, seating_row=seating_row, source_height=source_height)
    pillar = _scaled_crop(launcher, config.launcher_pillar_crop, scale)
    ramp = _scaled_crop(launcher, config.launcher_ramp_crop, scale)
    pivot_x, pivot_y = config.launcher_pivot_px
    pillar_anchor = (
        (pivot_x - config.launcher_pillar_crop[0]) * pillar.get_width() / config.launcher_pillar_crop[2],
        (pivot_y - config.launcher_pillar_crop[1]) * pillar.get_height() / config.launcher_pillar_crop[3],
    )
    ramp_anchor = (
        (pivot_x - config.launcher_ramp_crop[0]) * ramp.get_width() / config.launcher_ramp_crop[2],
        (pivot_y - config.launcher_ramp_crop[1]) * ramp.get_height() / config.launcher_ramp_crop[3],
    )
    return Piece(pillar, pillar_anchor, painted=True), Piece(ramp, ramp_anchor, painted=True)


def _scaled_crop(
    image: pygame.Surface,
    crop: tuple[int, int, int, int],
    scale: float,
) -> pygame.Surface:
    x, y, width, height = crop
    view = image.subsurface((x, y, width, height)).copy()
    size = (max(1, int(round(width * scale))), max(1, int(round(height * scale))))
    return pygame.transform.smoothscale(view, size)


def _fallback_pillar(config: Config) -> Piece:
    height = max(1, int(round(config.pixels_per_metre * config.h0_m)))
    width = 46
    surface = pygame.Surface((width, height), pygame.SRCALPHA)
    pygame.draw.rect(surface, _GREY, (8, 0, 30, height), border_radius=8)
    pygame.draw.rect(surface, _GREY, (0, height - 18, width, 18), border_radius=4)
    pygame.draw.line(surface, _CYAN, (4, 2), (width - 5, 2), 3)
    return Piece(surface, (width / 2.0, 0.0), painted=False)


def _fallback_ramp() -> Piece:
    surface = pygame.Surface((150, 18), pygame.SRCALPHA)
    pygame.draw.rect(surface, _GREY, (0, 4, 150, 10), border_radius=2)
    pygame.draw.line(surface, _CYAN, (0, 4), (150, 4), 2)
    return Piece(surface, (8.0, 9.0), painted=False)


def _load_dart(root: Path, config: Config, warnings: list[str]) -> Piece:
    path = root / "assets" / "aircraft" / "paper_dart.png"
    if not path.is_file():
        message = "paper_dart.png is missing; drawing a plain dart."
        log.warning(message)
        warnings.append(message)
        return _fallback_dart(config)
    image = pygame.image.load(str(path)).convert_alpha()
    measured = alpha_centroid(pygame.surfarray.array_alpha(image))
    cg = config.cg_px if cg_within_spec(measured) else measured
    if not cg_within_spec(measured):
        message = f"dart CG remeasured at ({measured[0]:.2f}, {measured[1]:.2f}); using that pivot."
        log.warning(message)
        warnings.append(message)
    drawn = (
        config.sprite_display_length_px,
        max(1, int(round(config.sprite_display_length_px * image.get_height() / image.get_width()))),
    )
    scaled = pygame.transform.smoothscale(image, drawn)
    anchor = (cg[0] * drawn[0] / image.get_width(), cg[1] * drawn[1] / image.get_height())
    return Piece(scaled, anchor, painted=False)


def _fallback_dart(config: Config) -> Piece:
    width = config.sprite_display_length_px
    height = max(1, int(round(width * _DART_SOURCE[1] / _DART_SOURCE[0])))
    surface = pygame.Surface((width, height), pygame.SRCALPHA)
    mid = height / 2.0
    nose = width - 1
    polygon = [
        (2, mid - 4),
        (width * 0.62, mid - 5),
        (nose, mid),
        (width * 0.62, mid + 5),
        (2, mid + 4),
    ]
    pygame.draw.polygon(surface, (248, 248, 248), polygon)
    pygame.draw.polygon(surface, (210, 214, 220), [(2, mid - 4), (18, mid), (2, mid + 4)])
    measured = alpha_centroid(pygame.surfarray.array_alpha(surface))
    return Piece(surface, measured, painted=False)


def _blit_dart(
    screen: pygame.Surface,
    piece: Piece,
    anchor_screen: tuple[float, float],
    angle_deg: float,
    horizon_y: float,
) -> None:
    """Draw the dart with its CG on the launch point, never below the horizon."""
    rotated = pygame.transform.rotate(piece.image, angle_deg)
    center = pivoted_center(anchor_screen, piece.image.get_size(), piece.anchor_px, angle_deg)
    center_y = clamp_sprite_center_y(center[1], float(rotated.get_height()), horizon_y)
    screen.blit(rotated, rotated.get_rect(center=(round(center[0]), round(center_y))))


def _blit_piece(screen: pygame.Surface, piece: Piece, anchor_screen: tuple[float, float], angle_deg: float) -> None:
    rotated = pygame.transform.rotate(piece.image, angle_deg)
    center = pivoted_center(anchor_screen, piece.image.get_size(), piece.anchor_px, angle_deg)
    screen.blit(rotated, rotated.get_rect(center=(round(center[0]), round(center[1]))))


def _draw_preview(
    screen: pygame.Surface,
    camera: Camera,
    config: Config,
    trajectory: Trajectory,
) -> None:
    points = [
        camera.to_screen(float(range_m), float(height_m), config.pixels_per_metre)
        for range_m, height_m in zip(trajectory.r, trajectory.h)
    ]
    for start, end in dash_segments(points):
        pygame.draw.line(screen, PREVIEW, (round(start[0]), round(start[1])), (round(end[0]), round(end[1])), 2)


def _draw_alpha_arc(
    screen: pygame.Surface,
    hinge: tuple[float, float],
    inputs: LaunchInputs,
    config: Config,
) -> None:
    sweep = theta0_deg(inputs, config) - inputs.gamma0_deg
    points = arc_points(hinge, 36.0, inputs.gamma0_deg, sweep)
    if len(points) >= 2:
        pygame.draw.lines(screen, ACCENT, False, [(round(x), round(y)) for x, y in points], 2)
    label = number_font(15).render(alpha_arc_label(config), True, ACCENT)
    mid = arc_points(hinge, 52.0, inputs.gamma0_deg, sweep, count=2)[1]
    screen.blit(label, (round(mid[0]) + 6, round(mid[1]) - label.get_height() // 2))

