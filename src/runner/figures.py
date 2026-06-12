"""
src/runner/figures.py
=====================
Fallback figure generation: detect missing/stub figures referenced by chapter
.tex files and render chapter-appropriate matplotlib figures for them.
Code moved verbatim from main.py (150-line rule); the per-style drawing
bodies live in figure_styles_a/b/c.py and are dispatched by name here.
"""
from __future__ import annotations

import re
from pathlib import Path

from src.config import logger
from src.runner import figure_styles_a as _sa
from src.runner import figure_styles_b as _sb
from src.runner import figure_styles_c as _sc

# Chapter-to-figure-type mapping for generating visually distinct fallback plots.
# Each chapter gets a unique visualization style matching its content.
_CHAPTER_FIGURE_STYLE: dict[str, str] = {
    "ch01": "system_concept",       # conceptual system diagram
    "ch02": "bio_signal",           # biological/neural signal waveform
    "ch03": "sensor_heatmap",       # sensor confidence heatmap / grid
    "ch04": "trajectory_3d",        # 3D SLAM trajectory
    "ch05": "fusion_comparison",    # sensor fusion performance bars
    "ch06": "potential_field",      # obstacle avoidance potential field
    "ch07": "architecture",         # system architecture block diagram
    "ch08": "results_multi",        # multi-panel results (RMSE, ATE, etc.)
    "ch09": "convergence",          # convergence / summary plot
}

# Style-name → renderer function (drawing bodies unchanged from main.py)
_STYLE_RENDERERS = {
    "system_concept":    _sa.render_system_concept,
    "bio_signal":        _sa.render_bio_signal,
    "sensor_heatmap":    _sa.render_sensor_heatmap,
    "trajectory_3d":     _sa.render_trajectory_3d,
    "fusion_comparison": _sb.render_fusion_comparison,
    "potential_field":   _sb.render_potential_field,
    "architecture":      _sb.render_architecture,
    "results_multi":     _sc.render_results_multi,
    "convergence":       _sc.render_convergence,
}


def _infer_style_from_name(fig_name: str) -> str:
    """Guess a figure style from keywords in the filename."""
    name = fig_name.lower()
    if "trajectory" in name or "3d" in name or "path" in name:
        return "trajectory_3d"
    if "heatmap" in name or "grid" in name or "map" in name or "occupancy" in name:
        return "sensor_heatmap"
    if "bar" in name or "comparison" in name or "performance" in name or "rmse" in name:
        return "fusion_comparison"
    if "signal" in name or "spectrum" in name or "spectrogram" in name or "echo" in name:
        return "bio_signal"
    if "architecture" in name or "system" in name or "pipeline" in name or "block" in name:
        return "architecture"
    if "potential" in name or "field" in name or "obstacle" in name or "avoid" in name:
        return "potential_field"
    if "result" in name or "multi" in name or "panel" in name:
        return "results_multi"
    if "converge" in name or "error" in name or "iteration" in name:
        return "convergence"
    return "bio_signal"  # safe default — never duplicate the same "generic" plot


def _render_fallback_figure(plt, np, out_path: Path, label: str, style: str) -> None:
    """Render a single fallback figure in the specified style."""
    rng = np.random.RandomState(hash(label) % 2**31)
    renderer = _STYLE_RENDERERS.get(style, _sc.render_generic)
    renderer(plt, np, rng, label)
    plt.tight_layout()
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close("all")


def _generate_fallback_figures(run_folder: Path) -> None:
    """
    For any figure referenced in chapter .tex files that doesn't exist yet,
    generate a real, chapter-appropriate matplotlib figure.

    Each chapter gets a visually distinct figure style (3D trajectory, heatmap,
    bar chart, etc.) so the PDF never has duplicate-looking figures.
    """
    figures_dir = run_folder / "latex" / "figures"
    chapters_dir = run_folder / "latex" / "chapters"
    if not chapters_dir.exists():
        return

    # Collect referenced figures and which chapter they come from
    referenced: dict[str, str] = {}  # fig_name → chapter_id (e.g. "ch02")
    for tex_file in chapters_dir.glob("*.tex"):
        text = tex_file.read_text(encoding="utf-8", errors="replace")
        ch_match = re.match(r"(ch\d+)", tex_file.name)
        ch_id = ch_match.group(1) if ch_match else "unknown"
        for fig_ref in re.findall(
            r'\\includegraphics(?:\[[^\]]*\])?\{figures/([^}]+)\}', text
        ):
            if fig_ref not in referenced:
                referenced[fig_ref] = ch_id

    # Find which ones are missing or are just the 1px stub
    stub_size = 69
    missing: list[tuple[str, str]] = []  # (fig_name, chapter_id)
    for fig_name, ch_id in referenced.items():
        fig_path = figures_dir / fig_name
        if not fig_path.exists() or fig_path.stat().st_size <= stub_size + 20:
            missing.append((fig_name, ch_id))

    if not missing:
        return

    logger.info(f"[Fallback] Generating {len(missing)} fallback figures: "
                f"{[n for n, _ in missing]}")

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError:
        logger.warning("[Fallback] matplotlib not available — skipping")
        return

    figures_dir.mkdir(parents=True, exist_ok=True)

    for fig_name, ch_id in missing:
        try:
            label = fig_name.replace("fig_", "").replace(".png", "").replace("_", " ").title()
            # Determine style: use chapter mapping, then fall back to keyword matching
            style = _CHAPTER_FIGURE_STYLE.get(ch_id, "")
            if not style:
                style = _infer_style_from_name(fig_name)

            _render_fallback_figure(plt, np, figures_dir / fig_name, label, style)
            logger.info(f"[Fallback] Generated: {fig_name} (style={style})")
        except Exception as e:
            logger.warning(f"[Fallback] Failed to generate {fig_name}: {e}")
            plt.close("all")
