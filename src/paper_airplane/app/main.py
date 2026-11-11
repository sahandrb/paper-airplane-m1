"""Pygame shell: splash, dusk field, footer, and the About panel.

Launch inputs, the split ramp, and playback are later phases. This loop only
opens the window and holds the pre-launch frame.
"""

from __future__ import annotations

import os
import time

import pygame

from paper_airplane.app.about import ABOUT_LINES, CAPTION, CREDIT, FOOTER, HINT
from paper_airplane.app.background import draw_world, load_scenery
from paper_airplane.app.camera import prelaunch_camera
from paper_airplane.app.theme import (
    ACCENT,
    DIM,
    PANEL,
    PANEL_ALPHA,
    TEXT,
    WARNING,
    label_font,
    label_font_fitting,
)
from paper_airplane.config import DEFAULT_CONFIG, Config

_TARGET_FPS = 60


def run_app(
    config: Config | None = None,
    *,
    frame_limit: int | None = None,
    splash_s: float = 2.0,
) -> int:
    """Open the 1280x720 window and run until the user quits.

    ``frame_limit`` closes the window after that many frames. The environment
    variable ``PAPER_AIRPLANE_FRAME_LIMIT`` does the same, so a check can open
    the window and return.
    """
    config = DEFAULT_CONFIG if config is None else config
    if frame_limit is None:
        raw_limit = os.environ.get("PAPER_AIRPLANE_FRAME_LIMIT")
        if raw_limit:
            frame_limit = int(raw_limit)
    raw_splash = os.environ.get("PAPER_AIRPLANE_SPLASH_S")
    if raw_splash:
        splash_s = float(raw_splash)

    pygame.display.init()
    pygame.font.init()
    try:
        return _loop(config, frame_limit=frame_limit, splash_s=splash_s)
    finally:
        pygame.quit()


def _loop(config: Config, *, frame_limit: int | None, splash_s: float) -> int:
    width = config.window_width_px
    height = config.window_height_px
    try:
        screen = pygame.display.set_mode((width, height))
    except pygame.error as exc:
        print(f"Could not open the flight-lab window: {exc}")
        return 1
    pygame.display.set_caption(CAPTION)
    scenery = load_scenery()
    for message in scenery.warnings:
        print(message)
    camera = prelaunch_camera(config)
    clock = pygame.time.Clock()
    showing_splash = splash_s > 0.0
    splash_deadline = time.perf_counter() + splash_s
    about_open = False
    quit_prompt = False
    frames = 0

    while True:
        if showing_splash and time.perf_counter() >= splash_deadline:
            showing_splash = False
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return 0
            if showing_splash and event.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                showing_splash = False
                continue
            if event.type != pygame.KEYDOWN:
                continue
            about_open, quit_prompt, finished = _on_key(event.key, about_open, quit_prompt)
            if finished:
                return 0

        draw_world(screen, camera, config, scenery)
        if showing_splash:
            _draw_splash(screen)
        else:
            _draw_header(screen)
            if scenery.warnings:
                _draw_warnings(screen, scenery.warnings)
        _draw_footer(screen)
        if about_open:
            _draw_about(screen)
        if quit_prompt:
            _draw_quit(screen)
        pygame.display.flip()
        clock.tick(_TARGET_FPS)
        frames += 1
        if frame_limit is not None and frames >= frame_limit:
            return 0


def _on_key(key: int, about_open: bool, quit_prompt: bool) -> tuple[bool, bool, bool]:
    """Apply one key. The third value is true when the user confirmed quit."""
    if key == pygame.K_a and not quit_prompt:
        return (not about_open, quit_prompt, False)
    if key == pygame.K_ESCAPE:
        if about_open:
            return (False, quit_prompt, False)
        if quit_prompt:
            return (about_open, False, False)
        return (about_open, True, False)
    if quit_prompt and key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_y):
        return (about_open, quit_prompt, True)
    return (about_open, quit_prompt, False)


def _draw_header(screen: pygame.Surface) -> None:
    bar_h = 36
    bar = pygame.Surface((screen.get_width(), bar_h), pygame.SRCALPHA)
    bar.fill((*PANEL, 170))
    screen.blit(bar, (0, 0))
    font = label_font_fitting(CREDIT, screen.get_width() - 32, 16)
    line = font.render(CREDIT, True, TEXT)
    screen.blit(line, (16, (bar_h - line.get_height()) // 2))


def _draw_footer(screen: pygame.Surface) -> None:
    font = label_font(15)
    footer = font.render(FOOTER, True, TEXT)
    footer.set_alpha(190)
    screen.blit(
        footer,
        (screen.get_width() - footer.get_width() - 16, screen.get_height() - footer.get_height() - 10),
    )
    hint = font.render(HINT, True, DIM)
    screen.blit(hint, (16, screen.get_height() - hint.get_height() - 10))


def _draw_warnings(screen: pygame.Surface, warnings: tuple[str, ...]) -> None:
    font = label_font(16)
    y = 44
    for message in warnings:
        line = font.render(message, True, WARNING)
        screen.blit(line, (16, y))
        y += line.get_height() + 4


def _draw_splash(screen: pygame.Surface) -> None:
    shade = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
    shade.fill((8, 12, 24, 150))
    screen.blit(shade, (0, 0))
    title = label_font(42).render(CAPTION, True, TEXT)
    credit_font = label_font_fitting(CREDIT, screen.get_width() - 80, 18)
    credit = credit_font.render(CREDIT, True, DIM)
    hint = label_font(16).render("any key continues", True, DIM)
    cx = screen.get_width() // 2
    cy = screen.get_height() // 2
    screen.blit(title, (cx - title.get_width() // 2, cy - 78))
    screen.blit(credit, (cx - credit.get_width() // 2, cy - 8))
    screen.blit(hint, (cx - hint.get_width() // 2, cy + 36))


def _draw_about(screen: pygame.Surface) -> None:
    title_font = label_font(26)
    body_font = label_font(20)
    fonts = [title_font, *([body_font] * (len(ABOUT_LINES) - 1))]
    rendered = [font.render(text, True, TEXT) for font, text in zip(fonts, ABOUT_LINES)]
    _blit_panel(screen, rendered, gap=8)


def _draw_quit(screen: pygame.Surface) -> None:
    font = label_font(22)
    rendered = [
        font.render("Quit the flight lab?", True, TEXT),
        label_font(18).render("Enter quits. Esc stays.", True, DIM),
    ]
    _blit_panel(screen, rendered, gap=14)


def _blit_panel(screen: pygame.Surface, lines: list[pygame.Surface], *, gap: int) -> None:
    width = max(line.get_width() for line in lines) + 64
    height = sum(line.get_height() for line in lines) + gap * (len(lines) - 1) + 56
    panel = pygame.Surface((width, height), pygame.SRCALPHA)
    panel.fill((*PANEL, PANEL_ALPHA))
    pygame.draw.rect(panel, ACCENT, panel.get_rect(), 1)
    y = 28
    for line in lines:
        panel.blit(line, ((width - line.get_width()) // 2, y))
        y += line.get_height() + gap
    screen.blit(panel, ((screen.get_width() - width) // 2, (screen.get_height() - height) // 2))
