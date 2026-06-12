"""
tests/test_tools_network.py
===========================
Network-tool unit tests for src/tools/search_tools.py and
src/tools/web_scraper.py. All HTTP / external library access is monkeypatched;
no real network calls are made.
"""

from __future__ import annotations

import sys
import types

import pytest

import src.tools.search_tools as search_tools
from src.tools.search_tools import ArxivSearchTool, SerperDevSearchTool
from src.tools.web_scraper import NavigatorWebScraperTool

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _FakeResponse:
    """Minimal stand-in for requests.Response."""

    def __init__(self, *, json_data=None, text="", status_code=200, raise_exc=None):
        self._json = json_data
        self.text = text
        self.content = text.encode("utf-8")
        self.status_code = status_code
        self._raise_exc = raise_exc

    def raise_for_status(self):
        if self._raise_exc is not None:
            raise self._raise_exc

    def json(self):
        return self._json


# ---------------------------------------------------------------------------
# SerperDevSearchTool
# ---------------------------------------------------------------------------

def test_serper_missing_api_key(monkeypatch):
    monkeypatch.delenv("SERPER_API_KEY", raising=False)
    tool = SerperDevSearchTool()
    result = tool._run(query="kalman filter")
    assert "ERROR" in result
    assert "SERPER_API_KEY" in result


def test_serper_success(monkeypatch):
    monkeypatch.setenv("SERPER_API_KEY", "fake-key")
    fake_json = {
        "organic": [
            {
                "title": "Kalman Filter Tutorial",
                "link": "https://example.com/kf",
                "snippet": "An introduction to the Kalman filter.",
            },
            {
                "title": "Second Result",
                "link": "https://example.com/two",
                "snippet": "Another snippet.",
            },
        ]
    }

    def fake_post(url, headers=None, json=None, timeout=None):
        # Confirm the API key header is forwarded.
        assert headers["X-API-KEY"] == "fake-key"
        return _FakeResponse(json_data=fake_json)

    monkeypatch.setattr(search_tools.requests, "post", fake_post)

    tool = SerperDevSearchTool()
    result = tool._run(query="kalman filter", n_results=2)
    assert "Kalman Filter Tutorial" in result
    assert "https://example.com/kf" in result
    assert "An introduction to the Kalman filter." in result
    assert "Second Result" in result
    assert "Search results for:" in result


def test_serper_respects_n_results(monkeypatch):
    monkeypatch.setenv("SERPER_API_KEY", "fake-key")
    fake_json = {
        "organic": [
            {"title": f"Result {i}", "link": f"https://e.com/{i}", "snippet": f"s{i}"}
            for i in range(5)
        ]
    }
    monkeypatch.setattr(
        search_tools.requests, "post",
        lambda *a, **k: _FakeResponse(json_data=fake_json),
    )
    tool = SerperDevSearchTool()
    result = tool._run(query="q", n_results=1)
    assert "Result 0" in result
    assert "Result 1" not in result


def test_serper_empty_results(monkeypatch):
    monkeypatch.setenv("SERPER_API_KEY", "fake-key")
    monkeypatch.setattr(
        search_tools.requests, "post",
        lambda *a, **k: _FakeResponse(json_data={"organic": []}),
    )
    tool = SerperDevSearchTool()
    result = tool._run(query="nothing here")
    assert "No results found" in result
    assert "nothing here" in result


def test_serper_http_error(monkeypatch):
    monkeypatch.setenv("SERPER_API_KEY", "fake-key")

    def fake_post(*a, **k):
        return _FakeResponse(raise_exc=RuntimeError("503 Server Error"))

    monkeypatch.setattr(search_tools.requests, "post", fake_post)
    tool = SerperDevSearchTool()
    result = tool._run(query="q")
    assert "ERROR" in result
    assert "Serper.dev error" in result
    assert "503 Server Error" in result


def test_serper_request_exception(monkeypatch):
    monkeypatch.setenv("SERPER_API_KEY", "fake-key")

    def fake_post(*a, **k):
        raise ConnectionError("network down")

    monkeypatch.setattr(search_tools.requests, "post", fake_post)
    tool = SerperDevSearchTool()
    result = tool._run(query="q")
    assert "ERROR" in result
    assert "network down" in result


# ---------------------------------------------------------------------------
# ArxivSearchTool
# ---------------------------------------------------------------------------

class _FakeAuthor:
    def __init__(self, name):
        self.name = name


class _FakePaper:
    def __init__(self, title, authors, pdf_url):
        self.title = title
        self.authors = [_FakeAuthor(a) for a in authors]
        self.pdf_url = pdf_url


def _install_fake_arxiv(monkeypatch, *, papers=None, raise_on_results=None):
    """Install a fake `arxiv` module into sys.modules."""
    fake = types.ModuleType("arxiv")

    class FakeSearch:
        def __init__(self, query=None, max_results=None):
            self.query = query
            self.max_results = max_results

    class FakeClient:
        def results(self, search):
            if raise_on_results is not None:
                raise raise_on_results
            return iter(papers or [])

    fake.Search = FakeSearch
    fake.Client = FakeClient
    monkeypatch.setitem(sys.modules, "arxiv", fake)
    return fake


def test_arxiv_success(monkeypatch):
    papers = [
        _FakePaper("Attention Is All You Need", ["Ashish Vaswani", "Noam Shazeer"],
                   "https://arxiv.org/pdf/1706.03762"),
        _FakePaper("Deep Residual Learning", ["Kaiming He"],
                   "https://arxiv.org/pdf/1512.03385"),
    ]
    _install_fake_arxiv(monkeypatch, papers=papers)
    tool = ArxivSearchTool()
    result = tool._run(query="transformers", n_results=2)
    assert "arXiv results for:" in result
    assert "Attention Is All You Need" in result
    assert "Ashish Vaswani, Noam Shazeer" in result
    assert "https://arxiv.org/pdf/1706.03762" in result
    assert "Deep Residual Learning" in result


def test_arxiv_empty(monkeypatch):
    _install_fake_arxiv(monkeypatch, papers=[])
    tool = ArxivSearchTool()
    result = tool._run(query="obscure topic")
    assert "No arXiv results" in result
    assert "obscure topic" in result


def test_arxiv_query_exception(monkeypatch):
    _install_fake_arxiv(monkeypatch, raise_on_results=RuntimeError("api boom"))
    tool = ArxivSearchTool()
    result = tool._run(query="q")
    assert "ERROR" in result
    assert "arXiv query failed" in result
    assert "api boom" in result


def test_arxiv_import_error(monkeypatch):
    # Force `import arxiv` to fail by removing it and blocking re-import.
    monkeypatch.setitem(sys.modules, "arxiv", None)
    tool = ArxivSearchTool()
    result = tool._run(query="q")
    assert "ERROR" in result
    assert "'arxiv' package not installed" in result


# ---------------------------------------------------------------------------
# NavigatorWebScraperTool
# ---------------------------------------------------------------------------

_SAMPLE_HTML = """
<html>
  <head><style>.x{color:red}</style></head>
  <body>
    <nav>NAV MENU</nav>
    <h1>Main Heading</h1>
    <p>This is the readable body paragraph.</p>
    <script>console.log("noise");</script>
    <footer>FOOTER LINKS</footer>
  </body>
</html>
"""


def test_web_scraper_success(monkeypatch):
    import requests

    def fake_get(url, headers=None, timeout=None):
        return _FakeResponse(text=_SAMPLE_HTML)

    monkeypatch.setattr(requests, "get", fake_get)
    tool = NavigatorWebScraperTool()
    result = tool._run(url="https://example.com")
    assert "Main Heading" in result
    assert "This is the readable body paragraph." in result
    # Stripped tags must not appear in the cleaned text.
    assert "console.log" not in result
    assert "NAV MENU" not in result
    assert "FOOTER LINKS" not in result


def test_web_scraper_caps_at_8kb(monkeypatch):
    import requests

    big_html = "<html><body><p>" + ("a" * 20000) + "</p></body></html>"
    monkeypatch.setattr(
        requests, "get", lambda *a, **k: _FakeResponse(text=big_html)
    )
    tool = NavigatorWebScraperTool()
    result = tool._run(url="https://example.com/big")
    assert len(result) <= 8000


def test_web_scraper_http_error(monkeypatch):
    import requests

    def fake_get(*a, **k):
        return _FakeResponse(text="", raise_exc=RuntimeError("404 Not Found"))

    monkeypatch.setattr(requests, "get", fake_get)
    tool = NavigatorWebScraperTool()
    result = tool._run(url="https://example.com/missing")
    assert "ERROR" in result
    assert "Scraper failed" in result
    assert "404 Not Found" in result


def test_web_scraper_request_exception(monkeypatch):
    import requests

    def fake_get(*a, **k):
        raise ConnectionError("dns failure")

    monkeypatch.setattr(requests, "get", fake_get)
    tool = NavigatorWebScraperTool()
    result = tool._run(url="https://bad.example")
    assert "ERROR" in result
    assert "dns failure" in result


if __name__ == "__main__":  # pragma: no cover
    sys.exit(pytest.main([__file__, "-q"]))
