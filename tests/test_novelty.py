"""Tests for src/novelty/ pipeline.

Live tests (those hitting external APIs) are marked with @pytest.mark.live and
can be excluded with `pytest -m "not live"` for offline CI runs.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# Asegurar que la raiz del repo esta en sys.path
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from src.novelty import (
    arxiv_search,
    llm_judge,
    mathlib_checker,
)
from src.novelty.arxiv_search import PaperCandidate, combine_and_filter
from src.novelty.block_comparator import strip_latex_for_query
from src.novelty.mathlib_checker import MathlibMatch, MathlibResult


# ---------------------------------------------------------------------------
# strip_latex_for_query — unit tests (no network, no model)
# ---------------------------------------------------------------------------

def test_strip_latex_plain_title():
    """Título sin LaTeX se devuelve intacto (salvo whitespace)."""
    assert strip_latex_for_query("Commutativity of addition") == "Commutativity of addition"


def test_strip_latex_cite_removed():
    r"""Título que es solo una cita bibliográfica queda vacío o sin la cita.

    Caso real: S\'ark\"ozy~\cite{Sarkozy2001}
    Esperado:  la parte legible del nombre sin \cite ni acentos LaTeX.
    """
    result = strip_latex_for_query(r"S\'ark\"ozy~\cite{Sarkozy2001}")
    # \cite{...} debe desaparecer completamente.
    assert "cite" not in result
    assert "Sarkozy2001" not in result
    # La parte legible del nombre debe conservarse.
    assert "Sark" in result or "ark" in result.lower()


def test_strip_latex_accents():
    r"""Acentos LaTeX se transliteran a la letra base sin el comando.

    \'a  → a,  \"o → o,  \`e → e
    """
    result = strip_latex_for_query(r"Lagrange\'s theorem on \'etale cohomology and M\"obius")
    assert "\\'" not in result
    assert '\\"' not in result
    # Letras base deben estar presentes.
    assert "Lagrange" in result
    assert "obius" in result  # M\"obius → Mobius


# ---------------------------------------------------------------------------
# Stage 0 - live test (skipped if network unreachable)
# ---------------------------------------------------------------------------

@pytest.mark.live
def test_stage0_finds_nat_add_comm():
    """Live: Leandex should locate Nat.add_comm for the canonical query."""
    block = {
        "type": "theorem",
        "title": "Commutativity of natural number addition",
        "content_latex": "For all natural numbers $a$ and $b$, $a + b = b + a$.",
    }
    result = mathlib_checker.check_in_mathlib(block, use_cache=False)
    if not result.matches:
        pytest.skip("Leandex returned no matches (service may be down)")
    names = [m.lean_name for m in result.matches]
    assert any("add_comm" in n.lower() for n in names), (
        f"Expected an *add_comm* declaration in matches, got: {names}"
    )


# ---------------------------------------------------------------------------
# Stage 1 - combine_and_filter
# ---------------------------------------------------------------------------

def _cand(arxiv_id, score, **kw):
    return PaperCandidate(
        paper_id=kw.get("paper_id", arxiv_id),
        title=kw.get("title", f"Paper {arxiv_id}"),
        abstract=kw.get("abstract", "abstract"),
        arxiv_id=arxiv_id,
        similarity_score=score,
        embedding=kw.get("embedding"),
        source=kw.get("source", "semantic_scholar"),
    )


def test_combine_and_filter_dedupe_and_threshold():
    candidates = [
        _cand("2401.0001", 0.9, source="semantic_scholar", embedding=[0.1] * 4),
        _cand("2401.0001", 0.7, source="arxiv"),  # duplicate, lower score
        _cand("2401.0002", 0.5, source="arxiv"),
        _cand("2401.0003", 0.2, source="arxiv"),  # below threshold
        _cand(None, 0.9),                          # no arxiv_id, dropped
    ]
    out = combine_and_filter(candidates, threshold=0.3)
    assert [c.arxiv_id for c in out] == ["2401.0001", "2401.0002"]
    # Embedding del primer match se conserva tras la deduplicacion.
    assert out[0].embedding == [0.1] * 4
    # Ordenado descendente.
    assert out[0].similarity_score >= out[1].similarity_score


def test_combine_and_filter_empty():
    assert combine_and_filter([], threshold=0.5) == []


def test_normalize_arxiv_id():
    from src.novelty.arxiv_search import _normalize_arxiv_id

    assert _normalize_arxiv_id("arXiv:2401.0001") == "2401.0001"
    assert _normalize_arxiv_id("http://arxiv.org/abs/2401.0001") == "2401.0001"
    assert _normalize_arxiv_id(None) is None


# ---------------------------------------------------------------------------
# Stage 1 - search_semantic_scholar with mocked HTTP
# ---------------------------------------------------------------------------

class _FakeResponse:
    def __init__(self, payload, status=200):
        self._payload = payload
        self.status_code = status
        self.text = json.dumps(payload)

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self._payload


def test_search_semantic_scholar_mocked(monkeypatch, tmp_path):
    fake_payload = {
        "data": [
            {
                "paperId": "p1",
                "title": "Squarefree integers in short intervals",
                "abstract": "We prove a new bound on squarefree integers.",
                "externalIds": {"ArXiv": "2401.1111"},
                "embedding": {"vector": [0.1, 0.2, 0.3]},
            },
            {
                "paperId": "p2",
                "title": "Unrelated paper without arxiv id",
                "abstract": "Something different.",
                "externalIds": {"DOI": "10.0/x"},
            },
        ]
    }

    def fake_get(url, params=None, headers=None, timeout=None):
        assert "paper/search" in url
        return _FakeResponse(fake_payload)

    monkeypatch.setattr(arxiv_search.requests, "get", fake_get)

    # Bypass MiniLM scoring para no requerir el modelo en tests.
    monkeypatch.setattr(
        arxiv_search,
        "_cosine_similarity_text",
        lambda a, b: 0.5,
    )

    # Redirigir cache a un dir temporal para no escribir en repo.
    monkeypatch.setattr(arxiv_search._cache, "CACHE_ROOT", tmp_path)

    out = arxiv_search.search_semantic_scholar(
        "abstract about squarefree integers", top_k=5, use_cache=False
    )
    assert len(out) == 1  # el segundo se descarta por no tener arxiv_id
    cand = out[0]
    assert cand.arxiv_id == "2401.1111"
    assert cand.embedding == [0.1, 0.2, 0.3]
    assert cand.similarity_score == pytest.approx(0.5)
    assert cand.source == "semantic_scholar"


# ---------------------------------------------------------------------------
# Stage 3 - judge_theorem_pair with mocked Claude Code
# ---------------------------------------------------------------------------

def test_judge_theorem_pair_equivalent(monkeypatch, tmp_path):
    fake_response = (
        '{"verdict": "equivalent", "confidence": 0.95, '
        '"reasoning": "Both state Pythagoras."}'
    )
    monkeypatch.setattr(llm_judge, "_call_deepseek", lambda *args, **kwargs: fake_response)
    monkeypatch.setattr(llm_judge._cache, "CACHE_ROOT", tmp_path)

    block_a = {
        "title": "Pythagorean theorem",
        "content_latex": "In a right triangle, $a^2 + b^2 = c^2$.",
    }
    block_b = {
        "title": "Pythagoras",
        "content_latex": "For a right triangle: $a^2 + b^2 = c^2$.",
    }

    verdict = llm_judge.judge_theorem_pair(block_a, block_b, use_cache=False)
    assert verdict.verdict == "equivalent"
    assert verdict.confidence == pytest.approx(0.95)
    assert "Pythagoras" in verdict.reasoning


def test_judge_theorem_pair_handles_invalid_verdict(monkeypatch, tmp_path):
    fake_response = '{"verdict": "nonsense", "confidence": 0.5}'
    monkeypatch.setattr(llm_judge, "_call_deepseek", lambda *args, **kwargs: fake_response)
    monkeypatch.setattr(llm_judge._cache, "CACHE_ROOT", tmp_path)

    verdict = llm_judge.judge_theorem_pair(
        {"title": "x", "content_latex": "x"},
        {"title": "y", "content_latex": "y"},
        use_cache=False,
    )
    assert verdict.verdict == "different"


# ---------------------------------------------------------------------------
# NoveltyChecker - short-circuit on IN_MATHLIB
# (DEPRECATED: old pipeline, replaced by src/novelty/orchestrator.check_novelty)
# ---------------------------------------------------------------------------

@pytest.mark.skip(reason="Old NoveltyChecker pipeline removed; update to check_novelty API")
def test_novelty_checker_short_circuit_in_mathlib(monkeypatch):
    fake_match = MathlibMatch(
        lean_name="Nat.add_comm",
        statement="∀ a b, a + b = b + a",
        similarity=0.97,
        url="https://example.org/Nat.add_comm",
    )
    fake_result = MathlibResult(
        found=True, matches=[fake_match], best_similarity=0.97
    )
    monkeypatch.setattr(
        novelty_checker.mathlib_checker,
        "check_in_mathlib",
        lambda block: fake_result,
    )

    # Si la cascada no corta en stage 0, estos fallarian (no deberian llamarse):
    def _should_not_be_called(*args, **kwargs):
        raise AssertionError("Stage > 0 should not run when IN_MATHLIB short-circuits")

    monkeypatch.setattr(
        novelty_checker.arxiv_search,
        "search_semantic_scholar",
        _should_not_be_called,
    )
    monkeypatch.setattr(
        novelty_checker.arxiv_search,
        "search_arxiv",
        _should_not_be_called,
    )

    checker = NoveltyChecker()
    block = {
        "type": "theorem",
        "title": "Commutativity of addition",
        "content_latex": "$a + b = b + a$",
    }
    bv = checker.check_block(block, paper_abstract="abstract")
    assert bv.label == NoveltyLabel.IN_MATHLIB
    assert bv.stage_stopped == 0
    assert bv.closest_match["lean_name"] == "Nat.add_comm"


@pytest.mark.skip(reason="Old NoveltyChecker pipeline removed; update to check_novelty API")
def test_check_paper_recommendation_publishable(monkeypatch):
    """Si todos los bloques son NOVEL la recomendacion es PUBLISHABLE."""
    monkeypatch.setattr(
        novelty_checker.NoveltyChecker,
        "check_block",
        lambda self, block, paper_abstract: novelty_checker.BlockVerdict(
            label=NoveltyLabel.NOVEL,
            verdict="no_candidates",
            stage_stopped=1,
            reasoning="ok",
        ),
    )
    checker = NoveltyChecker()
    pv = checker.check_paper(
        [{"type": "theorem", "title": "T1", "content_latex": "x"}],
        abstract="abs",
    )
    assert pv.recommendation == "PUBLISHABLE"
    assert pv.summary == {"NOVEL": 1}


@pytest.mark.skip(reason="Old NoveltyChecker pipeline removed; update to check_novelty API")
def test_check_paper_recommendation_needs_review(monkeypatch):
    verdicts = iter(
        [
            novelty_checker.BlockVerdict(
                label=NoveltyLabel.NOVEL,
                verdict="x",
                stage_stopped=1,
                reasoning="",
            ),
            novelty_checker.BlockVerdict(
                label=NoveltyLabel.NOT_NOVEL,
                verdict="equivalent",
                stage_stopped=3,
                reasoning="",
            ),
        ]
    )
    monkeypatch.setattr(
        novelty_checker.NoveltyChecker,
        "check_block",
        lambda self, block, paper_abstract: next(verdicts),
    )
    checker = NoveltyChecker()
    pv = checker.check_paper(
        [
            {"type": "theorem", "title": "A", "content_latex": "x"},
            {"type": "theorem", "title": "B", "content_latex": "y"},
        ],
        abstract="abs",
    )
    assert pv.recommendation == "NEEDS REVIEW"
    assert pv.summary == {"NOVEL": 1, "NOT_NOVEL": 1}


@pytest.mark.skip(reason="Old NoveltyChecker pipeline removed; update to check_novelty API")
def test_definitions_are_skipped():
    checker = NoveltyChecker()
    block = {"type": "definition", "content_latex": "A group is..."}
    bv = checker.check_block(block, paper_abstract="abstract")
    assert bv.label == NoveltyLabel.NOVEL
    assert bv.stage_stopped == -1
    assert "definition" in bv.reasoning.lower()
