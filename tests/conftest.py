"""
tests/conftest.py
=================
Shared pytest fixtures for the NavigatorCrew test suite.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from tests.conftest_data import FULL_BIB, PARTIAL_BIB


@pytest.fixture
def good_chapter_content() -> str:
    """A valid minimal .tex chapter satisfying all quality-gate criteria."""
    words = " ".join(["מילה"] * 1800)
    return (
        r"\selectlanguage{hebrew}" + "\n"
        r"\section{פרק לדוגמה}" + "\n"
        r"\label{sec:example}" + "\n\n"
        + words + "\n\n"
        + r"\subsection{תת-סעיף ראשון}" + "\n"
        + r"\begin{equation} x_{k+1} = A x_k + B u_k \label{eq:state}\end{equation}" + "\n"
        + r"\subsection{תת-סעיף שני}" + "\n"
        + r"\begin{equation} P_{k+1} = A P_k A^T + Q \label{eq:cov}\end{equation}" + "\n"
        + r"\subsection{תת-סעיף שלישי}" + "\n"
        + r"\begin{equation} z_k = H x_k + v_k \label{eq:meas}\end{equation}" + "\n"
        + r"\subsection{תת-סעיף רביעי}" + "\n"
        + r"\subsection{תת-סעיף חמישי}" + "\n"
        + r"\begin{figure}[H]" + "\n"
        + r"    \includegraphics[width=0.95\columnwidth]{figures/fig_trajectory_3d.png}" + "\n"
        + r"    \caption{תיאור. \en{(note)}}" + "\n"
        + r"    \label{fig:trajectory}" + "\n"
        + r"\end{figure}" + "\n"
        + r"\cite{Thrun2005ProbRobotics} \cite{Kalman1960} \cite{Grisetti2010g2o}" + "\n"
    )


@pytest.fixture
def bad_chapter_content() -> str:
    """A minimal .tex chapter missing all structural elements."""
    return r"""
\selectlanguage{hebrew}
\section{פרק קצר}
\label{sec:short}
טקסט מינימלי ללא אלמנטים נדרשים.
"""


@pytest.fixture
def full_bib_content() -> str:
    """A references.bib string containing all 14 required citation keys."""
    return FULL_BIB


@pytest.fixture
def partial_bib_content() -> str:
    """A references.bib with only 5 entries — below the MIN_BIB_ENTRIES=10 threshold."""
    return PARTIAL_BIB


@pytest.fixture
def tmp_latex_dir(tmp_path: Path) -> Path:
    """Create a full latex/ structure with good content in a temp directory."""
    chapters_dir = tmp_path / "latex" / "chapters"
    figures_dir = tmp_path / "latex" / "figures"
    chapters_dir.mkdir(parents=True)
    figures_dir.mkdir(parents=True)

    good = (
        r"\selectlanguage{hebrew}" + "\n"
        + r"\section{Test}" + "\n"
        + " ".join(["word"] * 1800) + "\n"
        + r"\subsection{A}" + "\n" + r"\subsection{B}" + "\n"
        + r"\subsection{C}" + "\n" + r"\subsection{D}" + "\n"
        + r"\subsection{E}" + "\n"
        + r"\begin{equation}x=1\label{eq:a}\end{equation}" + "\n"
        + r"\begin{equation}y=2\label{eq:b}\end{equation}" + "\n"
        + r"\begin{equation}z=3\label{eq:c}\end{equation}" + "\n"
        + r"\includegraphics{figures/fig.png}" + "\n"
        + r"\cite{Thrun2005ProbRobotics}" + "\n"
        + r"\cite{Kalman1960}" + "\n"
        + r"\cite{Grisetti2010g2o}" + "\n"
    )

    for fname in [
        "abstract.tex", "ch02_bio_basis.tex", "ch03_sensors.tex",
        "ch04_slam.tex", "ch05_fusion.tex", "ch06_algorithm.tex",
        "ch07_oursystem.tex", "ch08_results.tex", "ch09_conclusion.tex",
    ]:
        (chapters_dir / fname).write_text(good, encoding="utf-8")

    bib = "\n".join(
        f"@misc{{{key},\n  title={{{key}}}\n}}"
        for key in [
            "Thrun2005ProbRobotics", "Kalman1960", "Grisetti2010g2o",
            "MurArtal2015ORB", "Julier1997CovarianceIntersection",
            "GriffinBatEcholocation", "GriffithBatEcholocation",
            "Simmons1979BatSonar", "Schnitzler1968DSC", "Schuller1974DSC",
            "MossEcholocation", "Rihaczek1969MatchedFilter",
            "CrewAIDocs", "AnthropicClaude",
        ]
    )
    (tmp_path / "latex" / "references.bib").write_text(bib, encoding="utf-8")
    (tmp_path / "outputs").mkdir(exist_ok=True)

    return tmp_path


@pytest.fixture
def mock_agent() -> MagicMock:
    """A mock CrewAI agent with standard attributes."""
    agent = MagicMock()
    agent.role = "Test Role"
    agent.allow_delegation = False
    agent.memory = False
    agent.max_iter = 12
    agent.verbose = True
    agent.tools = []
    return agent
