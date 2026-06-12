"""Tests for src/stubs.py — stub chapter generator."""
from pathlib import Path

from src.stubs import (
    _abstract_stub,
    _chapter_stub,
    _references_bib,
    _stub_png,
    _words,
    write_stub_chapters,
)


class TestStubPng:
    def test_starts_with_png_signature(self):
        data = _stub_png()
        assert data[:8] == b"\x89PNG\r\n\x1a\n"

    def test_returns_bytes(self):
        assert isinstance(_stub_png(), bytes)

    def test_contains_ihdr_and_iend(self):
        data = _stub_png()
        assert b"IHDR" in data
        assert b"IEND" in data


class TestWords:
    def test_returns_approx_n_words(self):
        text = _words(100)
        assert len(text.split()) == 100

    def test_small_count(self):
        assert len(_words(5).split()) == 5

    def test_zero_words(self):
        assert _words(0) == ""

    def test_returns_hebrew(self):
        text = _words(10)
        assert any("\u0590" <= c <= "\u05FF" for c in text)


class TestReferencesBib:
    def test_has_14_entries(self):
        bib = _references_bib()
        assert bib.count("@misc{") == 14

    def test_contains_known_keys(self):
        bib = _references_bib()
        for key in ("Thrun2005", "Kalman1960", "Vaswani2017"):
            assert f"@misc{{{key}," in bib

    def test_ends_with_newline(self):
        assert _references_bib().endswith("\n")


class TestAbstractStub:
    def test_starts_with_selectlanguage(self):
        text = _abstract_stub()
        assert text.startswith(r"\selectlanguage{hebrew}")

    def test_word_count_at_least_100(self):
        text = _abstract_stub()
        body = text.split("\n", 1)[1]
        assert len(body.split()) >= 100


class TestChapterStub:
    def test_has_section_label(self):
        tex = _chapter_stub("intro", "ch01", n_sub=0, n_eq=0, n_fig=0, n_cite=0, n_words=100)
        assert r"\section{intro}" in tex
        assert r"\label{sec:ch01}" in tex

    def test_subsections(self):
        tex = _chapter_stub("Topic", "ch02", n_sub=3, n_eq=0, n_fig=0, n_cite=0, n_words=300)
        assert tex.count(r"\subsection{") == 3
        assert r"\label{sub:ch02_1}" in tex
        assert r"\label{sub:ch02_3}" in tex

    def test_equations(self):
        tex = _chapter_stub("S", "ch03", n_sub=3, n_eq=2, n_fig=0, n_cite=0, n_words=300)
        assert tex.count(r"\begin{equation}") == 2
        assert r"\label{eq:ch03_1}" in tex
        assert r"\label{eq:ch03_2}" in tex

    def test_figures(self):
        tex = _chapter_stub("S", "ch04", n_sub=1, n_eq=0, n_fig=2, n_cite=0, n_words=200)
        assert tex.count(r"\begin{figure}[H]") == 2
        assert r"\label{fig:ch04_1}" in tex
        assert r"\label{fig:ch04_2}" in tex
        assert "fig_stub.png" in tex

    def test_citations(self):
        tex = _chapter_stub("S", "ch05", n_sub=1, n_eq=0, n_fig=0, n_cite=3, n_words=200)
        assert tex.count(r"\cite{") == 3

    def test_selectlanguage_header(self):
        tex = _chapter_stub("S", "ch01", n_sub=0, n_eq=0, n_fig=0, n_cite=0, n_words=100)
        assert tex.startswith(r"\selectlanguage{hebrew}")


class TestWriteStubChapters:
    def test_creates_all_files(self, tmp_path: Path):
        write_stub_chapters(tmp_path, "test topic")
        chapters_dir = tmp_path / "latex" / "chapters"
        figures_dir = tmp_path / "latex" / "figures"
        bib_path = tmp_path / "latex" / "references.bib"
        assert chapters_dir.is_dir()
        assert figures_dir.is_dir()
        assert bib_path.is_file()
        tex_files = sorted(chapters_dir.glob("*.tex"))
        assert len(tex_files) == 10
        assert (figures_dir / "fig_stub.png").is_file()

    def test_png_is_valid(self, tmp_path: Path):
        write_stub_chapters(tmp_path, "test")
        png = (tmp_path / "latex" / "figures" / "fig_stub.png").read_bytes()
        assert png[:8] == b"\x89PNG\r\n\x1a\n"

    def test_bib_has_entries(self, tmp_path: Path):
        write_stub_chapters(tmp_path, "test")
        bib = (tmp_path / "latex" / "references.bib").read_text(encoding="utf-8")
        assert bib.count("@misc{") == 14

    def test_abstract_content(self, tmp_path: Path):
        write_stub_chapters(tmp_path, "test")
        abstract = (tmp_path / "latex" / "chapters" / "abstract.tex").read_text(encoding="utf-8")
        assert r"\selectlanguage{hebrew}" in abstract

    def test_chapter_content(self, tmp_path: Path):
        write_stub_chapters(tmp_path, "test")
        ch01 = (tmp_path / "latex" / "chapters" / "ch01_intro.tex").read_text(encoding="utf-8")
        assert r"\section{" in ch01
        assert r"\subsection{" in ch01

    def test_idempotent(self, tmp_path: Path):
        write_stub_chapters(tmp_path, "t")
        write_stub_chapters(tmp_path, "t")
        assert len(list((tmp_path / "latex" / "chapters").glob("*.tex"))) == 10
