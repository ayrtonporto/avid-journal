"""Orquestador del pipeline de novedad (Stages 0-3 en v1).

Stage 4 (formalizacion del bloque candidato + arbol de tipos dependientes) y
Stage 5 (comparacion de metodo de prueba) quedan fuera de scope. Tras un
veredicto "equivalent" en Stage 3 devolvemos NOT_NOVEL directamente.

Los parametros `lean_project_path` y `threshold_type_tree` se conservan en
`__init__` por compatibilidad hacia adelante: cuando se implementen los
Stages 4-5 no habra que romper la API.
"""

from __future__ import annotations

import logging
from collections import Counter
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, Iterable, List, Optional

from src.novelty import arxiv_search, block_comparator, llm_judge, mathlib_checker, paper_extractor
from src.novelty.block_comparator import strip_latex_for_query

logger = logging.getLogger(__name__)


class NoveltyLabel(str, Enum):
    NOVEL = "NOVEL"
    NOVEL_METHOD = "NOVEL_METHOD"
    GENERALIZATION = "GENERALIZATION"
    NOT_NOVEL = "NOT_NOVEL"
    IN_MATHLIB = "IN_MATHLIB"


PROVING_TYPES = {"theorem", "lemma", "proposition", "corollary"}


@dataclass
class BlockVerdict:
    label: NoveltyLabel
    verdict: str
    stage_stopped: int
    closest_match: Optional[Dict[str, Any]] = None
    reasoning: str = ""

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["label"] = self.label.value
        return d


@dataclass
class PaperVerdict:
    per_block: List[BlockVerdict] = field(default_factory=list)
    summary: Dict[str, int] = field(default_factory=dict)
    recommendation: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "per_block": [bv.to_dict() for bv in self.per_block],
            "summary": self.summary,
            "recommendation": self.recommendation,
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Prioridad para decidir el "veredicto mas fuerte" entre varios pares.
_VERDICT_PRIORITY = {
    "equivalent": 4,
    "specialization": 3,
    "generalization": 2,
    "different": 1,
}


def _block_query(block: Dict[str, Any]) -> str:
    """Texto corto para search_arxiv: titulo + primer trozo del enunciado.

    Aplica strip_latex_for_query antes de devolver cualquier texto para
    evitar que comandos LaTeX crudos (\\cite{}, \\', \\", ~, etc.) contaminen
    la query y provoquen busquedas irrelevantes.
    """
    title = strip_latex_for_query((block.get("title") or "").strip())
    if title:
        return title
    content = strip_latex_for_query(block.get("content_latex") or "")
    return " ".join(content.split())[:120]


def _serialize_pair(pair: block_comparator.BlockPair) -> Dict[str, Any]:
    return {
        "block_new_label": pair.block_new.get("label"),
        "block_new_title": pair.block_new.get("title"),
        "block_candidate_label": pair.block_candidate.get("label"),
        "block_candidate_title": pair.block_candidate.get("title"),
        "similarity_score": pair.similarity_score,
    }


# ---------------------------------------------------------------------------
# NoveltyChecker
# ---------------------------------------------------------------------------

class NoveltyChecker:
    def __init__(
        self,
        lean_project_path: Optional[str] = None,
        threshold_stage1: float = 0.3,
        threshold_stage2: float = 0.7,
        threshold_type_tree: float = 0.3,
        max_candidates_stage2: int = 5,
        ss_top_k: int = 20,
        arxiv_top_k: int = 10,
    ):
        # lean_project_path y threshold_type_tree no se usan en v1.
        # Se conservan para que Stages 4-5 puedan anadirse sin romper la API.
        self.lean_project_path = lean_project_path
        self.threshold_stage1 = threshold_stage1
        self.threshold_stage2 = threshold_stage2
        self.threshold_type_tree = threshold_type_tree
        self.max_candidates_stage2 = max_candidates_stage2
        self.ss_top_k = ss_top_k
        self.arxiv_top_k = arxiv_top_k

    # ------------------------------------------------------------------
    # API publica
    # ------------------------------------------------------------------

    def check_block(
        self,
        block: Dict[str, Any],
        paper_abstract: str,
        ss_fallback_queries: Optional[Iterable[str]] = None,
        exclude_arxiv_ids: Optional[Iterable[str]] = None,
    ) -> BlockVerdict:
        btype = (block.get("type") or "").lower()

        # Definiciones: no se chequean por novedad en v1.
        if btype == "definition":
            return BlockVerdict(
                label=NoveltyLabel.NOVEL,
                verdict="not_checked",
                stage_stopped=-1,
                reasoning="definitions are not checked for novelty in v1",
            )

        notes: List[str] = []

        # ── Stage 0: Mathlib ─────────────────────────────────────────
        try:
            ml = mathlib_checker.check_in_mathlib(block)
            if ml.found and ml.matches:
                best = ml.matches[0]
                return BlockVerdict(
                    label=NoveltyLabel.IN_MATHLIB,
                    verdict="found_in_mathlib",
                    stage_stopped=0,
                    closest_match={
                        "lean_name": best.lean_name,
                        "statement": best.statement,
                        "similarity": best.similarity,
                        "url": best.url,
                    },
                    reasoning=(
                        f"Leandex match {best.lean_name} (sim={best.similarity:.3f}) "
                        f">= {mathlib_checker.SIMILARITY_THRESHOLD}"
                    ),
                )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Stage 0 failed: %s", exc)
            notes.append(f"stage0_error: {exc}")

        # ── Stage 1: busqueda de candidatos ──────────────────────────
        candidates: List[arxiv_search.PaperCandidate] = []
        try:
            ss = arxiv_search.search_semantic_scholar(
                paper_abstract,
                top_k=self.ss_top_k,
                fallback_queries=ss_fallback_queries,
                exclude_arxiv_ids=exclude_arxiv_ids,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Semantic Scholar failed: %s", exc)
            notes.append(f"semantic_scholar_error: {exc}")
            ss = []

        try:
            ax = arxiv_search.search_arxiv(
                _block_query(block),
                top_k=self.arxiv_top_k,
                reference_text=paper_abstract,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("ArXiv search failed: %s", exc)
            notes.append(f"arxiv_error: {exc}")
            ax = []

        candidates = arxiv_search.combine_and_filter(
            list(ss) + list(ax), threshold=self.threshold_stage1
        )

        if not candidates:
            return BlockVerdict(
                label=NoveltyLabel.NOVEL,
                verdict="no_candidates",
                stage_stopped=1,
                reasoning=(
                    "no candidate papers above stage1 threshold "
                    f"({self.threshold_stage1})"
                    + ("; " + "; ".join(notes) if notes else "")
                ),
            )

        # ── Stage 2: pares similares ─────────────────────────────────
        all_pairs: List[block_comparator.BlockPair] = []
        for cand in candidates[: self.max_candidates_stage2]:
            try:
                cand_blocks = paper_extractor.extract_blocks(cand.arxiv_id)
            except Exception as exc:  # noqa: BLE001
                logger.warning("extract_blocks failed for %s: %s", cand.arxiv_id, exc)
                notes.append(f"extract_error[{cand.arxiv_id}]: {exc}")
                continue
            if not cand_blocks:
                continue
            try:
                pairs = block_comparator.find_similar_pairs(
                    [block], cand_blocks, threshold=self.threshold_stage2
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("find_similar_pairs failed: %s", exc)
                notes.append(f"compare_error[{cand.arxiv_id}]: {exc}")
                continue
            for p in pairs:
                # Anota arxiv_id en el bloque candidato para trazabilidad.
                p.block_candidate.setdefault("_arxiv_id", cand.arxiv_id)
            all_pairs.extend(pairs)

        if not all_pairs:
            return BlockVerdict(
                label=NoveltyLabel.NOVEL,
                verdict="no_similar_blocks",
                stage_stopped=2,
                reasoning=(
                    "no candidate block above stage2 threshold "
                    f"({self.threshold_stage2}) over "
                    f"{min(self.max_candidates_stage2, len(candidates))} candidates"
                    + ("; " + "; ".join(notes) if notes else "")
                ),
            )

        # ── Stage 3: juicio LLM ──────────────────────────────────────
        all_pairs.sort(key=lambda p: p.similarity_score, reverse=True)
        # Limitar el numero de juicios por bloque para acotar coste.
        pairs_to_judge = all_pairs[:5]

        judgements: List[Dict[str, Any]] = []
        for pair in pairs_to_judge:
            try:
                jv = llm_judge.judge_theorem_pair(pair.block_new, pair.block_candidate)
            except Exception as exc:  # noqa: BLE001
                logger.warning("judge_theorem_pair failed: %s", exc)
                notes.append(f"judge_error: {exc}")
                continue
            judgements.append(
                {
                    "pair": pair,
                    "verdict": jv.verdict,
                    "confidence": jv.confidence,
                    "reasoning": jv.reasoning,
                }
            )

        if not judgements:
            return BlockVerdict(
                label=NoveltyLabel.NOVEL,
                verdict="judge_unavailable",
                stage_stopped=3,
                reasoning="LLM judge unavailable; "
                + ("; ".join(notes) if notes else "no successful judgments"),
            )

        # Elegir el juicio mas fuerte
        judgements.sort(
            key=lambda j: (
                _VERDICT_PRIORITY.get(j["verdict"], 0),
                j["confidence"],
            ),
            reverse=True,
        )
        strongest = judgements[0]
        verdict = strongest["verdict"]
        pair = strongest["pair"]
        closest_match = _serialize_pair(pair)
        closest_match["llm_verdict"] = verdict
        closest_match["llm_confidence"] = strongest["confidence"]
        closest_match["llm_reasoning"] = strongest["reasoning"]
        closest_match["arxiv_id"] = pair.block_candidate.get("_arxiv_id")

        if verdict == "equivalent":
            label = NoveltyLabel.NOT_NOVEL  # Stages 4-5 omitidos en v1
            reasoning = (
                f"LLM judged equivalent to {pair.block_candidate.get('title') or '?'} "
                f"in arXiv:{pair.block_candidate.get('_arxiv_id')}"
                " (Stages 4-5 not run in v1)"
            )
        elif verdict == "specialization":
            label = NoveltyLabel.NOT_NOVEL
            reasoning = "LLM judged this block to be a specialization of an existing result"
        elif verdict == "generalization":
            label = NoveltyLabel.GENERALIZATION
            reasoning = "LLM judged this block generalizes an existing result"
        else:  # different
            label = NoveltyLabel.NOVEL
            reasoning = "all LLM judgments returned 'different'"

        if notes:
            reasoning = reasoning + "; " + "; ".join(notes)

        return BlockVerdict(
            label=label,
            verdict=verdict,
            stage_stopped=3,
            closest_match=closest_match,
            reasoning=reasoning,
        )

    def check_paper(
        self, blocks: List[Dict[str, Any]], abstract: str
    ) -> PaperVerdict:
        per_block: List[BlockVerdict] = []
        for blk in blocks:
            try:
                bv = self.check_block(blk, abstract)
            except Exception as exc:  # noqa: BLE001
                logger.exception("check_block failed: %s", exc)
                bv = BlockVerdict(
                    label=NoveltyLabel.NOVEL,
                    verdict="error",
                    stage_stopped=-1,
                    reasoning=f"check_block crashed: {exc}",
                )
            per_block.append(bv)

        counts = Counter(bv.label.value for bv in per_block)
        summary = dict(counts)

        labels = {bv.label for bv in per_block}
        if NoveltyLabel.NOT_NOVEL in labels and len(labels) == 1:
            recommendation = "REDUNDANT"
        elif NoveltyLabel.IN_MATHLIB in labels and labels.issubset(
            {NoveltyLabel.IN_MATHLIB, NoveltyLabel.NOT_NOVEL}
        ):
            recommendation = "REDUNDANT"
        elif NoveltyLabel.NOT_NOVEL in labels or NoveltyLabel.IN_MATHLIB in labels:
            recommendation = "NEEDS REVIEW"
        else:
            recommendation = "PUBLISHABLE"

        return PaperVerdict(
            per_block=per_block,
            summary=summary,
            recommendation=recommendation,
        )
