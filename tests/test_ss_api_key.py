"""Tests for Semantic Scholar API key integration and rate limiter.

All tests use mocks — no real network calls to SS are made.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import src.novelty.arxiv_search as arxiv_search
from src.novelty.arxiv_search import SS_MIN_INTERVAL, _ss_headers, _ss_rate_limit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _reset_rate_limiter() -> None:
    """Resetea el estado global del rate limiter para aislar tests."""
    arxiv_search._ss_last_call = 0.0


def _reset_warning_flag() -> None:
    """Resetea el flag de warning anónimo para aislar tests."""
    arxiv_search._ss_anon_warning_emitted = False


# ---------------------------------------------------------------------------
# _ss_headers — presencia / ausencia del header x-api-key
# ---------------------------------------------------------------------------

def test_ss_headers_with_api_key_includes_header(monkeypatch):
    """Cuando SEMANTIC_SCHOLAR_API_KEY está configurada, x-api-key aparece."""
    monkeypatch.setenv("SEMANTIC_SCHOLAR_API_KEY", "test-key-abc123")
    headers = _ss_headers()
    assert "x-api-key" in headers
    assert headers["x-api-key"] == "test-key-abc123"


def test_ss_headers_without_api_key_omits_header(monkeypatch):
    """Cuando SEMANTIC_SCHOLAR_API_KEY no está configurada, x-api-key no aparece."""
    monkeypatch.delenv("SEMANTIC_SCHOLAR_API_KEY", raising=False)
    _reset_warning_flag()
    headers = _ss_headers()
    assert "x-api-key" not in headers


def test_ss_headers_empty_api_key_omits_header(monkeypatch):
    """Una key vacía (variable definida pero sin valor) equivale a sin key."""
    monkeypatch.setenv("SEMANTIC_SCHOLAR_API_KEY", "")
    _reset_warning_flag()
    headers = _ss_headers()
    assert "x-api-key" not in headers


def test_ss_headers_whitespace_only_key_omits_header(monkeypatch):
    """Una key de solo espacios se trata como ausente."""
    monkeypatch.setenv("SEMANTIC_SCHOLAR_API_KEY", "   ")
    _reset_warning_flag()
    headers = _ss_headers()
    assert "x-api-key" not in headers


def test_ss_headers_always_includes_accept(monkeypatch):
    """El header Accept: application/json siempre está presente."""
    monkeypatch.setenv("SEMANTIC_SCHOLAR_API_KEY", "any-key")
    assert _ss_headers().get("Accept") == "application/json"

    monkeypatch.delenv("SEMANTIC_SCHOLAR_API_KEY", raising=False)
    _reset_warning_flag()
    assert _ss_headers().get("Accept") == "application/json"


# ---------------------------------------------------------------------------
# Warning de modo anónimo — emitido solo una vez
# ---------------------------------------------------------------------------

def test_anon_warning_emitted_once(monkeypatch, caplog):
    """El warning de modo anónimo se emite exactamente una vez por proceso."""
    import logging

    monkeypatch.delenv("SEMANTIC_SCHOLAR_API_KEY", raising=False)
    _reset_warning_flag()

    with caplog.at_level(logging.WARNING, logger="src.novelty.arxiv_search"):
        _ss_headers()
        _ss_headers()
        _ss_headers()

    warning_msgs = [r for r in caplog.records if "anonymous mode" in r.message.lower()]
    assert len(warning_msgs) == 1, (
        f"Expected exactly 1 anonymous-mode warning, got {len(warning_msgs)}"
    )


def test_no_warning_when_key_present(monkeypatch, caplog):
    """No se emite warning cuando la API key está configurada."""
    import logging

    monkeypatch.setenv("SEMANTIC_SCHOLAR_API_KEY", "some-valid-key")
    _reset_warning_flag()

    with caplog.at_level(logging.WARNING, logger="src.novelty.arxiv_search"):
        _ss_headers()
        _ss_headers()

    warning_msgs = [r for r in caplog.records if "anonymous mode" in r.message.lower()]
    assert len(warning_msgs) == 0


# ---------------------------------------------------------------------------
# Rate limiter (_ss_rate_limit)
# ---------------------------------------------------------------------------

def test_rate_limiter_enforces_min_interval():
    """Dos llamadas consecutivas deben estar separadas al menos SS_MIN_INTERVAL s."""
    _reset_rate_limiter()

    t0 = time.monotonic()
    _ss_rate_limit()
    t1 = time.monotonic()
    _ss_rate_limit()
    t2 = time.monotonic()

    gap = t2 - t1
    assert gap >= SS_MIN_INTERVAL * 0.95, (
        f"Gap between calls ({gap:.3f}s) is less than SS_MIN_INTERVAL "
        f"({SS_MIN_INTERVAL}s) — rate limiter not working"
    )


def test_rate_limiter_does_not_sleep_when_enough_time_passed():
    """Si ya pasó más de SS_MIN_INTERVAL, no hay sleep (la llamada es instantánea)."""
    # Forzar que la última llamada fue hace mucho tiempo
    arxiv_search._ss_last_call = time.monotonic() - SS_MIN_INTERVAL * 10

    t0 = time.monotonic()
    _ss_rate_limit()
    elapsed = time.monotonic() - t0

    # Sin sleep, esto debe completarse en < 50ms
    assert elapsed < 0.05, (
        f"_ss_rate_limit slept {elapsed:.3f}s when no sleep was needed"
    )


def test_rate_limiter_updates_last_call_timestamp():
    """_ss_rate_limit actualiza _ss_last_call después de cada invocación."""
    _reset_rate_limiter()
    assert arxiv_search._ss_last_call == 0.0

    t_before = time.monotonic()
    _ss_rate_limit()
    t_after = time.monotonic()

    assert t_before <= arxiv_search._ss_last_call <= t_after + 0.01


# ---------------------------------------------------------------------------
# _fetch_semantic_scholar — integración del header en el request HTTP
# ---------------------------------------------------------------------------

def _make_ok_response() -> MagicMock:
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json.return_value = {"data": []}
    return resp


def test_fetch_ss_sends_api_key_header(monkeypatch):
    """_fetch_semantic_scholar incluye x-api-key cuando la key está configurada."""
    monkeypatch.setenv("SEMANTIC_SCHOLAR_API_KEY", "my-secret-key")
    _reset_rate_limiter()

    with patch("requests.get", return_value=_make_ok_response()) as mock_get:
        payload = arxiv_search._fetch_semantic_scholar("test query", top_k=5)

    call_kwargs = mock_get.call_args[1]
    sent_headers = call_kwargs.get("headers", {})
    assert "x-api-key" in sent_headers
    assert sent_headers["x-api-key"] == "my-secret-key"
    assert payload["_meta"]["used_api_key"] is True
    assert payload["_meta"]["data_len"] == 0


def test_fetch_ss_omits_api_key_header_when_not_set(monkeypatch):
    """_fetch_semantic_scholar omite x-api-key cuando no hay key configurada."""
    monkeypatch.delenv("SEMANTIC_SCHOLAR_API_KEY", raising=False)
    _reset_warning_flag()
    _reset_rate_limiter()

    with patch("requests.get", return_value=_make_ok_response()) as mock_get:
        arxiv_search._fetch_semantic_scholar("test query", top_k=5)

    call_kwargs = mock_get.call_args[1]
    sent_headers = call_kwargs.get("headers", {})
    assert "x-api-key" not in sent_headers


def test_fetch_ss_calls_rate_limiter(monkeypatch):
    """_fetch_semantic_scholar invoca _ss_rate_limit antes de cada request."""
    monkeypatch.setenv("SEMANTIC_SCHOLAR_API_KEY", "key")
    _reset_rate_limiter()

    call_log: list[float] = []

    original_rate_limit = arxiv_search._ss_rate_limit

    def spy_rate_limit():
        call_log.append(time.monotonic())
        # Bypass sleep para no ralentizar el test
        arxiv_search._ss_last_call = time.monotonic()

    with patch.object(arxiv_search, "_ss_rate_limit", side_effect=spy_rate_limit):
        with patch("requests.get", return_value=_make_ok_response()):
            arxiv_search._fetch_semantic_scholar("q1", top_k=3)
            arxiv_search._fetch_semantic_scholar("q2", top_k=3)

    assert len(call_log) == 2, (
        f"_ss_rate_limit should have been called twice, got {len(call_log)}"
    )


def test_search_ss_uses_fallback_query_when_primary_empty(monkeypatch):
    """Si el abstract no trae resultados, se prueba la query fallback."""
    monkeypatch.setenv("SEMANTIC_SCHOLAR_API_KEY", "key")
    _reset_rate_limiter()

    calls: list[str] = []

    def fake_fetch(query: str, top_k: int) -> dict:
        calls.append(query)
        if query == "abstract query":
            return {"data": [], "_meta": {"status_code": 200, "data_len": 0}}
        return {
            "data": [
                {
                    "paperId": "p1",
                    "title": "Title match",
                    "abstract": "candidate abstract",
                    "externalIds": {"ArXiv": "2603.29961"},
                }
            ],
            "_meta": {"status_code": 200, "data_len": 1},
        }

    monkeypatch.setattr(arxiv_search, "_fetch_semantic_scholar", fake_fetch)
    monkeypatch.setattr(arxiv_search, "_cosine_similarity_text", lambda a, b: 0.5)

    results = arxiv_search.search_semantic_scholar(
        "abstract query",
        top_k=5,
        use_cache=False,
        fallback_queries=["title query"],
    )

    assert calls == ["abstract query", "title query"]
    assert len(results) == 1
    assert results[0].arxiv_id == "2603.29961"


def test_search_ss_excludes_current_arxiv_id(monkeypatch):
    monkeypatch.setattr(arxiv_search, "_cosine_similarity_text", lambda a, b: 0.5)
    monkeypatch.setattr(
        arxiv_search,
        "_fetch_semantic_scholar",
        lambda query, top_k: {
            "data": [
                {
                    "paperId": "self",
                    "title": "Self",
                    "abstract": "self abstract",
                    "externalIds": {"ArXiv": "2603.29961v1"},
                },
                {
                    "paperId": "other",
                    "title": "Other",
                    "abstract": "other abstract",
                    "externalIds": {"ArXiv": "2604.06609"},
                },
            ]
        },
    )

    results = arxiv_search.search_semantic_scholar(
        "query",
        top_k=5,
        use_cache=False,
        exclude_arxiv_ids=["2603.29961"],
    )

    assert [candidate.arxiv_id for candidate in results] == ["2604.06609"]
