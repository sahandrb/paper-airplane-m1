"""Owner-editable configuration.

Homework literals from the professor's MATLAB and every value the specification
marks CONFIG live here. Physics modules read this object; they do not carry
their own copies of these numbers.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    """Point-mass paper-airplane constants.

    Monte Carlo sigmas are an assumption: illustrative hand-throw scatter.
    They are not from Stengel and not from a measured data set.
    """

    wing_area_m2: float = 0.017
    aspect_ratio: float = 0.86
    oswald_efficiency: float = 0.9
    mass_kg: float = 0.003
    gravity_m_s2: float = 9.8
    density_kg_m3: float = 1.225
    cd0: float = 0.02
    h0_m: float = 2.0
    r0_m: float = 0.0
    tf_s: float = 6.0
    pi_homework: float = 3.141592

    reference_rtol: float = 1e-8
    reference_atol: float = 1e-10
    physical_rtol: float = 1e-10
    physical_atol: float = 1e-12
    survey_rtol: float = 1e-6
    survey_atol: float = 1e-8
    survey_max_step_s: float = 0.05
    integrator_method: str = "RK23"
    # Solver bracket only. Physical flight still stops on the ground event.
    physical_horizon_s: float = 30.0

    v_eps_m_s: float = 1e-9
    v_min_stop_m_s: float = 0.05

    v0_min_m_s: float = 1.0
    v0_max_m_s: float = 12.0
    v0_step_m_s: float = 0.05
    gamma0_min_deg: float = -40.0
    gamma0_max_deg: float = 50.0
    gamma0_step_deg: float = 0.5

    window_width_px: int = 1280
    window_height_px: int = 720
    pixels_per_metre: float = 83.5
    sprite_display_length_px: int = 110
    prelaunch_launcher_x_frac: float = 0.08
    ground_screen_y0: int = 548
    follow_x_frac: float = 0.32
    margin_px: int = 40
    camera_tau_s: float = 0.12

    max_trails: int = 24
    max_legend: int = 12

    monte_carlo_n: int = 50
    monte_carlo_sigma_v_m_s: float = 0.20
    monte_carlo_sigma_gamma_deg: float = 3.0
    heatmap_n_v: int = 41
    heatmap_n_g: int = 31

    cg_px: tuple[float, float] = (388.0, 119.0)
    launcher_rest_gamma_deg: float = 16.1
    launcher_pivot_px: tuple[float, float] = (199.0, 124.0)

    trajectory_samples: int = 2401


DEFAULT_CONFIG = Config()
