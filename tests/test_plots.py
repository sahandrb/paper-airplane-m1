"""Headless Figure 1, Figure 2, and the range heatmap."""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.colors as mcolors
import numpy as np
import pytest

from paper_airplane.__main__ import main
from paper_airplane.plots import (
    CASE_COLORS,
    CASE_LABELS,
    figure1_path,
    figure2_histories,
    heatmap,
)
from paper_airplane.simulation import HeatmapResult, cases_abcd


def _note(figure) -> str:
    return " ".join(text.get_text() for text in figure.texts)


def test_reference_figures_match_the_professor_layout() -> None:
    flights = cases_abcd()
    path = figure1_path(flights)
    histories = figure2_histories(flights)

    axis = path.axes[0]
    assert axis.get_xlabel() == "Range, m"
    assert axis.get_ylabel() == "Height, m"
    legend = [text.get_text() for text in axis.get_legend().get_texts()]
    assert legend == list(CASE_LABELS)
    colors = [mcolors.to_hex(line.get_color()).lower() for line in axis.get_lines()]
    assert colors == [color.lower() for color in CASE_COLORS]
    assert min(float(np.min(line.get_ydata())) for line in axis.get_lines()) < 0.0
    assert "S. Ranjbaripour" in _note(path)
    assert "Atashgah" not in _note(path)

    labels = [panel.get_ylabel() for panel in histories.axes]
    assert labels == [
        "Velocity, m/s",
        "Flight Path Angle, rad",
        "Altitude, m",
        "Range, m",
    ]
    gamma = histories.axes[1].get_lines()[-1].get_ydata()
    assert float(np.max(gamma)) == pytest.approx(6.7835, abs=1e-3)
    assert float(np.max(histories.axes[0].get_lines()[0].get_xdata())) == pytest.approx(6.0)
    assert "S. Ranjbaripour" in _note(histories)
    assert "Atashgah" not in _note(histories)

    path.clf()
    histories.clf()


def test_heatmap_marks_cases_without_a_hard_coded_peak() -> None:
    grid = HeatmapResult(
        v0_m_s=np.linspace(1.0, 12.0, 4),
        gamma0_rad=np.deg2rad(np.linspace(-40.0, 50.0, 3)),
        range_m=np.full((3, 4), 10.0),
    )
    figure = heatmap(grid)
    labels = [text.get_text() for text in figure.axes[0].texts]
    assert "A, (V*, gamma*)" in labels
    assert "B" in labels
    assert "C" in labels
    assert "D" in labels
    assert figure.axes[0].get_xlabel() == "V0, m/s"
    assert figure.axes[0].get_ylabel() == "gamma0, deg"
    assert "S. Ranjbaripour" in _note(figure)
    assert "16.0" not in _note(figure)
    figure.clf()


def test_reference_command_writes_both_pngs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    assert main(["--reference-plots"]) == 0
    folders = list(Path("outputs").glob("run_*"))
    assert len(folders) == 1
    assert (folders[0] / "figure1_path.png").stat().st_size > 1000
    assert (folders[0] / "figure2_histories.png").stat().st_size > 1000


def test_heatmap_command_writes_a_png(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    fake = HeatmapResult(
        v0_m_s=np.linspace(1.0, 12.0, 4),
        gamma0_rad=np.deg2rad(np.linspace(-40.0, 50.0, 3)),
        range_m=np.full((3, 4), 10.0),
    )
    monkeypatch.setattr("paper_airplane.plots.range_heatmap", lambda config=None: fake)
    assert main(["--heatmap"]) == 0
    folders = list(Path("outputs").glob("run_*"))
    assert len(folders) == 1
    assert (folders[0] / "heatmap.png").stat().st_size > 1000


def test_no_flags_opens_the_window(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("paper_airplane.app.main.run_app", lambda: 0)
    assert main([]) == 0
