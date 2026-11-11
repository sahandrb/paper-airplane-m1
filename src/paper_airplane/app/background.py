"""Dusk field: a screen-fixed sky and a ground strip that scrolls with range."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import pygame

from paper_airplane.app.camera import Camera, ground_scroll_px, unsplit_launcher_dest, visible_metre_marks
from paper_airplane.app.theme import GROUND_FALLBACK, SKY_HORIZON, SKY_TOP, TICK, number_font
from paper_airplane.config import Config

log = logging.getLogger(__name__)

# The supplied dusk plate is 1280x720. Rows 0..547 are sky. The rest is ground.
SKY_ROWS = 548


def project_root() -> Path:
    """Repository root, whether the process was started from that directory or not."""
    return Path(__file__).resolve().parents[3]


@dataclass(frozen=True)
class Scenery:
    """Loaded plates. ``None`` means the caller should use the flat fallback."""

    sky: pygame.Surface | None
    ground: pygame.Surface | None
    launcher: pygame.Surface | None
    warnings: tuple[str, ...]


def load_scenery(root: Path | None = None) -> Scenery:
    """Load the dusk plate and the unsplit catapult. A missing file does not raise."""
    root = project_root() if root is None else root
    warnings: list[str] = []
    sky: pygame.Surface | None = None
    ground: pygame.Surface | None = None
    plate = root / "assets" / "background" / "dusk_field.jpg"
    if plate.is_file():
        image = pygame.image.load(str(plate)).convert()
        sky_h = min(SKY_ROWS, image.get_height())
        sky = image.subsurface((0, 0, image.get_width(), sky_h)).copy()
        if image.get_height() > sky_h:
            ground = image.subsurface((0, sky_h, image.get_width(), image.get_height() - sky_h)).copy()
    else:
        message = "dusk_field.jpg is missing; drawing the fallback sky and ground."
        log.warning(message)
        warnings.append(message)

    launcher: pygame.Surface | None = None
    catapult = root / "assets" / "launcher" / "catapult.png"
    if catapult.is_file():
        launcher = pygame.image.load(str(catapult)).convert_alpha()
    else:
        message = "catapult.png is missing; the pre-launch frame has no launcher."
        log.warning(message)
        warnings.append(message)
    return Scenery(sky=sky, ground=ground, launcher=launcher, warnings=tuple(warnings))


def draw_world(
    screen: pygame.Surface,
    camera: Camera,
    config: Config,
    scenery: Scenery,
) -> None:
    """Paint sky, the h < 0 band, metre ticks, and the unsplit catapult."""
    ground_y = int(round(camera.cam_y))
    if scenery.sky is not None:
        screen.fill(SKY_HORIZON)
        screen.blit(scenery.sky, (0, 0))
    else:
        _draw_fallback_sky(screen, ground_y)
    height = screen.get_height()
    if ground_y < height:
        if scenery.ground is not None:
            _blit_ground(screen, scenery.ground, camera, ground_y)
        else:
            pygame.draw.rect(
                screen,
                GROUND_FALLBACK,
                (0, max(ground_y, 0), screen.get_width(), height - max(ground_y, 0)),
            )
    _draw_ticks(screen, camera, config, ground_y)
    _draw_launcher(screen, camera, config, scenery.launcher)


def _draw_fallback_sky(screen: pygame.Surface, ground_y: int) -> None:
    """#0B2A6B at the top through #E07A3A at the ground line."""
    width = screen.get_width()
    top_row = max(ground_y, 0)
    span = max(top_row - 1, 1)
    for y in range(top_row):
        t = y / span
        colour = tuple(int(SKY_TOP[i] + (SKY_HORIZON[i] - SKY_TOP[i]) * t) for i in range(3))
        pygame.draw.line(screen, colour, (0, y), (width, y))
    if ground_y < 0:
        screen.fill(GROUND_FALLBACK)


def _blit_ground(screen: pygame.Surface, strip: pygame.Surface, camera: Camera, top_y: int) -> None:
    """Tile the ground plate through every pixel with world h < 0, scrolling in r."""
    strip_w = strip.get_width()
    strip_h = strip.get_height()
    if strip_w <= 0 or strip_h <= 0:
        return
    offset = ground_scroll_px(camera.cam_x, strip_w)
    width = screen.get_width()
    bottom = screen.get_height()
    y = top_y
    if y < 0:
        y += ((-y) // strip_h) * strip_h
    while y < bottom:
        x = -offset
        while x < width:
            screen.blit(strip, (x, y))
            x += strip_w
        y += strip_h


def _draw_ticks(screen: pygame.Surface, camera: Camera, config: Config, ground_y: int) -> None:
    """One tick per metre and a label every five metres, in world range."""
    ppm = config.pixels_per_metre
    width = screen.get_width()
    height = screen.get_height()
    overlay = pygame.Surface((width, height), pygame.SRCALPHA)
    colour = (*TICK, 160)
    font = number_font(15)
    pygame.draw.line(overlay, colour, (0, ground_y), (width, ground_y), 1)
    for mark in visible_metre_marks(camera, width, ppm):
        sx = int(round(camera.to_screen(float(mark), 0.0, ppm)[0]))
        if sx < -30 or sx > width + 30:
            continue
        labelled = mark % 5 == 0
        tick_h = 16 if labelled else 8
        pygame.draw.line(overlay, colour, (sx, ground_y), (sx, ground_y - tick_h), 1)
        if not labelled:
            continue
        label = font.render(str(mark), True, TICK)
        label.set_alpha(160)
        overlay.blit(label, (sx - label.get_width() // 2, ground_y - tick_h - label.get_height() - 2))
    screen.blit(overlay, (0, 0))


def _draw_launcher(
    screen: pygame.Surface,
    camera: Camera,
    config: Config,
    launcher: pygame.Surface | None,
) -> None:
    """Blit the whole catapult. The split ramp arrives with the pre-launch pose.

    The left edge stays on world ``r = 0`` and the base stays on ``h = 0``,
    so a later camera move carries the launcher with the field.
    """
    if launcher is None:
        return
    drawn_w, drawn_h = unsplit_launcher_dest(
        config,
        (launcher.get_width(), launcher.get_height()),
    )[2:]
    size = (max(1, int(round(drawn_w))), max(1, int(round(drawn_h))))
    screen.blit(
        pygame.transform.smoothscale(launcher, size),
        (int(round(camera.cam_x)), int(round(camera.cam_y - drawn_h))),
    )
