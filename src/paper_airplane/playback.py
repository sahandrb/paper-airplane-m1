"""Play a precomputed trajectory. This module stays free of the display library."""

from __future__ import annotations

import numpy as np

from paper_airplane.config import Config
from paper_airplane.dynamics import dynamic_pressure, theta_rad
from paper_airplane.energy import ke, pe, total
from paper_airplane.simulation import Trajectory

SPEEDS: tuple[float, ...] = (0.25, 1.0, 4.0)


class Sample:
    """One instant of the true state. Angles are radians. Nothing here is filtered."""

    __slots__ = ("t", "v", "gamma", "h", "r", "theta", "q_dyn", "ke", "pe", "energy")

    def __init__(
        self,
        t: float,
        v: float,
        gamma: float,
        h: float,
        r: float,
        theta: float,
        q_dyn: float,
        ke_j: float,
        pe_j: float,
        energy_j: float,
    ) -> None:
        self.t = t
        self.v = v
        self.gamma = gamma
        self.h = h
        self.r = r
        self.theta = theta
        self.q_dyn = q_dyn
        self.ke = ke_j
        self.pe = pe_j
        self.energy = energy_j


def sample_at(path: Trajectory, t_sim: float) -> Sample:
    """Linear sample. A height within 1e-16 of the ground is shown as zero."""
    t_final = float(path.t[-1])
    t_value = min(max(float(t_sim), float(path.t[0])), t_final)
    height = _interp(path.t, path.h, t_value)
    if abs(height) <= 1e-16:
        height = 0.0
    return Sample(
        t=t_value,
        v=_interp(path.t, path.v, t_value),
        gamma=_interp(path.t, path.gamma, t_value),
        h=height,
        r=_interp(path.t, path.r, t_value),
        theta=_interp(path.t, path.theta, t_value),
        q_dyn=_interp(path.t, path.q_dyn, t_value),
        ke_j=_interp(path.t, path.ke, t_value),
        pe_j=_interp(path.t, path.pe, t_value),
        energy_j=_interp(path.t, path.energy, t_value),
    )


def launch_sample(airspeed: float, gamma_rad: float, config: Config) -> Sample:
    """The rail state, before integration starts."""
    height = config.h0_m
    dynamic = float(np.asarray(dynamic_pressure(airspeed, config)))
    theta = float(np.asarray(theta_rad(gamma_rad, config)))
    kinetic = float(np.asarray(ke(airspeed, config)))
    potential = float(np.asarray(pe(height, config)))
    return Sample(
        t=0.0,
        v=airspeed,
        gamma=gamma_rad,
        h=height,
        r=config.r0_m,
        theta=theta,
        q_dyn=dynamic,
        ke_j=kinetic,
        pe_j=potential,
        energy_j=float(np.asarray(total(airspeed, height, config))),
    )


def advance_time(t_sim: float, dt_wall_s: float, speed: float, t_final: float) -> float:
    """``t_sim += speed * dt_wall``, clamped to the sample."""
    return min(t_final, max(0.0, t_sim + speed * dt_wall_s))


def cycle_speed(speed: float, direction: int) -> float:
    """Step through 0.25×, 1×, and 4×."""
    index = SPEEDS.index(speed) if speed in SPEEDS else 1
    return SPEEDS[(index + direction) % len(SPEEDS)]


def points_until(path: Trajectory, t_sim: float, tip: tuple[float, float]) -> tuple[tuple[float, float], ...]:
    """World points from the start through the played instant, ending on the dart."""
    count = int(np.searchsorted(path.t, t_sim, side="right"))
    count = max(1, min(count, len(path.t)))
    body = tuple((float(path.r[i]), float(path.h[i])) for i in range(count) if float(path.t[i]) <= t_sim)
    if not body or abs(body[-1][0] - tip[0]) > 1e-9 or abs(body[-1][1] - tip[1]) > 1e-9:
        body = body + (tip,)
    return body


def extremes(path: Trajectory, t_sim: float) -> tuple[float, float, float, float]:
    """Min and max of V and gamma, in m/s and degrees, up to the played time."""
    mask = path.t <= t_sim + 1e-9
    if not np.any(mask):
        mask = np.zeros(len(path.t), dtype=bool)
        mask[0] = True
    speed = path.v[mask]
    glide = np.degrees(path.gamma[mask])
    return float(np.min(speed)), float(np.max(speed)), float(np.min(glide)), float(np.max(glide))


def _interp(time: np.ndarray, values: np.ndarray, t_value: float) -> float:
    return float(np.interp(t_value, time, values))
