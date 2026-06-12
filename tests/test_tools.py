"""
tests/test_tools.py
====================
Unit tests for Module 3: Tool definitions.
"""

from src.tools import FileReaderTool, PythonCodeExecutorTool, SafeFileWriterTool


def test_code_executor_security():
    tool = PythonCodeExecutorTool()
    # Test forbidden import
    result = tool._run(code="import socket", output_filename="test.png")
    assert "SECURITY BLOCK" in result

def test_safe_file_writer_security():
    tool = SafeFileWriterTool()
    # Test writing to forbidden src/ dir
    result = tool._run(file_path="src/new_tool.py", content="print(1)")
    assert "SECURITY BLOCK" in result

def test_file_reader_exists(tmp_path):
    f = tmp_path / "test.txt"
    f.write_text("hello", encoding="utf-8")
    tool = FileReaderTool()
    result = tool._run(file_path=str(f))
    assert result == "hello"
