"""Colours and fonts for the flight-lab window."""

from __future__ import annotations

import pygame

SKY_TOP = (0x0B, 0x2A, 0x6B)
SKY_HORIZON = (0xE0, 0x7A, 0x3A)
GROUND_FALLBACK = (0x1A, 0x2A, 0x24)
TICK = (0xC9, 0xD2, 0xC8)
PANEL = (12, 16, 28)
PANEL_ALPHA = 210
TEXT = (0xE8, 0xED, 0xF5)
DIM = (0x9A, 0xA6, 0xB2)
ACCENT = (0x4C, 0x9B, 0xE8)
WARNING = (0xE8, 0x5D, 0x4C)
OK = (0x5D, 0xBE, 0x7E)
PREVIEW = (0xC5, 0xD0, 0xDC)

_LABEL_FACES = ("Segoe UI", "DejaVu Sans", "Helvetica")
_NUMBER_FACES = ("Consolas", "DejaVu Sans Mono", "Menlo")
_chosen: dict[tuple[str, ...], str | None] = {}


def _match(candidates: tuple[str, ...]) -> str | None:
    cached = _chosen.get(candidates)
    if candidates in _chosen:
        return cached
    if not pygame.font.get_init():
        pygame.font.init()
    installed = set(pygame.font.get_fonts())
    found = None
    for name in candidates:
        if name.lower().replace(" ", "") in installed:
            found = name
            break
    _chosen[candidates] = found
    return found


def _font(candidates: tuple[str, ...], size: int) -> pygame.font.Font:
    name = _match(candidates)
    if name is None:
        return pygame.font.Font(None, size)
    return pygame.font.SysFont(name, size)


def label_font(size: int) -> pygame.font.Font:
    """Segoe UI, DejaVu Sans, or Helvetica for words."""
    return _font(_LABEL_FACES, size)


def number_font(size: int) -> pygame.font.Font:
    """Consolas, DejaVu Sans Mono, or Menlo for numbers."""
    return _font(_NUMBER_FACES, size)


def label_font_fitting(text: str, max_width: int, size: int) -> pygame.font.Font:
    """Largest label font at or below ``size`` that keeps ``text`` on one line."""
    while size > 12:
        font = label_font(size)
        if font.size(text)[0] <= max_width:
            return font
        size -= 1
    return label_font(12)
