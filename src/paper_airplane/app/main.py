"""Pygame shell: dusk field, live pre-launch pose, and the About panel.

Playback, trails, and the later analysis views are not in this loop.
"""

from __future__ import annotations

import math
import os
import time
from dataclasses import replace

import pygame

from paper_airplane.app.about import ABOUT_LINES, CAPTION, CREDIT, FOOTER, HINT
from paper_airplane.app.actors import draw_pose, draw_preview_path, load_flight_art
from paper_airplane.app.background import draw_world, load_scenery, project_root
from paper_airplane.app.camera import prelaunch_camera
from paper_airplane.app.dock import draw_buckle_banner, draw_dock, draw_dock_panel, hit_test, value_from_pointer
from paper_airplane.app.prelaunch import (
    DOCK_WIDTH,
    LaunchInputs,
    apply_preset,
    default_inputs,
    step_launch,
    toggle_mode,
)
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
from paper_airplane.simulation import Trajectory, preview

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
    pygame.key.set_repeat(180, 40)
    scenery = load_scenery()
    art = load_flight_art(scenery.launcher, project_root(), config)
    for message in scenery.warnings + art.warnings:
        print(message)
    camera = prelaunch_camera(config)
    inputs = default_inputs(config)
    trajectory, cache_key = _refresh_preview(None, None, inputs, config)
    dragging: str | None = None
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
            locked = about_open or quit_prompt
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and not locked:
                inputs, dragging = _on_pointer(inputs, event.pos, config)
            elif event.type == pygame.MOUSEMOTION and dragging is not None and not locked:
                inputs = _set_slider(inputs, dragging, event.pos[0], config)
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                dragging = None
            elif event.type == pygame.KEYDOWN:
                about_open, quit_prompt, finished = _on_key(event.key, about_open, quit_prompt)
                if finished:
                    return 0
                if not about_open and not quit_prompt:
                    inputs = _apply_launch_key(event.key, inputs, config)
        trajectory, cache_key = _refresh_preview(trajectory, cache_key, inputs, config)
        _draw_frame(
            screen,
            camera,
            config,
            scenery,
            art,
            inputs,
            trajectory,
            showing_splash=showing_splash,
            about_open=about_open,
            quit_prompt=quit_prompt,
        )
        pygame.display.flip()
        clock.tick(_TARGET_FPS)
        frames += 1
        if frame_limit is not None and frames >= frame_limit:
            return 0


def _refresh_preview(
    trajectory: Trajectory | None,
    cache_key: tuple[float, float, str] | None,
    inputs: LaunchInputs,
    config: Config,
) -> tuple[Trajectory, tuple[float, float, str]]:
    """Integrate only when V0, gamma0, or the mode changes."""
    fresh = (round(inputs.v0_m_s, 5), round(inputs.gamma0_deg, 5), inputs.mode)
    if trajectory is not None and fresh == cache_key:
        return trajectory, fresh
    path = preview(inputs.v0_m_s, math.radians(inputs.gamma0_deg), inputs.mode, config)
    return path, fresh


def _on_pointer(
    inputs: LaunchInputs,
    pos: tuple[int, int],
    config: Config,
) -> tuple[LaunchInputs, str | None]:
    name = hit_test(pos)
    if name == "mode-reference":
        return replace(inputs, mode="reference"), None
    if name == "mode-physical":
        return replace(inputs, mode="physical"), None
    if name is not None and name.startswith("preset-"):
        return apply_preset(inputs, name[-1], config), None
    if name is not None and name.startswith("slider-"):
        return _set_slider(inputs, name, pos[0], config), name
    return inputs, None


def _set_slider(inputs: LaunchInputs, name: str, x: int, config: Config) -> LaunchInputs:
    value = value_from_pointer(name, x, config)
    if name == "slider-v0":
        return replace(inputs, v0_m_s=value)
    return replace(inputs, gamma0_deg=value)


def _apply_launch_key(key: int, inputs: LaunchInputs, config: Config) -> LaunchInputs:
    if key == pygame.K_LEFT:
        return step_launch(inputs, config, gamma_steps=-1)
    if key == pygame.K_RIGHT:
        return step_launch(inputs, config, gamma_steps=1)
    if key in (pygame.K_UP, pygame.K_w):
        return step_launch(inputs, config, v_steps=1)
    if key in (pygame.K_DOWN, pygame.K_s):
        return step_launch(inputs, config, v_steps=-1)
    preset = {
        pygame.K_1: "a",
        pygame.K_KP_1: "a",
        pygame.K_2: "b",
        pygame.K_KP_2: "b",
        pygame.K_3: "c",
        pygame.K_KP_3: "c",
        pygame.K_4: "d",
        pygame.K_KP_4: "d",
    }.get(key)
    if preset is not None:
        return apply_preset(inputs, preset, config)
    if key == pygame.K_TAB:
        return toggle_mode(inputs)
    return inputs


def _draw_frame(
    screen: pygame.Surface,
    camera: object,
    config: Config,
    scenery: object,
    art: object,
    inputs: LaunchInputs,
    trajectory: Trajectory,
    *,
    showing_splash: bool,
    about_open: bool,
    quit_prompt: bool,
) -> None:
    draw_world(screen, camera, config, scenery)
    draw_preview_path(screen, camera, config, trajectory)
    if not showing_splash:
        draw_dock_panel(screen)
    draw_pose(screen, camera, config, art, inputs)
    if showing_splash:
        _draw_splash(screen)
    else:
        landing = float(trajectory.r[-1]) if inputs.mode == "physical" else None
        duration = float(trajectory.t[-1]) if landing is not None else None
        draw_dock(screen, inputs, config, landing_range_m=landing, flight_time_s=duration)
        draw_buckle_banner(screen, inputs)
        _draw_header(screen)
        if scenery.warnings or art.warnings:
            _draw_warnings(screen, scenery.warnings + art.warnings)
    _draw_footer(screen)
    if about_open:
        _draw_about(screen)
    if quit_prompt:
        _draw_quit(screen)


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
    font = label_font_fitting(CREDIT, screen.get_width() - DOCK_WIDTH - 32, 16)
    line = font.render(CREDIT, True, TEXT)
    screen.blit(line, (DOCK_WIDTH + 16, (bar_h - line.get_height()) // 2))


def _draw_footer(screen: pygame.Surface) -> None:
    font = label_font(15)
    footer = font.render(FOOTER, True, TEXT)
    footer.set_alpha(190)
    screen.blit(
        footer,
        (screen.get_width() - footer.get_width() - 16, screen.get_height() - footer.get_height() - 10),
    )
    hint = font.render(HINT, True, DIM)
    screen.blit(hint, (DOCK_WIDTH + 16, screen.get_height() - hint.get_height() - 10))


def _draw_warnings(screen: pygame.Surface, warnings: tuple[str, ...]) -> None:
    font = label_font(16)
    y = 44
    for message in warnings:
        line = font.render(message, True, WARNING)
        screen.blit(line, (DOCK_WIDTH + 16, y))
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
