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


