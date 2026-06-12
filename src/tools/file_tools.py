"""
src/tools/file_tools.py
========================
SafeFileWriterTool and FileReaderTool.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from src.config import PROJECT_ROOT, PROTECTED_FILES, WRITABLE_DIRS, logger

ALLOWED_BASE_DIRS: tuple[Path, ...] = tuple(
    (PROJECT_ROOT / d).resolve() for d in WRITABLE_DIRS
)


class SafeFileWriterInput(BaseModel):
    """Arguments for SafeFileWriterTool: the `file_path` to write and the text `content` to write to it."""

    file_path: str = Field(..., description="Path to write.")
    content: str = Field(..., description="Content to write.")


class SafeFileWriterTool(BaseTool):
    """Write a text file, but only inside allowed directories and never over protected files."""

    name: str = "SafeFileWriterTool"
    description: str = "Write a text file safely."
    args_schema: type[BaseModel] = SafeFileWriterInput

    def _run(self, file_path: str, content: str, **kwargs: Any) -> str:
        """Write `content` to `file_path` after security checks, returning a SUCCESS message with the resolved path or a SECURITY BLOCK message."""
        raw = Path(file_path)
        resolved = (PROJECT_ROOT / raw).resolve() if not raw.is_absolute() else raw.resolve()

        if not any(str(resolved).startswith(str(base)) for base in ALLOWED_BASE_DIRS):
            return "SECURITY BLOCK: outside allowed directories."

        # Check both basename and relative path from PROJECT_ROOT
        try:
            rel_path = str(resolved.relative_to(PROJECT_ROOT))
        except ValueError:
            rel_path = ""
        if resolved.name in PROTECTED_FILES or rel_path in PROTECTED_FILES:
            return "SECURITY BLOCK: protected file."

        resolved.parent.mkdir(parents=True, exist_ok=True)
        resolved.write_text(content, encoding="utf-8")
        size_kb = resolved.stat().st_size // 1024
        logger.info(f"SafeFileWriterTool: wrote {resolved.name} ({size_kb} KB)")
        return f"SUCCESS: wrote to {resolved}"


class FileReaderInput(BaseModel):
    """Arguments for FileReaderTool: the `file_path` to read."""

    file_path: str = Field(..., description="Path to read.")


class FileReaderTool(BaseTool):
    """Read the text content of a file, resolving paths relative to the project root."""

    name: str = "FileReaderTool"
    description: str = "Read a text file."
    args_schema: type[BaseModel] = FileReaderInput

    def _run(self, file_path: str, **kwargs: Any) -> str:
        """Resolve `file_path` against the project root and return the file's text content, or an ERROR message if it is not found."""
        raw = Path(file_path)
        # LLMs sometimes pass "/outputs/foo.md" (leading slash) which would
        # resolve to the filesystem root. Strip the leading slash so relative
        # resolution against PROJECT_ROOT works correctly.
        if raw.is_absolute() and not raw.exists():
            raw = Path(str(raw).lstrip("/"))
        resolved = (PROJECT_ROOT / raw).resolve() if not raw.is_absolute() else raw.resolve()

        if not resolved.exists():
            return f"ERROR: file not found at {resolved}. Make sure the path is relative to the project root (e.g. 'outputs/current/research_briefs.md')."

        return resolved.read_text(encoding="utf-8", errors="replace")
