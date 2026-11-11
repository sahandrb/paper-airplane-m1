"""Point-mass longitudinal equations. No pitch inertia.

State vector x = [V, gamma, h, r], with gamma in radians.
"""

from __future__ import annotations

import math

import numpy as np

from paper_airplane.aero import cd_star, cl_star
from paper_airplane.config import DEFAULT_CONFIG, Config
from paper_airplane.equilibrium import alpha_star_rad


class SpeedTooSmallError(ValueError):
    """Raised when airspeed is below V_EPS and gammadot would divide by V."""


def _cfg(config: Config | None) -> Config:
    return DEFAULT_CONFIG if config is None else config


def dynamic_pressure(airspeed: float | np.ndarray, config: Config | None = None) -> np.ndarray:
    """q = 1/2 rho V^2."""
    cfg = _cfg(config)
    speed = np.asarray(airspeed, dtype=np.float64)
    return 0.5 * cfg.density_kg_m3 * speed * speed


def theta_rad(gamma_rad: float | np.ndarray, config: Config | None = None) -> np.ndarray:
    """Pitch theta = alpha_star + gamma. Kinematic, not a dynamic state."""
    cfg = _cfg(config)
    gamma = np.asarray(gamma_rad, dtype=np.float64)
    return alpha_star_rad(cfg) + gamma


def rhs(t: float, state: np.ndarray, config: Config | None = None) -> np.ndarray:
    """d/dt [V, gamma, h, r].

    CL and CD are the constant (L/D)max pair. If V < V_EPS this raises
    SpeedTooSmallError instead of dividing.
    """
    del t
    cfg = _cfg(config)
    airspeed = float(state[0])
    gamma = float(state[1])
    if airspeed < cfg.v_eps_m_s:
        raise SpeedTooSmallError(
            f"airspeed {airspeed} m/s is below V_EPS {cfg.v_eps_m_s}; gammadot is singular"
        )
    cl = cl_star(cfg)
    cd = cd_star(cfg)
    dynamic = float(dynamic_pressure(airspeed, cfg))
    mass = cfg.mass_kg
    gravity = cfg.gravity_m_s2
    area = cfg.wing_area_m2
    d_airspeed = (-cd * dynamic * area - mass * gravity * math.sin(gamma)) / mass
    d_gamma = (cl * dynamic * area - mass * gravity * math.cos(gamma)) / (mass * airspeed)
    d_altitude = airspeed * math.sin(gamma)
    d_range = airspeed * math.cos(gamma)
    return np.array([d_airspeed, d_gamma, d_altitude, d_range], dtype=np.float64)
