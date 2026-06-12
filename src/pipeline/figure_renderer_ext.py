"""
figure_renderer_ext.py
======================
Extended fallback figure styles: potential_field, architecture,
results_multi, convergence, and default.
These are called from figure_renderer._render_fallback_figure.
"""



def _render_potential_field(plt, np, rng, label: str) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.5))
    xx, yy = np.meshgrid(np.linspace(-5, 5, 60), np.linspace(-5, 5, 60))
    goal = np.array([4, 4])
    u_att = 0.5 * ((xx - goal[0])**2 + (yy - goal[1])**2)
    obstacles = [(-1, 0), (1, 2), (-2, 3)]
    u_rep = np.zeros_like(xx)
    for ox, oy in obstacles:
        dist = np.sqrt((xx - ox)**2 + (yy - oy)**2)
        dist = np.maximum(dist, 0.3)
        u_rep += 2.0 / dist**2
    u_total = u_att + np.minimum(u_rep, 15)
    axes[0].contourf(xx, yy, u_total, levels=30, cmap="coolwarm")
    axes[0].plot(*goal, "g*", markersize=20, label="Goal")
    for ox, oy in obstacles:
        axes[0].plot(ox, oy, "rs", markersize=14)
    path_x = [-4, -3, -2.5, -1.5, 0, 1, 2, 3, 4]
    path_y = [-4, -3, -1.5, -0.5, 0.5, 1, 2.5, 3.5, 4]
    axes[0].plot(path_x, path_y, "w-o", linewidth=2.5, markersize=5, label="Path")
    axes[0].set_xlabel("X [m]", fontsize=12)
    axes[0].set_ylabel("Y [m]", fontsize=12)
    axes[0].set_title("Potential Field + Path", fontsize=13)
    axes[0].legend(fontsize=10, loc="lower right")
    axes[0].tick_params(labelsize=11)
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


def _render_architecture(plt, np, rng, label: str) -> None:
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
    pairs = [
        ((3.5, 6.75), (5, 5.75)), ((3.5, 4.75), (5, 5.25)),
        ((3.5, 2.75), (5, 3.75)),
        ((7.5, 5.75), (9, 5.75)), ((7.5, 3.75), (9, 3.75)),
        ((11.5, 5.5), (13, 5)), ((11.5, 3.5), (13, 4.5)),
    ]
    for (x1, y1), (x2, y2) in pairs:
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                    arrowprops={"arrowstyle": "-|>", "lw": 1.8, "color": "#555"},
                    zorder=1)
    ax.set_title(label, fontsize=14, fontweight="bold")
    ax.axis("off")


def _render_results_multi(plt, np, rng, label: str) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(13, 9))
    t = np.linspace(0, 60, 300)
    err_prop = 2 * np.exp(-0.05 * t) + 0.5 + 0.3 * rng.randn(300) * np.exp(-0.02 * t)
    err_base = 4 * np.exp(-0.03 * t) + 1.5 + 0.5 * rng.randn(300) * np.exp(-0.01 * t)
    axes[0, 0].plot(t, err_base, alpha=0.7, label="Baseline EKF", color="#90CAF9")
    axes[0, 0].plot(t, err_prop, alpha=0.9, label="Proposed", color="#F44336")
    axes[0, 0].set_xlabel("Time [s]", fontsize=11)
    axes[0, 0].set_ylabel("Position Error [cm]", fontsize=11)
    axes[0, 0].set_title("(a) Position Error Over Time", fontsize=12)
    axes[0, 0].legend(fontsize=10)
    axes[0, 0].tick_params(labelsize=10)
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
    axis_labels = ["X(B)", "Y(B)", "Z(B)", "X(P)", "Y(P)", "Z(P)"]
    means = [0.3, 0.5, 0.2, 0.1, 0.15, 0.08]
    stds = [0.8, 1.2, 0.5, 0.3, 0.4, 0.2]
    bar_colors = ["#90CAF9"] * 3 + ["#FFCDD2"] * 3
    axes[1, 0].bar(axis_labels, means, yerr=stds, color=bar_colors,
                    edgecolor="#333", linewidth=0.8, capsize=4)
    axes[1, 0].set_ylabel("Mean Error [cm]", fontsize=11)
    axes[1, 0].set_title("(c) Per-Axis Error Distribution", fontsize=12)
    axes[1, 0].tick_params(labelsize=10)
    modules = ["Sonar\nProc", "EKF\nUpdate", "Map\nUpdate", "Path\nPlan", "Total"]
    times = [3.2, 5.1, 4.8, 2.3, 15.4]
    axes[1, 1].barh(modules, times, color=["#81C784"] * 4 + ["#FFB74D"])
    axes[1, 1].set_xlabel("Time [ms]", fontsize=11)
    axes[1, 1].set_title("(d) Computation Time Breakdown", fontsize=12)
    axes[1, 1].tick_params(labelsize=10)
    for i, v in enumerate(times):
        axes[1, 1].text(v + 0.2, i, f"{v} ms", va="center", fontsize=10)


def _render_convergence(plt, np, rng, label: str) -> None:
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


def _render_default(plt, np, rng, label: str) -> None:
    fig, ax = plt.subplots(figsize=(8, 5))
    x = np.linspace(0, 10, 200)
    ax.plot(x, np.sin(x) * np.exp(-0.2 * x), label="Signal A", linewidth=2)
    ax.plot(x, np.cos(x) * np.exp(-0.15 * x), label="Signal B", linewidth=2)
    ax.set_xlabel("Time [s]", fontsize=11)
    ax.set_ylabel("Amplitude", fontsize=11)
    ax.set_title(label, fontsize=13)
    ax.legend(fontsize=11)
    ax.tick_params(labelsize=11)
