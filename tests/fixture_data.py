"""
tests/fixture_data.py
======================
Large string constants used by conftest fixtures.
Separated to keep conftest.py under the 150-line limit.
"""

GOOD_CHAPTER_CONTENT = (
    r"\selectlanguage{hebrew}" + "\n"
    r"\section{פרק לדוגמה}" + "\n"
    r"\label{sec:example}" + "\n\n"
    + " ".join(["מילה"] * 1800) + "\n\n"
    + r"\subsection{תת-סעיף ראשון}" + "\n"
    + "תוכן ראשון עם הסבר מפורט על האלגוריתם.\n"
    + r"\begin{equation}" + "\n"
    + r"    x_{k+1} = A x_k + B u_k" + "\n"
    + r"    \label{eq:state}" + "\n"
    + r"\end{equation}" + "\n"
    + r"ניתן לראות במשוואה~(\ref{eq:state}) את מודל המצב." + "\n\n"
    + r"\subsection{תת-סעיף שני}" + "\n"
    + "תוכן שני עם עוד הסבר על הנושא.\n"
    + r"\begin{equation}" + "\n"
    + r"    P_{k+1} = A P_k A^T + Q" + "\n"
    + r"    \label{eq:covariance}" + "\n"
    + r"\end{equation}" + "\n"
    + r"מטריצת השגיאות מוגדרת ב-(\ref{eq:covariance})." + "\n\n"
    + r"\subsection{תת-סעיף שלישי}" + "\n"
    + "תוכן שלישי עם ניתוח תוצאות.\n"
    + r"\begin{equation}" + "\n"
    + r"    z_k = H x_k + v_k" + "\n"
    + r"    \label{eq:measurement}" + "\n"
    + r"\end{equation}" + "\n"
    + r"מודל המדידה מוצג במשוואה~(\ref{eq:measurement})." + "\n\n"
    + r"\subsection{תת-סעיף רביעי}" + "\n"
    + "תוכן רביעי עם דיון נוסף.\n\n"
    + r"\subsection{תת-סעיף חמישי}" + "\n"
    + "תוכן חמישי עם ניתוח השוואתי.\n\n"
    + r"\begin{figure}[H]" + "\n"
    + r"    \centering" + "\n"
    + r"    \includegraphics[width=0.95\columnwidth]{figures/fig_trajectory_3d.png}" + "\n"
    + r"    \caption{תיאור התמונה. \en{(Technical note)}}" + "\n"
    + r"    \label{fig:trajectory}" + "\n"
    + r"\end{figure}" + "\n\n"
    + r"ניתן לראות ב-\figref{fig:trajectory} את המסלול." + "\n"
    + r"\cite{Thrun2005ProbRobotics} הוא המקור העיקרי." + "\n"
    + r"עוד מקור \cite{Kalman1960} לאימות." + "\n"
    + r"מקור נוסף \cite{Grisetti2010g2o} להשלמה." + "\n"
)

BAD_CHAPTER_CONTENT = (
    r"\selectlanguage{hebrew}" + "\n"
    r"\section{פרק קצר}" + "\n"
    r"\label{sec:short}" + "\n"
    "טקסט מינימלי ללא אלמנטים נדרשים.\n"
)

_BIB_ENTRIES_FULL = [
    ("book", "Thrun2005ProbRobotics", "author={Thrun, Sebastian and Burgard, Wolfram and Fox, Dieter},title={Probabilistic Robotics},publisher={MIT Press},year={2005}"),
    ("article", "Kalman1960", "author={Kalman, R. E.},title={A New Approach to Linear Filtering and Prediction Problems},journal={Transactions of the ASME},year={1960},volume={82},pages={35--45}"),
    ("article", "Grisetti2010g2o", "author={Grisetti, Giorgio and others},title={A Tutorial on Graph-Based SLAM},journal={IEEE Intelligent Transportation Systems Magazine},year={2010}"),
    ("article", "MurArtal2015ORB", "author={Mur-Artal, Raul and others},title={ORB-SLAM: A Versatile and Accurate Monocular SLAM System},journal={IEEE Transactions on Robotics},year={2015}"),
    ("article", "Julier1997CovarianceIntersection", "author={Julier, Simon J. and Uhlmann, Jeffrey K.},title={A Non-divergent Estimation Algorithm},journal={American Control Conference},year={1997}"),
    ("article", "GriffinBatEcholocation", "author={Griffin, Donald R.},title={Listening in the Dark},journal={Yale University Press},year={1958}"),
    ("article", "GriffithBatEcholocation", "author={Griffith, S. C.},title={Bat Echolocation Studies},journal={Journal of Experimental Biology},year={2000}"),
    ("article", "Simmons1979BatSonar", "author={Simmons, James A.},title={Perception of Echo Phase Information in Bat Sonar},journal={Science},year={1979}"),
    ("article", "Schnitzler1968DSC", "author={Schnitzler, Hans-Ulrich},title={Die Ultraschall-Ortungslaute der Hufeisen-Fledermause},journal={Zeitschrift fur vergleichende Physiologie},year={1968}"),
    ("article", "Schuller1974DSC", "author={Schuller, Gerd},title={The Role of the Doppler Shift Compensation},journal={Journal of Comparative Physiology},year={1974}"),
    ("book", "MossEcholocation", "author={Moss, Cynthia F. and Sinha, Shiva R.},title={Neurobiology of Echolocation in Bats},publisher={Academic Press},year={2003}"),
    ("article", "Rihaczek1969MatchedFilter", "author={Rihaczek, A. W.},title={Principles of High Resolution Radar},journal={McGraw-Hill},year={1969}"),
    ("misc", "CrewAIDocs", "title={CrewAI Documentation},url={https://docs.crewai.com},note={Accessed: June 2026}"),
    ("misc", "AnthropicClaude", "title={Anthropic Claude API},url={https://www.anthropic.com},note={Accessed: June 2026}"),
]

FULL_BIB_CONTENT = "\n".join(
    f"@{kind}{{{key},\n  {fields}\n}}" for kind, key, fields in _BIB_ENTRIES_FULL
)

PARTIAL_BIB_CONTENT = "\n".join(
    f"@{kind}{{{key},\n  {fields}\n}}" for kind, key, fields in _BIB_ENTRIES_FULL[:5]
)
