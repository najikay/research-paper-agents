"""
src/tasks/domain_tasks.py
=========================
Factory functions for domain-expert enrichment and domain-fix tasks.
"""

from __future__ import annotations

from crewai import Agent, Task

_STAGING = "outputs/current"

DOMAIN_DESCRIPTIONS: dict[str, str] = {
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


def create_task_domain_expert(
    expert: Agent,
    domain_key: str,
    domain_description: str,
    context: list[Task],
) -> Task:
    """Create a domain-expert enrichment task for a single specialist."""
    return Task(
        description=f"""
You are a PhD-level domain specialist. You MUST contribute technical depth
to the academic paper being written.

Your domain expertise: {domain_description}

STEP 0 — Read the paper outline and research briefs to understand the topic:
    FileReaderTool("{_STAGING}/paper_outline.md")
    FileReaderTool("{_STAGING}/research_briefs.md")
    Then use web search (SerperDevSearchTool, ArxivSearchTool) to find domain-specific content.

YOUR MANDATORY OUTPUT — produce ALL of the following:

1. TECHNICAL ANALYSIS (500+ words):
   State-of-the-art methods, dominant approaches, and known failure modes
   from YOUR domain that are relevant to the paper topic. Be specific:
   name methods, cite years, give quantitative performance numbers.

2. EQUATIONS (minimum 3, LaTeX-ready):
   Each as: \\begin{{equation}} ... \\label{{eq:domain_{domain_key}_N}} \\end{{equation}}
   Include variable definitions after each equation.
   Only equations from YOUR domain — not already in the research briefs.

3. ALGORITHMS OR METHODS (minimum 2):
   Pseudocode or step-by-step descriptions of key algorithms from your field.

4. BIBTEX REFERENCES (minimum 5):
   Full BibTeX entries: @article{{Key, author=..., title=..., journal=..., year=..., doi=...}}
   Only real, verifiable references. No fabricated citations.

5. INTEGRATION NOTES (200+ words):
   How your domain contributions connect to the paper's overall system.

Write your complete contribution using SafeFileWriterTool to:
    {_STAGING}/domain_{domain_key}.md

IMPORTANT: You MUST produce all 5 sections. Do not skip any section.
Do not write "DOMAIN SKIP" or "DOMAIN EXPERT COMPLETE" without content.
Your output will be validated — empty or trivial responses will be flagged.
""".strip(),
        expected_output=(
            f"Complete domain contribution saved to {_STAGING}/domain_{domain_key}.md "
            f"containing: technical analysis (500+ words), 3+ LaTeX equations, "
            f"2+ algorithms, 5+ BibTeX references, and integration notes."
        ),
        agent=expert,
        context=context,
    )


def create_task_fix_domain(
    fixer: Agent,
    domain_key: str,
    topic: str,
    outline_content: str,
) -> Task:
    """Create a fix task when a domain expert fails to produce usable content."""
    desc = DOMAIN_DESCRIPTIONS.get(domain_key, domain_key)
    return Task(
        description=f"""
You are a Research Fixer. A domain expert failed to produce usable content.
Your job: produce the missing domain contribution yourself.

PAPER TOPIC: {topic}

PAPER OUTLINE:
{outline_content}

DOMAIN TO COVER: {desc}

Write a complete domain contribution with:
1. Technical analysis (500+ words) of state-of-the-art from this domain
2. At least 3 LaTeX-ready equations with variable definitions
3. At least 2 algorithm/method descriptions
4. At least 5 BibTeX references (real, verifiable)
5. Integration notes on how this domain connects to the paper

CRITICAL — use SafeFileWriterTool to write your output to EXACTLY this path:
    {_STAGING}/domain_{domain_key}.md
Do NOT change this filename. Do NOT use a different name.

You have web search tools (SerperDevSearchTool, ArxivSearchTool) — use them
to find real papers and data. Do NOT fabricate citations.
""".strip(),
        expected_output=(
            f"Domain contribution saved to {_STAGING}/domain_{domain_key}.md "
            f"with technical analysis, equations, algorithms, references, and integration notes."
        ),
        agent=fixer,
    )
