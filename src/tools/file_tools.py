"""
src/tools/file_tools.py
========================
SafeFileWriterTool and FileReaderTool.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from src.config import PROJECT_ROOT, PROTECTED_FILES, WRITABLE_DIRS, logger

ALLOWED_BASE_DIRS: tuple[Path, ...] = tuple(
    (PROJECT_ROOT / d).resolve() for d in WRITABLE_DIRS
)


class SafeFileWriterInput(BaseModel):
    file_path: str = Field(..., description="Path to write.")
    content: str = Field(..., description="Content to write.")


class SafeFileWriterTool(BaseTool):
    name: str = "SafeFileWriterTool"
    description: str = "Write a text file safely."
    args_schema: Type[BaseModel] = SafeFileWriterInput

    def _run(self, file_path: str, content: str, **kwargs: Any) -> str:
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
    file_path: str = Field(..., description="Path to read.")


class FileReaderTool(BaseTool):
    name: str = "FileReaderTool"
    description: str = "Read a text file."
    args_schema: Type[BaseModel] = FileReaderInput

    def _run(self, file_path: str, **kwargs: Any) -> str:
        raw = Path(file_path)
        resolved = (PROJECT_ROOT / raw).resolve() if not raw.is_absolute() else raw.resolve()

        if not resolved.exists():
            return "ERROR: file not found."

        return resolved.read_text(encoding="utf-8", errors="replace")
