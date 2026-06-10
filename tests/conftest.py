"""
tests/conftest.py
=================
Shared pytest fixtures for the NavigatorCrew test suite.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest


# ---------------------------------------------------------------------------
# Chapter content fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def good_chapter_content() -> str:
    """A valid minimal .tex chapter satisfying all quality-gate criteria."""
    # Build a string that has:
    #   >=3 \begin{equation}, >=1 \includegraphics, >=4 \subsection,
    #   >=3 \cite{}, >=2500 words, no em dashes, no \begin{center}
    words = " ".join(["מילה"] * 2500)  # ~2500 Hebrew words to exceed the 2200-word ch06/ch08 threshold
    return r"""
\selectlanguage{hebrew}
\section{פרק לדוגמה}
\label{sec:example}

""" + words + r"""

\subsection{תת-סעיף ראשון}
תוכן ראשון עם הסבר מפורט על האלגוריתם.
\begin{equation}
    x_{k+1} = A x_k + B u_k
    \label{eq:state}
\end{equation}
ניתן לראות במשוואה~(\ref{eq:state}) את מודל המצב.

\subsection{תת-סעיף שני}
תוכן שני עם עוד הסבר על הנושא.
\begin{equation}
    P_{k+1} = A P_k A^T + Q
    \label{eq:covariance}
\end{equation}
מטריצת השגיאות מוגדרת ב-(\ref{eq:covariance}).

\subsection{תת-סעיף שלישי}
תוכן שלישי עם ניתוח תוצאות.
\begin{equation}
    z_k = H x_k + v_k
    \label{eq:measurement}
\end{equation}
מודל המדידה מוצג במשוואה~(\ref{eq:measurement}).

\subsection{תת-סעיף רביעי}
תוכן רביעי עם דיון נוסף.

\subsection{תת-סעיף חמישי}
תוכן חמישי עם ניתוח השוואתי.

\begin{figure}[H]
    \centering
    \includegraphics[width=0.95\columnwidth]{figures/fig_trajectory_3d.png}
    \caption{תיאור התמונה. \en{(Technical note)}}
    \label{fig:trajectory}
\end{figure}

ניתן לראות ב-\figref{fig:trajectory} את המסלול.
\cite{Thrun2005ProbRobotics} הוא המקור העיקרי.
עוד מקור \cite{Kalman1960} לאימות.
מקור נוסף \cite{Grisetti2010g2o} להשלמה.
"""


@pytest.fixture
def bad_chapter_content() -> str:
    """A minimal .tex chapter missing all structural elements (used to trigger quality failures)."""
    return r"""
\selectlanguage{hebrew}
\section{פרק קצר}
\label{sec:short}
טקסט מינימלי ללא אלמנטים נדרשים.
"""


@pytest.fixture
def full_bib_content() -> str:
    """A references.bib string containing all 14 required citation keys."""
    return r"""
@book{Thrun2005ProbRobotics,
  author    = {Thrun, Sebastian and Burgard, Wolfram and Fox, Dieter},
  title     = {Probabilistic Robotics},
  publisher = {MIT Press},
  year      = {2005}
}
@article{Kalman1960,
  author  = {Kalman, R. E.},
  title   = {A New Approach to Linear Filtering and Prediction Problems},
  journal = {Transactions of the ASME},
  year    = {1960},
  volume  = {82},
  pages   = {35--45}
}
@article{Grisetti2010g2o,
  author  = {Grisetti, Giorgio and others},
  title   = {A Tutorial on Graph-Based SLAM},
  journal = {IEEE Intelligent Transportation Systems Magazine},
  year    = {2010}
}
@article{MurArtal2015ORB,
  author  = {Mur-Artal, Raul and others},
  title   = {ORB-SLAM: A Versatile and Accurate Monocular SLAM System},
  journal = {IEEE Transactions on Robotics},
  year    = {2015}
}
@article{Julier1997CovarianceIntersection,
  author  = {Julier, Simon J. and Uhlmann, Jeffrey K.},
  title   = {A Non-divergent Estimation Algorithm},
  journal = {American Control Conference},
  year    = {1997}
}
@article{GriffinBatEcholocation,
  author  = {Griffin, Donald R.},
  title   = {Listening in the Dark},
  journal = {Yale University Press},
  year    = {1958}
}
@article{GriffithBatEcholocation,
  author  = {Griffith, S. C.},
  title   = {Bat Echolocation Studies},
  journal = {Journal of Experimental Biology},
  year    = {2000}
}
@article{Simmons1979BatSonar,
  author  = {Simmons, James A.},
  title   = {Perception of Echo Phase Information in Bat Sonar},
  journal = {Science},
  year    = {1979}
}
@article{Schnitzler1968DSC,
  author  = {Schnitzler, Hans-Ulrich},
  title   = {Die Ultraschall-Ortungslaute der Hufeisen-Fledermause},
  journal = {Zeitschrift fur vergleichende Physiologie},
  year    = {1968}
}
@article{Schuller1974DSC,
  author  = {Schuller, Gerd},
  title   = {The Role of the Doppler Shift Compensation},
  journal = {Journal of Comparative Physiology},
  year    = {1974}
}
@book{MossEcholocation,
  author    = {Moss, Cynthia F. and Sinha, Shiva R.},
  title     = {Neurobiology of Echolocation in Bats},
  publisher = {Academic Press},
  year      = {2003}
}
@article{Rihaczek1969MatchedFilter,
  author  = {Rihaczek, A. W.},
  title   = {Principles of High Resolution Radar},
  journal = {McGraw-Hill},
  year    = {1969}
}
@misc{CrewAIDocs,
  title  = {CrewAI Documentation},
  url    = {https://docs.crewai.com},
  note   = {Accessed: June 2026}
}
@misc{AnthropicClaude,
  title  = {Anthropic Claude API},
  url    = {https://www.anthropic.com},
  note   = {Accessed: June 2026}
}
"""


@pytest.fixture
def partial_bib_content() -> str:
    """A references.bib with only 5 entries — below the MIN_BIB_ENTRIES=10 threshold."""
    return r"""
@book{Thrun2005ProbRobotics,
  author    = {Thrun, Sebastian and Burgard, Wolfram and Fox, Dieter},
  title     = {Probabilistic Robotics},
  publisher = {MIT Press},
  year      = {2005}
}
@article{Kalman1960,
  author  = {Kalman, R. E.},
  title   = {A New Approach to Linear Filtering},
  journal = {ASME Transactions},
  year    = {1960}
}
@article{Grisetti2010g2o,
  author  = {Grisetti, Giorgio},
  title   = {Graph-Based SLAM},
  journal = {IEEE ITS},
  year    = {2010}
}
@article{MurArtal2015ORB,
  author  = {Mur-Artal, Raul},
  title   = {ORB-SLAM},
  journal = {IEEE TRO},
  year    = {2015}
}
@article{Julier1997CovarianceIntersection,
  author  = {Julier, Simon},
  title   = {Covariance Intersection},
  journal = {ACC},
  year    = {1997}
}
"""


# ---------------------------------------------------------------------------
# Filesystem fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_latex_dir(tmp_path: Path) -> Path:
    """
    Create a full latex/chapters/ + latex/figures/ + latex/references.bib structure
    with good content in a temporary directory.
    """
    chapters_dir = tmp_path / "latex" / "chapters"
    figures_dir  = tmp_path / "latex" / "figures"
    chapters_dir.mkdir(parents=True)
    figures_dir.mkdir(parents=True)

    good = (
        r"\selectlanguage{hebrew}" + "\n"
        r"\section{Test}" + "\n"
        + " ".join(["word"] * 2500) + "\n"
        + r"\subsection{A}" + "\n"
        + r"\subsection{B}" + "\n"
        + r"\subsection{C}" + "\n"
        + r"\subsection{D}" + "\n"
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

    # Stub outputs/ dir so quality gate can write the report
    (tmp_path / "outputs").mkdir(exist_ok=True)

    return tmp_path


# ---------------------------------------------------------------------------
# Mock agent fixture
# ---------------------------------------------------------------------------

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
