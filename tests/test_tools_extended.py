"""
tests/test_tools_extended.py
=============================
Extended tests for search_tools and web_scraper (low-coverage modules).
"""

from __future__ import annotations

from types import ModuleType
from unittest.mock import MagicMock, patch

from src.tools.search_tools import ArxivSearchTool, SerperDevSearchTool
from src.tools.web_scraper import NavigatorWebScraperTool

# ── SerperDevSearchTool ──────────────────────────────────────────────────

class TestSerperDevSearchTool:
    def test_no_api_key(self, monkeypatch):
        monkeypatch.delenv("SERPER_API_KEY", raising=False)
        tool = SerperDevSearchTool()
        assert tool._run("test query") == "ERROR: SERPER_API_KEY is not set."

    def test_successful_search(self, monkeypatch):
        monkeypatch.setenv("SERPER_API_KEY", "test-key")
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "organic": [
                {"title": "Paper A", "link": "https://a.com", "snippet": "snip A"},
                {"title": "Paper B", "link": "https://b.com", "snippet": "snip B"},
            ]
        }
        with patch("src.tools.search_tools.requests.post", return_value=mock_resp) as mp:
            tool = SerperDevSearchTool()
            result = tool._run("SLAM survey", n_results=2)
            mp.assert_called_once()
        assert "[1] Paper A" in result
        assert "[2] Paper B" in result
        assert "https://b.com" in result

    def test_request_exception(self, monkeypatch):
        monkeypatch.setenv("SERPER_API_KEY", "test-key")
        with patch("src.tools.search_tools.requests.post", side_effect=ConnectionError("timeout")):
            result = SerperDevSearchTool()._run("query")
        assert "ERROR: Serper.dev error:" in result

    def test_no_organic_results(self, monkeypatch):
        monkeypatch.setenv("SERPER_API_KEY", "test-key")
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"organic": []}
        with patch("src.tools.search_tools.requests.post", return_value=mock_resp):
            result = SerperDevSearchTool()._run("obscure query")
        assert "No results found" in result

# ── ArxivSearchTool ──────────────────────────────────────────────────────

class TestArxivSearchTool:
    def _make_mock_paper(self, title, author_name, pdf_url):
        paper = MagicMock()
        paper.title = title
        author = MagicMock()
        author.name = author_name
        paper.authors = [author]
        paper.pdf_url = pdf_url
        return paper

    def test_successful_search(self, monkeypatch):
        fake_arxiv = ModuleType("arxiv")
        fake_client = MagicMock()
        fake_client.results.return_value = [
            self._make_mock_paper("Deep SLAM", "Alice", "https://arxiv.org/pdf/1"),
        ]
        fake_arxiv.Client = MagicMock(return_value=fake_client)
        fake_arxiv.Search = MagicMock()
        monkeypatch.setitem(__import__("sys").modules, "arxiv", fake_arxiv)
        result = ArxivSearchTool()._run("deep SLAM", n_results=1)
        assert "[1] Deep SLAM" in result
        assert "Alice" in result

    def test_no_results(self, monkeypatch):
        fake_arxiv = ModuleType("arxiv")
        fake_client = MagicMock()
        fake_client.results.return_value = []
        fake_arxiv.Client = MagicMock(return_value=fake_client)
        fake_arxiv.Search = MagicMock()
        monkeypatch.setitem(__import__("sys").modules, "arxiv", fake_arxiv)
        result = ArxivSearchTool()._run("zzzzz")
        assert "No arXiv results" in result

    def test_exception(self, monkeypatch):
        fake_arxiv = ModuleType("arxiv")
        fake_arxiv.Client = MagicMock(side_effect=RuntimeError("boom"))
        fake_arxiv.Search = MagicMock()
        monkeypatch.setitem(__import__("sys").modules, "arxiv", fake_arxiv)
        result = ArxivSearchTool()._run("query")
        assert "ERROR: arXiv query failed:" in result

    def test_import_error(self, monkeypatch):
        monkeypatch.setitem(__import__("sys").modules, "arxiv", None)
        result = ArxivSearchTool()._run("query")
        assert "not installed" in result

# ── NavigatorWebScraperTool ──────────────────────────────────────────────

class TestNavigatorWebScraperTool:
    def test_successful_scrape(self):
        html = "<html><body><script>x</script><p>Hello World</p></body></html>"
        mock_resp = MagicMock()
        mock_resp.text = html
        with patch("requests.get", return_value=mock_resp):
            result = NavigatorWebScraperTool()._run("https://example.com")
        assert "Hello World" in result
        assert "<script>" not in result

    def test_request_failure(self):
        with patch("requests.get", side_effect=ConnectionError("refused")):
            result = NavigatorWebScraperTool()._run("https://bad.url")
        assert "ERROR: Scraper failed:" in result
