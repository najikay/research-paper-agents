"""
test_stubs_figures_b.py
=======================
Split from test_stubs_figures.py.
"""

from __future__ import annotations

from pathlib import Path  # noqa: E402

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pytest  # noqa: E402

from src.runner import figure_styles_a, figure_styles_c  # noqa: E402


def _fresh_rng() -> np.random.RandomState:
    """Deterministic RNG exposing the legacy .randn/.rand/.uniform API the
    renderers call."""
    return np.random.RandomState(0)


def _render_and_save(render_fn, out_path: Path) -> None:
    """Invoke a (plt, np, rng, label) renderer, save the current figure to
    out_path as PNG, then close all figures."""
    try:
        render_fn(plt, np, _fresh_rng(), "Test Label")
        plt.savefig(out_path, format="png")
    finally:
        plt.close("all")


@pytest.mark.parametrize(
    "render_fn",
    [
        figure_styles_a.render_system_concept,
        figure_styles_a.render_bio_signal,
        figure_styles_a.render_sensor_heatmap,
        figure_styles_a.render_trajectory_3d,
    ],
)
def test_figure_styles_a_renderers(tmp_path: Path, render_fn) -> None:
    """Each figure_styles_a renderer draws without error and yields a
    non-empty PNG."""
    out = tmp_path / f"{render_fn.__name__}.png"
    _render_and_save(render_fn, out)
    assert out.is_file()
    assert out.stat().st_size > 0
    assert out.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")


@pytest.mark.parametrize(
    "render_fn",
    [
        figure_styles_c.render_results_multi,
        figure_styles_c.render_convergence,
        figure_styles_c.render_generic,
    ],
)
def test_figure_styles_c_renderers(tmp_path: Path, render_fn) -> None:
    """Each figure_styles_c renderer draws without error and yields a
    non-empty PNG (covers render_generic and render_results_multi)."""
    out = tmp_path / f"{render_fn.__name__}.png"
    _render_and_save(render_fn, out)
    assert out.is_file()
    assert out.stat().st_size > 0
    assert out.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
