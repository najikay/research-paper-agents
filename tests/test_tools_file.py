"""
tests/test_tools_file.py
========================
Unit tests for SafeFileWriterTool and FileReaderTool.
"""

from __future__ import annotations

from pathlib import Path

from src.tools.file_tools import FileReaderTool, SafeFileWriterTool

# ---------------------------------------------------------------------------
# SafeFileWriterTool — security block tests
# ---------------------------------------------------------------------------

def test_write_outside_allowed_dirs_blocked():
    """Writing to src/ must be blocked (outside WRITABLE_DIRS)."""
    tool = SafeFileWriterTool()
    result = tool._run(file_path="src/evil.py", content="evil")
    assert "SECURITY BLOCK" in result
    assert "outside allowed directories" in result


def test_write_to_protected_basename_blocked():
    """.env must be blocked by its basename, regardless of directory."""
    tool = SafeFileWriterTool()
    result = tool._run(file_path="outputs/.env", content="evil")
    assert "SECURITY BLOCK" in result
    assert "protected file" in result


def test_write_to_protected_relpath_blocked():
    """latex/main.tex must be blocked by its relative path."""
    tool = SafeFileWriterTool()
    result = tool._run(file_path="latex/main.tex", content="evil")
    assert "SECURITY BLOCK" in result
    assert "protected file" in result


def test_write_to_protected_cover_blocked():
    """latex/chapters/cover.tex must be blocked by its relative path."""
    tool = SafeFileWriterTool()
    result = tool._run(file_path="latex/chapters/cover.tex", content="evil")
    assert "SECURITY BLOCK" in result
    assert "protected file" in result


def test_write_success_to_outputs(tmp_path, monkeypatch):
    """Writing to outputs/ in a tmp_path context must succeed and return SUCCESS."""
    import src.config as cfg
    import src.tools.file_tools as ft

    monkeypatch.setattr(cfg, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(ft, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(
        ft, "ALLOWED_BASE_DIRS",
        tuple((tmp_path / d).resolve() for d in cfg.WRITABLE_DIRS),
    )

    (tmp_path / "outputs").mkdir(parents=True, exist_ok=True)

    tool = SafeFileWriterTool()
    result = tool._run(file_path="outputs/test.md", content="hello world")

    assert "SUCCESS" in result
    assert (tmp_path / "outputs" / "test.md").exists()


def test_write_creates_parent_dirs(tmp_path, monkeypatch):
    """SafeFileWriterTool must create intermediate directories automatically."""
    import src.config as cfg
    import src.tools.file_tools as ft

    monkeypatch.setattr(cfg, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(ft, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(
        ft, "ALLOWED_BASE_DIRS",
        tuple((tmp_path / d).resolve() for d in cfg.WRITABLE_DIRS),
    )

    tool = SafeFileWriterTool()
    result = tool._run(file_path="outputs/subdir/deep/file.md", content="deep content")

    assert "SUCCESS" in result
    assert (tmp_path / "outputs" / "subdir" / "deep" / "file.md").exists()


# ---------------------------------------------------------------------------
# FileReaderTool tests
# ---------------------------------------------------------------------------

def test_read_existing_file(tmp_path: Path):
    """FileReaderTool must return the file contents for an existing file."""
    test_file = tmp_path / "chapter.tex"
    test_file.write_text("\\section{Test}", encoding="utf-8")

    tool = FileReaderTool()
    result = tool._run(file_path=str(test_file))
    assert "\\section{Test}" in result


def test_read_missing_file():
    """FileReaderTool must return an error string starting with 'ERROR:' for a missing file."""
    tool = FileReaderTool()
    result = tool._run(file_path="/nonexistent/path/that/does/not/exist.tex")
    assert result.startswith("ERROR:"), f"Expected error message, got: {result!r}"


def test_write_content_correct(tmp_path, monkeypatch):
    """Content written by SafeFileWriterTool must be identical when read back."""
    import src.config as cfg
    import src.tools.file_tools as ft

    monkeypatch.setattr(cfg, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(ft, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(
        ft, "ALLOWED_BASE_DIRS",
        tuple((tmp_path / d).resolve() for d in cfg.WRITABLE_DIRS),
    )

    expected_content = "# Test\n\nSome content here.\n"
    writer = SafeFileWriterTool()
    writer._run(file_path="outputs/roundtrip.md", content=expected_content)

    reader = FileReaderTool()
    written_path = tmp_path / "outputs" / "roundtrip.md"
    actual = reader._run(file_path=str(written_path))
    assert actual == expected_content
