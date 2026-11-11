"""Section 12.6: drag work accounts for the loss of mechanical energy."""

import numpy as np

from paper_airplane.energy import drag_power
from paper_airplane.equilibrium import gamma_star_rad, v_star
from paper_airplane.simulation import integrate_reference


def _trapz(values: np.ndarray, time_s: np.ndarray) -> float:
    return float(np.sum((values[1:] + values[:-1]) * 0.5 * np.diff(time_s)))


def test_case_a_energy_drop_equals_drag_work() -> None:
    flight = integrate_reference(v_star(), gamma_star_rad())
    delta_energy = float(flight.energy[-1] - flight.energy[0])
    work = _trapz(np.asarray(drag_power(flight.v), dtype=np.float64), flight.t)
    assert abs(delta_energy + work) < 1e-10
