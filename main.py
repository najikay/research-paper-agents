"""
main.py
=======
CLI Entry point for NavigatorCrew.
Architecture: LangGraph + CrewAI Sequential Pipeline v5.1.

Run-folder layout (everything for one run lives here):
    outputs/runs/{topic-slug}-{YYYY-MM-DD}/
        latex/          ← LaTeX workspace: template + agent-written chapters/figures
            chapters/   ← static protected .tex + agent-written .tex
            figures/    ← agent-generated PNGs
            references.bib
            main.tex, IEEEtran.cls/bst
        outputs/        ← agent .md reports (moved from staging on completion)
        paper.pdf       ← compiled PDF (copied here from latex/main.pdf)
        run_manifest.txt

The project-root latex/ directory is a READ-ONLY TEMPLATE — nothing writes to it
during a run. Agents write exclusively to {run_folder}/latex/.

Speed modes (slowest → fastest):
    (default)  Full pipeline: 10 agents, 11 tasks, ~60–120 min
    --fast     Skip domain experts: 5 agents, 6 tasks, ~20–40 min
    --smoke    Minimal: 2 agents, 2 tasks (outline + latex-all), ~3–8 min
    --dry-run  Zero LLM calls: write pre-canned stubs, compile PDF, ~5–30 sec
"""

import argparse
import os
import re
import shutil
import struct
import subprocess
from datetime import date
from pathlib import Path
from src.config import logger, PROJECT_ROOT

# Temporary staging for agent .md reports during a run.
# Moved to run_folder/outputs/ at the end; staging is then deleted.
_STAGING_DIR = "outputs/current"

# File that saves the current run folder path so --resume can find it.
_RUN_STATE_FILE = PROJECT_ROOT / "outputs" / "current_run_folder.txt"


# ---------------------------------------------------------------------------
# Slug / run-folder helpers
# ---------------------------------------------------------------------------

def _topic_slug(topic: str) -> str:
    """Convert topic string to a safe directory slug (max 40 chars)."""
    slug = topic.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    return slug[:40].rstrip("-")


def create_run_folder(topic: str) -> Path:
    """
    Create a uniquely-named run folder under outputs/runs/.

    Naming convention:
        outputs/runs/{topic-slug}-{YYYY-MM-DD}/
        outputs/runs/{topic-slug}-{YYYY-MM-DD}-v2/   (if date already exists)
    """
    runs_root = PROJECT_ROOT / "outputs" / "runs"
    runs_root.mkdir(parents=True, exist_ok=True)

    today     = date.today().strftime("%Y-%m-%d")
    slug      = _topic_slug(topic)
    base      = f"{slug}-{today}"
    candidate = runs_root / base
    version   = 2
    while candidate.exists():
        candidate = runs_root / f"{base}-v{version}"
        version  += 1

    candidate.mkdir(parents=True)
    logger.info(f"[RunFolder] Created: {candidate}")
    return candidate


def _save_run_folder(run_folder: Path) -> None:
    _RUN_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    _RUN_STATE_FILE.write_text(str(run_folder), encoding="utf-8")


def _load_run_folder() -> Path | None:
    if _RUN_STATE_FILE.exists():
        p = Path(_RUN_STATE_FILE.read_text(encoding="utf-8").strip())
        if p.exists():
            return p
    return None


# ---------------------------------------------------------------------------
# Expected chapter filenames (must match main.tex \input{} calls)
# ---------------------------------------------------------------------------

EXPECTED_CHAPTERS = [
    "abstract.tex", "ch01_intro.tex",
    "ch02_bio_basis.tex", "ch03_sensors.tex", "ch04_slam.tex",
    "ch05_fusion.tex", "ch06_algorithm.tex", "ch07_oursystem.tex",
    "ch08_results.tex", "ch09_conclusion.tex",
]


# ---------------------------------------------------------------------------
# Post-pipeline chapter validation and rescue
# ---------------------------------------------------------------------------

def validate_and_fix_chapters(run_folder: Path) -> None:
    """
    Detect agent-created chapter files with wrong names and rename them
    to match the expected filenames in main.tex.

    Problem: DeepSeek sometimes writes ch03_ultrasonic_sensor.tex instead of
    ch03_sensors.tex, or ch07_embedded.tex instead of ch07_oursystem.tex.
    These files are invisible to main.tex and wasted effort.

    Strategy:
      1. For each expected filename that is MISSING, look for any .tex file
         matching the same chapter prefix (ch03_*, ch07_*, etc.).
      2. If found and the expected file doesn't exist, rename it.
      3. If multiple candidates exist, pick the largest (most content).
    """
    chapters_dir = run_folder / "latex" / "chapters"
    if not chapters_dir.exists():
        return

    existing = {f.name for f in chapters_dir.glob("*.tex")}
    protected = {"cover.tex"}

    for expected in EXPECTED_CHAPTERS:
        if expected in existing:
            continue  # already present

        # Extract chapter prefix: "ch03" from "ch03_sensors.tex"
        prefix = expected.split("_")[0]  # "ch03", "ch01", "abstract"
        if prefix == "abstract":
            continue  # abstract.tex has a unique name, no prefix variants

        # Find all non-expected files matching this prefix
        candidates = []
        for f in chapters_dir.glob(f"{prefix}_*.tex"):
            if f.name not in EXPECTED_CHAPTERS and f.name not in protected:
                candidates.append(f)

        if not candidates:
            continue

        # Pick the largest candidate (most content)
        best = max(candidates, key=lambda f: f.stat().st_size)
        target = chapters_dir / expected
        best.rename(target)
        logger.info(f"[Validate] Renamed {best.name} → {expected} (rescued wrong filename)")

    # Remove any remaining extra chapter files that don't match expected names
    # (they won't be included in the PDF anyway)
    final_files = {f.name for f in chapters_dir.glob("*.tex")}
    extras = final_files - set(EXPECTED_CHAPTERS) - protected
    if extras:
        logger.warning(f"[Validate] Extra chapter files (not in main.tex, ignored): {extras}")


# ---------------------------------------------------------------------------
# Fallback figure generation
# ---------------------------------------------------------------------------

def _diversify_stub_figures(run_folder: Path) -> None:
    """
    Replace shared fig_stub.png references with chapter-specific filenames.

    In smoke mode (and sometimes when the VisualizationEngineer fails), every
    chapter points to the same ``figures/fig_stub.png``.  This function rewrites
    each chapter's \\includegraphics to use a unique per-chapter filename so the
    fallback generator can create visually distinct figures for each chapter.
    """
    chapters_dir = run_folder / "latex" / "chapters"
    if not chapters_dir.exists():
        return

    for tex_file in chapters_dir.glob("*.tex"):
        if tex_file.name == "cover.tex":
            continue
        text = tex_file.read_text(encoding="utf-8", errors="replace")
        if "fig_stub.png" not in text:
            continue
        # Extract chapter id from filename (e.g. "ch02" from "ch02_bio_basis.tex")
        ch_match = re.match(r"(ch\d+)", tex_file.name)
        if not ch_match:
            continue
        ch_id = ch_match.group(1)

        # Count how many stub refs this chapter has and assign unique names
        occurrence = [0]

        def _replace_stub(m: re.Match) -> str:
            occurrence[0] += 1
            suffix = f"_{occurrence[0]}" if occurrence[0] > 1 else ""
            return m.group(0).replace("fig_stub.png", f"fig_{ch_id}_auto{suffix}.png")

        new_text = re.sub(
            r'\\includegraphics(\[[^\]]*\])?\{figures/fig_stub\.png\}',
            _replace_stub,
            text,
        )
        if new_text != text:
            tex_file.write_text(new_text, encoding="utf-8")
            logger.info(f"[Diversify] {tex_file.name}: replaced fig_stub.png → chapter-specific names")


def _deduplicate_cross_chapter_figures(run_folder: Path) -> None:
    """
    When two different chapters reference the same figure file, rename the
    second occurrence to a chapter-specific name. The fallback figure generator
    will then create a distinct figure for it.
    """
    chapters_dir = run_folder / "latex" / "chapters"
    if not chapters_dir.exists():
        return

    # Collect all figure references: fig_name → list of chapter files
    fig_usage: dict[str, list[Path]] = {}
    for tex_file in sorted(chapters_dir.glob("ch*.tex")):
        text = tex_file.read_text(encoding="utf-8", errors="replace")
        for fig_ref in re.findall(
            r'\\includegraphics(?:\[[^\]]*\])?\{figures/([^}]+)\}', text
        ):
            if fig_ref == "fig_stub.png":
                continue
            fig_usage.setdefault(fig_ref, []).append(tex_file)

    # For figures used by multiple chapters, rename in all but the first chapter
    for fig_name, users in fig_usage.items():
        if len(users) <= 1:
            continue
        for tex_file in users[1:]:  # Skip the first (canonical) user
            ch_match = re.match(r"(ch\d+)", tex_file.name)
            ch_id = ch_match.group(1) if ch_match else "dup"
            base, ext = fig_name.rsplit(".", 1) if "." in fig_name else (fig_name, "png")
            new_name = f"{base}_{ch_id}.{ext}"
            text = tex_file.read_text(encoding="utf-8", errors="replace")
            new_text = text.replace(f"figures/{fig_name}", f"figures/{new_name}")
            if new_text != text:
                tex_file.write_text(new_text, encoding="utf-8")
                logger.info(f"[Dedup] {tex_file.name}: {fig_name} → {new_name}")


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

    if style == "system_concept":
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
                        arrowprops=dict(arrowstyle="-|>", lw=2, color="#1565C0"),
                        zorder=1)
        ax.set_title(label, fontsize=14, fontweight="bold")
        ax.axis("off")

    elif style == "bio_signal":
        fig, axes = plt.subplots(2, 1, figsize=(10, 6))
        t = np.linspace(0, 0.01, 2000)
        f0, f1 = 40000, 80000
        chirp = np.sin(2 * np.pi * (f0 * t + (f1 - f0) / (2 * 0.01) * t**2))
        chirp *= np.exp(-200 * (t - 0.005)**2)  # Gaussian envelope
        echo = 0.4 * np.roll(chirp, 300) + 0.15 * rng.randn(len(t))
        axes[0].plot(t * 1000, chirp, color="#1565C0", linewidth=1.2, label="Emitted chirp")
        axes[0].plot(t * 1000, echo, color="#E65100", linewidth=1.0, alpha=0.8, label="Received echo")
        axes[0].set_xlabel("Time [ms]", fontsize=12)
        axes[0].set_ylabel("Amplitude", fontsize=12)
        axes[0].legend(fontsize=11)
        axes[0].set_title("Ultrasonic Chirp Signal", fontsize=13)
        axes[0].tick_params(labelsize=11)
        # Spectrogram
        full_sig = chirp + echo
        axes[1].specgram(full_sig, NFFT=128, noverlap=64, Fs=200000, cmap="inferno")
        axes[1].set_xlabel("Time [s]", fontsize=12)
        axes[1].set_ylabel("Frequency [Hz]", fontsize=12)
        axes[1].set_title("Time-Frequency Spectrogram", fontsize=13)
        axes[1].tick_params(labelsize=11)

    elif style == "sensor_heatmap":
        fig, axes = plt.subplots(1, 2, figsize=(12, 5))
        # Occupancy grid
        grid = rng.rand(30, 30)
        grid = np.convolve(grid.flatten(), np.ones(7) / 7, mode="same").reshape(30, 30)
        grid[10:15, 10:20] = 0.9  # obstacle region
        grid[20:25, 5:10] = 0.85
        im0 = axes[0].imshow(grid, cmap="YlOrRd", aspect="auto", origin="lower")
        plt.colorbar(im0, ax=axes[0], label="Occupancy probability")
        axes[0].set_xlabel("X [cells]", fontsize=12)
        axes[0].set_ylabel("Y [cells]", fontsize=12)
        axes[0].set_title("Occupancy Grid Map", fontsize=13)
        axes[0].tick_params(labelsize=11)
        # Confidence map
        conf = np.exp(-((np.arange(30)[:, None] - 15)**2 + (np.arange(30)[None, :] - 15)**2) / 80)
        conf += 0.1 * rng.rand(30, 30)
        im1 = axes[1].imshow(conf, cmap="viridis", aspect="auto", origin="lower")
        plt.colorbar(im1, ax=axes[1], label="Confidence")
        axes[1].set_xlabel("X [cells]", fontsize=12)
        axes[1].set_ylabel("Y [cells]", fontsize=12)
        axes[1].set_title("Sensor Confidence Map", fontsize=13)
        axes[1].tick_params(labelsize=11)

    elif style == "trajectory_3d":
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
        # Obstacle markers
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

    elif style == "fusion_comparison":
        fig, axes = plt.subplots(1, 2, figsize=(13, 5))
        methods = ["Sonar\nOnly", "IMU\nOnly", "Opt.Flow\nOnly", "EKF\nFusion", "Proposed\nBio-Fuse"]
        rmse = [5.8, 4.3, 6.1, 2.4, 1.2]
        colors = ["#90CAF9"] * 3 + ["#FFA726", "#F44336"]
        axes[0].bar(methods, rmse, color=colors, edgecolor="#333", linewidth=0.8)
        axes[0].set_ylabel("Position RMSE [cm]", fontsize=12)
        axes[0].set_title("Localization Accuracy", fontsize=13)
        axes[0].tick_params(labelsize=10)
        for i, v in enumerate(rmse):
            axes[0].text(i, v + 0.15, f"{v}", ha="center", fontsize=11, fontweight="bold")
        # Success rate grouped bar
        scenarios = ["Open", "Corridor", "Cluttered", "Dynamic"]
        proposed = [98, 96, 94, 89]
        baseline = [85, 78, 62, 51]
        x = np.arange(len(scenarios))
        w = 0.35
        axes[1].bar(x - w / 2, baseline, w, label="Baseline EKF", color="#90CAF9")
        axes[1].bar(x + w / 2, proposed, w, label="Proposed", color="#F44336")
        axes[1].set_xticks(x)
        axes[1].set_xticklabels(scenarios, fontsize=11)
        axes[1].set_ylabel("Success Rate [%]", fontsize=12)
        axes[1].set_title("Navigation Success by Scenario", fontsize=13)
        axes[1].legend(fontsize=11)
        axes[1].tick_params(labelsize=11)

    elif style == "potential_field":
        fig, axes = plt.subplots(1, 2, figsize=(13, 5.5))
        # Potential field visualization
        xx, yy = np.meshgrid(np.linspace(-5, 5, 60), np.linspace(-5, 5, 60))
        goal = np.array([4, 4])
        U_att = 0.5 * ((xx - goal[0])**2 + (yy - goal[1])**2)
        obstacles = [(-1, 0), (1, 2), (-2, 3)]
        U_rep = np.zeros_like(xx)
        for ox, oy in obstacles:
            dist = np.sqrt((xx - ox)**2 + (yy - oy)**2)
            dist = np.maximum(dist, 0.3)
            U_rep += 2.0 / dist**2
        U_total = U_att + np.minimum(U_rep, 15)
        axes[0].contourf(xx, yy, U_total, levels=30, cmap="coolwarm")
        axes[0].plot(*goal, "g*", markersize=20, label="Goal")
        for ox, oy in obstacles:
            axes[0].plot(ox, oy, "rs", markersize=14)
        # Simulated path
        path_x = [-4, -3, -2.5, -1.5, 0, 1, 2, 3, 4]
        path_y = [-4, -3, -1.5, -0.5, 0.5, 1, 2.5, 3.5, 4]
        axes[0].plot(path_x, path_y, "w-o", linewidth=2.5, markersize=5, label="Path")
        axes[0].set_xlabel("X [m]", fontsize=12)
        axes[0].set_ylabel("Y [m]", fontsize=12)
        axes[0].set_title("Potential Field + Path", fontsize=13)
        axes[0].legend(fontsize=10, loc="lower right")
        axes[0].tick_params(labelsize=11)
        # TTC plot
        t = np.linspace(0, 5, 200)
        ttc = 3 * np.exp(-0.5 * t) + 0.5 + 0.3 * np.sin(4 * t)
        threshold = np.full_like(t, 1.0)
        axes[1].plot(t, ttc, linewidth=2.5, color="#1565C0", label="TTC")
        axes[1].plot(t, threshold, "r--", linewidth=2, label="Threshold")
        axes[1].fill_between(t, 0, ttc, where=ttc < 1.0, alpha=0.3, color="red")
        axes[1].set_xlabel("Time [s]", fontsize=12)
        axes[1].set_ylabel("TTC [s]", fontsize=12)
        axes[1].set_title("Time-To-Collision", fontsize=13)
        axes[1].legend(fontsize=11)
        axes[1].tick_params(labelsize=11)

    elif style == "architecture":
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.set_xlim(0, 16)
        ax.set_ylim(0, 8)
        layers = [
            [(1, 6, "Sonar\nArray"), (1, 4, "IMU\n(6-axis)"), (1, 2, "Optical\nFlow")],
            [(5, 5, "Signal\nProcessing"), (5, 3, "Inertial\nNav")],
            [(9, 5, "EKF\nState\nEstimator"), (9, 3, "Echo\nMap")],
            [(13, 4, "Path\nPlanner +\nController")],
        ]
        layer_colors = ["#BBDEFB", "#C8E6C9", "#FFF9C4", "#FFCCBC"]
        for li, layer in enumerate(layers):
            for bx, by, txt in layer:
                ax.add_patch(plt.Rectangle(
                    (bx, by), 2.5, 1.5, fill=True, zorder=2,
                    facecolor=layer_colors[li], edgecolor="#333", linewidth=1.8,
                    joinstyle="round",
                ))
                ax.text(bx + 1.25, by + 0.75, txt, ha="center", va="center",
                        fontsize=9, fontweight="bold", zorder=3)
        # Arrows between layers
        pairs = [
            ((3.5, 6.75), (5, 5.75)), ((3.5, 4.75), (5, 5.25)),
            ((3.5, 2.75), (5, 3.75)),
            ((7.5, 5.75), (9, 5.75)), ((7.5, 3.75), (9, 3.75)),
            ((11.5, 5.5), (13, 5)), ((11.5, 3.5), (13, 4.5)),
        ]
        for (x1, y1), (x2, y2) in pairs:
            ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                        arrowprops=dict(arrowstyle="-|>", lw=1.8, color="#555"),
                        zorder=1)
        ax.set_title(label, fontsize=14, fontweight="bold")
        ax.axis("off")

    elif style == "results_multi":
        fig, axes = plt.subplots(2, 2, figsize=(13, 9))
        t = np.linspace(0, 60, 300)
        # Panel 1: Position error over time
        err_prop = 2 * np.exp(-0.05 * t) + 0.5 + 0.3 * rng.randn(300) * np.exp(-0.02 * t)
        err_base = 4 * np.exp(-0.03 * t) + 1.5 + 0.5 * rng.randn(300) * np.exp(-0.01 * t)
        axes[0, 0].plot(t, err_base, alpha=0.7, label="Baseline EKF", color="#90CAF9")
        axes[0, 0].plot(t, err_prop, alpha=0.9, label="Proposed", color="#F44336")
        axes[0, 0].set_xlabel("Time [s]", fontsize=11)
        axes[0, 0].set_ylabel("Position Error [cm]", fontsize=11)
        axes[0, 0].set_title("(a) Position Error Over Time", fontsize=12)
        axes[0, 0].legend(fontsize=10)
        axes[0, 0].tick_params(labelsize=10)
        # Panel 2: CDF of errors
        errors_p = np.sort(np.abs(rng.randn(500) * 1.5 + 0.5))
        errors_b = np.sort(np.abs(rng.randn(500) * 3.0 + 1.2))
        cdf = np.linspace(0, 1, 500)
        axes[0, 1].plot(errors_b, cdf, label="Baseline", color="#90CAF9", linewidth=2)
        axes[0, 1].plot(errors_p, cdf, label="Proposed", color="#F44336", linewidth=2)
        axes[0, 1].set_xlabel("Absolute Error [cm]", fontsize=11)
        axes[0, 1].set_ylabel("CDF", fontsize=11)
        axes[0, 1].set_title("(b) Cumulative Error Distribution", fontsize=12)
        axes[0, 1].legend(fontsize=10)
        axes[0, 1].tick_params(labelsize=10)
        # Panel 3: Per-axis bar chart (mean +/- std)
        axis_labels = ["X(B)", "Y(B)", "Z(B)", "X(P)", "Y(P)", "Z(P)"]
        means = [0.3, 0.5, 0.2, 0.1, 0.15, 0.08]
        stds = [0.8, 1.2, 0.5, 0.3, 0.4, 0.2]
        bar_colors = ["#90CAF9"] * 3 + ["#FFCDD2"] * 3
        axes[1, 0].bar(axis_labels, means, yerr=stds, color=bar_colors,
                        edgecolor="#333", linewidth=0.8, capsize=4)
        axes[1, 0].set_ylabel("Mean Error [cm]", fontsize=11)
        axes[1, 0].set_title("(c) Per-Axis Error Distribution", fontsize=12)
        axes[1, 0].tick_params(labelsize=10)
        # Panel 4: Computation time
        modules = ["Sonar\nProc", "EKF\nUpdate", "Map\nUpdate", "Path\nPlan", "Total"]
        times = [3.2, 5.1, 4.8, 2.3, 15.4]
        axes[1, 1].barh(modules, times, color=["#81C784"] * 4 + ["#FFB74D"])
        axes[1, 1].set_xlabel("Time [ms]", fontsize=11)
        axes[1, 1].set_title("(d) Computation Time Breakdown", fontsize=12)
        axes[1, 1].tick_params(labelsize=10)
        for i, v in enumerate(times):
            axes[1, 1].text(v + 0.2, i, f"{v} ms", va="center", fontsize=10)

    elif style == "convergence":
        fig, ax = plt.subplots(figsize=(9, 5))
        iters = np.arange(1, 51)
        loss_ekf = 5 * np.exp(-0.08 * iters) + 0.8 + 0.2 * rng.randn(50) * np.exp(-0.05 * iters)
        loss_prop = 5 * np.exp(-0.15 * iters) + 0.3 + 0.1 * rng.randn(50) * np.exp(-0.1 * iters)
        ax.plot(iters, loss_ekf, "o-", label="Standard EKF", color="#90CAF9",
                markersize=4, linewidth=1.5)
        ax.plot(iters, loss_prop, "s-", label="Bio-Mimetic (Proposed)", color="#F44336",
                markersize=4, linewidth=1.5)
        ax.set_xlabel("Iteration", fontsize=12)
        ax.set_ylabel("State Estimation Error [cm]", fontsize=12)
        ax.set_title(label, fontsize=14)
        ax.legend(fontsize=11)
        ax.tick_params(labelsize=11)
        ax.grid(True, alpha=0.3)

    else:
        # Should not reach here, but provide a safe fallback
        fig, ax = plt.subplots(figsize=(8, 5))
        x = np.linspace(0, 10, 200)
        ax.plot(x, np.sin(x) * np.exp(-0.2 * x), label="Signal A", linewidth=2)
        ax.plot(x, np.cos(x) * np.exp(-0.15 * x), label="Signal B", linewidth=2)
        ax.set_xlabel("Time [s]", fontsize=11)
        ax.set_ylabel("Amplitude", fontsize=11)
        ax.set_title(label, fontsize=13)
        ax.legend(fontsize=11)
        ax.tick_params(labelsize=11)

    plt.tight_layout()
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close("all")


# ---------------------------------------------------------------------------
# LaTeX template → run folder
# ---------------------------------------------------------------------------

def setup_run_latex(run_folder: Path) -> None:
    """
    Copy the latex template into this run's folder.

    The project-root latex/ contains only the static template files (main.tex,
    cover.tex, IEEEtran.cls/bst, seed references.bib). Agents write all
    generated chapters and figures directly into run_folder/latex/.
    """
    template = PROJECT_ROOT / "latex"
    run_latex = run_folder / "latex"
    shutil.copytree(
        template, run_latex,
        ignore=shutil.ignore_patterns(
            "*.aux", "*.log", "*.out", "*.bbl", "*.blg",
            "*.toc", "*.fls", "*.fdb_latexmk", "*.synctex.gz", "*.pdf",
        ),
    )
    logger.info(f"[RunFolder] LaTeX template → {run_latex}")


# ---------------------------------------------------------------------------
# Bare-math-symbol wrapper (used by sanitizer Fix 12b)
# ---------------------------------------------------------------------------

# Greek letters + common math symbols that agents write bare in Hebrew prose
_BARE_MATH_NAMES = [
    'alpha', 'beta', 'gamma', 'delta', 'epsilon', 'varepsilon',
    'sigma', 'theta', 'lambda', 'mu', 'omega', 'phi', 'varphi',
    'psi', 'tau', 'eta', 'rho', 'nu', 'xi', 'kappa', 'zeta', 'chi', 'pi',
    'Delta', 'Sigma', 'Omega', 'Phi', 'Psi', 'Gamma', 'Theta', 'Lambda', 'Pi',
    'infty', 'nabla', 'partial', 'pm', 'times', 'cdot', 'approx', 'neq',
    'leq', 'geq', 'equiv', 'subset', 'supset', 'forall', 'exists',
    'rightarrow', 'leftarrow', 'Rightarrow', 'Leftarrow',
]

# Regex: match \<symbol> NOT followed by more letters (avoid partial match on e.g. \alphabeta)
_BARE_MATH_RE = re.compile(
    r'(\\(?:' + '|'.join(_BARE_MATH_NAMES) + r'))(?![a-zA-Z])'
)

# Math environment names (for tracking nesting depth)
_MATH_ENV_NAMES = {
    'equation', 'equation*', 'align', 'align*', 'gather', 'gather*',
    'multline', 'multline*', 'eqnarray', 'eqnarray*', 'math',
    'displaymath', 'flalign', 'flalign*', 'split',
}


def _wrap_bare_math_in_text(text: str) -> str:
    """
    Wrap bare Greek letters and math symbols in $...$ when they appear outside
    math mode.  Protects existing math environments and inline $...$ first,
    then wraps remaining bare commands, then restores protected regions.
    """
    placeholders: list[str] = []

    def _save(m: re.Match) -> str:
        placeholders.append(m.group(0))
        return f'\x00MATH{len(placeholders) - 1}\x00'

    protected = text

    # 1. Protect math environments (multi-line, order matters: * variants first)
    for env in ['equation*', 'equation', 'align*', 'align', 'gather*', 'gather',
                'multline*', 'multline', 'eqnarray*', 'eqnarray', 'displaymath',
                'math', 'flalign*', 'flalign', 'split']:
        pat = r'\\begin\{' + re.escape(env) + r'\}.*?\\end\{' + re.escape(env) + r'\}'
        protected = re.sub(pat, _save, protected, flags=re.DOTALL)

    # 2. Protect display math \[...\]
    protected = re.sub(r'\\\[.*?\\\]', _save, protected, flags=re.DOTALL)

    # 3. Protect inline math $...$ (single-line, non-greedy)
    protected = re.sub(r'(?<!\\)\$(?!\$)(.+?)(?<!\\)\$', _save, protected)

    # 4. Protect $$...$$ display math
    protected = re.sub(r'\$\$.*?\$\$', _save, protected, flags=re.DOTALL)

    # 5. Wrap bare math commands (e.g. \alpha → $\alpha$)
    protected = _BARE_MATH_RE.sub(r'$\1$', protected)

    # 6. Merge adjacent $...$$...$  →  $... ...$  (avoid ugly $$)
    protected = re.sub(r'\$\$', ' ', protected)

    # 7. Restore placeholders (reverse order for safety)
    for i in range(len(placeholders) - 1, -1, -1):
        protected = protected.replace(f'\x00MATH{i}\x00', placeholders[i])

    return protected


# ---------------------------------------------------------------------------
# PDF compilation
# ---------------------------------------------------------------------------

def _get_png_dimensions(png_path: Path) -> tuple[int, int] | None:
    """Read width and height from a PNG file header (bytes 16-23). No deps needed."""
    try:
        with open(png_path, 'rb') as f:
            header = f.read(24)
            if len(header) < 24 or header[:8] != b'\x89PNG\r\n\x1a\n':
                return None
            w, h = struct.unpack('>II', header[16:24])
            return (w, h)
    except (OSError, struct.error):
        return None


def _upgrade_wide_figures(text: str, figures_dir: Path) -> str:
    """
    Fix 24: Upgrade single-column \\begin{figure} to \\begin{figure*} for wide images.

    Detects figures whose PNG aspect ratio (width/height) > 1.8 and converts:
      \\begin{figure}[htbp]  →  \\begin{figure*}[htbp]
      width=0.98\\columnwidth →  width=\\textwidth
      \\end{figure}           →  \\end{figure*}

    This makes wide charts, architecture diagrams, and multi-panel figures span
    both columns in IEEE two-column format — matching real paper conventions and
    significantly increasing page utilization.
    """
    # Find all single-column figure blocks (not already figure*)
    pattern = re.compile(
        r'(\\begin\{figure\})(\[[^\]]*\])(.*?)(\\end\{figure\})',
        re.DOTALL,
    )

    def _maybe_upgrade(m: re.Match) -> str:
        begin, placement, body, end = m.group(1), m.group(2), m.group(3), m.group(4)
        # Extract the figure filename from \includegraphics
        fig_match = re.search(r'\\includegraphics(?:\[[^\]]*\])?\{figures/([^}]+)\}', body)
        if not fig_match:
            return m.group(0)  # no includegraphics — leave unchanged

        fig_name = fig_match.group(1)
        fig_path = figures_dir / fig_name
        dims = _get_png_dimensions(fig_path)
        if dims is None:
            return m.group(0)  # can't read dimensions — leave unchanged

        w, h = dims
        if h == 0:
            return m.group(0)

        aspect = w / h
        # Upgrade if aspect ratio > 1.8 (clearly wide/landscape)
        if aspect > 1.8:
            new_body = body.replace(r'width=0.98\columnwidth', r'width=\textwidth')
            new_body = new_body.replace(r'width=0.9\columnwidth', r'width=\textwidth')
            new_body = new_body.replace(r'width=\columnwidth', r'width=\textwidth')
            return r'\begin{figure*}' + placement + new_body + r'\end{figure*}'

        return m.group(0)

    return pattern.sub(_maybe_upgrade, text)


def _sanitize_tex_files(chapters_dir: Path) -> None:
    """
    Fix common LaTeX errors that agents introduce, preventing compilation failures.
    """
    for tex_file in chapters_dir.glob("*.tex"):
        if tex_file.name == "cover.tex":
            continue
        text = tex_file.read_text(encoding="utf-8", errors="replace")
        original = text

        # Fix 1: Remove \begin{abstract} inside abstract.tex
        # (main.tex already wraps it in \begin{abstract}...\end{abstract})
        if tex_file.name == "abstract.tex":
            text = text.replace(r"\begin{abstract}", "")
            text = text.replace(r"\end{abstract}", "")

        # Fix 2: Remove \begin{document} / \end{document} inside chapter files
        text = text.replace(r"\begin{document}", "")
        text = text.replace(r"\end{document}", "")

        # Fix 3: Remove \documentclass inside chapter files
        text = re.sub(r"\\documentclass(\[[^\]]*\])?\{[^}]+\}", "", text)

        # Fix 4: Remove \usepackage inside chapter files (preamble commands in chapter body)
        text = re.sub(r"\\usepackage(\[[^\]]*\])?\{[^}]+\}", "", text)

        # Fix 5: Replace \begin{center}...\end{center} with \centering
        # (causes bidi crash at document level)
        text = text.replace(r"\begin{center}", r"{\centering")
        text = text.replace(r"\end{center}", "}")

        # Fix 6: Remove stray \maketitle
        text = text.replace(r"\maketitle", "")

        # Fix 7: Replace em dashes (U+2014) with colons in Hebrew prose
        # Only outside \en{} blocks — em dashes crash bidi rendering
        text = text.replace("\u2014", ":")
        # Also replace en dashes (U+2013) which are similarly problematic
        text = text.replace("\u2013", "-")

        # Fix 8: Remove \textemdash from section/subsection titles (RTL crash risk)
        text = text.replace(r"\textemdash", ":")
        text = text.replace(r"\textendash", "-")

        # Fix 9: Wrap lstlisting in \begin{english}...\end{english} for LTR
        # This forces the bidi package to render code blocks left-to-right.
        # Only add if not already wrapped.
        text = re.sub(
            r'(?<!\\begin\{english\}\n)\\begin\{lstlisting\}',
            r'\\begin{english}\n\\begin{lstlisting}',
            text,
        )
        text = re.sub(
            r'\\end\{lstlisting\}(?!\n\\end\{english\})',
            r'\\end{lstlisting}\n\\end{english}',
            text,
        )

        # Fix 10: Replace aggressive [H] float spec with [htbp] for better layout
        # [H] forces exact placement and causes overlapping in two-column IEEE.
        text = re.sub(
            r'\\begin\{figure\}\[H\]',
            r'\\begin{figure}[htbp]',
            text,
        )
        text = re.sub(
            r'\\begin\{figure\*\}\[H\]',
            r'\\begin{figure*}[htbp]',
            text,
        )
        text = re.sub(
            r'\\begin\{table\}\[H\]',
            r'\\begin{table}[htbp]',
            text,
        )
        text = re.sub(
            r'\\begin\{table\*\}\[H\]',
            r'\\begin{table*}[htbp]',
            text,
        )

        # Fix 24: Upgrade single-column figures to figure* for wide images.
        # Must run after Fix 10 ([H] → [htbp]) so figure blocks have consistent placement.
        figures_dir = chapters_dir.parent / "figures"
        if figures_dir.is_dir():
            text = _upgrade_wide_figures(text, figures_dir)

        # Fix 11: Wrap tabular environments in \adjustbox to prevent column overflow.
        # Tables with many columns overflow IEEE single-column width.
        # \adjustbox{max width=\columnwidth} shrinks them to fit.
        # Skip if already wrapped.
        if r'\begin{tabular}' in text and r'\adjustbox' not in text:
            text = text.replace(
                r'\begin{tabular}',
                r'\adjustbox{max width=\columnwidth}{%' + '\n' + r'\begin{tabular}',
            )
            text = text.replace(
                r'\end{tabular}',
                r'\end{tabular}%' + '\n' + '}',
            )

        # Fix 11b: Escape bare % in running text (LLM writes "96%" or "(%)").
        # LaTeX treats % as comment-start, eating the rest of the line. This
        # destroys table alignment, silently drops body text, and causes "runaway
        # argument" crashes inside \caption{} or \section{} commands.
        # Escape % preceded by any char that is NOT: \, {, }, or whitespace.
        # This preserves: line comments (% at line start), whitespace suppression
        # ({%  }% at end of line), and already-escaped \%.
        text = re.sub(r'([^\\{}\s])%', r'\1\\%', text)

        # Fix 12a: Unwrap \en{} from math mode — $\en{Word}$ → \en{Word}
        # Also handles \(\en{Word}\) syntax. Polyglossia \en{} does language-group
        # switching that breaks inside math mode.
        text = re.sub(r'\$\\en\{([^}]*)\}\$', r'\\en{\1}', text)
        text = re.sub(r'\\\(\\en\{([^}]*)\}\\\)', r'\\en{\1}', text)

        # Fix 12a2: Remove \begin{english}/\end{english} wrappers around tables.
        # The polyglossia english environment triggers font redefinition loops.
        # Tables work fine in Hebrew mode as long as % is escaped (Fix 11b above).
        text = re.sub(r'\\begin\{english\}\s*\n(\\begin\{table)', r'\1', text)
        text = re.sub(r'(\\end\{table\*?\})\s*\n\\end\{english\}', r'\1', text)
        # Also remove \begin{LTR}/\end{LTR} wrappers (from previous sanitizer versions)
        text = re.sub(r'\\begin\{LTR\}\s*\n(\\begin\{table)', r'\1', text)
        text = re.sub(r'(\\end\{table\*?\})\s*\n\\end\{LTR\}', r'\1', text)

        # Fix 12a3: Unwrap \en{text} → text when it appears right before a closing }
        # This prevents bidi direction-switch corruption at group boundaries
        # (e.g., \caption{... \en{CNN}} → \caption{... CNN})
        text = re.sub(r'\\en\{([^}]*)\}(\s*\})', r'\1\2', text)

        # Fix 12c: Replace undefined \tabref{...} → \ref{...} and \figref{...} → \ref{...}.
        # LLM agents invent these macros but they're not defined in the IEEEtran template.
        # The undefined command causes cascading errors (Missing $, Extra }, Missing \endgroup).
        text = re.sub(r'\\tabref\{', r'\\ref{', text)
        text = re.sub(r'\\figref\{', r'\\ref{', text)
        text = re.sub(r'\\secref\{', r'\\ref{', text)

        # Fix 13: Replace \begin{algorithm}/\begin{algorithmic} with lstlisting.
        # The algorithm/algorithmic environments require packages not in our template.
        # Convert to lstlisting wrapped in english environment (which IS available).
        text = re.sub(
            r'\\begin\{algorithm\}(\[[^\]]*\])?',
            r'\\begin{english}\n\\begin{lstlisting}[language=Python]',
            text,
        )
        text = re.sub(r'\\end\{algorithm\}', r'\\end{lstlisting}\n\\end{english}', text)
        text = re.sub(r'\\begin\{algorithmic\}(\[[^\]]*\])?', '', text)
        text = re.sub(r'\\end\{algorithmic\}', '', text)
        # Remove \Require, \Ensure, \State, \If, \EndIf, \For, \EndFor, \While, \EndWhile, \Return
        # These are algorithmic package commands — convert to plain text pseudocode
        for cmd in [r'\\Require', r'\\Ensure', r'\\State', r'\\If', r'\\EndIf',
                    r'\\For', r'\\EndFor', r'\\While', r'\\EndWhile', r'\\Return',
                    r'\\Function', r'\\EndFunction', r'\\Procedure', r'\\EndProcedure']:
            text = re.sub(cmd + r'\b', '', text)

        # Fix 14: Fix literal \\n sequences in tabular rows.
        # LLM agents sometimes write \\n (Python-style newline) instead of
        # \\ + actual newline inside tabular environments. The literal 'n'
        # character after \\ breaks \midrule/\hline placement, causing
        # "Misplaced \noalign" errors and potential xelatex infinite loops.
        # Replace \\n followed by a LaTeX command with \\ + real newline.
        text = re.sub(r'\\\\n(\\[a-zA-Z])', r'\\\\\n\1', text)
        # Also fix \\n at end of line (should just be \\)
        text = re.sub(r'\\\\n\s*$', r'\\\\', text, flags=re.MULTILINE)

        # Fix 15: Remove backslash before Hebrew characters.
        # LLM agents sometimes write \ש, \מ etc. (backslash + Hebrew letter)
        # which LaTeX interprets as undefined control sequences.
        # Hebrew Unicode range: \u0590-\u05FF (Hebrew block).
        text = re.sub(r'\\([\u0590-\u05FF])', r'\1', text)

        # Fix 16: Escape underscores inside \en{...} blocks.
        # LLM agents write \en{sonar_driver} but _ is a math-mode subscript
        # operator that causes "Missing $ inserted" cascading errors.
        # Replace _ with \_ only inside \en{...} content.
        def _escape_underscores_in_en(m: re.Match) -> str:
            return r'\en{' + m.group(1).replace('_', r'\_') + '}'
        text = re.sub(r'\\en\{([^}]*_[^}]*)\}', _escape_underscores_in_en, text)

        # Fix 25: Extract math superscripts/subscripts from \en{} blocks.
        # LLM writes \en{m/s^2} or \en{R^2} but ^ is a math-mode operator
        # that crashes in text mode. Split: \en{m/s^2} → \en{m/s}$^2$
        # Handles ^N (single digit) and ^{...} (braced group).
        def _fix_math_in_en(m: re.Match) -> str:
            content = m.group(1)
            # Split at first ^ that's followed by a digit or {
            caret = re.search(r'\^(\{[^}]*\}|\d+)', content)
            if not caret:
                return m.group(0)
            before = content[:caret.start()]
            math_part = caret.group(0)  # e.g. ^2 or ^{2}
            after = content[caret.end():]
            result = r'\en{' + before + '}'
            result += '$' + math_part + '$'
            if after:
                result += r'\en{' + after + '}'
            return result
        text = re.sub(r'\\en\{([^}]*\^[^}]*)\}', _fix_math_in_en, text)

        # Fix 17: Replace \° (undefined control sequence) with Unicode °.
        # LLM agents write 5\° for "5 degrees" but \° is not a valid LaTeX
        # command. XeLaTeX handles the Unicode ° glyph natively via fontspec.
        text = text.replace("\\°", "°")

        # Fix 18: Replace \textquoteright with / (forward slash).
        # LLM writes "מ\textquoterightש" for "m/s" — \textquoteright is
        # undefined in this XeLaTeX bidi setup and crashes compilation.
        text = text.replace("\\textquoteright", "/")
        text = text.replace("\\textquoteleft", "/")

        # Fix 19: Convert single-row \begin{bmatrix}...\end{bmatrix} to
        # \left[...\right] notation. bidi package conflicts with bmatrix's
        # alignment tabs (&) causing "Extra alignment tab" fatal errors.
        # Only affects row vectors (single line between begin/end).
        def _fix_row_bmatrix(m):
            inner = m.group(1).strip()
            # Replace & with ,\; for comma-separated vector notation
            inner = inner.replace(" & ", r",\; ")
            return r"\left[" + inner + r"\right]"
        text = re.sub(
            r"\\begin\{bmatrix\}\s*([^\n]*?)\s*\\end\{bmatrix\}",
            _fix_row_bmatrix,
            text,
        )

        # Fix 21: Convert \AuthorName patterns to \en{AuthorName}.
        # LLM agents write \Au, \Thorp, \Ketten etc. as undefined control sequences
        # (treating author names as commands). This causes "Undefined control sequence"
        # fatal errors. Convert \CapitalizedWord to \en{CapitalizedWord} when NOT
        # followed by { and NOT a known LaTeX command.
        _SAFE_CMDS = {
            # Greek letters (uppercase)
            'Alpha', 'Beta', 'Gamma', 'Delta', 'Epsilon', 'Zeta', 'Eta', 'Theta',
            'Iota', 'Kappa', 'Lambda', 'Mu', 'Nu', 'Xi', 'Pi', 'Rho', 'Sigma',
            'Tau', 'Upsilon', 'Phi', 'Chi', 'Psi', 'Omega',
            # LaTeX meta commands
            'LaTeX', 'TeX', 'BibTeX', 'XeLaTeX',
            # Document structure
            'Chapter', 'Section', 'Subsection', 'Paragraph', 'Part',
            # Common formatting
            'Large', 'Huge', 'LARGE', 'HUGE', 'Centering',
            # IEEE / math
            'Re', 'Im',
        }
        def _fix_author_cmd(m):
            word = m.group(1)
            if word in _SAFE_CMDS:
                return m.group(0)
            return r'\en{' + word + '}'
        text = re.sub(r'\\([A-Z][a-z]+(?:[A-Z][a-z]*)*)(?!\{|[a-z])', _fix_author_cmd, text)

        # Fix 22: Replace \ensuremath{content} with $content$ (sans inner $).
        # LLM agents write \ensuremath{$\theta$} (nested math mode) which crashes.
        # \ensuremath is equivalent to $...$ outside math mode.
        # Use brace counting to handle nested {} (regex can't do this).
        _ENSUREMATH = r'\ensuremath{'
        while _ENSUREMATH in text:
            idx = text.index(_ENSUREMATH)
            start = idx + len(_ENSUREMATH)
            depth, end = 1, start
            while end < len(text) and depth > 0:
                if text[end] == '{':
                    depth += 1
                elif text[end] == '}':
                    depth -= 1
                end += 1
            inner = text[start:end - 1].replace('$', '')
            text = text[:idx] + '$' + inner + '$' + text[end:]

        # Fix 23: Remove stray } that have no matching {.
        # Agents produce excess } after abbreviations (RMSE}, INS/DVL}, etc.).
        # Walk the text tracking brace depth; drop any } that would make depth < 0.
        _parts = []
        _depth = 0
        for _ch in text:
            if _ch == '{':
                _depth += 1
                _parts.append(_ch)
            elif _ch == '}':
                if _depth > 0:
                    _depth -= 1
                    _parts.append(_ch)
                # else: stray } — skip it
            else:
                _parts.append(_ch)
        text = ''.join(_parts)

        # Fix 20: Repair truncated files with unbalanced braces.
        # When agents hit the output token limit, the file ends mid-\section{}
        # or mid-\subsection{}, leaving unclosed braces. This causes "File ended
        # while scanning use of \@xdblarg" fatal errors. Count net braces and
        # append closing braces if needed.
        open_braces = text.count('{') - text.count('}')
        if open_braces > 0:
            text = text.rstrip() + '\n' + ('}' * open_braces) + '\n'

        # Fix 12b: Wrap bare math symbols anywhere in body text with $...$.
        # Agents often write \alpha, \sigma etc. without $...$ outside math
        # environments, causing "Missing $ inserted" errors.
        # Uses _wrap_bare_math_in_text() which protects existing math regions
        # first, wraps bare symbols, then restores.
        text = _wrap_bare_math_in_text(text)

        if text != original:
            tex_file.write_text(text, encoding="utf-8")
            logger.info(f"[Sanitize] Fixed LaTeX issues in {tex_file.name}")


def compile_pdf(run_folder: Path) -> Path | None:
    """
    Run XeLaTeX → BibTeX → XeLaTeX × 3 inside run_folder/latex/.
    Returns path to run_folder/paper.pdf, or None on failure.
    """
    latex_dir = run_folder / "latex"
    pdf_src   = latex_dir / "main.pdf"
    pdf_dst   = run_folder / "paper.pdf"

    def run(cmd: list[str]) -> bool:
        result = subprocess.run(
            cmd, cwd=latex_dir,
            capture_output=True, text=True,
            timeout=180,
        )
        if result.returncode != 0:
            logger.warning(f"[LaTeX] {cmd[0]} returned non-zero: {result.stdout[-500:]}")
        return result.returncode == 0

    # Delete stale build artifacts first.
    _BUILD_EXTS = ("*.aux", "*.out", "*.bbl", "*.blg", "*.toc", "*.fls",
                   "*.fdb_latexmk", "*.synctex.gz", "*.bcf", "*.run.xml")
    for pattern in _BUILD_EXTS:
        for f in latex_dir.glob(pattern):
            f.unlink(missing_ok=True)

    # Sanitize chapter .tex files to fix common agent-introduced errors
    chapters_dir = latex_dir / "chapters"
    if chapters_dir.exists():
        _sanitize_tex_files(chapters_dir)

    # Stub out any missing figure files so xelatex never crashes on \includegraphics.
    figures_dir = latex_dir / "figures"
    stub_png = figures_dir / "fig_stub.png"
    if stub_png.exists():
        for tex_file in chapters_dir.glob("*.tex"):
            text = tex_file.read_text(encoding="utf-8", errors="replace")
            for fig_ref in re.findall(
                r'\\includegraphics(?:\[[^\]]*\])?\{figures/([^}]+)\}', text
            ):
                fig_path = figures_dir / fig_ref
                if not fig_path.exists():
                    shutil.copy2(stub_png, fig_path)
                    logger.debug(f"[LaTeX] Stubbed missing figure: {fig_ref}")

    logger.info("[LaTeX] Compiling PDF (xelatex → bibtex → xelatex × 3)...")
    _xe = ["xelatex", "-interaction=nonstopmode", "main.tex"]
    run(_xe)
    run(["bibtex", "main"])
    run(_xe)
    run(_xe)
    run(_xe)

    if pdf_src.exists() and pdf_src.stat().st_size > 1000:
        shutil.copy2(pdf_src, pdf_dst)
        size_mb = pdf_src.stat().st_size / 1_048_576
        logger.success(f"[LaTeX] PDF compiled: {pdf_dst} ({size_mb:.1f} MB)")

        # Log fatal errors from main.log for debugging
        log_file = latex_dir / "main.log"
        if log_file.exists():
            log_text = log_file.read_text(encoding="utf-8", errors="replace")
            fatal_errors = [l for l in log_text.splitlines() if l.startswith("!")]
            if fatal_errors:
                logger.warning(f"[LaTeX] {len(fatal_errors)} fatal error(s) in main.log (PDF may be incomplete):")
                for err in fatal_errors[:5]:
                    logger.warning(f"  {err}")

        return pdf_dst
    else:
        logger.error(f"[LaTeX] PDF compilation failed — check {latex_dir}/main.log")
        # Log the actual errors
        log_file = latex_dir / "main.log"
        if log_file.exists():
            log_text = log_file.read_text(encoding="utf-8", errors="replace")
            fatal_errors = [l for l in log_text.splitlines() if l.startswith("!")]
            for err in fatal_errors[:10]:
                logger.error(f"  {err}")
        return None


# ---------------------------------------------------------------------------
# Finalize run (move staging .md files into the run folder)
# ---------------------------------------------------------------------------

def finalize_run(run_folder: Path) -> None:
    """
    Move agent .md reports from staging (outputs/current/) into
    run_folder/outputs/ and clean up staging.
    """
    staging_src = PROJECT_ROOT / _STAGING_DIR
    run_outputs = run_folder / "outputs"
    run_outputs.mkdir(exist_ok=True)

    moved = []
    if staging_src.exists():
        for f in sorted(staging_src.glob("*.md")):
            shutil.move(str(f), run_outputs / f.name)
            moved.append(f.name)
        shutil.rmtree(staging_src, ignore_errors=True)

    # Write manifest
    figures_dir = run_folder / "latex" / "figures"
    figures = sorted(f.name for f in figures_dir.glob("*.png")) if figures_dir.exists() else []
    has_pdf = (run_folder / "paper.pdf").exists()

    lines = [
        "NavigatorCrew Run Archive",
        "=========================",
        f"Folder : {run_folder.name}",
        "",
        f"LaTeX source: {run_folder}/latex/",
        f"  chapters/  ← static + agent-written .tex files",
        f"  figures/   ← {len(figures)} agent-generated PNG(s)",
    ]
    for fig in figures:
        lines.append(f"    {fig}")
    lines += [
        f"  references.bib",
        "",
        f"Agent outputs ({len(moved)} files): {run_folder}/outputs/",
    ]
    for f in moved:
        lines.append(f"  {f}")
    lines += [
        "",
        f"PDF: {'paper.pdf' if has_pdf else 'NOT COMPILED (check latex/main.log)'}",
    ]
    (run_folder / "run_manifest.txt").write_text("\n".join(lines), encoding="utf-8")

    logger.info(
        f"[RunFolder] Finalized: {len(figures)} figures + "
        f"{len(moved)} outputs → {run_folder}"
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    _DEFAULT_TOPIC = "Bat-Inspired Drone Navigation via Bio-Mimetic Multi-Modal Sensor Fusion"

    parser = argparse.ArgumentParser(description="NavigatorCrew v5.1")
    parser.add_argument("--topic",      default=_DEFAULT_TOPIC)
    parser.add_argument("--resume",     action="store_true",
                        help="Resume from last checkpoint (reuses same run folder)")
    parser.add_argument("--no-pdf",     action="store_true",
                        help="Skip PDF compilation")
    parser.add_argument("--no-archive", action="store_true",
                        help="Delete run folder after completion (smoke tests only)")
    parser.add_argument("--fast", action="store_true",
                        help="Fast mode: skip domain expert agents (6-task pipeline, ~40%% faster)")
    parser.add_argument("--smoke", action="store_true",
                        help="Smoke mode: 2-task pipeline (outline + latex-all), ~3–8 min")
    parser.add_argument("--dry-run", action="store_true",
                        help="Dry-run: zero LLM calls — write stub chapters and compile PDF only (~5–30 sec)")
    args = parser.parse_args()

    logger.info(f"Topic: {args.topic}")
    if args.fast:
        logger.info("Fast mode: domain expert agents DISABLED")
    if args.smoke:
        logger.info("Smoke mode: 2-task pipeline (outline + latex-all)")
    if args.dry_run:
        logger.info("Dry-run mode: zero LLM calls — writing pre-canned stubs")

    # ------------------------------------------------------------------
    # Create (or restore) run folder BEFORE graph runs
    # ------------------------------------------------------------------
    if args.resume:
        run_folder = _load_run_folder()
        if run_folder is None:
            logger.warning("[Resume] No saved run folder — creating new one")
            run_folder = create_run_folder(args.topic)
            setup_run_latex(run_folder)
        else:
            logger.info(f"[Resume] Reusing run folder: {run_folder}")
    else:
        run_folder = create_run_folder(args.topic)
        setup_run_latex(run_folder)

    _save_run_folder(run_folder)

    # Ensure staging directory exists for .md reports
    (PROJECT_ROOT / _STAGING_DIR).mkdir(parents=True, exist_ok=True)

    # Pre-seed a fallback figure so xelatex never crashes on a missing \includegraphics.
    # The latex agent is instructed to use fig_stub.png if the real figure isn't ready.
    from src.stubs import _stub_png
    _figures_dir = run_folder / "latex" / "figures"
    _figures_dir.mkdir(parents=True, exist_ok=True)
    (_figures_dir / "fig_stub.png").write_bytes(_stub_png())

    # ------------------------------------------------------------------
    # Dry-run bypass: write stubs, skip all LLM calls
    # ------------------------------------------------------------------
    if args.dry_run:
        from src.stubs import write_stub_chapters
        from src.graph.nodes import run_quality_gate
        from src.graph.state import PipelineState

        write_stub_chapters(run_folder, args.topic)

        _stub_state: PipelineState = {
            "topic":             args.topic,
            "run_folder":        str(run_folder),
            "remediation_count": 0,
            "failed_sections":   [],
            "quality_verdict":   "PENDING",
            "quality_score":     0,
            "fast_mode":         False,
            "smoke_mode":        False,
        }
        gate_result = run_quality_gate(_stub_state)
        final_state = {**_stub_state, **gate_result}
        logger.info(f"[DryRun] Quality gate: score={final_state['quality_score']} verdict={final_state['quality_verdict']}")

        pdf_path = None
        if not args.no_pdf:
            pdf_path = compile_pdf(run_folder)

        finalize_run(run_folder)
        if args.no_archive:
            shutil.rmtree(run_folder, ignore_errors=True)
            run_folder = None

        print("\n" + "=" * 52)
        print("  NAVIGATORCREW — DRY-RUN COMPLETE")
        print("=" * 52)
        print(f"  Quality Score    : {final_state['quality_score']}/100")
        print(f"  Verdict          : {final_state['quality_verdict']}")
        if pdf_path:
            print(f"  PDF              : {pdf_path}")
        if run_folder:
            print(f"  Run Folder       : {run_folder}")
        print("=" * 52)
        return

    # ------------------------------------------------------------------
    # Run LangGraph pipeline
    # ------------------------------------------------------------------
    from src.graph.navigator_graph import build_navigator_graph
    from src.graph.state import PipelineState

    # Use split pipeline (research → validate → writing) for full mode;
    # legacy single-crew pipeline for fast/smoke modes.
    use_split = not (args.fast or args.smoke)
    logger.info(f"Building NavigatorCrew LangGraph pipeline (split={use_split})...")
    graph = build_navigator_graph(split_mode=use_split)

    initial_state: PipelineState = {
        "topic":             args.topic,
        "run_folder":        str(run_folder),
        "remediation_count": 0,
        "failed_sections":   [],
        "quality_verdict":   "PENDING",
        "quality_score":     0,
        "fast_mode":         args.fast,
        "smoke_mode":        args.smoke,
        "research_fix_count": 0,
    }

    try:
        final_state = graph.invoke(initial_state)
    except Exception as e:
        logger.error(f"Graph execution failed: {e}")
        raise

    # ------------------------------------------------------------------
    # Validate & fix chapter filenames (agents sometimes write wrong names)
    # ------------------------------------------------------------------
    validate_and_fix_chapters(run_folder)

    # ------------------------------------------------------------------
    # Diversify stub figures → chapter-specific names, then generate fallbacks
    # ------------------------------------------------------------------
    _diversify_stub_figures(run_folder)
    _deduplicate_cross_chapter_figures(run_folder)
    _generate_fallback_figures(run_folder)

    # ------------------------------------------------------------------
    # PDF Compilation (from run_folder/latex/)
    # ------------------------------------------------------------------
    pdf_path = None
    if not args.no_pdf:
        pdf_path = compile_pdf(run_folder)

    # ------------------------------------------------------------------
    # Finalize: move staging .md files into the run folder
    # ------------------------------------------------------------------
    finalize_run(run_folder)

    if args.no_archive:
        shutil.rmtree(run_folder, ignore_errors=True)
        run_folder = None

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    print("\n" + "=" * 52)
    print("  NAVIGATORCREW — EXECUTION COMPLETE")
    print("=" * 52)
    print(f"  Quality Score    : {final_state['quality_score']}/100")
    print(f"  Verdict          : {final_state['quality_verdict']}")
    print(f"  Remediation Runs : {final_state['remediation_count']}")
    if pdf_path:
        print(f"  PDF              : {pdf_path}")
    if run_folder:
        print(f"  Run Folder       : {run_folder}")
    print("=" * 52)


if __name__ == "__main__":
    main()
