"""
src/runner/figure_styles_b.py
=============================
Fallback figure renderers: fusion comparison, potential field, architecture.
Bodies moved verbatim from main.py's _render_fallback_figure (150-line rule).
"""
from __future__ import annotations


def render_fusion_comparison(plt, np, rng, label):
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


def render_potential_field(plt, np, rng, label):
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


def render_architecture(plt, np, rng, label):
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
