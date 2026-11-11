"""Constant aerodynamic coefficients at maximum lift-to-drag ratio.

CLa and epsilon use the homework literal pi stored on Config. Lift and drag
coefficients stay constant during flight.
"""

from __future__ import annotations

import math

from paper_airplane.config import DEFAULT_CONFIG, Config


def _cfg(config: Config | None) -> Config:
    return DEFAULT_CONFIG if config is None else config


def cla(config: Config | None = None) -> float:
    """Helmbold finite-wing lift slope, per radian."""
    cfg = _cfg(config)
    aspect = cfg.aspect_ratio
    return cfg.pi_homework * aspect / (1.0 + math.sqrt(1.0 + (aspect / 2.0) ** 2))


def epsilon(config: Config | None = None) -> float:
    """Induced-drag factor."""
    cfg = _cfg(config)
    return 1.0 / (cfg.pi_homework * cfg.oswald_efficiency * cfg.aspect_ratio)


def cl_star(config: Config | None = None) -> float:
    """Lift coefficient at (L/D)max."""
    cfg = _cfg(config)
    return math.sqrt(cfg.cd0 / epsilon(cfg))


def cd_star(config: Config | None = None) -> float:
    """Drag coefficient at (L/D)max. Induced drag equals CD0 there."""
    cfg = _cfg(config)
    cl = cl_star(cfg)
    return cfg.cd0 + epsilon(cfg) * cl * cl


def ld_max(config: Config | None = None) -> float:
    """Maximum lift-to-drag ratio."""
    cfg = _cfg(config)
    return cl_star(cfg) / cd_star(cfg)


def span_m(config: Config | None = None) -> float:
    """Wing span from AR = b^2 / S. Not used by the equations of motion."""
    cfg = _cfg(config)
    return math.sqrt(cfg.aspect_ratio * cfg.wing_area_m2)


def mean_chord_m(config: Config | None = None) -> float:
    """Mean chord S / b. Not used by the equations of motion."""
    cfg = _cfg(config)
    return cfg.wing_area_m2 / span_m(cfg)
