"""World-coordinate trails and the legend text. No display library."""

from __future__ import annotations

import math
from dataclasses import dataclass, field, replace

from paper_airplane.config import Config
from paper_airplane.simulation import Trajectory

TRAIL_COLOURS: tuple[str, ...] = (
    "#0072BD",
    "#D95319",
    "#EDB120",
    "#7E2F8E",
    "#77AC30",
    "#4DBEEE",
    "#A2142F",
    "#D07C7C",
)

REFERENCE_NOTE = (
    "Reference mode: integration continues below h = 0 (professor / Stengel, tf = 6 s)."
)
OVERFLOW_HINT = "Oldest trail dropped."
DOCK_HINT = "RESET clears trails. RESTART flies again and keeps them."
PHYSICAL_HUD = "range = {range_m:.2f} m,  flight time = {flight_time_s:.2f} s"


@dataclass(frozen=True)
class Trail:
    """One stored flight. ``complete`` means the clip reached its last sample."""

    colour: str
    v0_m_s: float
    gamma0_deg: float
    mode: str
    tag: str
    points: tuple[tuple[float, float], ...] = ()
    range_m: float | None = None
    complete: bool = False
    caption: str = ""


@dataclass(frozen=True)
class TrailBook:
    trails: tuple[Trail, ...] = ()
    colour_index: int = 0
    scroll: int = 0
    overflow: bool = False


@dataclass
class Session:
    """Playback state. The sliders live outside this object and are not cleared."""

    phase: str = "prelaunch"
    speed: float = 1.0
    t_sim: float = 0.0
    flight: Trajectory | None = None
    flight_v0: float = 0.0
    flight_gamma_deg: float = 0.0
    flight_mode: str = "reference"
    book: TrailBook = field(default_factory=TrailBook)
    note: str = ""


def begin_trail(book: TrailBook, v0: float, gamma_deg: float, mode: str, config: Config, tag: str = "") -> TrailBook:
    """Append a run that does not yet know its range."""
    trail = Trail(
        colour=TRAIL_COLOURS[book.colour_index % len(TRAIL_COLOURS)],
        v0_m_s=v0,
        gamma0_deg=gamma_deg,
        mode=mode,
        tag=tag,
    )
    return _push(book, trail, config)


def paint_active(
    book: TrailBook,
    points: tuple[tuple[float, float], ...],
    range_m: float | None,
    complete: bool,
    caption: str | None = None,
) -> TrailBook:
    """Replace the points of the trail that is currently playing."""
    if not book.trails:
        return book
    active = replace(
        book.trails[-1],
        points=points,
        range_m=range_m,
        complete=complete,
        caption=book.trails[-1].caption if caption is None else caption,
    )
    return replace(book, trails=book.trails[:-1] + (active,))


def add_finished_reference(
    book: TrailBook,
    tag: str,
    v0: float,
    gamma_deg: float,
    path: Trajectory,
    config: Config,
) -> TrailBook:
    """One Reference A–D trail, already finished, with no playback."""
    started = begin_trail(book, v0, gamma_deg, "reference", config, tag)
    points = tuple((float(path.r[i]), float(path.h[i])) for i in range(len(path.t)))
    return paint_active(started, points, float(path.r[-1]), True)


def reset_book() -> TrailBook:
    """Drop every trail. The next launch starts the colour cycle again."""
    return TrailBook()


def cleared(session: Session) -> Session:
    """RESET: back to the rail, no trails, sliders untouched."""
    return Session(speed=session.speed)


def returned(session: Session) -> Session:
    """RESTART: back to the rail, trails kept."""
    return Session(speed=session.speed, book=session.book)


def scroll_legend(book: TrailBook, steps: int, config: Config) -> TrailBook:
    """Move the visible window. Zero scroll shows the newest rows."""
    hidden = max(0, len(book.trails) - config.max_legend)
    return replace(book, scroll=min(hidden, max(0, book.scroll + steps)))


def visible_legend(book: TrailBook, config: Config) -> tuple[Trail, ...]:
    count = config.max_legend
    if len(book.trails) <= count:
        return book.trails
    end = len(book.trails) - book.scroll
    start = max(0, end - count)
    return book.trails[start:end]


def legend_line(trail: Trail) -> str:
    """One legend row. Reference and phugoid range is ``r(6 s)`` only when the clip finished."""
    if trail.caption:
        return trail.caption
    head = f"{trail.tag}  " if trail.tag else ""
    line = f"{head}V0={trail.v0_m_s:.2f} m/s  γ0={_degrees(trail.gamma0_deg)}"
    if trail.range_m is None:
        return line
    if trail.mode in ("reference", "phugoid") and trail.complete:
        return f"{line}  r(6 s)={trail.range_m:.2f} m"
    return f"{line}  r={trail.range_m:.2f} m"


def mc_legend_line(
    v0_m_s: float,
    gamma0_deg: float,
    sigma_v: float,
    sigma_gamma_deg: float,
    n: int,
    mean_m: float,
    std_m: float,
) -> str:
    """The single Monte Carlo row. Samples do not get rows of their own."""
    glide = f"{gamma0_deg:.1f}".replace("-", "−")
    if math.isnan(mean_m) or math.isnan(std_m):
        span = "n/a"
    else:
        span = f"{mean_m:.2f} ± {std_m:.2f} m"
    return (
        f"MC  N={n}  V0={v0_m_s:.2f} ± {sigma_v:.2f} m/s  "
        f"γ0={glide} ± {sigma_gamma_deg:.1f}°  r={span}"
    )


def shows_reference_ground(mode: str, book: TrailBook) -> bool:
    """The below-ground note is on when a Reference or phugoid path can cross h = 0."""
    if mode in ("reference", "phugoid"):
        return True
    return any(
        trail.mode in ("reference", "phugoid") and any(height < 0.0 for _range, height in trail.points)
        for trail in book.trails
    )


def _push(book: TrailBook, trail: Trail, config: Config) -> TrailBook:
    trails = book.trails + (trail,)
    overflow = book.overflow
    if len(trails) > config.max_trails:
        trails = trails[-config.max_trails :]
        overflow = True
    return replace(
        book,
        trails=trails,
        colour_index=book.colour_index + 1,
        overflow=overflow,
    )


def _degrees(value: float) -> str:
    text = f"{value:.1f}°"
    return text.replace("-", "−")
