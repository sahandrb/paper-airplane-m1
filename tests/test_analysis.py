"""Mode cycle, the phugoid limit, the Monte Carlo row, and export."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from paper_airplane.analysis import HeatmapCache, ensure_heatmap
from paper_airplane.app.prelaunch import default_inputs, linear_model_outside, presets, toggle_mode
from paper_airplane.config import DEFAULT_CONFIG
from paper_airplane.export import CSV_HEADER, write_run_table
from paper_airplane.simulation import HeatmapResult, Trajectory
from paper_airplane.trails import Trail, legend_line, mc_legend_line


def test_tab_cycles_five_modes() -> None:
    inputs = default_inputs(DEFAULT_CONFIG)
    seen = [inputs.mode]
    for _ in range(5):
        inputs = toggle_mode(inputs)
        seen.append(inputs.mode)
    assert seen == ["reference", "physical", "phugoid", "montecarlo", "heatmap", "reference"]


def test_preset_d_is_outside_the_linear_region_and_a_is_not() -> None:
    cases = presets(DEFAULT_CONFIG)
    assert linear_model_outside(*cases["a"], DEFAULT_CONFIG) is False
    assert linear_model_outside(*cases["d"], DEFAULT_CONFIG) is True


def test_phugoid_legend_uses_the_six_second_range() -> None:
    trail = Trail(
        colour="#0072BD",
        v0_m_s=3.55,
        gamma0_deg=-10.3,
        mode="phugoid",
        tag="",
        range_m=20.95,
        complete=True,
    )
    assert legend_line(trail).endswith("r(6 s)=20.95 m")
    assert "r(6 s)" not in legend_line(Trail(
        colour="#0072BD",
        v0_m_s=3.55,
        gamma0_deg=-10.3,
        mode="montecarlo",
        tag="",
        range_m=11.03,
        complete=True,
    ))


def test_monte_carlo_legend_is_one_row() -> None:
    assert mc_legend_line(3.55, -10.3, 0.20, 3.0, 50, 11.03, 0.40) == (
        "MC  N=50  V0=3.55 ± 0.20 m/s  γ0=−10.3 ± 3.0°  r=11.03 ± 0.40 m"
    )


def test_csv_header_and_meta_row(tmp_path: Path) -> None:
    zeros = np.zeros(1)
    path = Trajectory(
        t=np.array([0.0]),
        v=np.array([3.5]),
        gamma=np.zeros(1),
        h=np.array([2.0]),
        r=np.zeros(1),
        theta=np.zeros(1),
        q_dyn=zeros,
        ke=zeros,
        pe=zeros,
        energy=zeros,
        status="ok",
        terminated_by="tf",
    )
    folder = write_run_table(
        path,
        tmp_path,
        v0_m_s=3.5,
        gamma0_deg=-10.0,
        mode="reference",
        range_m=1.0,
        t_final=0.0,
    )
    text = (folder / "run.csv").read_text(encoding="utf-8")
    assert text.splitlines()[0] == CSV_HEADER
    meta = (folder / "meta.txt").read_text(encoding="utf-8").strip()
    assert meta == "V0=3.5 gamma0=-10 mode=reference range=1 t_final=0"


def test_heatmap_cache_does_not_recompute(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {"n": 0}

    def fake(config: object = None, progress: object = None) -> HeatmapResult:
        del config
        calls["n"] += 1
        if progress is not None:
            progress(1, 1)  # type: ignore[operator]
        return HeatmapResult(np.array([1.0]), np.array([0.0]), np.array([[1.0]]))

    monkeypatch.setattr("paper_airplane.analysis.range_heatmap", fake)
    cache = HeatmapCache()
    ensure_heatmap(cache)
    ensure_heatmap(cache)
    assert calls["n"] == 1
    ensure_heatmap(cache, force=True)
    assert calls["n"] == 2


def test_export_module_has_no_display_library() -> None:
    text = (Path(__file__).resolve().parents[1] / "src" / "paper_airplane" / "export.py").read_text(encoding="utf-8")
    assert "pygame" not in text
    assert "smooth_display_angle" not in text
