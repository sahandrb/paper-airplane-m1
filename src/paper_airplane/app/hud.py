"""Telemetry, trails, the minimap, and the results strip."""

from __future__ import annotations

import math

import numpy as np
import pygame

from paper_airplane.aero import ld_max
from paper_airplane.app.camera import Camera
from paper_airplane.analysis import phugoid_metrics
from paper_airplane.app.prelaunch import DOCK_WIDTH, LINEAR_LIMIT, dash_segments, presets
from paper_airplane.app.theme import (
    DIM,
    PANEL,
    PANEL_ALPHA,
    TEXT,
    WARNING,
    label_font,
    label_font_fitting,
    number_font,
)
from paper_airplane.config import Config
from paper_airplane.equilibrium import alpha_star_deg, gamma_star_deg, v_star
from paper_airplane.linearize import HybridPath
from paper_airplane.playback import Sample, extremes
from paper_airplane.simulation import HeatmapResult, MonteCarloResult, Trajectory
from paper_airplane.trails import (
    OVERFLOW_HINT,
    PHYSICAL_HUD,
    REFERENCE_NOTE,
    TrailBook,
    legend_line,
    shows_reference_ground,
    visible_legend,
)

TELEMETRY_WIDTH = 260
MINI_W = 180
MINI_H = 90
MINI_R = (-2.5, 23.0)
MINI_H_RANGE = (-2.5, 5.5)
POINT_MASS = "point-mass: alpha fixed, no pitch inertia"


def draw_reference_ground(screen: pygame.Surface, camera: Camera, mode: str, book: TrailBook) -> None:
    """Hatch and the exact Reference caption when a path may cross below h = 0."""
    if not shows_reference_ground(mode, book):
        return
    ground_y = int(round(camera.cam_y))
    _hatch(screen, ground_y)
    x = DOCK_WIDTH + 16
    font = label_font_fitting(REFERENCE_NOTE, screen.get_width() - TELEMETRY_WIDTH - x - 24, 15)
    line = font.render(REFERENCE_NOTE, True, (226, 176, 78))
    y = min(max(ground_y + 8, 0), screen.get_height() - line.get_height() - 8)
    plate = pygame.Surface((line.get_width() + 16, line.get_height() + 8), pygame.SRCALPHA)
    plate.fill((*PANEL, 210))
    screen.blit(plate, (x, y))
    screen.blit(line, (x + 8, y + 4))


def draw_trails(
    screen: pygame.Surface,
    camera: Camera,
    config: Config,
    book: TrailBook,
) -> None:
    """World polylines under the dart. Reference samples below the ground are dashed."""
    ppm = config.pixels_per_metre
    for trail in book.trails:
        colour = _rgb(trail.colour)
        solid: list[tuple[float, float]] = []
        dashed: list[tuple[float, float]] = []

        def flush_dashed() -> None:
            for start, end in dash_segments(dashed, dash=8.0, gap=6.0):
                pygame.draw.line(screen, colour, _px(start), _px(end), 2)

        for range_m, height_m in trail.points:
            point = camera.to_screen(range_m, height_m, ppm)
            below = trail.mode == "reference" and height_m < 0.0
            if below:
                if solid:
                    dashed.append(solid[-1])
                    solid = []
                dashed.append(point)
            else:
                if dashed:
                    flush_dashed()
                    solid.append(dashed[-1])
                    dashed = []
                solid.append(point)
            if len(solid) == 2:
                pygame.draw.line(screen, colour, _px(solid[0]), _px(solid[1]), 2)
                solid = [solid[1]]
        if dashed:
            flush_dashed()


def draw_legend(screen: pygame.Surface, book: TrailBook, config: Config) -> None:
    rows = visible_legend(book, config)
    if not rows and not book.overflow:
        return
    font = number_font(14)
    lines = [legend_line(trail) for trail in rows]
    if book.overflow:
        lines.append(OVERFLOW_HINT)
    width = max(font.size(line)[0] for line in lines) + 28
    height = len(lines) * 18 + 10
    x = DOCK_WIDTH + 12
    y = 108
    plate = pygame.Surface((width, height), pygame.SRCALPHA)
    plate.fill((*PANEL, 210))
    screen.blit(plate, (x, y))
    text_rows = lines[: len(rows)]
    for index, (trail, line) in enumerate(zip(rows, text_rows)):
        pygame.draw.rect(screen, _rgb(trail.colour), (x + 8, y + 8 + index * 18, 12, 12))
        screen.blit(font.render(line, True, TEXT), (x + 24, y + 6 + index * 18))
    if book.overflow:
        screen.blit(font.render(OVERFLOW_HINT, True, DIM), (x + 8, y + 6 + len(rows) * 18))


def draw_telemetry(
    screen: pygame.Surface,
    camera: Camera,
    config: Config,
    sample: Sample,
    book: TrailBook,
    *,
    landed: bool,
) -> None:
    """Right-hand numbers from the true state, plus the minimap."""
    panel = pygame.Surface((TELEMETRY_WIDTH, screen.get_height()), pygame.SRCALPHA)
    panel.fill((*PANEL, PANEL_ALPHA))
    origin_x = screen.get_width() - TELEMETRY_WIDTH
    screen.blit(panel, (origin_x, 0))
    speed = v_star(config)
    font = number_font(15)
    lines = (
        f"t = {sample.t:.2f} s",
        f"V = {sample.v:.2f} m/s  ({sample.v / speed:.2f} V*)",
        f"gamma = {math.degrees(sample.gamma):.2f} deg",
        f"theta = {math.degrees(sample.theta):.2f} deg",
        f"alpha = {alpha_star_deg(config):.2f} deg",
        f"h = {sample.h:.2f} m",
        f"r = {sample.r:.2f} m",
        f"q = {sample.q_dyn:.2f} Pa",
        f"L/D = {ld_max(config):.2f}",
        f"KE = {sample.ke:.4f} J",
        f"PE = {sample.pe:.4f} J",
        f"E = {sample.energy:.4f} J",
    )
    y = 48
    for line in lines:
        screen.blit(font.render(line, True, TEXT), (origin_x + 12, y))
        y += 18
    screen.blit(label_font(13).render(POINT_MASS, True, DIM), (origin_x + 12, y + 2))
    y += 24
    if landed:
        text = PHYSICAL_HUD.format(range_m=sample.r, flight_time_s=sample.t)
        y = _blit_fitted(screen, text, origin_x + 12, y, TELEMETRY_WIDTH - 24)
    _minimap(screen, pygame.Rect(origin_x + 12, y + 8, MINI_W, MINI_H), camera, config, sample, book)


def draw_results(
    screen: pygame.Surface,
    path: Trajectory,
    t_sim: float,
    mode: str,
    sample: Sample,
) -> None:
    """Freeze strip: time, range, extremes, and the four actions."""
    v_min, v_max, g_min, g_max = extremes(path, t_sim)
    if mode in ("reference", "phugoid"):
        range_text = f"r(6 s) = {sample.r:.2f} m"
    else:
        range_text = f"range = {sample.r:.2f} m"
    summary = (
        f"t = {sample.t:.2f} s   {range_text}   "
        f"V {v_min:.2f}..{v_max:.2f} m/s   gamma {g_min:.1f}..{g_max:.1f} deg"
    )
    y = screen.get_height() - 108
    plate = pygame.Surface((screen.get_width() - DOCK_WIDTH - TELEMETRY_WIDTH - 16, 52), pygame.SRCALPHA)
    plate.fill((*PANEL, 220))
    screen.blit(plate, (DOCK_WIDTH + 8, y))
    screen.blit(number_font(14).render(summary, True, TEXT), (DOCK_WIDTH + 16, y + 4))
    for name, rect in result_hits(screen.get_width(), screen.get_height()):
        label = {"plots": "Show plots", "export": "Export", "reset": "RESET", "restart": "RESTART"}[name]
        pygame.draw.rect(screen, (36, 44, 58), rect, border_radius=4)
        pygame.draw.rect(screen, (76, 155, 232), rect, 1, border_radius=4)
        text = label_font(13).render(label, True, TEXT)
        screen.blit(text, text.get_rect(center=rect.center))


def result_hits(width: int, height: int) -> tuple[tuple[str, pygame.Rect], ...]:
    y = height - 80
    specs = (("plots", "Show plots", 92), ("export", "Export", 72), ("reset", "RESET", 72), ("restart", "RESTART", 84))
    right = width - TELEMETRY_WIDTH - 16
    boxes: list[tuple[str, pygame.Rect]] = []
    for name, _label, box_w in reversed(specs):
        right -= box_w
        boxes.append((name, pygame.Rect(right, y, box_w - 6, 24)))
        right -= 4
    return tuple(reversed(boxes))


def legend_scroll_hit(pos: tuple[int, int]) -> bool:
    return pos[0] >= DOCK_WIDTH and pos[1] < 280


def _hatch(screen: pygame.Surface, ground_y: int) -> None:
    if ground_y >= screen.get_height():
        return
    top = max(ground_y, 0)
    overlay = pygame.Surface((screen.get_width(), screen.get_height() - top), pygame.SRCALPHA)
    colour = (201, 210, 200, 50)
    for offset in range(-screen.get_height(), screen.get_width(), 14):
        pygame.draw.line(overlay, colour, (offset, 0), (offset + 80, overlay.get_height()), 1)
    screen.blit(overlay, (0, top))


def _minimap(
    screen: pygame.Surface,
    rect: pygame.Rect,
    camera: Camera,
    config: Config,
    sample: Sample,
    book: TrailBook,
) -> None:
    pygame.draw.rect(screen, (8, 12, 20), rect)
    pygame.draw.rect(screen, DIM, rect, 1)
    for trail in book.trails:
        mapped = [_mini(range_m, height_m, rect) for range_m, height_m in trail.points]
        if len(mapped) >= 2:
            pygame.draw.lines(screen, _rgb(trail.colour), False, mapped, 1)
    view = _view_rect(camera, config, rect).clip(rect)
    if view.width > 0 and view.height > 0:
        pygame.draw.rect(screen, TEXT, view, 1)
    pygame.draw.circle(screen, (255, 255, 255), _mini(sample.r, sample.h, rect), 3)


def _view_rect(camera: Camera, config: Config, mini: pygame.Rect) -> pygame.Rect:
    ppm = config.pixels_per_metre
    r_left = (0.0 - camera.cam_x) / ppm
    r_right = (config.window_width_px - camera.cam_x) / ppm
    h_top = (camera.cam_y - 0.0) / ppm
    h_bottom = (camera.cam_y - config.window_height_px) / ppm
    x0, y0 = _mini(r_left, h_top, mini)
    x1, y1 = _mini(r_right, h_bottom, mini)
    return pygame.Rect(min(x0, x1), min(y0, y1), abs(x1 - x0), abs(y1 - y0))


def _mini(range_m: float, height_m: float, rect: pygame.Rect) -> tuple[int, int]:
    r0, r1 = MINI_R
    h0, h1 = MINI_H_RANGE
    x = rect.x + (range_m - r0) / (r1 - r0) * rect.w
    y = rect.y + (h1 - height_m) / (h1 - h0) * rect.h
    return int(round(x)), int(round(y))


def _blit_fitted(screen: pygame.Surface, text: str, x: int, y: int, max_width: int) -> int:
    """Draw one HUD sentence, breaking after the comma when the panel is narrow."""
    font = number_font(14)
    if font.size(text)[0] <= max_width or ",  " not in text:
        screen.blit(font.render(text, True, TEXT), (x, y))
        return y + 20
    head, tail = text.split(",  ", 1)
    screen.blit(font.render(f"{head},", True, TEXT), (x, y))
    screen.blit(font.render(tail, True, TEXT), (x, y + 16))
    return y + 36


def _rgb(colour: str) -> tuple[int, int, int]:
    text = colour.removeprefix("#")
    return (int(text[0:2], 16), int(text[2:4], 16), int(text[4:6], 16))


def _px(point: tuple[float, float]) -> tuple[int, int]:
    return (int(round(point[0])), int(round(point[1])))


def draw_hybrid(screen: pygame.Surface, camera: Camera, config: Config, path: HybridPath) -> None:
    """Full linear path, dashed, under the dart. It is not a legend row."""
    points = [camera.to_screen(float(path.r[i]), float(path.h[i]), config.pixels_per_metre) for i in range(len(path.t))]
    for start, end in dash_segments(points, dash=8.0, gap=6.0):
        pygame.draw.line(screen, (226, 176, 78), _px(start), _px(end), 2)


def draw_scatter(screen: pygame.Surface, camera: Camera, config: Config, result: MonteCarloResult) -> None:
    """Faint sample paths and a landing rug. These paths are not stored as trails."""
    ppm = config.pixels_per_metre
    colour = (176, 184, 196)
    for flight in result.trajectories:
        mapped = [camera.to_screen(float(flight.r[i]), float(flight.h[i]), ppm) for i in range(len(flight.t))]
        if len(mapped) >= 2:
            pygame.draw.lines(screen, colour, False, [_px(point) for point in mapped], 1)
        if flight.terminated_by == "ground":
            landing = camera.to_screen(float(flight.r[-1]), 0.0, ppm)
            pygame.draw.line(screen, (232, 220, 170), _px(landing), (int(round(landing[0])), int(round(landing[1])) - 8), 2)


def draw_energy_strip(screen: pygame.Surface, sample: Sample) -> None:
    """KE, PE, and total for the played sample, on the telemetry panel."""
    font = number_font(14)
    x = screen.get_width() - TELEMETRY_WIDTH + 12
    y = 530
    for text in (
        f"KE = {sample.ke:.4f} J",
        f"PE = {sample.pe:.4f} J",
        f"E = {sample.energy:.4f} J",
    ):
        screen.blit(font.render(text, True, TEXT), (x, y))
        y += 18


def draw_phugoid_notes(screen: pygame.Surface, config: Config, *, outside: bool) -> None:
    """Jacobian readout, and the small-perturbation sentence when it applies."""
    font = number_font(14)
    x = screen.get_width() - TELEMETRY_WIDTH + 12
    y = 400
    for piece in phugoid_metrics(config).split("    "):
        screen.blit(font.render(piece, True, TEXT), (x, y))
        y += 18
    if outside:
        note = label_font(14)
        for line in _wrap_note(LINEAR_LIMIT, note, TELEMETRY_WIDTH - 24):
            screen.blit(note.render(line, True, WARNING), (x, y))
            y += 18


def _wrap_note(text: str, font: pygame.font.Font, max_width: int) -> list[str]:
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


def draw_assumption(screen: pygame.Surface, result: MonteCarloResult) -> None:
    """The exact scatter sentence, plus how many samples hit the speed guard."""
    font = label_font(14)
    first = font.render(result.assumption, True, DIM)
    second = font.render(f"V → 0 before landing: {result.speed_collapse_count}", True, DIM)
    y = screen.get_height() - 188
    screen.blit(first, (DOCK_WIDTH + 16, y))
    screen.blit(second, (DOCK_WIDTH + 16, y + 18))


def draw_progress(screen: pygame.Surface, caption: str, fraction: float) -> None:
    """A short bar while a grid or a Monte Carlo set is integrating."""
    width = 420
    height = 36
    x = (screen.get_width() - width) // 2
    y = (screen.get_height() - height) // 2
    plate = pygame.Surface((width, height), pygame.SRCALPHA)
    plate.fill((*PANEL, 230))
    screen.blit(plate, (x, y))
    font = label_font(15)
    screen.blit(font.render(caption, True, TEXT), (x + 12, y + 8))
    span = width - 24
    pygame.draw.rect(screen, DIM, (x + 12, y + 26, span, 4))
    pygame.draw.rect(screen, (76, 155, 232), (x + 12, y + 26, int(span * min(1.0, max(0.0, fraction))), 4))


def draw_heatmap_view(
    screen: pygame.Surface,
    grid: HeatmapResult,
    config: Config,
    *,
    v0_m_s: float,
    gamma0_deg: float,
) -> None:
    """Landing range in place of the sky. The peak is whatever the grid computed."""
    rect = pygame.Rect(DOCK_WIDTH + 8, 44, screen.get_width() - DOCK_WIDTH - TELEMETRY_WIDTH - 16, screen.get_height() - 120)
    screen.fill((8, 12, 22), rect)
    finite = grid.range_m[np.isfinite(grid.range_m)]
    low = float(np.min(finite)) if finite.size else 0.0
    high = float(np.max(finite)) if finite.size else 1.0
    span = high - low if high > low else 1.0
    cell_w = rect.w / grid.range_m.shape[1]
    cell_h = rect.h / grid.range_m.shape[0]
    for i in range(grid.range_m.shape[0]):
        for j in range(grid.range_m.shape[1]):
            value = float(grid.range_m[i, j])
            colour = (40, 44, 52) if not math.isfinite(value) else _range_colour((value - low) / span)
            pygame.draw.rect(
                screen,
                colour,
                (rect.x + j * cell_w, rect.y + (grid.range_m.shape[0] - 1 - i) * cell_h, cell_w + 1, cell_h + 1),
            )
    _mark(screen, rect, grid, v_star(config), gamma_star_deg(config), (255, 255, 255))
    for name, (speed, glide) in presets(config).items():
        _mark(screen, rect, grid, speed, glide, (20, 20, 20))
        del name
    _mark(screen, rect, grid, v0_m_s, gamma0_deg, (232, 80, 70))
    caption = label_font(14).render("Landing range. Recompute builds the grid again.", True, TEXT)
    screen.blit(caption, (rect.x + 8, rect.bottom - 22))


def _range_colour(fraction: float) -> tuple[int, int, int]:
    fraction = min(1.0, max(0.0, fraction))
    return (
        int(20 + 210 * fraction),
        int(50 + 140 * (1.0 - abs(fraction - 0.5) * 2.0)),
        int(180 * (1.0 - fraction)),
    )


def _mark(
    screen: pygame.Surface,
    rect: pygame.Rect,
    grid: HeatmapResult,
    speed: float,
    glide_deg: float,
    colour: tuple[int, int, int],
) -> None:
    speeds = grid.v0_m_s
    angles = np.degrees(grid.gamma0_rad)
    if speeds[-1] == speeds[0] or angles[-1] == angles[0]:
        return
    x = rect.x + (speed - float(speeds[0])) / (float(speeds[-1]) - float(speeds[0])) * rect.w
    y = rect.y + (float(angles[-1]) - glide_deg) / (float(angles[-1]) - float(angles[0])) * rect.h
    pygame.draw.circle(screen, colour, (int(round(x)), int(round(y))), 5, 1)
