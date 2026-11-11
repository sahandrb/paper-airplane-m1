"""Headless Matplotlib figures for the reference cases and the range grid.

The interactive window is a later milestone. Callers that only save files
select the Agg backend before importing pyplot.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import numpy as np

from paper_airplane.config import DEFAULT_CONFIG, Config
from paper_airplane.equilibrium import gamma_star_rad, v_star
from paper_airplane.simulation import HeatmapResult, Trajectory, cases_abcd, range_heatmap

CASE_ORDER = ("a", "b", "c", "d")
CASE_COLORS = ("#0072BD", "#D95319", "#EDB120", "#7E2F8E")
CASE_LABELS = (
    "a: Equilibrium glide",
    "b: Horizontal launch, V",
    "c: Horizontal launch, 1.5V",
    "d: Horizontal launch, 3V",
)
FOOTNOTE = (
    "Paper Airplane Flight Lab — S. Ranjbaripour, University of Tehran. "
    "Model: Stengel, Flight Dynamics (2005), Example 1.3-1."
)


def _cfg(config: Config | None) -> Config:
    return DEFAULT_CONFIG if config is None else config


def _pyplot():
    import matplotlib.pyplot as plt

    plt.rcParams.update(
        {
            "axes.grid": True,
            "grid.alpha": 0.35,
            "axes.labelsize": 11,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "font.size": 10,
        }
    )
    return plt


def _footnote(figure) -> None:
    figure.text(0.01, 0.012, FOOTNOTE, fontsize=9, ha="left", va="bottom", color="#333333")
    figure.subplots_adjust(bottom=0.16)


def _run_folder(directory: Path | None) -> Path:
    if directory is None:
        folder = Path("outputs") / datetime.now().strftime("run_%Y%m%d_%H%M%S")
    else:
        folder = Path(directory)
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def _ensure_headless() -> None:
    import matplotlib

    matplotlib.use("Agg", force=True)


def figure1_path(
    flights: dict[str, Trajectory] | None = None,
    config: Config | None = None,
):
    """Height against range for Reference cases a-d. Negative height stays visible."""
    plt = _pyplot()
    cfg = _cfg(config)
    series = cases_abcd(cfg) if flights is None else flights
    figure, axis = plt.subplots(figsize=(8.0, 5.0))
    for key, color, label in zip(CASE_ORDER, CASE_COLORS, CASE_LABELS, strict=True):
        flight = series[key]
        axis.plot(flight.r, flight.h, color=color, label=label, linewidth=1.6)
    axis.set_xlabel("Range, m")
    axis.set_ylabel("Height, m")
    axis.grid(True)
    axis.legend()
    _footnote(figure)
    return figure


def figure2_histories(
    flights: dict[str, Trajectory] | None = None,
    config: Config | None = None,
):
    """V, gamma in radians, altitude, and range from 0 to 6 s."""
    plt = _pyplot()
    cfg = _cfg(config)
    series = cases_abcd(cfg) if flights is None else flights
    figure, axes = plt.subplots(2, 2, figsize=(10.0, 7.0), sharex=True)
    panels = (
        (axes[0, 0], "v", "Velocity, m/s"),
        (axes[0, 1], "gamma", "Flight Path Angle, rad"),
        (axes[1, 0], "h", "Altitude, m"),
        (axes[1, 1], "r", "Range, m"),
    )
    for key, color, label in zip(CASE_ORDER, CASE_COLORS, CASE_LABELS, strict=True):
        flight = series[key]
        for axis, attr, ylabel in panels:
            axis.plot(flight.t, getattr(flight, attr), color=color, label=label, linewidth=1.3)
            axis.set_ylabel(ylabel)
    for axis, _attr, _ylabel in panels:
        axis.set_xlim(0.0, cfg.tf_s)
        axis.grid(True)
    axes[1, 0].set_xlabel("Time, s")
    axes[1, 1].set_xlabel("Time, s")
    axes[0, 0].legend()
    _footnote(figure)
    return figure


def heatmap(grid: HeatmapResult | None = None, config: Config | None = None):
    """Landing range over the slider rectangle. The peak is the computed grid."""
    plt = _pyplot()
    cfg = _cfg(config)
    survey = range_heatmap(cfg) if grid is None else grid
    figure, axis = plt.subplots(figsize=(8.0, 5.5))
    gamma_deg = np.rad2deg(survey.gamma0_rad)
    mesh = axis.pcolormesh(
        survey.v0_m_s,
        gamma_deg,
        survey.range_m,
        shading="nearest",
    )
    figure.colorbar(mesh, ax=axis, label="Landing range, m")
    axis.set_xlabel("V0, m/s")
    axis.set_ylabel("gamma0, deg")
    speed = v_star(cfg)
    glide_deg = float(np.rad2deg(gamma_star_rad(cfg)))
    marks = (
        (speed, glide_deg, "A, (V*, gamma*)"),
        (speed, 0.0, "B"),
        (1.5 * speed, 0.0, "C"),
        (3.0 * speed, 0.0, "D"),
    )
    for airspeed, angle_deg, name in marks:
        axis.scatter([airspeed], [angle_deg], c="black", s=28, zorder=3)
        axis.annotate(name, (airspeed, angle_deg), textcoords="offset points", xytext=(5, 5), fontsize=8)
    axis.grid(False)
    _footnote(figure)
    return figure


def write_reference_plots(
    directory: Path | None = None,
    config: Config | None = None,
) -> Path:
    """Save Figure 1 and Figure 2. Returns the output directory."""
    _ensure_headless()
    plt = _pyplot()
    folder = _run_folder(directory)
    flights = cases_abcd(config)
    path_figure = figure1_path(flights, config)
    path_figure.savefig(folder / "figure1_path.png")
    plt.close(path_figure)
    history_figure = figure2_histories(flights, config)
    history_figure.savefig(folder / "figure2_histories.png")
    plt.close(history_figure)
    return folder


def write_heatmap(
    directory: Path | None = None,
    grid: HeatmapResult | None = None,
    config: Config | None = None,
) -> Path:
    """Save the landing-range heatmap. Returns the output directory."""
    _ensure_headless()
    plt = _pyplot()
    folder = _run_folder(directory)
    figure = heatmap(grid, config)
    figure.savefig(folder / "heatmap.png")
    plt.close(figure)
    return folder
