"""Left-hand launch dock: mode, sliders, presets, and readouts."""

from __future__ import annotations

from dataclasses import dataclass

import pygame

from paper_airplane.app.prelaunch import (
    DOCK_WIDTH,
    LaunchInputs,
    buckle_warning,
    readout_lines,
    slider_value,
)
from paper_airplane.app.theme import ACCENT, DIM, OK, PANEL, PANEL_ALPHA, TEXT, WARNING, label_font, number_font
from paper_airplane.config import Config


@dataclass(frozen=True)
class HitBox:
    name: str
    rect: pygame.Rect


def dock_hits() -> tuple[HitBox, ...]:
    """Click targets. Slider boxes are taller than the drawn track."""
    return (
        HitBox("mode-reference", pygame.Rect(16, 48, 128, 26)),
        HitBox("mode-physical", pygame.Rect(152, 48, 128, 26)),
        HitBox("preset-a", pygame.Rect(16, 82, 64, 26)),
        HitBox("preset-b", pygame.Rect(84, 82, 64, 26)),
        HitBox("preset-c", pygame.Rect(152, 82, 64, 26)),
        HitBox("preset-d", pygame.Rect(220, 82, 64, 26)),
        HitBox("slider-v0", pygame.Rect(16, 128, DOCK_WIDTH - 32, 22)),
        HitBox("slider-gamma", pygame.Rect(16, 176, DOCK_WIDTH - 32, 22)),
    )


def hit_test(pos: tuple[int, int]) -> str | None:
    for box in dock_hits():
        if box.rect.collidepoint(pos):
            return box.name
    return None


def value_from_pointer(name: str, x: int, config: Config) -> float:
    """Slider value for a pointer x, snapped to that slider's step."""
    track = _track(name)
    fraction = 0.0 if track.width == 0 else (x - track.x) / track.width
    if name == "slider-v0":
        return slider_value(fraction, config.v0_min_m_s, config.v0_max_m_s, config.v0_step_m_s)
    return slider_value(fraction, config.gamma0_min_deg, config.gamma0_max_deg, config.gamma0_step_deg)


def draw_dock_panel(screen: pygame.Surface) -> None:
    """Full-height translucent column. The airplane is drawn over it."""
    panel = pygame.Surface((DOCK_WIDTH, screen.get_height()), pygame.SRCALPHA)
    panel.fill((*PANEL, PANEL_ALPHA))
    screen.blit(panel, (0, 0))


def draw_dock(
    screen: pygame.Surface,
    inputs: LaunchInputs,
    config: Config,
    *,
    landing_range_m: float | None,
    flight_time_s: float | None,
) -> None:
    """Buttons, sliders, and readouts. Call this after the airplane so the numbers stay visible."""
    _draw_modes(screen, inputs)
    _draw_presets(screen)
    _draw_slider(screen, "slider-v0", "V0", inputs.v0_m_s, config.v0_min_m_s, config.v0_max_m_s)
    _draw_slider(
        screen,
        "slider-gamma",
        "gamma0",
        inputs.gamma0_deg,
        config.gamma0_min_deg,
        config.gamma0_max_deg,
    )
    font = number_font(15)
    lines = readout_lines(
        inputs,
        config,
        landing_range_m=landing_range_m,
        flight_time_s=flight_time_s,
    )
    block_h = len(lines) * 18 + 12
    y = screen.get_height() - block_h - 14
    _backing(screen, pygame.Rect(8, y - 6, DOCK_WIDTH - 16, block_h))
    for line in lines:
        surf = font.render(line, True, TEXT)
        screen.blit(surf, (16, y))
        y += surf.get_height() + 2


def draw_buckle_banner(screen: pygame.Surface, inputs: LaunchInputs) -> None:
    """The wing note sits in the open sky, clear of the ramp and the dart."""
    warning = buckle_warning(inputs.v0_m_s)
    if warning is None:
        return
    x = DOCK_WIDTH + 16
    max_width = screen.get_width() - x - 16
    font = label_font(15)
    lines = _wrap(warning, font, max_width)
    width = max(font.size(line)[0] for line in lines) + 20
    height = len(lines) * 20 + 12
    plate = pygame.Surface((width, height), pygame.SRCALPHA)
    plate.fill((*PANEL, 220))
    screen.blit(plate, (x, 46))
    y = 52
    for line in lines:
        screen.blit(font.render(line, True, WARNING), (x + 10, y))
        y += 20


def _backing(screen: pygame.Surface, rect: pygame.Rect) -> None:
    plate = pygame.Surface(rect.size, pygame.SRCALPHA)
    plate.fill((*PANEL, 230))
    screen.blit(plate, rect.topleft)


def _track(name: str) -> pygame.Rect:
    for box in dock_hits():
        if box.name == name:
            return box.rect
    raise KeyError(name)


def _draw_modes(screen: pygame.Surface, inputs: LaunchInputs) -> None:
    _button(screen, dock_hits()[0].rect, "Reference", inputs.mode == "reference", OK)
    _button(screen, dock_hits()[1].rect, "Physical", inputs.mode == "physical", OK)


def _draw_presets(screen: pygame.Surface) -> None:
    for box, label in zip(dock_hits()[2:6], ("A", "B", "C", "D")):
        _button(screen, box.rect, label, False, ACCENT)


def _draw_slider(
    screen: pygame.Surface,
    name: str,
    caption: str,
    value: float,
    low: float,
    high: float,
) -> None:
    track = _track(name)
    label = label_font(14).render(caption, True, DIM)
    screen.blit(label, (track.x, track.y - 16))
    line_y = track.centery
    pygame.draw.line(screen, DIM, (track.left, line_y), (track.right, line_y), 3)
    span = high - low
    fraction = 0.0 if span == 0 else (value - low) / span
    knob_x = track.left + fraction * track.width
    pygame.draw.circle(screen, ACCENT, (int(round(knob_x)), line_y), 7)


def _button(screen: pygame.Surface, rect: pygame.Rect, caption: str, selected: bool, colour: tuple[int, int, int]) -> None:
    pygame.draw.rect(screen, colour if selected else (36, 44, 58), rect, border_radius=4)
    pygame.draw.rect(screen, colour, rect, 1, border_radius=4)
    text = label_font(14).render(caption, True, TEXT)
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
