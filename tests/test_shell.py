"""One dummy-driver frame of the dusk shell. No real window."""

from __future__ import annotations

import os

os.environ["SDL_VIDEODRIVER"] = "dummy"

import pygame

from paper_airplane.app.background import Scenery, draw_world, load_scenery, project_root
from paper_airplane.app.camera import Camera, prelaunch_camera
from paper_airplane.app.theme import GROUND_FALLBACK, SKY_HORIZON, SKY_TOP, TICK
from paper_airplane.config import DEFAULT_CONFIG


def _init() -> None:
    pygame.display.init()
    pygame.font.init()


def test_theme_colours_match_the_specification() -> None:
    assert SKY_TOP == (0x0B, 0x2A, 0x6B)
    assert SKY_HORIZON == (0xE0, 0x7A, 0x3A)
    assert GROUND_FALLBACK == (0x1A, 0x2A, 0x24)
    assert TICK == (0xC9, 0xD2, 0xC8)


def test_missing_art_draws_the_fallback_sky_and_ground() -> None:
    _init()
    screen = pygame.Surface((1280, 720))
    scenery = Scenery(sky=None, ground=None, launcher=None, warnings=())
    draw_world(screen, prelaunch_camera(DEFAULT_CONFIG), DEFAULT_CONFIG, scenery)
    assert screen.get_at((10, 0))[:3] == SKY_TOP
    assert screen.get_at((10, 547))[:3] == SKY_HORIZON
    assert screen.get_at((10, 700))[:3] == GROUND_FALLBACK
    # The ground line is #C9D2C8 at about 160 alpha over the fallback ground.
    line = screen.get_at((400, 548))
    assert line.r > GROUND_FALLBACK[0] + 40
    assert abs(line.r - line.g) < 20
    assert abs(line.g - line.b) < 20


def test_ground_strip_scrolls_with_range() -> None:
    _init()
    strip = pygame.Surface((1280, 172))
    strip.fill((20, 40, 30))
    pygame.draw.line(strip, (220, 20, 20), (0, 0), (0, 171))
    scenery = Scenery(sky=None, ground=strip, launcher=None, warnings=())
    screen = pygame.Surface((1280, 720))
    draw_world(screen, Camera(cam_x=40.0, cam_y=548.0), DEFAULT_CONFIG, scenery)
    assert screen.get_at((40, 600))[:3] == (220, 20, 20)
    assert screen.get_at((80, 600))[:3] == (20, 40, 30)
    draw_world(screen, Camera(cam_x=80.0, cam_y=548.0), DEFAULT_CONFIG, scenery)
    assert screen.get_at((80, 600))[:3] == (220, 20, 20)
    assert screen.get_at((40, 600))[:3] == (20, 40, 30)


def test_dusk_plate_splits_at_the_ground_line() -> None:
    _init()
    pygame.display.set_mode((1280, 720))
    scenery = load_scenery(project_root())
    assert scenery.warnings == ()
    assert scenery.sky is not None and scenery.sky.get_height() == 548
    assert scenery.ground is not None and scenery.ground.get_height() == 172
    assert scenery.launcher is not None


def test_about_toggles_and_escape_asks_before_quit() -> None:
    from paper_airplane.app.main import _on_key

    assert _on_key(pygame.K_a, False, False) == (True, False, False)
    assert _on_key(pygame.K_a, True, False) == (False, False, False)
    assert _on_key(pygame.K_ESCAPE, True, False) == (False, False, False)
    assert _on_key(pygame.K_ESCAPE, False, False) == (False, True, False)
    assert _on_key(pygame.K_ESCAPE, False, True) == (False, False, False)
    assert _on_key(pygame.K_RETURN, False, True) == (False, True, True)
    assert _on_key(pygame.K_a, False, True) == (False, True, False)


def test_run_app_returns_without_a_real_display() -> None:
    from paper_airplane.app.main import run_app

    assert run_app(frame_limit=2, splash_s=0.0) == 0
