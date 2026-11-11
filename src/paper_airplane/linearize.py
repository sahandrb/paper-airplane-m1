"""Linear phugoid about the equilibrium glide, plus the hybrid (r, h) path."""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from scipy.integrate import solve_ivp
from scipy.linalg import expm

from paper_airplane.aero import cd_star, cl_star
from paper_airplane.config import DEFAULT_CONFIG, Config
from paper_airplane.equilibrium import gamma_star_rad, v_star


def _cfg(config: Config | None) -> Config:
    return DEFAULT_CONFIG if config is None else config


@dataclass(frozen=True)
class HybridPath:
    """Linear (V, gamma) with the exact path kinematics."""

    t: np.ndarray
    v: np.ndarray
    gamma: np.ndarray
    h: np.ndarray
    r: np.ndarray


def jacobian(airspeed: float, gamma_rad: float, config: Config | None = None) -> np.ndarray:
    """2x2 Jacobian of (Vdot, gammadot) at one (V, gamma)."""
    cfg = _cfg(config)
    cl = cl_star(cfg)
    cd = cd_star(cfg)
    mass = cfg.mass_kg
    gravity = cfg.gravity_m_s2
    rho = cfg.density_kg_m3
    area = cfg.wing_area_m2
    return np.array(
        [
            [
                -cd * rho * airspeed * area / mass,
                -gravity * math.cos(gamma_rad),
            ],
            [
                cl * rho * area / (2.0 * mass) + gravity * math.cos(gamma_rad) / (airspeed * airspeed),
                gravity * math.sin(gamma_rad) / airspeed,
            ],
        ],
        dtype=np.float64,
    )


def jacobian_at_eq(config: Config | None = None) -> np.ndarray:
    cfg = _cfg(config)
    return jacobian(v_star(cfg), gamma_star_rad(cfg), cfg)


def eigenvalues_at_eq(config: Config | None = None) -> np.ndarray:
    return np.linalg.eigvals(jacobian_at_eq(config))


def _sigma_omega(config: Config) -> tuple[float, float]:
    values = eigenvalues_at_eq(config)
    sigma = float(np.real(values[0]))
    omega = float(np.max(np.abs(np.imag(values))))
    return sigma, omega


def linear_period_s(config: Config | None = None) -> float:
    """Damped period 2 pi / Im(lambda). Uses mathematical pi."""
    _, omega = _sigma_omega(_cfg(config))
    return 2.0 * math.pi / omega


def damping_ratio(config: Config | None = None) -> float:
    sigma, omega = _sigma_omega(_cfg(config))
    natural = math.hypot(sigma, omega)
    return -sigma / natural


def lanchester_period_s(config: Config | None = None) -> float:
    """Drag-free phugoid period pi * sqrt(2) * V* / g."""
    cfg = _cfg(config)
    return math.pi * math.sqrt(2.0) * v_star(cfg) / cfg.gravity_m_s2


def linear_state(
    time_s: float | np.ndarray,
    dv0: float,
    dgamma0: float,
    config: Config | None = None,
) -> tuple[np.ndarray, np.ndarray] | tuple[float, float]:
    """V_lin(t), gamma_lin(t) from expm(J t) applied to the initial perturbation."""
    cfg = _cfg(config)
    times = np.asarray(time_s, dtype=np.float64)
    scalar = times.ndim == 0
    times = np.atleast_1d(times)
    matrix = jacobian_at_eq(cfg)
    delta0 = np.array([dv0, dgamma0], dtype=np.float64)
    airspeed = np.empty(times.size, dtype=np.float64)
    gamma = np.empty(times.size, dtype=np.float64)
    equilibrium_speed = v_star(cfg)
    equilibrium_gamma = gamma_star_rad(cfg)
    for index, instant in enumerate(times):
        delta = expm(matrix * float(instant)) @ delta0
        airspeed[index] = equilibrium_speed + delta[0]
        gamma[index] = equilibrium_gamma + delta[1]
    if scalar:
        return float(airspeed[0]), float(gamma[0])
    return airspeed, gamma


def hybrid_path(
    dv0: float,
    dgamma0: float,
    tf: float | None = None,
    n_samples: int | None = None,
    config: Config | None = None,
) -> HybridPath:
    """Integrate hdot and rdot with the linear airspeed and flight-path angle."""
    cfg = _cfg(config)
    final = cfg.tf_s if tf is None else tf
    samples = cfg.trajectory_samples if n_samples is None else n_samples

    def kinematics(time_s: float, state: np.ndarray) -> np.ndarray:
        del state
        airspeed, gamma = linear_state(time_s, dv0, dgamma0, cfg)
        return np.array(
            [airspeed * math.sin(gamma), airspeed * math.cos(gamma)],
            dtype=np.float64,
        )

    solution = solve_ivp(
        kinematics,
        (0.0, float(final)),
        np.array([cfg.h0_m, cfg.r0_m], dtype=np.float64),
        method=cfg.integrator_method,
        rtol=cfg.reference_rtol,
        atol=cfg.reference_atol,
        dense_output=True,
    )
    time = np.linspace(0.0, float(solution.t[-1]), samples)
    path = solution.sol(time)
    airspeed, gamma = linear_state(time, dv0, dgamma0, cfg)
    return HybridPath(
        t=time,
        v=np.asarray(airspeed, dtype=np.float64),
        gamma=np.asarray(gamma, dtype=np.float64),
        h=np.asarray(path[0], dtype=np.float64),
        r=np.asarray(path[1], dtype=np.float64),
    )
