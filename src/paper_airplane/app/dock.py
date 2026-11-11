"""Bottom launch bar: mode, sliders, presets, and readouts. It stays on the ground."""

from __future__ import annotations

from dataclasses import dataclass

import pygame

from paper_airplane.app.prelaunch import (
    MODE_LABELS,
    N_MAX,
    N_MIN,
    N_STEP,
    SIGMA_G_MAX,
    SIGMA_G_MIN,
    SIGMA_G_STEP,
    SIGMA_V_MAX,
    SIGMA_V_MIN,
    SIGMA_V_STEP,
    LaunchInputs,
    buckle_warning,
    readout_lines,
    scale_caption,
    slider_value,
)
from paper_airplane.trails import DOCK_HINT, REFERENCE_NOTE
from paper_airplane.app.theme import ACCENT, DIM, OK, PANEL, TEXT, WARNING, label_font, number_font
from paper_airplane.config import Config

BAR_TOP = 556
BAR_BOTTOM = 712


@dataclass(frozen=True)
class HitBox:
    name: str
    rect: pygame.Rect


def dock_hits(ground_y: int = 548) -> tuple[HitBox, ...]:
    """Click targets on the ground bar. Nothing here sits above the horizon."""
    row = ground_y + 16
    track = ground_y + 72
    return (
        HitBox("preset-a", pygame.Rect(16, row, 48, 24)),
        HitBox("preset-b", pygame.Rect(70, row, 48, 24)),
        HitBox("preset-c", pygame.Rect(124, row, 48, 24)),
        HitBox("preset-d", pygame.Rect(178, row, 48, 24)),
        HitBox("mode", pygame.Rect(240, row, 168, 24)),
        HitBox("launch", pygame.Rect(500, row, 88, 24)),
        HitBox("reset", pygame.Rect(596, row, 88, 24)),
        HitBox("restart", pygame.Rect(692, row, 100, 24)),
        HitBox("slider-v0", pygame.Rect(16, track, 460, 20)),
        HitBox("slider-gamma", pygame.Rect(496, track, 420, 20)),
    )


def scatter_hits(ground_y: int = 548) -> tuple[HitBox, ...]:
    """Monte Carlo steppers, on the ground bar."""
    y = ground_y + 112
    return (
        HitBox("scatter-n", pygame.Rect(16, y, 250, 18)),
        HitBox("scatter-sv", pygame.Rect(280, y, 250, 18)),
        HitBox("scatter-sg", pygame.Rect(544, y, 250, 18)),
    )


def recompute_hit(ground_y: int = 548) -> HitBox:
    return HitBox("recompute", pygame.Rect(16, ground_y + 112, 150, 24))


def hit_test(
    pos: tuple[int, int],
    *,
    mode: str = "reference",
    height: int = 720,
    ground_y: int = 548,
) -> str | None:
    del height
    boxes: tuple[HitBox, ...] = dock_hits(ground_y)
    if mode == "montecarlo":
        boxes = boxes + scatter_hits(ground_y)
    elif mode == "heatmap":
        boxes = boxes + (recompute_hit(ground_y),)
    for box in boxes:
        if box.rect.collidepoint(pos):
            return box.name
    return None


def value_from_pointer(name: str, x: int, config: Config, height: int = 720) -> float:
    """Slider value for a pointer x, snapped to that slider's step."""
    del height
    track = _track(name, config.ground_screen_y0)
    fraction = 0.0 if track.width == 0 else (x - track.x) / track.width
    if name == "slider-v0":
        return slider_value(fraction, config.v0_min_m_s, config.v0_max_m_s, config.v0_step_m_s)
    if name == "scatter-n":
        return slider_value(fraction, N_MIN, N_MAX, N_STEP)
    if name == "scatter-sv":
        return slider_value(fraction, SIGMA_V_MIN, SIGMA_V_MAX, SIGMA_V_STEP)
    if name == "scatter-sg":
        return slider_value(fraction, SIGMA_G_MIN, SIGMA_G_MAX, SIGMA_G_STEP)
    return slider_value(fraction, config.gamma0_min_deg, config.gamma0_max_deg, config.gamma0_step_deg)


def draw_dock(
    screen: pygame.Surface,
    inputs: LaunchInputs,
    config: Config,
    *,
    landing_range_m: float | None,
    flight_time_s: float | None,
    speed: float = 1.0,
    show_readouts: bool = True,
    show_reference: bool = False,
    sound_muted: bool = False,
) -> None:
    """One bar over the ground strip. Call this after the airplane."""
    top = config.ground_screen_y0 + 8
    height = BAR_BOTTOM - top
    plate = pygame.Surface((screen.get_width(), height), pygame.SRCALPHA)
    plate.fill((*PANEL, 190))
    screen.blit(plate, (0, top))
    _draw_presets(screen, config.ground_screen_y0)
    _draw_modes(screen, inputs, config.ground_screen_y0)
    screen.blit(number_font(14).render(f"{speed:g}×", True, TEXT), (420, top + 12))
    sound_label = "N muted" if sound_muted else "N ♪"
    screen.blit(label_font(13).render(sound_label, True, DIM), (808, top + 14))
    _button(screen, _track("launch", config.ground_screen_y0), "LAUNCH", False, ACCENT)
    _button(screen, _track("reset", config.ground_screen_y0), "RESET", False, ACCENT)
    _button(screen, _track("restart", config.ground_screen_y0), "RESTART", False, ACCENT)
    _draw_slider(
        screen,
        "slider-v0",
        "V0",
        inputs.v0_m_s,
        config.v0_min_m_s,
        config.v0_max_m_s,
        config.ground_screen_y0,
    )
    _draw_slider(
        screen,
        "slider-gamma",
        "gamma0",
        inputs.gamma0_deg,
        config.gamma0_min_deg,
        config.gamma0_max_deg,
        config.ground_screen_y0,
    )
    if inputs.mode == "montecarlo":
        _draw_scatter_controls(screen, inputs, config.ground_screen_y0)
    elif inputs.mode == "heatmap":
        _button(screen, recompute_hit(config.ground_screen_y0).rect, "Recompute", False, ACCENT)
    elif show_readouts:
        _draw_readouts(screen, inputs, config, landing_range_m, flight_time_s)
    _draw_notes(screen, config, show_reference=show_reference)


def draw_buckle_banner(screen: pygame.Surface, inputs: LaunchInputs) -> None:
    """The wing note stays in the top-left sky, well above the launcher."""
    warning = buckle_warning(inputs.v0_m_s)
    if warning is None:
        return
    x = 12
    font = label_font(13)
    lines = _wrap(warning, font, 460)
    width = max(font.size(line)[0] for line in lines) + 16
    height = len(lines) * 16 + 8
    plate = pygame.Surface((width, height), pygame.SRCALPHA)
    plate.fill((*PANEL, 200))
    screen.blit(plate, (x, 24))
    y = 28
    for line in lines:
        screen.blit(font.render(line, True, WARNING), (x + 8, y))
        y += 16


def _draw_readouts(
    screen: pygame.Surface,
    inputs: LaunchInputs,
    config: Config,
    landing_range_m: float | None,
    flight_time_s: float | None,
) -> None:
    font = number_font(12)
    lines = readout_lines(inputs, config, landing_range_m=landing_range_m, flight_time_s=flight_time_s)
    text = "   ".join(lines[:3])
    screen.blit(font.render(text, True, TEXT), (16, config.ground_screen_y0 + 124))


def _draw_notes(screen: pygame.Surface, config: Config, *, show_reference: bool) -> None:
    y = config.ground_screen_y0 + 148
    font = label_font(12)
    screen.blit(font.render(DOCK_HINT, True, DIM), (16, y))
    if show_reference:
        screen.blit(font.render(REFERENCE_NOTE, True, (226, 176, 78)), (300, y))
    caption = number_font(12).render(scale_caption(config), True, TEXT)
    length = int(round(config.pixels_per_metre))
    x = screen.get_width() - length - 36
    bar_y = config.ground_screen_y0 + 108
    screen.blit(caption, (x + length - caption.get_width(), bar_y - 14))
    pygame.draw.line(screen, TEXT, (x, bar_y), (x + length, bar_y), 2)
    pygame.draw.line(screen, TEXT, (x, bar_y - 4), (x, bar_y + 4), 2)
    pygame.draw.line(screen, TEXT, (x + length, bar_y - 4), (x + length, bar_y + 4), 2)
    metres = number_font(12).render("1 m", True, TEXT)
    screen.blit(metres, (x + length + 6, bar_y - metres.get_height() // 2))


def _track(name: str, ground_y: int = 548) -> pygame.Rect:
    for box in (*dock_hits(ground_y), *scatter_hits(ground_y), recompute_hit(ground_y)):
        if box.name == name:
            return box.rect
    raise KeyError(name)


def _draw_modes(screen: pygame.Surface, inputs: LaunchInputs, ground_y: int) -> None:
    _button(screen, _track("mode", ground_y), MODE_LABELS.get(inputs.mode, inputs.mode), True, OK)


def _draw_presets(screen: pygame.Surface, ground_y: int) -> None:
    for name, label in zip(("preset-a", "preset-b", "preset-c", "preset-d"), ("A", "B", "C", "D")):
        _button(screen, _track(name, ground_y), label, False, ACCENT)


def _draw_scatter_controls(screen: pygame.Surface, inputs: LaunchInputs, ground_y: int) -> None:
    _draw_slider(screen, "scatter-n", "N", inputs.n_throws, N_MIN, N_MAX, ground_y)
    _draw_slider(screen, "scatter-sv", "sigma V", inputs.sigma_v_m_s, SIGMA_V_MIN, SIGMA_V_MAX, ground_y)
    _draw_slider(screen, "scatter-sg", "sigma gamma", inputs.sigma_gamma_deg, SIGMA_G_MIN, SIGMA_G_MAX, ground_y)


def _draw_slider(
    screen: pygame.Surface,
    name: str,
    caption: str,
    value: float,
    low: float,
    high: float,
    ground_y: int = 548,
) -> None:
    track = _track(name, ground_y)
    label = label_font(12).render(caption, True, DIM)
    screen.blit(label, (track.x, track.y - 14))
    line_y = track.centery
    pygame.draw.line(screen, DIM, (track.left, line_y), (track.right, line_y), 3)
    span = high - low
    fraction = 0.0 if span == 0 else (value - low) / span
    knob_x = track.left + fraction * track.width
    pygame.draw.circle(screen, ACCENT, (int(round(knob_x)), line_y), 6)


def _button(screen: pygame.Surface, rect: pygame.Rect, caption: str, selected: bool, colour: tuple[int, int, int]) -> None:
    pygame.draw.rect(screen, colour if selected else (36, 44, 58), rect, border_radius=4)
    pygame.draw.rect(screen, colour, rect, 1, border_radius=4)
    text = label_font(13).render(caption, True, TEXT)
    screen.blit(text, text.get_rect(center=rect.center))


def _wrap(text: str, font: pygame.font.Font, max_width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        trial = word if not current else f"{current} {word}"
        if font.size(trial)[0] <= max_width:
            current = trial
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines
