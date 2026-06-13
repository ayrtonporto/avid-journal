#!/usr/bin/env python3
"""
Smoke test end-to-end del pipeline de novelty check.

Ejecuta cada stage del pipeline de forma explícita e imprime resultados
intermedios con encabezados claros. Los errores por stage se capturan y
se muestra el traceback completo, pero la ejecución continúa.

Uso:
    python scripts/smoke_test.py
    python scripts/smoke_test.py 2309.03764
    python scripts/smoke_test.py 2309.03764 --verbose
    python scripts/smoke_test.py --help

Flags:
    -v, --verbose   Muestra queries exactas enviadas a cada API, JSON crudo de
                    los primeros 3 resultados, lista completa de bloques con sus
                    scores en Stage 2 (umbral=0), prompt completo enviado a
                    Claude y respuesta cruda en Stage 3, y tiempos por
                    sub-operación dentro de cada stage.

Paper por defecto: 2309.03764
  "On the automorphism group of a Johnson graph" (math.GR, ~6 pp)
  Corto, entornos theorem/lemma estándar, LaTeX source disponible en ArXiv.
  Cambiá ARXIV_ID o pasalo como argumento si querés probar con otro paper.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import textwrap
import time
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional

# ── path setup ────────────────────────────────────────────────────────────────
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# ── imports del módulo novelty ────────────────────────────────────────────────
from src.novelty import (
    arxiv_search,
    block_comparator,
    llm_judge,
    mathlib_checker,
    paper_extractor,
)
from src.novelty.block_comparator import strip_latex_for_query
from src.novelty.novelty_checker import (
    BlockVerdict,
    NoveltyChecker,
    NoveltyLabel,
)
from src.novelty.paper_extractor import (
    extract_abstract_from_tex,
    extract_blocks_from_file,
    fetch_abstract,
)

# ── configuración ─────────────────────────────────────────────────────────────

ARXIV_ID = "2309.03764"

# Umbrales idénticos a los defaults de NoveltyChecker para que el veredicto
# final de check_block sea comparable con los resultados por-stage del smoke.
THRESHOLD_STAGE1 = 0.3
THRESHOLD_STAGE2 = 0.7
MAX_CANDIDATES_STAGE2 = 5
SS_TOP_K = 20
ARXIV_TOP_K = 10

# Global verbose flag — se asigna en run() desde el argumento CLI.
VERBOSE: bool = False

_TITLE_PATTERN = re.compile(r"\\title\s*\{(?P<title>.*?)\}", re.DOTALL)


# ── helpers de presentación ───────────────────────────────────────────────────

def header(title: str) -> None:
    line = "=" * 60
    print(f"\n{line}")
    print(f"  {title}")
    print(line)


def subheader(title: str) -> None:
    print(f"\n── {title} ──")


def desc(*lines: str) -> None:
    """Descripción breve del stage — siempre visible, independiente de -v."""
    for line in lines:
        print(f"  {line}")
    print()


def indent(text: str, prefix: str = "    ") -> str:
    return textwrap.indent(str(text), prefix)


def show_block(block: Dict[str, Any], prefix: str = "  ") -> None:
    label = block.get("label") or "(sin label)"
    btype = block.get("type") or "?"
    title = block.get("title") or ""
    content = (block.get("content_latex") or "").strip()[:200]
    if len(block.get("content_latex") or "") > 200:
        content += " [...]"
    print(f"{prefix}label : {label}")
    print(f"{prefix}type  : {btype}")
    if title:
        print(f"{prefix}title : {title}")
    print(f"{prefix}statement (primeros 200 chars):")
    print(indent(content, prefix + "  "))


def stage_error(stage: str, exc: BaseException) -> None:
    print(f"\n  [ERROR en {stage}] {type(exc).__name__}: {exc}")
    print("  Traceback completo:")
    print(textwrap.indent(traceback.format_exc(), "    "))


def vprint(*args, **kwargs) -> None:
    """Imprime solo si --verbose está activo."""
    if VERBOSE:
        print(*args, **kwargs)


def lap(label: str, t0: float) -> float:
    """Imprime tiempo transcurrido (siempre visible). Devuelve perf_counter()."""
    elapsed = time.perf_counter() - t0
    print(f"  ⏱  {label}: {elapsed:.2f}s")
    return time.perf_counter()


def vlap(label: str, t0: float) -> float:
    """Como lap pero solo en verbose — para sub-operaciones granulares."""
    if VERBOSE:
        elapsed = time.perf_counter() - t0
        print(f"  ⏱  [v] {label}: {elapsed:.2f}s")
    return time.perf_counter()


def vraw(title: str, obj: Any, max_chars: int = 700) -> None:
    """Imprime JSON o texto con header, solo en verbose."""
    if not VERBOSE:
        return
    if isinstance(obj, str):
        text = obj
    else:
        text = json.dumps(obj, indent=2, ensure_ascii=False)
    snippet = text[:max_chars]
    if len(text) > max_chars:
        snippet += f"\n    ... [{len(text) - max_chars} chars más]"
    print(f"\n  [V] {title}:")
    print(textwrap.indent(snippet, "    "))


def _extract_title_from_latex(text: str) -> Optional[str]:
    """Extrae un titulo LaTeX simple y lo limpia para usarlo como query."""
    match = _TITLE_PATTERN.search(text or "")
    if not match:
        return None
    title = strip_latex_for_query(match.group("title")).strip()
    return title or None


def _title_fallback_query(arxiv_id: Optional[str], tex_path: Optional[str]) -> Optional[str]:
    """Obtiene un titulo del .tex para reintentar Semantic Scholar si el abstract falla."""
    try:
        if tex_path is not None:
            return _extract_title_from_latex(
                Path(tex_path).read_text(encoding="utf-8", errors="ignore")
            )
        if arxiv_id is not None:
            latex_text = paper_extractor.download_arxiv_latex(arxiv_id)
            return _extract_title_from_latex(latex_text or "")
    except Exception as exc:  # noqa: BLE001
        vprint(f"  [V] No se pudo extraer titulo fallback para SS: {exc}")
    return None


# ── función principal ─────────────────────────────────────────────────────────

def run(
    arxiv_id: Optional[str] = None,
    verbose: bool = False,
    tex_path: Optional[str] = None,
) -> None:
    global VERBOSE
    VERBOSE = verbose

    t_total = time.perf_counter()

    # ════════════════════════════════════════════════════════
    # EXTRACCIÓN
    # ════════════════════════════════════════════════════════
    header("EXTRACCIÓN")

    blocks: Optional[List[Dict[str, Any]]] = None
    t0 = time.perf_counter()

    if tex_path is not None:
        # ── Modo local: leer .tex desde disco ────────────────
        desc(
            "Lee el codigo fuente LaTeX desde un archivo local y extrae los",
            "bloques formalizables: theorem, lemma, proposition, corollary, definition.",
            "El primer bloque de tipo theorem/lemma es el que se somete al pipeline.",
        )
        print(f"  Fuente: archivo local {tex_path}")
        try:
            blocks = extract_blocks_from_file(tex_path)
        except Exception as exc:
            stage_error("EXTRACCIÓN (local)", exc)
            print("\n  Abortando: sin bloques no se puede continuar.")
            return
        lap("extract_blocks_from_file", t0)
    else:
        # ── Modo ArXiv: descargar desde la red ───────────────
        desc(
            "Descarga el codigo fuente LaTeX del paper desde ArXiv y extrae los",
            "bloques formalizables: theorem, lemma, proposition, corollary, definition.",
            "El primer bloque de tipo theorem/lemma es el que se somete al pipeline.",
        )
        print(f"  Paper: arXiv:{arxiv_id}")
        print(f"  Fuente: https://arxiv.org/abs/{arxiv_id}")
        try:
            print("\n  Descargando y parseando LaTeX...")
            blocks = paper_extractor.extract_blocks(arxiv_id, use_cache=False)
        except Exception as exc:
            stage_error("EXTRACCIÓN", exc)
            print("\n  Abortando: sin bloques no se puede continuar.")
            return
        lap("extract_blocks", t0)

    if not blocks:
        print("\n  ⚠️  extract_blocks devolvió lista vacía o None.")
        print("  Posibles causas: el paper no tiene source LaTeX disponible,")
        print("  o no contiene entornos theorem/lemma/definition reconocibles.")
        return

    print(f"\n  Bloques extraídos: {len(blocks)}")

    # Conteo por tipo
    type_counts: Dict[str, int] = {}
    for b in blocks:
        t = (b.get("type") or "unknown").lower()
        type_counts[t] = type_counts.get(t, 0) + 1
    subheader("Distribución por tipo")
    for t, n in sorted(type_counts.items()):
        print(f"    {t:20s} {n}")

    # Listado de labels
    subheader("Listado de bloques")
    for i, b in enumerate(blocks, 1):
        label = b.get("label") or "(sin label)"
        btype = (b.get("type") or "?").ljust(15)
        title = (b.get("title") or "")[:60]
        print(f"    [{i:2d}] {btype} {label}  {title}")

    # Elegir bloque de prueba: primer theorem o lemma
    FORMALIZABLE = ("theorem", "lemma", "proposition", "corollary")
    target_block: Optional[Dict[str, Any]] = None
    for b in blocks:
        if (b.get("type") or "").lower() in FORMALIZABLE:
            target_block = b
            break

    if target_block is None:
        print(f"\n  ⚠️  No se encontró ningún bloque de tipo {FORMALIZABLE}.")
        print("  Probá con otro arxiv_id que tenga teoremas explícitos.")
        return

    subheader("Bloque elegido para el smoke test")
    show_block(target_block)

    # ── Abstract para Stage 1 ────────────────────────────────────────────────
    # Caso arxiv_id: intentar el abstract real (fetch_abstract). Si falla o
    # devuelve vacío, hacer fallback al proxy construido desde los bloques.
    # Caso --tex local: usar el proxy directamente (no hay ArXiv para ese paper).

    def _build_proxy() -> str:
        parts = []
        for b in blocks[:5]:
            piece = strip_latex_for_query(
                (b.get("title") or "") + " " + (b.get("content_latex") or "")
            )
            parts.append(piece.strip())
        return " ".join(parts)[:500]

    if tex_path is None:
        # Modo ArXiv: intentar abstract real primero
        paper_abstract: Optional[str] = None
        t0_abs = time.perf_counter()
        try:
            fetched = fetch_abstract(arxiv_id, use_cache=True)
            if fetched and fetched.strip():
                paper_abstract = fetched.strip()[:500]
                abstract_source = "abstract real (ArXiv)"
            else:
                paper_abstract = _build_proxy()
                abstract_source = "proxy desde bloques (fetch_abstract devolvio vacio)"
        except Exception as exc:
            paper_abstract = _build_proxy()
            abstract_source = f"proxy desde bloques (fetch_abstract fallo: {exc})"
            print(f"\n  [WARN] fetch_abstract fallo, usando proxy: {exc}")
        lap(f"abstract ({abstract_source})", t0_abs)
    else:
        # Modo --tex local: intentar extraer \begin{abstract} del .tex
        real_abstract = extract_abstract_from_tex(tex_path)
        if real_abstract:
            paper_abstract = real_abstract[:500]
            abstract_source = "abstract real del .tex (seccion \\begin{abstract})"
        else:
            paper_abstract = _build_proxy()
            abstract_source = "proxy desde bloques (el .tex no tiene seccion abstract)"

    print(f"\n  Fuente del abstract: {abstract_source}")
    print(f"  Abstract para búsqueda (primeros 150 chars):")
    print(f"    {paper_abstract[:150]} [...]")
    ss_title_fallback = _title_fallback_query(arxiv_id, tex_path)
    if ss_title_fallback:
        vprint(f"\n  [V] Fallback title query para SS: {ss_title_fallback}")

    # ════════════════════════════════════════════════════════
    # STAGE 0 — Mathlib via Leandex
    # ════════════════════════════════════════════════════════
    header("STAGE 0  —  Mathlib (Leandex)")
    desc(
        "Consulta Leandex — índice semántico sobre ~100K declaraciones de Mathlib —",
        "para detectar si el bloque ya existe en la librería estándar de Lean 4.",
        "Si la similitud supera el threshold, el pipeline termina aquí con la etiqueta",
        f"IN_MATHLIB sin correr Stages 1-3. Threshold actual: {mathlib_checker.SIMILARITY_THRESHOLD}.",
    )
    stage0_result = None
    t0 = time.perf_counter()
    try:
        print("  Consultando Leandex...")
        stage0_result = mathlib_checker.check_in_mathlib(target_block, use_cache=False)
        print(f"  found          : {stage0_result.found}")
        print(f"  best_similarity: {stage0_result.best_similarity:.4f}")
        print(f"  threshold      : {mathlib_checker.SIMILARITY_THRESHOLD}")
        if stage0_result.matches:
            subheader("Top matches en Mathlib")
            for i, m in enumerate(stage0_result.matches[:3], 1):
                print(f"    [{i}] {m.lean_name}")
                print(f"         sim={m.similarity:.4f}")
                print(f"         url={m.url}")
                stmt = (m.statement or "")[:120]
                if stmt:
                    print(f"         stmt: {stmt}")
        else:
            print("  Sin matches en Mathlib.")
        if stage0_result.found:
            print(f"\n  ⛔ SHORT-CIRCUIT: bloque encontrado en Mathlib (sim >= threshold).")
            print("  El check_block real devolvería IN_MATHLIB aquí.")
    except Exception as exc:
        stage_error("STAGE 0", exc)
        print("  Continuando con stage0_result=None (asumimos no encontrado).")
    lap("Stage 0 total", t0)

    # ════════════════════════════════════════════════════════
    # STAGE 1 — Búsqueda de candidatos
    # ════════════════════════════════════════════════════════
    header("STAGE 1  —  Búsqueda de candidatos")
    desc(
        "Busca papers candidatos que puedan contener resultados similares al bloque.",
        "Dos fuentes: Semantic Scholar (abstract proxy como query) y ArXiv directo",
        "(título del bloque como query). Los candidatos se combinan, deducan por",
        "arxiv_id y filtran por score mínimo. El score se calcula con MiniLM entre",
        "el abstract proxy del paper nuevo y el abstract de cada candidato.",
        f"Thresholds — stage1: {THRESHOLD_STAGE1}  |  SS top-k: {SS_TOP_K}  |  ArXiv top-k: {ARXIV_TOP_K}",
    )

    ss_results: List[arxiv_search.PaperCandidate] = []
    ax_results: List[arxiv_search.PaperCandidate] = []
    candidates: List[arxiv_search.PaperCandidate] = []

    # Construir query limpia para ArXiv (igual que novelty_checker._block_query)
    block_query = strip_latex_for_query((target_block.get("title") or "").strip())
    if not block_query:
        block_query = strip_latex_for_query(target_block.get("content_latex") or "")
        block_query = " ".join(block_query.split())[:120]

    # ── Semantic Scholar ─────────────────────────────────────
    subheader("Semantic Scholar")
    t0 = time.perf_counter()

    if VERBOSE:
        # En verbose: llamamos a las funciones privadas para capturar raw JSON
        # sin hacer doble llamada HTTP.
        ss_query_str = arxiv_search._truncate_query(paper_abstract)
        vprint(f"  [V] Endpoint : {arxiv_search.SEMANTIC_SCHOLAR_ENDPOINT}")
        vprint(
            f"  [V] Params   : query=<arriba>, limit={SS_TOP_K},"
            f" fields={arxiv_search.SEMANTIC_SCHOLAR_FIELDS}"
        )

        ss_queries = [("abstract proxy", ss_query_str)]
        if ss_title_fallback and ss_title_fallback != ss_query_str:
            ss_queries.append(("title fallback", ss_title_fallback))

        raw_ss_payload: Dict[str, Any] = {"data": []}
        for idx, (query_label, query_text) in enumerate(ss_queries, 1):
            vprint(
                f"\n  [V] Query SS #{idx} ({query_label}, {len(query_text)} chars):"
            )
            vprint(f"      {query_text}")
            t_sub = time.perf_counter()
            try:
                raw_ss_payload = arxiv_search._fetch_semantic_scholar(
                    query_text, SS_TOP_K
                )
            except Exception as exc:
                raw_ss_payload = {"data": [], "error": str(exc)}
            vlap(f"HTTP fetch Semantic Scholar ({query_label})", t_sub)
            raw_papers = raw_ss_payload.get("data") or []
            meta = raw_ss_payload.get("_meta") or {}
            if meta:
                vprint(
                    "  [V] SS meta: "
                    f"status={meta.get('status_code')} "
                    f"total={meta.get('total')} "
                    f"data_len={meta.get('data_len')} "
                    f"used_api_key={meta.get('used_api_key')}"
                )
            if raw_papers or idx == len(ss_queries):
                break
            vprint("  [V] SS devolvio 0 resultados; probando fallback.")

        raw_papers = raw_ss_payload.get("data") or []
        if "error" in raw_ss_payload:
            vprint(f"  [V] SS error: {raw_ss_payload['error']}")
        elif not raw_papers:
            vprint(
                "  [V] SS devolvio 0 resultados reales con HTTP 200; "
                "esto no implica por si solo que la API key sea invalida."
            )

        vprint(f"\n  [V] JSON crudo SS — {len(raw_papers)} entradas. Mostrando primeros 3:")
        for idx, p in enumerate(raw_papers[:3], 1):
            vraw(f"Paper SS #{idx}", p, max_chars=500)

        # Construir candidatos desde el JSON crudo (replica search_semantic_scholar)
        ss_results.extend(arxiv_search._payload_to_candidates(raw_ss_payload))
        if arxiv_id:
            current_aid = arxiv_search._normalize_arxiv_id(arxiv_id)
            ss_results = [
                cand
                for cand in ss_results
                if arxiv_search._normalize_arxiv_id(cand.arxiv_id) != current_aid
            ]

        t_sub = time.perf_counter()
        for cand in ss_results:
            try:
                cand.similarity_score = arxiv_search._cosine_similarity_text(
                    paper_abstract, cand.abstract
                )
            except Exception:
                cand.similarity_score = 0.0
        ss_results.sort(key=lambda c: c.similarity_score, reverse=True)
        vlap("MiniLM scoring SS", t_sub)

    else:
        try:
            print(f"  Query: abstract proxy (top_k={SS_TOP_K})...")
            ss_results = arxiv_search.search_semantic_scholar(
                paper_abstract,
                top_k=SS_TOP_K,
                use_cache=False,
                fallback_queries=[ss_title_fallback] if ss_title_fallback else None,
                exclude_arxiv_ids=[arxiv_id] if arxiv_id else None,
            )
        except Exception as exc:
            stage_error("STAGE 1 / Semantic Scholar", exc)

    print(f"  Resultados con arxiv_id: {len(ss_results)}")
    for c in ss_results[:5]:
        print(f"    {c.arxiv_id}  sim={c.similarity_score:.4f}  {c.title[:60]}")
    if len(ss_results) > 5:
        print(f"    ... y {len(ss_results) - 5} más")
    lap("Semantic Scholar", t0)

    # ── ArXiv directo ────────────────────────────────────────
    subheader("ArXiv directo")
    t0 = time.perf_counter()

    if VERBOSE:
        vprint(f"\n  [V] Query exacta enviada a ArXiv ({len(block_query)} chars):")
        vprint(f"      '{block_query}'")
        vprint(
            f"  [V] Modo: arxiv.Search(sort_by=Relevance,"
            f" max_results={ARXIV_TOP_K})"
        )

        t_sub = time.perf_counter()
        try:
            raw_ax_list = arxiv_search._fetch_arxiv(block_query, ARXIV_TOP_K)
        except Exception as exc:
            raw_ax_list = []
            vprint(f"  [V] ArXiv fetch error: {exc}")
        vlap("HTTP fetch ArXiv", t_sub)

        vprint(
            f"\n  [V] JSON crudo ArXiv — {len(raw_ax_list)} entradas."
            f" Mostrando primeros 3:"
        )
        for idx, p in enumerate(raw_ax_list[:3], 1):
            vraw(f"Paper ArXiv #{idx}", p, max_chars=500)

        # Construir candidatos desde el JSON crudo (replica search_arxiv)
        for entry in raw_ax_list:
            ax_results.append(
                arxiv_search.PaperCandidate(
                    paper_id=entry.get("paper_id", ""),
                    title=entry.get("title", ""),
                    abstract=entry.get("abstract", ""),
                    arxiv_id=entry.get("arxiv_id"),
                    similarity_score=0.0,
                    embedding=None,
                    source="arxiv",
                )
            )

        t_sub = time.perf_counter()
        for cand in ax_results:
            try:
                cand.similarity_score = arxiv_search._cosine_similarity_text(
                    paper_abstract, cand.abstract
                )
            except Exception:
                cand.similarity_score = 0.0
        ax_results.sort(key=lambda c: c.similarity_score, reverse=True)
        vlap("MiniLM scoring ArXiv", t_sub)

    else:
        try:
            print(f"  Query: '{block_query[:80]}'  (top_k={ARXIV_TOP_K})...")
            ax_results = arxiv_search.search_arxiv(
                block_query,
                top_k=ARXIV_TOP_K,
                reference_text=paper_abstract,
                use_cache=False,
            )
        except Exception as exc:
            stage_error("STAGE 1 / ArXiv", exc)

    print(f"  Resultados: {len(ax_results)}")
    for c in ax_results[:5]:
        print(f"    {c.arxiv_id}  sim={c.similarity_score:.4f}  {c.title[:60]}")
    if len(ax_results) > 5:
        print(f"    ... y {len(ax_results) - 5} más")
    lap("ArXiv directo", t0)

    # ── Combinación y filtro ──────────────────────────────────
    subheader("Combinación y filtro")
    t0 = time.perf_counter()
    try:
        candidates = arxiv_search.combine_and_filter(
            list(ss_results) + list(ax_results),
            threshold=THRESHOLD_STAGE1,
        )
        print(f"  Threshold       : {THRESHOLD_STAGE1}")
        print(
            f"  Candidatos totales antes del filtro : "
            f"{len(ss_results) + len(ax_results)}"
        )
        print(f"  Candidatos tras dedup + filtro      : {len(candidates)}")
        if candidates:
            subheader("Candidatos que pasan a Stage 2")
            for i, c in enumerate(candidates[:MAX_CANDIDATES_STAGE2], 1):
                src = f"[{c.source[:2].upper()}]"
                print(
                    f"    [{i}] {src} {c.arxiv_id}  sim={c.similarity_score:.4f}"
                    f"  {c.title[:55]}"
                )
                if VERBOSE:
                    abstract_preview = (c.abstract or "").replace("\n", " ")[:200]
                    vprint(f"         abstract: {abstract_preview}")
        else:
            print(
                "  ⚠️  Sin candidatos — Stage 2 y 3 se saltearían en el pipeline real."
            )
    except Exception as exc:
        stage_error("STAGE 1 / combine_and_filter", exc)
    lap("combine_and_filter", t0)

    # ════════════════════════════════════════════════════════
    # STAGE 2 — Emparejamiento bloque-a-bloque
    # ════════════════════════════════════════════════════════
    header("STAGE 2  —  Emparejamiento bloque-a-bloque (MiniLM)")
    desc(
        "Para cada paper candidato de Stage 1, descarga su LaTeX y extrae sus",
        "bloques (theorem, lemma, etc.). Luego calcula la similitud coseno con",
        "MiniLM L6-v2 (384 dims, embeddings L2-normalizados) entre el bloque nuevo",
        "y cada bloque candidato. Los pares con similitud >= threshold pasan a Stage 3.",
        f"Threshold: {THRESHOLD_STAGE2}  |  MiniLM: rápido (~2ms/bloque en CPU, ~80MB).",
    )

    all_pairs: List[block_comparator.BlockPair] = []

    if not candidates:
        print("  Sin candidatos de Stage 1 — skipping.")
    else:
        # En verbose: mostrar todos los bloques del paper bajo análisis
        if VERBOSE:
            vprint(
                f"\n  [V] Bloques del paper bajo análisis"
                f" ({len(blocks)} total, mostrando todos):"
            )
            vprint(
                f"  [V]  {'type':<13} {'label':<22} content_latex (100 chars)"
            )
            vprint(f"  [V]  {'-'*13} {'-'*22} {'-'*40}")
            for b in blocks:
                btype = (b.get("type") or "?")[:12].ljust(13)
                blabel = (b.get("label") or "(sin label)")[:21].ljust(22)
                content_preview = (b.get("content_latex") or "").replace(
                    "\n", " "
                )[:100]
                vprint(f"  [V]  {btype} {blabel} {content_preview}")

        vprint(f"\n  [V] Threshold usado: {THRESHOLD_STAGE2}")
        print(
            f"\n  Procesando {min(MAX_CANDIDATES_STAGE2, len(candidates))}"
            f" paper(s) candidato(s)..."
        )
        t_stage2 = time.perf_counter()

        for cand in candidates[:MAX_CANDIDATES_STAGE2]:
            subheader(
                f"Candidato: arXiv:{cand.arxiv_id}  —  {cand.title[:55]}"
            )
            cand_blocks: Optional[List[Dict[str, Any]]] = None
            t0 = time.perf_counter()
            try:
                print(f"    Descargando y parseando LaTeX de {cand.arxiv_id}...")
                cand_blocks = paper_extractor.extract_blocks(
                    cand.arxiv_id, use_cache=False
                )
                if not cand_blocks:
                    print("    ⚠️  Sin bloques extraídos — skip.")
                    continue
                print(f"    Bloques extraídos: {len(cand_blocks)}")
            except Exception as exc:
                stage_error(
                    f"STAGE 2 / extract_blocks({cand.arxiv_id})", exc
                )
                continue
            lap("    extract_blocks candidato", t0)

            t0 = time.perf_counter()
            try:
                if VERBOSE:
                    # Calcular TODOS los pares (threshold=0.0) para ver
                    # distribución completa antes de filtrar.
                    all_raw_pairs = block_comparator.find_similar_pairs(
                        [target_block], cand_blocks, threshold=0.0
                    )
                    vlap("    embeddings + cosine sim (umbral=0.0)", t0)

                    vprint(
                        f"\n  [V] Distribución completa de scores —"
                        f" {len(all_raw_pairs)} pares calculados"
                        f" (mostrando primeros 15):"
                    )
                    vprint(
                        f"  [V]  {'score':<8} {'pasa?':<6}"
                        f" {'new_label':<20} {'cand_label':<20} cand_title"
                    )
                    for p in all_raw_pairs[:15]:
                        pasa = "✅ si" if p.similarity_score >= THRESHOLD_STAGE2 else "❌ no"
                        new_lbl = (
                            p.block_new.get("label") or "(sin label)"
                        )[:18]
                        cand_lbl = (
                            p.block_candidate.get("label") or "(sin label)"
                        )[:18]
                        cand_ttl = (
                            p.block_candidate.get("title") or ""
                        )[:30]
                        vprint(
                            f"  [V]  {p.similarity_score:.4f}   {pasa:<6}"
                            f" {new_lbl:<20} {cand_lbl:<20} {cand_ttl}"
                        )
                    if len(all_raw_pairs) > 15:
                        vprint(
                            f"  [V]  ... y {len(all_raw_pairs) - 15} pares más"
                        )

                    pairs = [
                        p
                        for p in all_raw_pairs
                        if p.similarity_score >= THRESHOLD_STAGE2
                    ]

                else:
                    pairs = block_comparator.find_similar_pairs(
                        [target_block], cand_blocks, threshold=THRESHOLD_STAGE2
                    )
                    lap("    embeddings + cosine sim", t0)

                for p in pairs:
                    p.block_candidate.setdefault("_arxiv_id", cand.arxiv_id)
                all_pairs.extend(pairs)

                if pairs:
                    print(
                        f"    Pares con sim >= {THRESHOLD_STAGE2}: {len(pairs)}"
                    )
                    for p in pairs[:3]:
                        cand_label = (
                            p.block_candidate.get("label") or "(sin label)"
                        )
                        cand_title = (
                            p.block_candidate.get("title") or ""
                        )[:50]
                        print(
                            f"      sim={p.similarity_score:.4f}"
                            f"  cand_label={cand_label}  {cand_title}"
                        )
                else:
                    print(f"    Sin pares con sim >= {THRESHOLD_STAGE2}.")

            except Exception as exc:
                stage_error(
                    f"STAGE 2 / find_similar_pairs({cand.arxiv_id})", exc
                )

        lap("Stage 2 total", t_stage2)
        print(f"\n  Total de pares similares encontrados: {len(all_pairs)}")
        if all_pairs:
            all_pairs.sort(key=lambda p: p.similarity_score, reverse=True)
            subheader("Top pares (ordenados por similitud)")
            for i, p in enumerate(all_pairs[:5], 1):
                src_id = p.block_candidate.get("_arxiv_id", "?")
                cand_label = p.block_candidate.get("label") or "(sin label)"
                cand_title = (p.block_candidate.get("title") or "")[:50]
                print(
                    f"    [{i}] sim={p.similarity_score:.4f}"
                    f"  arXiv:{src_id}  {cand_label}  {cand_title}"
                )

    # ════════════════════════════════════════════════════════
    # STAGE 3 — LLM judge
    # ════════════════════════════════════════════════════════
    header("STAGE 3  —  Juicio semántico (Claude)")
    desc(
        "Envía los pares más similares a Claude para un juicio matemático explícito.",
        "El modelo recibe el enunciado completo de ambos bloques y clasifica la relación:",
        "  equivalent     -> mismo resultado matematico (-> NOT_NOVEL en pipeline real)",
        "  specialization -> el bloque nuevo es caso particular del candidato (-> NOT_NOVEL)",
        "  generalization -> el bloque nuevo generaliza al candidato (-> GENERALIZATION)",
        "  different      -> resultados distintos (-> NOVEL)",
        "Se juzgan hasta 5 pares con mayor score de Stage 2. Costo: ~$0.003/par.",
    )

    pairs_to_judge = all_pairs[:5]

    if not pairs_to_judge:
        print("  Sin pares para juzgar — skipping.")
    else:
        print(
            f"  Juzgando {len(pairs_to_judge)} par(es) con"
            f" {llm_judge.DEFAULT_MODEL}..."
        )
        t_stage3 = time.perf_counter()

        for i, pair in enumerate(pairs_to_judge, 1):
            src_id = pair.block_candidate.get("_arxiv_id", "?")
            cand_label = pair.block_candidate.get("label") or "(sin label)"
            subheader(
                f"Par {i}/{len(pairs_to_judge)}"
                f"  —  sim={pair.similarity_score:.4f}"
                f"  cand={src_id}/{cand_label}"
            )
            t0 = time.perf_counter()
            try:
                if VERBOSE:
                    # Reconstruir el prompt que llm_judge enviará a Claude.
                    prompt_text = llm_judge.THEOREM_PROMPT.format(
                        title_new=(
                            pair.block_new.get("title") or "(no title)"
                        ),
                        statement_new=llm_judge._truncate(
                            pair.block_new.get("content_latex")
                        ),
                        title_candidate=(
                            pair.block_candidate.get("title") or "(no title)"
                        ),
                        statement_candidate=llm_judge._truncate(
                            pair.block_candidate.get("content_latex")
                        ),
                    )
                    vraw(
                        f"Prompt completo enviado a Claude ({len(prompt_text)} chars)",
                        prompt_text,
                        max_chars=1500,
                    )

                    # Interceptar _call_claude para capturar la respuesta cruda.
                    raw_resp_holder: List[str] = []
                    _orig = llm_judge._call_claude

                    def _intercepting(p, model, max_tokens=400, _orig=_orig):
                        result = _orig(p, model, max_tokens)
                        raw_resp_holder.append(result)
                        return result

                    llm_judge._call_claude = _intercepting
                    try:
                        jv = llm_judge.judge_theorem_pair(
                            pair.block_new,
                            pair.block_candidate,
                            use_cache=False,
                        )
                    finally:
                        llm_judge._call_claude = _orig

                    if raw_resp_holder:
                        vraw(
                            "Respuesta cruda de Claude",
                            raw_resp_holder[0],
                            max_chars=600,
                        )
                    vprint(f"\n  [V] Veredicto parseado : {jv.verdict}")
                    vprint(f"  [V] Confianza parseada : {jv.confidence:.3f}")

                else:
                    jv = llm_judge.judge_theorem_pair(
                        pair.block_new,
                        pair.block_candidate,
                        use_cache=False,
                    )

                verdict_icon = {
                    "equivalent": "⛔",
                    "specialization": "⚠️",
                    "generalization": "🔼",
                    "different": "✅",
                }.get(jv.verdict, "❓")
                print(f"    verdict    : {verdict_icon} {jv.verdict}")
                print(f"    confidence : {jv.confidence:.3f}")
                print(f"    reasoning  : {jv.reasoning}")

            except Exception as exc:
                stage_error(f"STAGE 3 / par {i}", exc)
            lap(f"    Par {i} (Claude incluido)", t0)

        lap("Stage 3 total", t_stage3)

    # ════════════════════════════════════════════════════════
    # VEREDICTO FINAL — via check_block (caja negra oficial)
    # ════════════════════════════════════════════════════════
    header("VEREDICTO FINAL  —  check_block (pipeline oficial)")
    desc(
        "Llama a NoveltyChecker.check_block() — la caja negra oficial del pipeline.",
        "Repite los stages internamente (puede usar caché poblado por los stages",
        "anteriores del smoke). El resultado aquí es el que vería un usuario real.",
    )
    print("  Llamando a NoveltyChecker.check_block()...")
    print("  (Repite los stages internamente — puede tardar si hay candidatos.)\n")

    checker = NoveltyChecker(
        threshold_stage1=THRESHOLD_STAGE1,
        threshold_stage2=THRESHOLD_STAGE2,
        max_candidates_stage2=MAX_CANDIDATES_STAGE2,
        ss_top_k=SS_TOP_K,
        arxiv_top_k=ARXIV_TOP_K,
    )

    final_verdict: Optional[BlockVerdict] = None
    t0 = time.perf_counter()
    try:
        # NoveltyChecker no expone use_cache=False por parámetro público;
        # los módulos internos usan sus propios defaults (use_cache=True).
        # Para el smoke test esto está bien: si el caché fue poblado en los
        # stages anteriores, check_block lo usará — coherente con un run real.
        final_verdict = checker.check_block(
            target_block,
            paper_abstract=paper_abstract,
            ss_fallback_queries=[ss_title_fallback] if ss_title_fallback else None,
            exclude_arxiv_ids=[arxiv_id] if arxiv_id else None,
        )
    except Exception as exc:
        stage_error("VEREDICTO FINAL / check_block", exc)
    lap("check_block", t0)

    if final_verdict is not None:
        label_icon = {
            NoveltyLabel.NOVEL: "✅ NOVEL",
            NoveltyLabel.NOVEL_METHOD: "🔬 NOVEL_METHOD",
            NoveltyLabel.GENERALIZATION: "🔼 GENERALIZATION",
            NoveltyLabel.NOT_NOVEL: "⛔ NOT_NOVEL",
            NoveltyLabel.IN_MATHLIB: "📚 IN_MATHLIB",
        }.get(final_verdict.label, str(final_verdict.label))

        print(f"\n  Etiqueta      : {label_icon}")
        print(f"  Verdict str   : {final_verdict.verdict}")
        print(f"  Stage stopped : {final_verdict.stage_stopped}")
        print(f"  Reasoning     : {final_verdict.reasoning}")

        if final_verdict.closest_match:
            subheader("Closest match")
            for k, v in final_verdict.closest_match.items():
                v_str = str(v)[:120]
                print(f"    {k:20s}: {v_str}")

    elapsed_total = time.perf_counter() - t_total
    print(f"\n  ⏱  Tiempo total del smoke test: {elapsed_total:.1f}s")
    print()


# ── entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Smoke test end-to-end del pipeline de novelty check.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent(
            """
            Ejemplos:
              python scripts/smoke_test.py
              python scripts/smoke_test.py 2309.03764
              python scripts/smoke_test.py 2309.03764 --verbose
              python scripts/smoke_test.py 2605.02064 -v
              python scripts/smoke_test.py --tex examples/tiny_even_numbers/paper.tex
              python scripts/smoke_test.py --tex path/to/paper.tex --verbose
            """
        ),
    )

    # arxiv_id y --tex son mutuamente excluyentes
    input_group = parser.add_mutually_exclusive_group()
    input_group.add_argument(
        "arxiv_id",
        nargs="?",
        default=None,
        help=f"arXiv ID del paper a analizar (default: {ARXIV_ID})",
    )
    input_group.add_argument(
        "--tex",
        metavar="PATH",
        default=None,
        dest="tex_path",
        help="Ruta a un archivo .tex local (alternativa a arxiv_id).",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        default=False,
        help=(
            "Modo verbose: queries exactas a SS y ArXiv, JSON crudo (primeros 3 "
            "resultados de cada API), abstract truncado por candidato, lista "
            "completa de bloques con scores en Stage 2 (umbral=0), prompt "
            "completo y respuesta cruda de Claude en Stage 3, tiempos por "
            "sub-operacion."
        ),
    )
    args = parser.parse_args()

    if args.tex_path is not None:
        # Modo local
        run(verbose=args.verbose, tex_path=args.tex_path)
    else:
        # Modo ArXiv: aplicar default si no se pasó arxiv_id
        raw_id = args.arxiv_id if args.arxiv_id is not None else ARXIV_ID
        # Normalizar: quitar prefijo "arXiv:" o URL si lo pasaron
        arxiv_id = raw_id.strip()
        for prefix in (
            "arXiv:",
            "arxiv:",
            "https://arxiv.org/abs/",
            "http://arxiv.org/abs/",
        ):
            if arxiv_id.startswith(prefix):
                arxiv_id = arxiv_id[len(prefix):]
                break
        run(arxiv_id=arxiv_id, verbose=args.verbose)
