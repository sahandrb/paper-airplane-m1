"""Equilibrium glide at the constant (L/D)max coefficients."""

from __future__ import annotations

import math

from paper_airplane.aero import cd_star, cl_star, cla, ld_max
from paper_airplane.config import DEFAULT_CONFIG, Config


def _cfg(config: Config | None) -> Config:
    return DEFAULT_CONFIG if config is None else config


def alpha_star_rad(config: Config | None = None) -> float:
    """Angle of attack locked to CL_star / CLa."""
    cfg = _cfg(config)
    return cl_star(cfg) / cla(cfg)


def alpha_star_deg(config: Config | None = None) -> float:
    return math.degrees(alpha_star_rad(config))


def gamma_star_rad(config: Config | None = None) -> float:
    """Flight-path angle from tan(gamma) = -CD/CL. Negative in the glide."""
    cfg = _cfg(config)
    return -math.atan(1.0 / ld_max(cfg))


def gamma_star_deg(config: Config | None = None) -> float:
    return math.degrees(gamma_star_rad(config))


def v_star_from_vertical_balance(config: Config | None = None) -> float:
    """Professor's speed: lift and drag both support weight in the descent."""
    cfg = _cfg(config)
    gamma = gamma_star_rad(cfg)
    cl = cl_star(cfg)
    cd = cd_star(cfg)
    denominator = cfg.density_kg_m3 * cfg.wing_area_m2 * (
        cl * math.cos(gamma) - cd * math.sin(gamma)
    )
    return math.sqrt(2.0 * cfg.mass_kg * cfg.gravity_m_s2 / denominator)


def v_star_from_lift_balance(config: Config | None = None) -> float:
    """Equivalent form L = m g cos(gamma), valid on the equilibrium glide."""
    cfg = _cfg(config)
    gamma = gamma_star_rad(cfg)
    cl = cl_star(cfg)
    return math.sqrt(
        2.0 * cfg.mass_kg * cfg.gravity_m_s2 * math.cos(gamma)
        / (cfg.density_kg_m3 * cfg.wing_area_m2 * cl)
    )


def v_star(config: Config | None = None) -> float:
    """Equilibrium airspeed used as V*. The vertical-balance formula."""
    return v_star_from_vertical_balance(config)
