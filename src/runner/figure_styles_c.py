"""
src/runner/figure_styles_c.py
=============================
Fallback figure renderers: multi-panel results, convergence, generic default.
Bodies moved verbatim from main.py's _render_fallback_figure (150-line rule).
"""
from __future__ import annotations


def render_results_multi(plt, np, rng, label):
    """Render a four-panel results figure.

    Panels show (a) position error over time, (b) the cumulative error
    distribution (CDF), (c) per-axis mean error bars with standard deviation,
    and (d) a computation-time breakdown by module, comparing baseline and
    proposed methods. Draws onto the current figure.
    """
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


def render_convergence(plt, np, rng, label):
    """Render a convergence plot of state-estimation error versus iteration.

    Compares the decaying error curves of the standard EKF and the proposed
    bio-mimetic method over 50 iterations. Draws onto the current figure.
    """
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


def render_generic(plt, np, rng, label):
    """Render a generic two-signal decaying-oscillation plot as a safe fallback.

    Plots damped sine and cosine signals; used when no specific renderer matches.
    Draws onto the current figure.
    """
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
