"""
test_run_archive_b.py
=====================
Split from test_run_archive.py.
"""

from __future__ import annotations
from pathlib import Path
from main import (
    import main as m
    import src.config as cfg
    import main as m
    import src.config as cfg
    import main as m
    import src.config as cfg
    import main as m
    import src.config as cfg
    import main as m
    import src.config as cfg
    import main as m
    import src.config as cfg


def test_finalize_run_writes_manifest(tmp_path, monkeypatch):
    """finalize_run must write run_manifest.txt containing 'NavigatorCrew'."""
    import main as m
    import src.config as cfg

    monkeypatch.setattr(cfg, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(m, "PROJECT_ROOT", tmp_path)

    run_folder = tmp_path / "run_test"
    _setup_run_dirs(run_folder)

    finalize_run(run_folder)

    manifest_path = run_folder / "run_manifest.txt"
    assert manifest_path.exists()
    content = manifest_path.read_text(encoding="utf-8")
    assert "NavigatorCrew" in content


def test_finalize_run_manifest_lists_figures(tmp_path, monkeypatch):
    """run_manifest.txt must include the name of each figure in run_folder/latex/figures/."""
    import main as m
    import src.config as cfg

    monkeypatch.setattr(cfg, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(m, "PROJECT_ROOT", tmp_path)

    run_folder = tmp_path / "run_test"
    _setup_run_dirs(run_folder)

    fig_name = "fig_trajectory_3d.png"
    (run_folder / "latex" / "figures" / fig_name).write_bytes(b"\x89PNG\r\n\x1a\n")

    finalize_run(run_folder)

    manifest = (run_folder / "run_manifest.txt").read_text(encoding="utf-8")
    assert fig_name in manifest


def test_finalize_run_latex_in_run_folder(tmp_path, monkeypatch):
    """The run folder must contain latex/ as the primary LaTeX source (set up by setup_run_latex).
    finalize_run must leave it untouched.
    """
    import main as m
    import src.config as cfg

    monkeypatch.setattr(cfg, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(m, "PROJECT_ROOT", tmp_path)

    run_folder = tmp_path / "run_test"
    _setup_run_dirs(run_folder)
    # Simulate that setup_run_latex already created the latex tree in run_folder
    (run_folder / "latex" / "main.tex").write_text("% main\n", encoding="utf-8")

    finalize_run(run_folder)

    assert (run_folder / "latex").exists(), (
        "latex/ must remain in the run folder after finalize_run"
    )
    assert (run_folder / "latex" / "main.tex").exists()


# ---------------------------------------------------------------------------
# validate_and_fix_chapters
# ---------------------------------------------------------------------------

def _setup_chapters_dir(run_folder: Path, files: dict[str, str] | None = None) -> Path:
    """Create run_folder/latex/chapters/ and optionally write tex files into it."""
    chapters = run_folder / "latex" / "chapters"
    chapters.mkdir(parents=True, exist_ok=True)
    if files:
        for name, content in files.items():
            (chapters / name).write_text(content, encoding="utf-8")
    return chapters


def test_validate_fix_renames_wrong_chapter(tmp_path):
    """A wrong-named ch03_ultrasonic_sensor.tex must be renamed to ch03_sensors.tex."""
    chapters = _setup_chapters_dir(tmp_path, {
        "ch03_ultrasonic_sensor.tex": r"\section{Sensors}" + " word" * 200,
    })

    validate_and_fix_chapters(tmp_path)

    assert (chapters / "ch03_sensors.tex").exists()
    assert not (chapters / "ch03_ultrasonic_sensor.tex").exists()


def test_validate_fix_picks_largest(tmp_path):
    """When multiple wrong-named files exist for the same prefix, the largest wins."""
    small_content = r"\section{Short}" + " x" * 10
    large_content = r"\section{Full chapter}" + " word" * 300

    chapters = _setup_chapters_dir(tmp_path, {
        "ch03_ultrasonic.tex": small_content,
        "ch03_sonar_detailed.tex": large_content,
    })

    validate_and_fix_chapters(tmp_path)

    assert (chapters / "ch03_sensors.tex").exists()
    renamed = (chapters / "ch03_sensors.tex").read_text(encoding="utf-8")
    assert "Full chapter" in renamed


def test_validate_fix_no_change_when_correct(tmp_path):
    """When all expected files already exist, nothing is renamed."""
    files = {}
    for name in EXPECTED_CHAPTERS:
        files[name] = r"\section{OK}" + " word" * 100
    chapters = _setup_chapters_dir(tmp_path, files)

    validate_and_fix_chapters(tmp_path)

    # All expected files still present
    for name in EXPECTED_CHAPTERS:
        assert (chapters / name).exists()


def test_validate_fix_does_not_touch_cover(tmp_path):
    """cover.tex must never be renamed even if it matches a prefix pattern."""
    chapters = _setup_chapters_dir(tmp_path, {
        "cover.tex": r"\maketitle",
    })

    validate_and_fix_chapters(tmp_path)

    assert (chapters / "cover.tex").exists()


def test_validate_fix_skips_abstract(tmp_path):
    """abstract.tex has no prefix variants — validation should not crash."""
    chapters = _setup_chapters_dir(tmp_path, {
        "abstract.tex": r"\begin{abstract} content \end{abstract}",
    })

    validate_and_fix_chapters(tmp_path)

    assert (chapters / "abstract.tex").exists()
