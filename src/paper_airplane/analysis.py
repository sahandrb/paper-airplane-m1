"""Cached landing-range grid and the phugoid readout. No display library."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np

from paper_airplane.config import Config
from paper_airplane.linearize import HybridPath, damping_ratio, eigenvalues_at_eq, linear_period_s
from paper_airplane.simulation import HeatmapResult, MonteCarloResult, range_heatmap


@dataclass
class Overlays:
    """The dashed phugoid and the faint Monte Carlo paths. RESET and RESTART drop both."""

    hybrid: HybridPath | None = None
    scatter: MonteCarloResult | None = None
    n: int = 50
    sigma_v: float = 0.20
    sigma_g: float = 3.0
    v0: float = 0.0
    gamma_deg: float = 0.0

    def clear(self) -> None:
        self.hybrid = None
        self.scatter = None


@dataclass
class HeatmapCache:
    """The 31 by 41 grid. Recompute only when ``force`` is set."""

    grid: HeatmapResult | None = None
    force: bool = False


def ensure_heatmap(
    cache: HeatmapCache,
    config: Config | None = None,
    progress: Callable[[int, int], None] | None = None,
    *,
    force: bool = False,
) -> HeatmapResult:
    """Build the grid once. A later call returns the same object."""
    if cache.grid is not None and not force and not cache.force:
        return cache.grid
    cache.grid = range_heatmap(config, progress=progress)
    cache.force = False
    return cache.grid


def phugoid_metrics(config: Config | None = None) -> str:
    """Eigenvalue, period, and damping from the Jacobian. Nothing here is typed in."""
    values = eigenvalues_at_eq(config)
    chosen = max(values, key=lambda value: float(np.imag(value)))
    real = float(np.real(chosen))
    imag = abs(float(np.imag(chosen)))
    return (
        f"lambda = {real:.4f} ± {imag:.4f} i    "
        f"T = {linear_period_s(config):.3f} s    "
        f"zeta = {damping_ratio(config):.3f}"
    )
