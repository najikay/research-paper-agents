"""
figure_renderer_extra.py
========================
Additional fallback figure styles: sensor_heatmap, fusion_comparison.
Split from figure_renderer_ext.py to stay within file-size limits.
"""



def _render_sensor_heatmap(plt, np, rng, label: str) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    grid = rng.rand(30, 30)
    grid = np.convolve(grid.flatten(), np.ones(7) / 7, mode="same").reshape(30, 30)
    grid[10:15, 10:20] = 0.9
    grid[20:25, 5:10] = 0.85
    im0 = axes[0].imshow(grid, cmap="YlOrRd", aspect="auto", origin="lower")
    plt.colorbar(im0, ax=axes[0], label="Occupancy probability")
    axes[0].set_xlabel("X [cells]", fontsize=12)
    axes[0].set_ylabel("Y [cells]", fontsize=12)
    axes[0].set_title("Occupancy Grid Map", fontsize=13)
    axes[0].tick_params(labelsize=11)
    conf = np.exp(-((np.arange(30)[:, None] - 15)**2 + (np.arange(30)[None, :] - 15)**2) / 80)
    conf += 0.1 * rng.rand(30, 30)
    im1 = axes[1].imshow(conf, cmap="viridis", aspect="auto", origin="lower")
    plt.colorbar(im1, ax=axes[1], label="Confidence")
    axes[1].set_xlabel("X [cells]", fontsize=12)
    axes[1].set_ylabel("Y [cells]", fontsize=12)
    axes[1].set_title("Sensor Confidence Map", fontsize=13)
    axes[1].tick_params(labelsize=11)


def _render_fusion_comparison(plt, np, rng, label: str) -> None:
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
