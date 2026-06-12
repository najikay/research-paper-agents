"""Tests for src/pipeline/figures.py and src/pipeline/figure_renderer.py."""
from __future__ import annotations

from unittest.mock import patch

import pytest

from src.pipeline.figure_renderer import _infer_style_from_name, _render_fallback_figure
from src.pipeline.figures import (
    _deduplicate_cross_chapter_figures as dedup,
)
from src.pipeline.figures import (
    _diversify_stub_figures as diversify,
)
from src.pipeline.figures import (
    _generate_fallback_figures as gen_fallback,
)

STUB = r"\includegraphics{figures/fig_stub.png}"


def _mkch(tmp_path):
    ch = tmp_path / "latex" / "chapters"
    ch.mkdir(parents=True)
    return ch


class TestDiversifyStubFigures:
    def test_single_stub(self, tmp_path):
        ch = _mkch(tmp_path)
        (ch / "ch03_sensors.tex").write_text(r"\includegraphics[w=1]{figures/fig_stub.png}")
        diversify(tmp_path)
        assert "fig_ch03_auto.png" in (ch / "ch03_sensors.tex").read_text()

    def test_multiple_stubs(self, tmp_path):
        ch = _mkch(tmp_path)
        (ch / "ch03_sensors.tex").write_text(STUB + "\n" + STUB)
        diversify(tmp_path)
        t = (ch / "ch03_sensors.tex").read_text()
        assert "fig_ch03_auto.png" in t and "fig_ch03_auto_2.png" in t

    def test_skips_cover(self, tmp_path):
        ch = _mkch(tmp_path)
        (ch / "cover.tex").write_text(STUB)
        diversify(tmp_path)
        assert "fig_stub" in (ch / "cover.tex").read_text()

    def test_skips_non_ch_prefix(self, tmp_path):
        ch = _mkch(tmp_path)
        (ch / "abstract.tex").write_text(STUB)
        diversify(tmp_path)
        assert "fig_stub" in (ch / "abstract.tex").read_text()

    def test_no_stubs_unchanged(self, tmp_path):
        ch = _mkch(tmp_path)
        orig = r"\includegraphics{figures/real.png}"
        (ch / "ch01_intro.tex").write_text(orig)
        diversify(tmp_path)
        assert (ch / "ch01_intro.tex").read_text() == orig

    def test_missing_dir(self, tmp_path):
        diversify(tmp_path)


class TestDeduplicateCrossChapter:
    def test_renames_second(self, tmp_path):
        ch = _mkch(tmp_path)
        (ch / "ch03_sensors.tex").write_text(r"\includegraphics{figures/my_fig.png}")
        (ch / "ch05_fusion.tex").write_text(r"\includegraphics{figures/my_fig.png}")
        dedup(tmp_path)
        assert "my_fig.png" in (ch / "ch03_sensors.tex").read_text()
        assert "my_fig_ch05.png" in (ch / "ch05_fusion.tex").read_text()

    def test_unique_unchanged(self, tmp_path):
        ch = _mkch(tmp_path)
        (ch / "ch03_sensors.tex").write_text(r"\includegraphics{figures/a.png}")
        (ch / "ch05_fusion.tex").write_text(r"\includegraphics{figures/b.png}")
        dedup(tmp_path)
        assert "a.png" in (ch / "ch03_sensors.tex").read_text()
        assert "b.png" in (ch / "ch05_fusion.tex").read_text()

    def test_ignores_stub(self, tmp_path):
        ch = _mkch(tmp_path)
        (ch / "ch03_sensors.tex").write_text(STUB)
        (ch / "ch05_fusion.tex").write_text(STUB)
        dedup(tmp_path)
        assert "fig_stub.png" in (ch / "ch05_fusion.tex").read_text()


class TestGenerateFallbackFigures:
    def _setup(self, tmp_path):
        ch = _mkch(tmp_path)
        fig = tmp_path / "latex" / "figures"
        fig.mkdir(parents=True)
        return ch, fig

    def test_generates_missing(self, tmp_path):
        ch, fig = self._setup(tmp_path)
        (ch / "ch03_sensors.tex").write_text(r"\includegraphics{figures/sensor_map.png}")
        gen_fallback(tmp_path)
        assert (fig / "sensor_map.png").exists() and (fig / "sensor_map.png").stat().st_size > 100

    def test_skips_large_existing(self, tmp_path):
        ch, fig = self._setup(tmp_path)
        (fig / "real.png").write_bytes(b"x" * 5000)
        (ch / "ch01_intro.tex").write_text(r"\includegraphics{figures/real.png}")
        gen_fallback(tmp_path)
        assert (fig / "real.png").read_bytes() == b"x" * 5000

    def test_matplotlib_import_error(self, tmp_path):
        ch, fig = self._setup(tmp_path)
        (ch / "ch01_intro.tex").write_text(r"\includegraphics{figures/miss.png}")
        import builtins

        real_import = builtins.__import__

        def mock_import(n, *a, **k):
            if n == "matplotlib":
                raise ImportError
            return real_import(n, *a, **k)

        with patch("builtins.__import__", side_effect=mock_import):
            gen_fallback(tmp_path)
        assert not (fig / "miss.png").exists()

    def test_missing_dir(self, tmp_path):
        gen_fallback(tmp_path)


class TestInferStyleFromName:
    @pytest.mark.parametrize("name,exp", [
        ("trajectory_3d.png", "trajectory_3d"), ("sensor_heatmap.png", "sensor_heatmap"),
        ("bar_comparison.png", "fusion_comparison"), ("echo_signal.png", "bio_signal"),
        ("system_pipeline.png", "architecture"), ("potential_field.png", "potential_field"),
        ("result_panel.png", "results_multi"), ("convergence_plot.png", "convergence"),
        ("random_name.png", "bio_signal"),
    ])
    def test_keyword_matching(self, name, exp):
        assert _infer_style_from_name(name) == exp


class TestRenderFallbackFigure:
    @pytest.mark.parametrize("style", [
        "system_concept", "bio_signal", "sensor_heatmap", "trajectory_3d",
        "fusion_comparison", "potential_field", "architecture",
        "results_multi", "convergence", "unknown_style",
    ])
    def test_produces_file(self, tmp_path, style):
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np

        out = tmp_path / f"fig_{style}.png"
        _render_fallback_figure(plt, np, out, "Test Label", style)
        assert out.exists() and out.stat().st_size > 100
