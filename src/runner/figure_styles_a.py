"""
src/runner/figure_styles_a.py
=============================
Fallback figure renderers: concept diagram, bio signal, heatmap, 3D trajectory.
Bodies moved verbatim from main.py's _render_fallback_figure (150-line rule).
Each renderer receives (plt, np, rng, label) and draws onto the current figure.
"""
from __future__ import annotations


def render_system_concept(plt, np, rng, label):
    """Render a system concept block diagram of the sensing/navigation pipeline.

    Draws labelled boxes (sensors, sensor fusion EKF, SLAM backend, obstacle
    avoidance, flight controller) connected by arrows onto the current figure.
    """
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


def render_bio_signal(plt, np, rng, label):
    """Render a two-panel ultrasonic bio-signal figure.

    Top panel plots an emitted Gaussian-windowed chirp and its noisy received
    echo; bottom panel shows the time-frequency spectrogram of the combined
    signal. Draws onto the current figure.
    """
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


def render_sensor_heatmap(plt, np, rng, label):
    """Render side-by-side sensor heatmaps.

    Left panel shows a smoothed occupancy-grid map with obstacle regions; right
    panel shows a Gaussian sensor confidence map. Each has its own colorbar and
    is drawn onto the current figure.
    """
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


def render_trajectory_3d(plt, np, rng, label):
    """Render a 3D spiral trajectory comparing ground-truth and estimated paths.

    Plots the ground-truth and noisy estimated trajectories on a 3D axis along
    with randomly placed obstacle markers. Draws onto the current figure.
    """
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
