"""
src/tasks/domains.py
====================
Domain-expert descriptions used by the research-phase task factories.
Moved verbatim from research_tasks.py (150-line rule).
"""
from __future__ import annotations

_DOMAIN_DESCRIPTIONS: dict[str, str] = {
    "vision_ai": (
        "Visual SLAM, monocular/stereo depth estimation, semantic segmentation, "
        "optical flow, neural feature descriptors, vision transformers, edge inference"
    ),
    "physics": (
        "Matched filter theory, LFM/FM sonar signal design, acoustic wave propagation, "
        "Doppler physics, cochlear mechanics, range-Doppler ambiguity, beamforming"
    ),
    "algorithms": (
        "EKF/UKF/particle filters, factor graph SLAM (g2o/GTSAM/iSAM2), "
        "covariance intersection, loop closure, CRLB, computational complexity of SLAM"
    ),
    "aerospace": (
        "UAV 6-DOF flight dynamics, IMU strapdown/INS, GPS-denied navigation, "
        "AUV/submarine sonar, DVL, multi-path acoustics, submarine↔cave navigation parallel"
    ),
    "biology": (
        "Bat echolocation (CF-FM sonar, acoustic fovea, DSC mechanism), "
        "neural computation for spatial mapping, bio-inspired algorithm design, "
        "dolphin biosonar, lateral line sensing"
    ),
    "signal_processing": (
        "Chirp/FM pulse design, matched filtering, beamforming (delay-and-sum, MVDR), "
        "time-of-flight estimation, Doppler shift processing, spectral analysis for bio-sonar, "
        "sonar equation, adaptive filtering (LMS, RLS)"
    ),
    "control_systems": (
        "Quadrotor dynamics and equations of motion, PID/LQR controller design, "
        "path planning (RRT*, A*, D*), trajectory optimization, obstacle avoidance, "
        "state estimation for control, real-time control on embedded platforms"
    ),
    "ml": (
        "Multi-modal sensor fusion networks (cross-attention, gating), "
        "1D-CNN for sonar signal encoding, reinforcement learning for navigation (PPO, SAC, GAE), "
        "training pipelines, loss functions, data augmentation for sensor data"
    ),
}
