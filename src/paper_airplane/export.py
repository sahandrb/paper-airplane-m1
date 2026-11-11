"""CSV and meta for one played run. This module stays free of the display library."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from paper_airplane.aero import ld_max
from paper_airplane.config import Config
from paper_airplane.equilibrium import alpha_star_deg
from paper_airplane.plots import _run_folder
from paper_airplane.simulation import Trajectory

CSV_HEADER = "t,V,gamma_rad,gamma_deg,theta_deg,alpha_deg,h,r,q_dyn,L_over_D,KE,PE,E"


def write_run_table(
    trajectory: Trajectory | None,
    directory: Path | None,
    *,
    v0_m_s: float,
    gamma0_deg: float,
    mode: str,
    range_m: float | None,
    t_final: float | None,
    config: Config | None = None,
) -> Path:
    """Write ``run.csv`` when a trajectory exists, and always write one meta row."""
    folder = _run_folder(directory)
    if trajectory is not None:
        alpha = alpha_star_deg(config)
        lift_over_drag = ld_max(config)
        rows = [CSV_HEADER]
        for index in range(len(trajectory.t)):
            rows.append(
                ",".join(
                    (
                        f"{float(trajectory.t[index]):.6g}",
                        f"{float(trajectory.v[index]):.6g}",
                        f"{float(trajectory.gamma[index]):.6g}",
                        f"{float(np.degrees(trajectory.gamma[index])):.6g}",
                        f"{float(np.degrees(trajectory.theta[index])):.6g}",
                        f"{alpha:.6g}",
                        f"{float(trajectory.h[index]):.6g}",
                        f"{float(trajectory.r[index]):.6g}",
                        f"{float(trajectory.q_dyn[index]):.6g}",
                        f"{lift_over_drag:.6g}",
                        f"{float(trajectory.ke[index]):.6g}",
                        f"{float(trajectory.pe[index]):.6g}",
                        f"{float(trajectory.energy[index]):.6g}",
                    )
                )
            )
        (folder / "run.csv").write_text("\n".join(rows) + "\n", encoding="utf-8")
    range_text = "" if range_m is None else f"{range_m:.6g}"
    time_text = "" if t_final is None else f"{t_final:.6g}"
    meta = (
        f"V0={v0_m_s:.6g} gamma0={gamma0_deg:.6g} mode={mode} "
        f"range={range_text} t_final={time_text}\n"
    )
    (folder / "meta.txt").write_text(meta, encoding="utf-8")
    return folder
