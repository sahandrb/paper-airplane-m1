"""RK23 trajectories of the point-mass paper airplane.

Reference runs follow the professor: tf = 6 s and no ground event.
Physical runs stop at the downward crossing of h = 0.
Monte Carlo speed and angle sigmas are an assumption, not Stengel data.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
from scipy.integrate import solve_ivp

from paper_airplane.config import DEFAULT_CONFIG, Config
from paper_airplane.dynamics import dynamic_pressure, rhs, theta_rad
from paper_airplane.energy import ke, pe, total
from paper_airplane.equilibrium import gamma_star_rad, v_star

SPEED_COLLAPSE_STATUS = "speed collapsed (V → 0); gammadot is singular"
PreviewMode = Literal["reference", "physical"]


def _cfg(config: Config | None) -> Config:
    return DEFAULT_CONFIG if config is None else config


@dataclass(frozen=True)
class Trajectory:
    """Sampled flight. Angles are radians. Energy may be negative below h = 0."""

    t: np.ndarray
    v: np.ndarray
    gamma: np.ndarray
    h: np.ndarray
    r: np.ndarray
    theta: np.ndarray
    q_dyn: np.ndarray
    ke: np.ndarray
    pe: np.ndarray
    energy: np.ndarray
    status: str
    terminated_by: str


@dataclass(frozen=True)
class MonteCarloResult:
    """One summary of N physical throws. Assumption: illustrative hand-throw scatter."""

    trajectories: tuple[Trajectory, ...]
    landing_range_m: np.ndarray
    mean_range_m: float
    std_range_m: float
    speed_collapse_count: int
    assumption: str = "Assumption: illustrative hand-throw scatter"


@dataclass(frozen=True)
class HeatmapResult:
    """Landing range on the slider rectangle. Shape of range_m is (n_gamma, n_v)."""

    v0_m_s: np.ndarray
    gamma0_rad: np.ndarray
    range_m: np.ndarray


def _finite_rhs(time_s: float, state: np.ndarray, config: Config) -> np.ndarray:
    """Keep a solver stage off the singular division. The V event still stops the run."""
    if float(state[0]) < config.v_eps_m_s:
        return np.zeros(4, dtype=np.float64)
    return rhs(time_s, state, config)


def _ground_event(time_s: float, state: np.ndarray) -> float:
    del time_s
    return float(state[2])


def _speed_event_factory(config: Config):
    def speed_event(time_s: float, state: np.ndarray) -> float:
        del time_s
        return float(state[0]) - config.v_min_stop_m_s

    speed_event.terminal = True
    speed_event.direction = -1
    return speed_event


_ground_event.terminal = True
_ground_event.direction = -1


def _event_time(solution, index: int) -> float | None:
    if solution.t_events is None or index >= len(solution.t_events):
        return None
    times = solution.t_events[index]
    if times is None or len(times) == 0:
        return None
    return float(times[0])


def _sample(
    solution,
    config: Config,
    clamp_ground: bool,
    n_samples: int,
) -> tuple[np.ndarray, np.ndarray]:
    time = np.linspace(0.0, float(solution.t[-1]), n_samples)
    states = np.array(solution.sol(time), dtype=np.float64, copy=True)
    states[:, -1] = np.asarray(solution.y[:, -1], dtype=np.float64)
    time[-1] = float(solution.t[-1])
    if clamp_ground:
        np.maximum(states[2], 0.0, out=states[2])
    return time, states


def _trajectory_from_states(
    time: np.ndarray,
    states: np.ndarray,
    status: str,
    terminated_by: str,
    config: Config,
) -> Trajectory:
    airspeed = np.asarray(states[0], dtype=np.float64)
    gamma = np.asarray(states[1], dtype=np.float64)
    altitude = np.asarray(states[2], dtype=np.float64)
    distance = np.asarray(states[3], dtype=np.float64)
    kinetic = np.asarray(ke(airspeed, config), dtype=np.float64)
    potential = np.asarray(pe(altitude, config), dtype=np.float64)
    return Trajectory(
        t=time,
        v=airspeed,
        gamma=gamma,
        h=altitude,
        r=distance,
        theta=np.asarray(theta_rad(gamma, config), dtype=np.float64),
        q_dyn=np.asarray(dynamic_pressure(airspeed, config), dtype=np.float64),
        ke=kinetic,
        pe=potential,
        energy=np.asarray(total(airspeed, altitude, config), dtype=np.float64),
        status=status,
        terminated_by=terminated_by,
    )


def _collapsed_point(
    airspeed: float,
    gamma: float,
    altitude: float,
    distance: float,
    config: Config,
) -> Trajectory:
    time = np.zeros(1, dtype=np.float64)
    states = np.array([[airspeed], [gamma], [altitude], [distance]], dtype=np.float64)
    return _trajectory_from_states(time, states, SPEED_COLLAPSE_STATUS, "speed", config)


def _integrate(
    airspeed0: float,
    gamma0: float,
    altitude0: float,
    range0: float,
    t_final: float,
    config: Config,
    *,
    ground: bool,
    rtol: float,
    atol: float,
    max_step: float | None,
    n_samples: int,
) -> Trajectory:
    if airspeed0 < config.v_min_stop_m_s:
        return _collapsed_point(airspeed0, gamma0, altitude0, range0, config)

    events = [_speed_event_factory(config)]
    if ground:
        events.append(_ground_event)
    options: dict = {
        "method": config.integrator_method,
        "rtol": rtol,
        "atol": atol,
        "dense_output": True,
        "events": events,
    }
    if max_step is not None:
        options["max_step"] = max_step
    solution = solve_ivp(
        lambda time_s, state: _finite_rhs(time_s, state, config),
        (0.0, float(t_final)),
        np.array([airspeed0, gamma0, altitude0, range0], dtype=np.float64),
        **options,
    )
    speed_time = _event_time(solution, 0)
    ground_time = _event_time(solution, 1) if ground else None
    if speed_time is not None and (ground_time is None or speed_time <= ground_time):
        status = SPEED_COLLAPSE_STATUS
        terminated_by = "speed"
        clamp = False
    elif ground_time is not None:
        status = "completed"
        terminated_by = "ground"
        clamp = True
    else:
        status = "completed"
        terminated_by = "final_time"
        clamp = False
    time, states = _sample(solution, config, clamp_ground=clamp, n_samples=n_samples)
    return _trajectory_from_states(time, states, status, terminated_by, config)


def integrate_reference(
    airspeed0: float,
    gamma0: float,
    h0: float | None = None,
    r0: float | None = None,
    tf: float | None = None,
    config: Config | None = None,
    n_samples: int | None = None,
) -> Trajectory:
    """Integrate to tf with no ground event. Altitude may become negative."""
    cfg = _cfg(config)
    return _integrate(
        airspeed0,
        gamma0,
        cfg.h0_m if h0 is None else h0,
        cfg.r0_m if r0 is None else r0,
        cfg.tf_s if tf is None else tf,
        cfg,
        ground=False,
        rtol=cfg.reference_rtol,
        atol=cfg.reference_atol,
        max_step=None,
        n_samples=cfg.trajectory_samples if n_samples is None else n_samples,
    )


def integrate_physical(
    airspeed0: float,
    gamma0: float,
    h0: float | None = None,
    r0: float | None = None,
    config: Config | None = None,
    *,
    rtol: float | None = None,
    atol: float | None = None,
    max_step: float | None = None,
    horizon_s: float | None = None,
    n_samples: int | None = None,
) -> Trajectory:
    """Stop at h = 0 crossed downward. Reported altitude is clamped to 0."""
    cfg = _cfg(config)
    return _integrate(
        airspeed0,
        gamma0,
        cfg.h0_m if h0 is None else h0,
        cfg.r0_m if r0 is None else r0,
        cfg.physical_horizon_s if horizon_s is None else horizon_s,
        cfg,
        ground=True,
        rtol=cfg.physical_rtol if rtol is None else rtol,
        atol=cfg.physical_atol if atol is None else atol,
        max_step=max_step,
        n_samples=cfg.trajectory_samples if n_samples is None else n_samples,
    )


def cases_abcd(config: Config | None = None) -> dict[str, Trajectory]:
    """Professor cases a-d on the Reference interval."""
    cfg = _cfg(config)
    speed = v_star(cfg)
    glide = gamma_star_rad(cfg)
    return {
        "a": integrate_reference(speed, glide, config=cfg),
        "b": integrate_reference(speed, 0.0, config=cfg),
        "c": integrate_reference(1.5 * speed, 0.0, config=cfg),
        "d": integrate_reference(3.0 * speed, 0.0, config=cfg),
    }


def preview(
    airspeed0: float,
    gamma0: float,
    mode: PreviewMode = "reference",
    config: Config | None = None,
) -> Trajectory:
    """Same solver as a launch. Reference keeps tf = 6 s; physical stops at the ground."""
    cfg = _cfg(config)
    if mode == "physical":
        return integrate_physical(
            airspeed0,
            gamma0,
            config=cfg,
            rtol=cfg.reference_rtol,
            atol=cfg.reference_atol,
        )
    if mode == "reference":
        return integrate_reference(airspeed0, gamma0, config=cfg)
    raise ValueError(f"unknown preview mode {mode}")


def monte_carlo(
    airspeed0: float,
    gamma0: float,
    n: int | None = None,
    sigma_v: float | None = None,
    sigma_gamma_deg: float | None = None,
    rng: np.random.Generator | None = None,
    config: Config | None = None,
) -> MonteCarloResult:
    """Physical throws with independent normal scatter.

    Assumption: illustrative hand-throw scatter. The sigmas are not from Stengel.
    """
    cfg = _cfg(config)
    count = cfg.monte_carlo_n if n is None else n
    speed_sigma = cfg.monte_carlo_sigma_v_m_s if sigma_v is None else sigma_v
    angle_sigma_deg = cfg.monte_carlo_sigma_gamma_deg if sigma_gamma_deg is None else sigma_gamma_deg
    generator = np.random.default_rng() if rng is None else rng
    speeds = generator.normal(airspeed0, speed_sigma, count)
    angles = generator.normal(gamma0, np.deg2rad(angle_sigma_deg), count)
    flights = tuple(
        integrate_physical(
            float(speed),
            float(angle),
            config=cfg,
            rtol=cfg.survey_rtol,
            atol=cfg.survey_atol,
            max_step=cfg.survey_max_step_s,
            n_samples=2,
        )
        for speed, angle in zip(speeds, angles, strict=True)
    )
    landed = np.array(
        [flight.r[-1] for flight in flights if flight.terminated_by == "ground"],
        dtype=np.float64,
    )
    collapses = sum(flight.terminated_by == "speed" for flight in flights)
    if landed.size == 0:
        mean_range = math_nan()
        std_range = math_nan()
    else:
        mean_range = float(np.mean(landed))
        std_range = float(np.std(landed, ddof=0))
    return MonteCarloResult(
        trajectories=flights,
        landing_range_m=landed,
        mean_range_m=mean_range,
        std_range_m=std_range,
        speed_collapse_count=collapses,
    )


def math_nan() -> float:
    return float("nan")


def range_heatmap(config: Config | None = None) -> HeatmapResult:
    """Physical landing range over the slider rectangle. The peak is computed."""
    cfg = _cfg(config)
    speeds = np.linspace(cfg.v0_min_m_s, cfg.v0_max_m_s, cfg.heatmap_n_v)
    angles = np.deg2rad(np.linspace(cfg.gamma0_min_deg, cfg.gamma0_max_deg, cfg.heatmap_n_g))
    ranges = np.empty((angles.size, speeds.size), dtype=np.float64)
    for i, angle in enumerate(angles):
        for j, speed in enumerate(speeds):
            flight = integrate_physical(
                float(speed),
                float(angle),
                config=cfg,
                rtol=cfg.survey_rtol,
                atol=cfg.survey_atol,
                max_step=cfg.survey_max_step_s,
                n_samples=2,
            )
            if flight.terminated_by == "ground":
                ranges[i, j] = flight.r[-1]
            else:
                ranges[i, j] = np.nan
    return HeatmapResult(v0_m_s=speeds, gamma0_rad=angles, range_m=ranges)
