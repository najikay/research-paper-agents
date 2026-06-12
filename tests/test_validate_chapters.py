"""
tests/test_validate_chapters.py
================================
Tests for validate_and_fix_chapters in src/pipeline/latex_compiler.py.
"""

from __future__ import annotations

from pathlib import Path

from src.pipeline.latex_compiler import EXPECTED_CHAPTERS, validate_and_fix_chapters

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _setup_chapters_dir(run_folder: Path, files: dict[str, str] | None = None) -> Path:
    """Create run_folder/latex/chapters/ and optionally write tex files into it."""
    chapters = run_folder / "latex" / "chapters"
    chapters.mkdir(parents=True, exist_ok=True)
    if files:
        for name, content in files.items():
            (chapters / name).write_text(content, encoding="utf-8")
    return chapters


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

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
