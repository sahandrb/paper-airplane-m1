"""Mechanical energy of the point mass. Datum for potential energy is h = 0."""

from __future__ import annotations

import numpy as np

from paper_airplane.aero import cd_star
from paper_airplane.config import DEFAULT_CONFIG, Config
from paper_airplane.dynamics import dynamic_pressure


def _cfg(config: Config | None) -> Config:
    return DEFAULT_CONFIG if config is None else config


def _as_float_or_array(value: np.ndarray) -> float | np.ndarray:
    if value.ndim == 0:
        return float(value)
    return value


def ke(airspeed: float | np.ndarray, config: Config | None = None) -> float | np.ndarray:
    """Kinetic energy 1/2 m V^2."""
    cfg = _cfg(config)
    speed = np.asarray(airspeed, dtype=np.float64)
    return _as_float_or_array(0.5 * cfg.mass_kg * speed * speed)


def pe(altitude_m: float | np.ndarray, config: Config | None = None) -> float | np.ndarray:
    """Potential energy m g h. Negative when the reference trajectory is below the ground."""
    cfg = _cfg(config)
    altitude = np.asarray(altitude_m, dtype=np.float64)
    return _as_float_or_array(cfg.mass_kg * cfg.gravity_m_s2 * altitude)


def total(
    airspeed: float | np.ndarray,
    altitude_m: float | np.ndarray,
    config: Config | None = None,
) -> float | np.ndarray:
    """E = KE + PE."""
    kinetic = np.asarray(ke(airspeed, config), dtype=np.float64)
    potential = np.asarray(pe(altitude_m, config), dtype=np.float64)
    return _as_float_or_array(kinetic + potential)


def drag_power(airspeed: float | np.ndarray, config: Config | None = None) -> float | np.ndarray:
    """D V, the rate at which drag removes mechanical energy."""
    cfg = _cfg(config)
    speed = np.asarray(airspeed, dtype=np.float64)
    drag = cd_star(cfg) * dynamic_pressure(speed, cfg) * cfg.wing_area_m2
    return _as_float_or_array(drag * speed)
