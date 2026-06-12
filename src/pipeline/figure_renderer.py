"""
figure_renderer.py
==================
Render chapter-appropriate matplotlib fallback figures.

Each chapter gets a visually distinct figure style (3D trajectory, heatmap,
bar chart, etc.) so the PDF never has duplicate-looking figures.
This module contains the first half of styles: system_concept, bio_signal,
sensor_heatmap, trajectory_3d, fusion_comparison.
"""

from pathlib import Path

from src.pipeline.figure_renderer_ext import (
    _render_architecture,
    _render_convergence,
    _render_default,
    _render_potential_field,
    _render_results_multi,
)
from src.pipeline.figure_renderer_extra import (
    _render_fusion_comparison,
    _render_sensor_heatmap,
)

# Chapter-to-figure-type mapping for generating visually distinct fallback plots.
_CHAPTER_FIGURE_STYLE: dict[str, str] = {
    "ch01": "system_concept",
    "ch02": "bio_signal",
    "ch03": "sensor_heatmap",
    "ch04": "trajectory_3d",
    "ch05": "fusion_comparison",
    "ch06": "potential_field",
    "ch07": "architecture",
    "ch08": "results_multi",
    "ch09": "convergence",
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
    return "bio_signal"


def _render_fallback_figure(plt, np, out_path: Path, label: str, style: str) -> None:
    """Render a single fallback figure in the specified style."""
    rng = np.random.RandomState(hash(label) % 2**31)

    if style == "system_concept":
        _render_system_concept(plt, np, rng, label)
    elif style == "bio_signal":
        _render_bio_signal(plt, np, rng, label)
    elif style == "sensor_heatmap":
        _render_sensor_heatmap(plt, np, rng, label)
    elif style == "trajectory_3d":
        _render_trajectory_3d(plt, np, rng, label)
    elif style == "fusion_comparison":
        _render_fusion_comparison(plt, np, rng, label)
    elif style == "potential_field":
        _render_potential_field(plt, np, rng, label)
    elif style == "architecture":
        _render_architecture(plt, np, rng, label)
    elif style == "results_multi":
        _render_results_multi(plt, np, rng, label)
    elif style == "convergence":
        _render_convergence(plt, np, rng, label)
    else:
        _render_default(plt, np, rng, label)

    plt.tight_layout()
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close("all")


def _render_system_concept(plt, np, rng, label: str) -> None:
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 6)
    boxes = [
        (0.5, 4, "Ultrasonic\nSensor"), (0.5, 2, "IMU"),
        (0.5, 0, "Optical\nFlow"),
        (4, 2.5, "Sensor\nFusion\n(EKF)"), (7, 4, "SLAM\nBackend"),
        (7, 1, "Obstacle\nAvoidance"),
        (10, 2.5, "Flight\nController"),
    ]
    for bx, by, txt in boxes:
        ax.add_patch(plt.Rectangle((bx, by), 2.2, 1.5, fill=True,
                                   facecolor="#E3F2FD", edgecolor="#1565C0",
                                   linewidth=2, zorder=2))
        ax.text(bx + 1.1, by + 0.75, txt, ha="center", va="center",
                fontsize=10, fontweight="bold", zorder=3)
    arrows = [
        ((2.7, 4.75), (4, 3.5)), ((2.7, 2.75), (4, 3.0)),
        ((2.7, 0.75), (4, 2.7)),
        ((6.2, 3.5), (7, 4.5)), ((6.2, 2.7), (7, 1.5)),
        ((9.2, 4.5), (10, 3.5)), ((9.2, 1.5), (10, 2.7)),
    ]
    for (x1, y1), (x2, y2) in arrows:
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                    arrowprops={"arrowstyle": "-|>", "lw": 2, "color": "#1565C0"},
                    zorder=1)
    ax.set_title(label, fontsize=14, fontweight="bold")
    ax.axis("off")


def _render_bio_signal(plt, np, rng, label: str) -> None:
    fig, axes = plt.subplots(2, 1, figsize=(10, 6))
    t = np.linspace(0, 0.01, 2000)
    f0, f1 = 40000, 80000
    chirp = np.sin(2 * np.pi * (f0 * t + (f1 - f0) / (2 * 0.01) * t**2))
    chirp *= np.exp(-200 * (t - 0.005)**2)
    echo = 0.4 * np.roll(chirp, 300) + 0.15 * rng.randn(len(t))
    axes[0].plot(t * 1000, chirp, color="#1565C0", linewidth=1.2, label="Emitted chirp")
    axes[0].plot(t * 1000, echo, color="#E65100", linewidth=1.0, alpha=0.8, label="Received echo")
    axes[0].set_xlabel("Time [ms]", fontsize=12)
    axes[0].set_ylabel("Amplitude", fontsize=12)
    axes[0].legend(fontsize=11)
    axes[0].set_title("Ultrasonic Chirp Signal", fontsize=13)
    axes[0].tick_params(labelsize=11)
    full_sig = chirp + echo
    axes[1].specgram(full_sig, NFFT=128, noverlap=64, Fs=200000, cmap="inferno")
    axes[1].set_xlabel("Time [s]", fontsize=12)
    axes[1].set_ylabel("Frequency [Hz]", fontsize=12)
    axes[1].set_title("Time-Frequency Spectrogram", fontsize=13)
    axes[1].tick_params(labelsize=11)


def _render_trajectory_3d(plt, np, rng, label: str) -> None:
    fig = plt.figure(figsize=(9, 7))
    ax = fig.add_subplot(111, projection="3d")
    t = np.linspace(0, 6 * np.pi, 800)
    x_gt = np.cos(t) * (1 + 0.2 * t)
    y_gt = np.sin(t) * (1 + 0.2 * t)
    z_gt = t * 0.3
    x_est = x_gt + 0.3 * rng.randn(len(t))
    y_est = y_gt + 0.3 * rng.randn(len(t))
    z_est = z_gt + 0.15 * rng.randn(len(t))
    ax.plot(x_gt, y_gt, z_gt, linewidth=2.5, color="#1565C0", label="Ground truth")
    ax.plot(x_est, y_est, z_est, linewidth=1.5, color="#E65100",
            alpha=0.7, label="Estimated")
    for _ in range(5):
        ox = rng.uniform(-5, 5)
        oy = rng.uniform(-5, 5)
        oz = rng.uniform(0, 5)
        ax.scatter(ox, oy, oz, s=200, c="red", marker="^", alpha=0.6)
    ax.set_xlabel("X [m]", fontsize=12)
    ax.set_ylabel("Y [m]", fontsize=12)
    ax.set_zlabel("Z [m]", fontsize=12)
    ax.set_title(label, fontsize=14)
    ax.legend(fontsize=11)


